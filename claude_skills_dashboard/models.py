"""Data models for skill tracking."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Session(BaseModel):
    """Represents a Claude Code session."""

    session_id: str
    project_path: str
    summary: Optional[str] = None
    first_prompt: Optional[str] = None
    message_count: int = 0
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    is_sidechain: bool = False
    file_path: Optional[str] = None
    children: list["Session"] = Field(default_factory=list)

    @property
    def short_id(self) -> str:
        """Return shortened session ID (first 8 chars)."""
        return self.session_id[:8] if len(self.session_id) > 8 else self.session_id

    @property
    def project_name(self) -> str:
        """Return just the project folder name."""
        if not self.project_path:
            return ""
        path = self.project_path.rstrip("/")
        last_component = path.split("/")[-1]
        # Handle encoded directory names (e.g., -Users-username-project-name)
        if last_component.startswith("-"):
            # Decode: replace - with / and get last component
            decoded = last_component.replace("-", "/")
            return decoded.split("/")[-1]
        return last_component

    @property
    def display_summary(self) -> str:
        """Return summary or truncated first prompt."""
        if self.summary:
            return self.summary[:60] + "..." if len(self.summary) > 60 else self.summary
        if self.first_prompt:
            return self.first_prompt[:60] + "..." if len(self.first_prompt) > 60 else self.first_prompt
        return "(no summary)"

    @property
    def all_session_ids(self) -> list[str]:
        """Return this session's ID plus all children's IDs."""
        ids = [self.session_id]
        for child in self.children:
            ids.append(child.session_id)
        return ids

    @property
    def total_message_count(self) -> int:
        """Return message count including all children."""
        return self.message_count + sum(c.message_count for c in self.children)

    def is_active(self, threshold_seconds: int = 300) -> bool:
        """Check if session or any child was modified within threshold."""
        if self.modified:
            delta = datetime.now(self.modified.tzinfo) - self.modified
            if delta.total_seconds() < threshold_seconds:
                return True
        for child in self.children:
            if child.is_active(threshold_seconds):
                return True
        return False


class SkillInvocation(BaseModel):
    """Represents a single skill invocation from a session transcript."""

    timestamp: datetime
    session: str
    skill: str
    args: Optional[str] = None
    cwd: str
    is_sidechain: bool = False
    agent_id: Optional[str] = None

    @property
    def short_session(self) -> str:
        """Return shortened session ID (first 8 chars)."""
        return self.session[:8] if len(self.session) > 8 else self.session

    @property
    def local_timestamp(self) -> datetime:
        """Return timestamp converted to local timezone."""
        if self.timestamp.tzinfo is not None:
            return self.timestamp.astimezone()
        return self.timestamp

    @property
    def formatted_time(self) -> str:
        """Return time formatted as HH:MM:SS in local timezone."""
        return self.local_timestamp.strftime("%H:%M:%S")

    @property
    def formatted_datetime(self) -> str:
        """Return datetime formatted as YYYY-MM-DD HH:MM in local timezone."""
        return self.local_timestamp.strftime("%Y-%m-%d %H:%M")


class AgentInvocation(BaseModel):
    """Represents a subagent spawning event from Task tool usage."""

    timestamp: datetime
    session: str
    subagent_type: str
    description: Optional[str] = None
    prompt: Optional[str] = None
    cwd: str
    is_sidechain: bool = False
    agent_id: Optional[str] = None

    @property
    def short_session(self) -> str:
        """Return shortened session ID (first 8 chars)."""
        return self.session[:8] if len(self.session) > 8 else self.session

    @property
    def local_timestamp(self) -> datetime:
        """Return timestamp converted to local timezone."""
        if self.timestamp.tzinfo is not None:
            return self.timestamp.astimezone()
        return self.timestamp

    @property
    def formatted_time(self) -> str:
        """Return time formatted as HH:MM:SS in local timezone."""
        return self.local_timestamp.strftime("%H:%M:%S")

    @property
    def formatted_datetime(self) -> str:
        """Return datetime formatted as YYYY-MM-DD HH:MM in local timezone."""
        return self.local_timestamp.strftime("%Y-%m-%d %H:%M")


class SkillStats(BaseModel):
    """Aggregated statistics for skill and agent usage."""

    total_invocations: int = 0
    unique_skills: int = 0
    unique_sessions: int = 0
    skill_counts: dict[str, int] = Field(default_factory=dict)
    session_counts: dict[str, int] = Field(default_factory=dict)
    total_agent_invocations: int = 0
    agent_counts: dict[str, int] = Field(default_factory=dict)

    @property
    def top_skills(self) -> list[tuple[str, int]]:
        """Return skills sorted by count descending."""
        return sorted(self.skill_counts.items(), key=lambda x: x[1], reverse=True)

    @property
    def top_agents(self) -> list[tuple[str, int]]:
        """Return agents sorted by count descending."""
        return sorted(self.agent_counts.items(), key=lambda x: x[1], reverse=True)
