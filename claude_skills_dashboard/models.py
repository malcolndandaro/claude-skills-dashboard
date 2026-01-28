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

    def is_active(self, threshold_seconds: int = 300) -> bool:
        """Check if session was modified within threshold (default 5 min)."""
        if not self.modified:
            return False
        delta = datetime.now(self.modified.tzinfo) - self.modified
        return delta.total_seconds() < threshold_seconds


class SkillInvocation(BaseModel):
    """Represents a single skill invocation from the tracking log."""

    timestamp: datetime
    session: str
    skill: str
    args: Optional[str] = None
    cwd: str

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
    """Aggregated statistics for skill usage."""

    total_invocations: int = 0
    unique_skills: int = 0
    unique_sessions: int = 0
    skill_counts: dict[str, int] = Field(default_factory=dict)
    session_counts: dict[str, int] = Field(default_factory=dict)

    @property
    def top_skills(self) -> list[tuple[str, int]]:
        """Return skills sorted by count descending."""
        return sorted(self.skill_counts.items(), key=lambda x: x[1], reverse=True)
