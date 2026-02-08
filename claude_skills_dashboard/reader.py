"""JSONL file reader for skill tracking data."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from dateutil.parser import parse as parse_datetime

from .models import Session, SkillInvocation

TRACKING_FILENAME = "skill-tracking.jsonl"
DEFAULT_TRACKING_FILE = Path.home() / ".claude" / TRACKING_FILENAME
DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def discover_tracking_files(projects_dir: Optional[Path] = None) -> list[Path]:
    """Find all project-level skill-tracking.jsonl files.

    Scans ~/.claude/projects/ for original project paths, then checks each
    for a .claude/skill-tracking.jsonl file.
    """
    projects_dir = projects_dir or DEFAULT_PROJECTS_DIR
    paths: list[Path] = []
    if not projects_dir.exists():
        return paths

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        index_file = project_dir / "sessions-index.json"
        if not index_file.exists():
            continue
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            original_path = data.get("originalPath")
            if original_path:
                tracking = Path(original_path) / ".claude" / TRACKING_FILENAME
                if tracking.exists() and tracking not in paths:
                    paths.append(tracking)
        except (json.JSONDecodeError, OSError):
            continue

    return paths


class SkillReader:
    """Reader for skill-tracking.jsonl files."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or DEFAULT_TRACKING_FILE

    def _parse_line(self, line: str) -> Optional[SkillInvocation]:
        """Parse a single JSONL line into a SkillInvocation."""
        line = line.strip()
        if not line:
            return None
        try:
            data = json.loads(line)
            return SkillInvocation(**data)
        except (json.JSONDecodeError, ValueError):
            return None

    def _read_file(self, path: Path) -> list[SkillInvocation]:
        """Read all invocations from a single tracking file."""
        if not path.exists():
            return []
        invocations = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                invocation = self._parse_line(line)
                if invocation:
                    invocations.append(invocation)
        return invocations

    def read_all(self) -> list[SkillInvocation]:
        """Read all invocations from the tracking file."""
        return self._read_file(self.file_path)

    def read_all_sources(self) -> list[SkillInvocation]:
        """Read invocations from the primary file and all project-level files.

        Merges user-level and project-level tracking, sorted by timestamp.
        """
        invocations = self.read_all()

        for path in discover_tracking_files():
            if path.resolve() != self.file_path.resolve():
                invocations.extend(self._read_file(path))

        invocations.sort(key=lambda inv: inv.timestamp)
        return invocations

    def read_since(self, since: datetime) -> list[SkillInvocation]:
        """Read invocations since a given timestamp."""
        all_invocations = self.read_all()
        return [inv for inv in all_invocations if inv.timestamp >= since]

    def filter_by_skill(
        self, skill_name: str, invocations: Optional[list[SkillInvocation]] = None
    ) -> list[SkillInvocation]:
        """Filter invocations by skill name (case-insensitive partial match)."""
        if invocations is None:
            invocations = self.read_all()
        skill_lower = skill_name.lower()
        return [inv for inv in invocations if skill_lower in inv.skill.lower()]

    def filter_by_session(
        self, session_id: str, invocations: Optional[list[SkillInvocation]] = None
    ) -> list[SkillInvocation]:
        """Filter invocations by session ID (prefix match)."""
        if invocations is None:
            invocations = self.read_all()
        return [inv for inv in invocations if inv.session.startswith(session_id)]

    def tail(self, n: int = 10) -> list[SkillInvocation]:
        """Return the last N invocations."""
        all_invocations = self.read_all()
        return all_invocations[-n:] if len(all_invocations) >= n else all_invocations

    def iter_from_position(self, position: int = 0) -> Iterator[tuple[int, SkillInvocation]]:
        """Iterate over invocations starting from a byte position.

        Yields tuples of (new_position, invocation).
        Useful for watching file changes.
        """
        if not self.file_path.exists():
            return

        with open(self.file_path, "r", encoding="utf-8") as f:
            f.seek(position)
            while True:
                line = f.readline()
                if not line:
                    break
                invocation = self._parse_line(line)
                if invocation:
                    yield f.tell(), invocation

    def get_file_size(self) -> int:
        """Get the current file size in bytes."""
        if not self.file_path.exists():
            return 0
        return self.file_path.stat().st_size


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

    def read_all_sessions(self) -> list[Session]:
        """Read all sessions from all projects."""
        if not self.projects_dir.exists():
            return []

        seen: dict[str, Session] = {}
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                for session in self.read_project_sessions(project_dir):
                    existing = seen.get(session.session_id)
                    if existing is None:
                        seen[session.session_id] = session
                    else:
                        # Keep the entry with the most recent modified time
                        existing_mtime = existing.modified or datetime.min.replace(tzinfo=timezone.utc)
                        new_mtime = session.modified or datetime.min.replace(tzinfo=timezone.utc)
                        if new_mtime > existing_mtime:
                            seen[session.session_id] = session

        sessions = list(seen.values())

        # Sort by modified time (most recent first)
        sessions.sort(key=lambda s: s.modified or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return sessions

    def get_active_sessions(self, threshold_seconds: int = 300) -> list[Session]:
        """Get sessions that were modified within the threshold."""
        all_sessions = self.read_all_sessions()
        return [s for s in all_sessions if s.is_active(threshold_seconds)]

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Find a session by its ID (prefix match)."""
        for session in self.read_all_sessions():
            if session.session_id.startswith(session_id):
                return session
        return None
