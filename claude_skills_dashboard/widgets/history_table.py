"""History table widget for browsing skill and agent invocations."""

from typing import Optional, Union

from textual.widgets import DataTable

from ..models import AgentInvocation, SkillInvocation


class HistoryTable(DataTable):
    """Scrollable table of skill and agent invocation history."""

    DEFAULT_CSS = """
    HistoryTable {
        width: 100%;
        height: 100%;
    }
    """

    COLUMNS = [
        ("Timestamp", 18),
        ("Type", 8),
        ("Name", 25),
        ("Session", 12),
        ("Details", 30),
    ]

    def __init__(self, **kwargs):
        super().__init__(
            cursor_type="row",
            zebra_stripes=True,
            **kwargs,
        )
        self._skill_invocations: list[SkillInvocation] = []
        self._agent_invocations: list[AgentInvocation] = []
        self._filter_skill: Optional[str] = None
        self._filter_sessions: Optional[list[str]] = None

    def on_mount(self) -> None:
        """Set up table columns when mounted."""
        for name, width in self.COLUMNS:
            self.add_column(name, width=width)

    def load_invocations(
        self,
        skills: list[SkillInvocation],
        agents: list[AgentInvocation] | None = None,
    ) -> None:
        """Load skill and agent invocations into the table."""
        self._skill_invocations = skills
        self._agent_invocations = agents or []
        self._refresh_table()

    def add_invocation(self, invocation: SkillInvocation) -> None:
        """Add a single skill invocation to the table."""
        self._skill_invocations.append(invocation)
        if self._matches_skill_filter(invocation):
            self._add_skill_row(invocation)

    def add_agent_invocation(self, invocation: AgentInvocation) -> None:
        """Add a single agent invocation to the table."""
        self._agent_invocations.append(invocation)
        if self._matches_agent_filter(invocation):
            self._add_agent_row(invocation)

    def _matches_skill_filter(self, invocation: SkillInvocation) -> bool:
        """Check if a skill invocation matches current filters."""
        if self._filter_skill:
            if self._filter_skill.lower() not in invocation.skill.lower():
                return False
        if self._filter_sessions:
            if not any(invocation.session.startswith(sid) for sid in self._filter_sessions):
                return False
        return True

    def _matches_agent_filter(self, invocation: AgentInvocation) -> bool:
        """Check if an agent invocation matches current filters."""
        if self._filter_skill:
            if self._filter_skill.lower() not in invocation.subagent_type.lower():
                return False
        if self._filter_sessions:
            if not any(invocation.session.startswith(sid) for sid in self._filter_sessions):
                return False
        return True

    def _type_label(self, inv: Union[SkillInvocation, AgentInvocation]) -> str:
        """Get the type label for a row."""
        if isinstance(inv, AgentInvocation):
            return "Sub" if inv.is_sidechain else "Agent"
        return "Sub" if inv.is_sidechain else "Skill"

    def _add_skill_row(self, invocation: SkillInvocation) -> None:
        """Add a single skill row to the table."""
        details = invocation.args or "-"
        if len(details) > 27:
            details = details[:27] + "..."
        self.add_row(
            invocation.formatted_datetime,
            self._type_label(invocation),
            invocation.skill,
            invocation.short_session,
            details,
        )

    def _add_agent_row(self, invocation: AgentInvocation) -> None:
        """Add a single agent row to the table."""
        details = invocation.description or invocation.prompt or "-"
        if len(details) > 27:
            details = details[:27] + "..."
        self.add_row(
            invocation.formatted_datetime,
            self._type_label(invocation),
            invocation.subagent_type,
            invocation.short_session,
            details,
        )

    def _refresh_table(self) -> None:
        """Refresh the table with filtered data."""
        self.clear()

        # Merge both lists with a sortable key
        merged: list[tuple[SkillInvocation | AgentInvocation, str]] = []
        for inv in self._skill_invocations:
            if self._matches_skill_filter(inv):
                merged.append((inv, "skill"))
        for inv in self._agent_invocations:
            if self._matches_agent_filter(inv):
                merged.append((inv, "agent"))

        # Sort by timestamp descending (newest first)
        merged.sort(key=lambda x: x[0].timestamp, reverse=True)

        for inv, kind in merged:
            if kind == "skill":
                self._add_skill_row(inv)
            else:
                self._add_agent_row(inv)

    def set_filter(
        self,
        skill: Optional[str] = None,
        session: Optional[str | list[str]] = None,
    ) -> None:
        """Set filter criteria and refresh table.

        ``session`` accepts a single ID string or a list of IDs (e.g. parent
        + children) for grouped filtering.
        """
        self._filter_skill = skill
        if session is None:
            self._filter_sessions = None
        elif isinstance(session, list):
            self._filter_sessions = session
        else:
            self._filter_sessions = [session]
        self._refresh_table()

    def clear_filter(self) -> None:
        """Clear all filters and refresh table."""
        self._filter_skill = None
        self._filter_sessions = None
        self._refresh_table()

    @property
    def current_filter(self) -> tuple[Optional[str], Optional[list[str]]]:
        """Return current filter values (skill, sessions)."""
        return (self._filter_skill, self._filter_sessions)
