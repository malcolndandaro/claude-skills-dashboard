"""History table widget for browsing skill invocations."""

from typing import Optional

from textual.widgets import DataTable

from ..models import SkillInvocation


class HistoryTable(DataTable):
    """Scrollable table of skill invocation history."""

    DEFAULT_CSS = """
    HistoryTable {
        width: 100%;
        height: 100%;
    }
    """

    COLUMNS = [
        ("Timestamp", 18),
        ("Skill", 25),
        ("Session", 12),
        ("Args", 30),
    ]

    def __init__(self, **kwargs):
        super().__init__(
            cursor_type="row",
            zebra_stripes=True,
            **kwargs,
        )
        self._invocations: list[SkillInvocation] = []
        self._filter_skill: Optional[str] = None
        self._filter_session: Optional[str] = None

    def on_mount(self) -> None:
        """Set up table columns when mounted."""
        for name, width in self.COLUMNS:
            self.add_column(name, width=width)

    def load_invocations(self, invocations: list[SkillInvocation]) -> None:
        """Load invocations into the table."""
        self._invocations = invocations
        self._refresh_table()

    def add_invocation(self, invocation: SkillInvocation) -> None:
        """Add a single invocation to the table."""
        self._invocations.append(invocation)
        if self._matches_filter(invocation):
            self._add_row(invocation)

    def _matches_filter(self, invocation: SkillInvocation) -> bool:
        """Check if an invocation matches current filters."""
        if self._filter_skill:
            if self._filter_skill.lower() not in invocation.skill.lower():
                return False
        if self._filter_session:
            if not invocation.session.startswith(self._filter_session):
                return False
        return True

    def _add_row(self, invocation: SkillInvocation) -> None:
        """Add a single row to the table."""
        args_display = invocation.args[:27] + "..." if invocation.args and len(invocation.args) > 30 else (invocation.args or "-")
        self.add_row(
            invocation.formatted_datetime,
            invocation.skill,
            invocation.short_session,
            args_display,
        )

    def _refresh_table(self) -> None:
        """Refresh the table with filtered data."""
        self.clear()
        filtered = [inv for inv in self._invocations if self._matches_filter(inv)]
        # Show in reverse chronological order
        for invocation in reversed(filtered):
            self._add_row(invocation)

    def set_filter(
        self,
        skill: Optional[str] = None,
        session: Optional[str] = None,
    ) -> None:
        """Set filter criteria and refresh table."""
        self._filter_skill = skill
        self._filter_session = session
        self._refresh_table()

    def clear_filter(self) -> None:
        """Clear all filters and refresh table."""
        self._filter_skill = None
        self._filter_session = None
        self._refresh_table()

    @property
    def current_filter(self) -> tuple[Optional[str], Optional[str]]:
        """Return current filter values (skill, session)."""
        return (self._filter_skill, self._filter_session)
