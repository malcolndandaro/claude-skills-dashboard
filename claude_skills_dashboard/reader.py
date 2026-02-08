"""Session JSONL reader for skill and agent tracking data."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dateutil.parser import parse as parse_datetime

from .models import AgentInvocation, Session, SkillInvocation

DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"


class SessionReader:
    """Reader for Claude Code session data from projects directory."""

    def __init__(self, projects_dir: Optional[Path] = None):
        self.projects_dir = projects_dir or DEFAULT_PROJECTS_DIR

    def _parse_session_entry(self, entry: dict, project_path: str) -> Optional[Session]:
        """Parse a session entry from sessions-index.json."""
        try:
            created = None
            modified = None
            if entry.get("created"):
                created = parse_datetime(entry["created"])

            # Use actual file modification time for more accurate "active" detection
            file_path = entry.get("fullPath")
            if file_path:
                session_file = Path(file_path)
                if session_file.exists():
                    mtime = session_file.stat().st_mtime
                    modified = datetime.fromtimestamp(mtime, tz=timezone.utc)

            # Fall back to metadata if file doesn't exist
            if modified is None and entry.get("modified"):
                modified = parse_datetime(entry["modified"])

            return Session(
                session_id=entry["sessionId"],
                project_path=entry.get("projectPath", project_path),
                summary=entry.get("summary"),
                first_prompt=entry.get("firstPrompt"),
                message_count=entry.get("messageCount", 0),
                created=created,
                modified=modified,
                is_sidechain=entry.get("isSidechain", False),
                file_path=file_path,
            )
        except (KeyError, ValueError):
            return None

    def read_project_sessions(self, project_dir: Path) -> list[Session]:
        """Read sessions from a single project directory."""
        sessions: dict[str, Session] = {}
        project_path = str(project_dir)

        # First, read from sessions-index.json
        index_file = project_dir / "sessions-index.json"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                project_path = data.get("originalPath", str(project_dir))
                for entry in data.get("entries", []):
                    session = self._parse_session_entry(entry, project_path)
                    if session and session.session_id not in sessions:
                        sessions[session.session_id] = session
            except (json.JSONDecodeError, OSError):
                pass

        # Then, scan for unindexed session files (recently created sessions)
        for jsonl_file in project_dir.glob("*.jsonl"):
            session_id = jsonl_file.stem
            if session_id not in sessions:
                # Create a minimal session entry from the file
                try:
                    mtime = jsonl_file.stat().st_mtime
                    modified = datetime.fromtimestamp(mtime, tz=timezone.utc)
                    session = Session(
                        session_id=session_id,
                        project_path=project_path,
                        summary="(new session)",
                        first_prompt=None,
                        message_count=0,
                        created=modified,
                        modified=modified,
                        is_sidechain=False,
                        file_path=str(jsonl_file),
                    )
                    sessions[session_id] = session
                except OSError:
                    pass

        return list(sessions.values())

    def _dedup_sessions(self, raw: list[Session]) -> list[Session]:
        """Deduplicate sessions by session_id, keeping most recently modified."""
        seen: dict[str, Session] = {}
        for session in raw:
            existing = seen.get(session.session_id)
            if existing is None:
                seen[session.session_id] = session
            else:
                existing_mtime = existing.modified or datetime.min.replace(tzinfo=timezone.utc)
                new_mtime = session.modified or datetime.min.replace(tzinfo=timezone.utc)
                if new_mtime > existing_mtime:
                    seen[session.session_id] = session
        return list(seen.values())

    @staticmethod
    def _group_sessions(sessions: list[Session]) -> list[Session]:
        """Group sidechain (subagent) sessions under their parent.

        Matching heuristic: a sidechain belongs to a main session when they
        share the same project_path and the sidechain was created during the
        main session's lifetime (between its created and modified timestamps).
        """
        main_sessions: list[Session] = []
        sidechains: list[Session] = []

        for s in sessions:
            if s.is_sidechain:
                sidechains.append(s)
            else:
                # Reset children in case of re-grouping
                s.children = []
                main_sessions.append(s)

        # Sort main sessions by created time so we can match sidechains
        main_sessions.sort(
            key=lambda s: s.created or datetime.min.replace(tzinfo=timezone.utc),
        )

        for sc in sidechains:
            best_parent: Optional[Session] = None
            best_distance: Optional[float] = None
            sc_created = sc.created or datetime.min.replace(tzinfo=timezone.utc)

            for main in main_sessions:
                if main.project_path != sc.project_path:
                    continue

                m_created = main.created or datetime.min.replace(tzinfo=timezone.utc)
                m_modified = main.modified or datetime.min.replace(tzinfo=timezone.utc)

                # Sidechain created within the main session's time window
                if m_created <= sc_created <= m_modified:
                    distance = abs((sc_created - m_created).total_seconds())
                    if best_distance is None or distance < best_distance:
                        best_parent = main
                        best_distance = distance

            if best_parent is not None:
                best_parent.children.append(sc)
            # If no parent found, the sidechain is treated as a standalone;
            # show it so it doesn't silently disappear.
            else:
                main_sessions.append(sc)

        return main_sessions

    def read_all_sessions(self) -> list[Session]:
        """Read all sessions from all projects, grouped by parent/child."""
        if not self.projects_dir.exists():
            return []

        raw: list[Session] = []
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                raw.extend(self.read_project_sessions(project_dir))

        unique = self._dedup_sessions(raw)
        grouped = self._group_sessions(unique)

        # Sort by modified time (most recent first)
        grouped.sort(
            key=lambda s: s.modified or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return grouped

    def get_active_sessions(self, threshold_seconds: int = 300) -> list[Session]:
        """Get sessions that were modified within the threshold."""
        all_sessions = self.read_all_sessions()
        return [s for s in all_sessions if s.is_active(threshold_seconds)]

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Find a session by its ID (prefix match)."""
        for session in self.read_all_sessions():
            if session.session_id.startswith(session_id):
                return session
            for child in session.children:
                if child.session_id.startswith(session_id):
                    return session
        return None


class SessionToolScanner:
    """Scans session JSONL files for Skill and Task tool invocations.

    Parses assistant messages from session transcripts to find tool_use blocks
    for Skill (skill invocations) and Task (agent spawning) tools.
    Supports incremental scanning via byte position tracking per file.
    """

    def __init__(self, projects_dir: Optional[Path] = None):
        self.projects_dir = projects_dir or DEFAULT_PROJECTS_DIR
        self._file_positions: dict[str, int] = {}

    def _parse_entry(
        self,
        entry: dict,
        session_id: str,
        is_sidechain: bool = False,
        agent_id: Optional[str] = None,
    ) -> list[SkillInvocation | AgentInvocation]:
        """Parse a single JSONL entry for Skill and Task tool invocations."""
        results: list[SkillInvocation | AgentInvocation] = []

        if entry.get("type") != "assistant":
            return results

        message = entry.get("message", {})
        content = message.get("content", [])

        # Extract timestamp from the entry
        timestamp_str = entry.get("timestamp")
        if not timestamp_str:
            return results

        try:
            timestamp = parse_datetime(timestamp_str)
        except (ValueError, TypeError):
            return results

        # Extract cwd from entry metadata or default
        cwd = entry.get("cwd", "")

        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue

            tool_name = block.get("name", "")
            tool_input = block.get("input", {})

            if tool_name == "Skill":
                skill_name = tool_input.get("skill", "")
                if not skill_name:
                    continue
                results.append(
                    SkillInvocation(
                        timestamp=timestamp,
                        session=session_id,
                        skill=skill_name,
                        args=tool_input.get("args"),
                        cwd=cwd,
                        is_sidechain=is_sidechain,
                        agent_id=agent_id,
                    )
                )
            elif tool_name == "Task":
                subagent_type = tool_input.get("subagent_type", "")
                if not subagent_type:
                    continue
                prompt = tool_input.get("prompt", "")
                results.append(
                    AgentInvocation(
                        timestamp=timestamp,
                        session=session_id,
                        subagent_type=subagent_type,
                        description=tool_input.get("description"),
                        prompt=prompt[:100] if prompt else None,
                        cwd=cwd,
                        is_sidechain=is_sidechain,
                        agent_id=agent_id,
                    )
                )

        return results

    def scan_file(
        self,
        file_path: Path,
        session_id: str,
        is_sidechain: bool = False,
        agent_id: Optional[str] = None,
        from_position: int = 0,
    ) -> tuple[list[SkillInvocation | AgentInvocation], int]:
        """Scan a session JSONL file for tool invocations.

        Returns (invocations, new_byte_position).
        """
        results: list[SkillInvocation | AgentInvocation] = []

        if not file_path.exists():
            return results, from_position

        try:
            file_size = file_path.stat().st_size
        except OSError:
            return results, from_position

        # Handle file truncation (file was rewritten/smaller than last position)
        if file_size < from_position:
            from_position = 0

        if file_size == from_position:
            return results, from_position

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                f.seek(from_position)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    invocations = self._parse_entry(
                        entry, session_id, is_sidechain, agent_id
                    )
                    results.extend(invocations)
                new_position = f.tell()
        except OSError:
            return results, from_position

        return results, new_position

    def scan_all(
        self, incremental: bool = True
    ) -> list[SkillInvocation | AgentInvocation]:
        """Scan all session JSONL files for tool invocations.

        Args:
            incremental: If True, only scan new content since last scan.
                If False, reset positions and scan from the beginning.
        """
        if not incremental:
            self._file_positions.clear()

        if not self.projects_dir.exists():
            return []

        results: list[SkillInvocation | AgentInvocation] = []

        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            # Scan parent session files: projects/<project>/*.jsonl
            for jsonl_file in project_dir.glob("*.jsonl"):
                session_id = jsonl_file.stem
                file_key = str(jsonl_file)
                from_pos = self._file_positions.get(file_key, 0)

                invocations, new_pos = self.scan_file(
                    jsonl_file, session_id, is_sidechain=False, from_position=from_pos
                )
                self._file_positions[file_key] = new_pos
                results.extend(invocations)

            # Scan subagent session files:
            # projects/<project>/<session-id>/subagents/agent-*.jsonl
            for agent_file in project_dir.glob("*/subagents/agent-*.jsonl"):
                agent_id = agent_file.stem.removeprefix("agent-")
                # Parent session id from the directory name
                parent_session_id = agent_file.parent.parent.name
                file_key = str(agent_file)
                from_pos = self._file_positions.get(file_key, 0)

                invocations, new_pos = self.scan_file(
                    agent_file,
                    parent_session_id,
                    is_sidechain=True,
                    agent_id=agent_id,
                    from_position=from_pos,
                )
                self._file_positions[file_key] = new_pos
                results.extend(invocations)

        results.sort(key=lambda inv: inv.timestamp)
        return results
