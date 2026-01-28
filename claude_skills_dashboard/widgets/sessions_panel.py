"""Sessions panel widget for displaying Claude Code sessions."""

from datetime import datetime, timezone

from rich.text import Text
from textual.message import Message
from textual.widgets import DataTable

from ..models import Session


class SessionsPanel(DataTable):
    """DataTable widget for displaying Claude Code sessions."""

    DEFAULT_CSS = """
    SessionsPanel {
        width: 100%;
        height: 100%;
    }
    """

    class SessionSelected(Message):
        """Message sent when a session is selected."""

        def __init__(self, session: Session) -> None:
            self.session = session
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(cursor_type="row", zebra_stripes=True, **kwargs)
        self._sessions: list[Session] = []

    def on_mount(self) -> None:
        """Set up the table columns."""
        self.add_column("Status", key="status", width=6)
        self.add_column("Project", key="project", width=25)
        self.add_column("Summary", key="summary")
        self.add_column("Msgs", key="msgs", width=5)
        self.add_column("Modified", key="modified", width=12)

    def load_sessions(self, sessions: list[Session]) -> None:
        """Load sessions into the table."""
        self._sessions = sessions
        self.clear()

        for session in sessions:
            # Use Text objects for proper styling
            if session.is_active():
                status = Text("●", style="bold green")
            else:
                status = Text("○", style="dim")

            modified = ""
            if session.modified:
                # Show relative time for recent, date for older
                now = datetime.now(timezone.utc)
                delta = now - session.modified
                if delta.total_seconds() < 60:
                    modified = "just now"
                elif delta.total_seconds() < 3600:
                    mins = int(delta.total_seconds() / 60)
                    modified = f"{mins}m ago"
                elif delta.total_seconds() < 86400:
                    hours = int(delta.total_seconds() / 3600)
                    modified = f"{hours}h ago"
                else:
                    # Convert to local time for display
                    local_modified = session.modified.astimezone()
                    modified = local_modified.strftime("%m-%d %H:%M")

            self.add_row(
                status,
                session.project_name[:25],
                session.display_summary,
                str(session.message_count),
                modified,
                key=session.session_id,
            )

    def refresh_sessions(self, sessions: list[Session]) -> None:
        """Refresh the sessions list."""
        self.load_sessions(sessions)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        if event.row_key and event.row_key.value:
            session_id = event.row_key.value
            for session in self._sessions:
                if session.session_id == session_id:
                    self.post_message(self.SessionSelected(session))
                    break

    def get_selected_session(self) -> Session | None:
        """Get the currently selected session."""
        if self.cursor_row is not None and 0 <= self.cursor_row < len(self._sessions):
            return self._sessions[self.cursor_row]
        return None
