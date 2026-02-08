"""Main Textual application for skill monitoring."""

from pathlib import Path
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from .models import Session, SkillInvocation
from .reader import DEFAULT_TRACKING_FILE, SessionReader, SkillReader
from .stats import compute_stats
from .watcher import SessionWatcher, SkillWatcher
from .widgets import HistoryTable, LiveFeed, SessionsPanel, StatsPanel


class FilterDialog(ModalScreen[tuple[str, str] | None]):
    """Modal dialog for setting filters."""

    DEFAULT_CSS = """
    FilterDialog {
        align: center middle;
    }

    FilterDialog > Container {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
    }

    FilterDialog .dialog-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    FilterDialog Input {
        width: 100%;
        margin-bottom: 1;
    }

    FilterDialog .button-row {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    FilterDialog Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        skill_filter: str = "",
        session_filter: str = "",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._skill_filter = skill_filter
        self._session_filter = session_filter

    def compose(self) -> ComposeResult:
        with Container():
            yield Label("Filter Invocations", classes="dialog-title")
            yield Label("Skill (partial match):")
            yield Input(
                value=self._skill_filter,
                placeholder="e.g., databricks",
                id="skill-input",
            )
            yield Label("Session ID (prefix):")
            yield Input(
                value=self._session_filter,
                placeholder="e.g., 3aa3643b",
                id="session-input",
            )
            with Horizontal(classes="button-row"):
                yield Button("Apply", variant="primary", id="apply")
                yield Button("Cancel", variant="default", id="cancel")

    @on(Button.Pressed, "#apply")
    def on_apply(self) -> None:
        skill = self.query_one("#skill-input", Input).value.strip()
        session = self.query_one("#session-input", Input).value.strip()
        self.dismiss((skill, session))

    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class SkillsDashboardApp(App):
    """TUI application for monitoring Claude Code skill usage."""

    TITLE = "Claude Skills Dashboard"

    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 2;
        grid-rows: 1fr 1fr;
        grid-columns: 1fr 1fr 1fr;
    }

    #live-feed-container {
        height: 100%;
        border: solid $primary;
        padding: 0 1;
    }

    #sessions-container {
        height: 100%;
        border: solid $secondary;
        padding: 0 1;
    }

    #stats-container {
        height: 100%;
        border: solid $accent;
        padding: 0 1;
    }

    #history-container {
        column-span: 3;
        height: 100%;
        border: solid $primary;
        padding: 0 1;
    }

    .panel-title {
        text-style: bold;
        color: $text;
        background: $surface;
        padding: 0 1;
        margin-bottom: 0;
    }

    #filter-status {
        dock: bottom;
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f", "open_filter", "Filter"),
        Binding("r", "reset_filter", "Reset Filter"),
        Binding("s", "refresh_sessions", "Refresh Sessions"),
        Binding("tab", "focus_next", "Next Panel"),
        Binding("shift+tab", "focus_previous", "Previous Panel"),
    ]

    def __init__(self, file_path: Optional[Path] = None):
        super().__init__()
        self.file_path = file_path or DEFAULT_TRACKING_FILE
        self.reader = SkillReader(self.file_path)
        self.session_reader = SessionReader()
        self.watcher: Optional[SkillWatcher] = None
        self.session_watcher: Optional[SessionWatcher] = None
        self._invocations: list[SkillInvocation] = []
        self._sessions: list[Session] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="live-feed-container"):
            yield Static("Live Feed", classes="panel-title")
            yield LiveFeed(id="live-feed")
        with Vertical(id="sessions-container"):
            yield Static("Sessions  [s]refresh", classes="panel-title")
            yield SessionsPanel(id="sessions-panel")
        with Vertical(id="stats-container"):
            yield Static("Statistics", classes="panel-title")
            yield StatsPanel(id="stats-panel")
        with Vertical(id="history-container"):
            yield Static("History  [f]ilter [r]eset", classes="panel-title")
            yield HistoryTable(id="history-table")
            yield Static("", id="filter-status")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        self._load_initial_data()
        self._start_watcher()
        self._start_session_watcher()

    def _load_initial_data(self) -> None:
        """Load initial data from the tracking file."""
        self._invocations = self.reader.read_all_sources()

        # Update stats
        stats = compute_stats(self._invocations)
        self.query_one("#stats-panel", StatsPanel).update_stats(stats)

        # Load history table
        self.query_one("#history-table", HistoryTable).load_invocations(self._invocations)

        # Load sessions
        self._refresh_sessions()

    def _start_watcher(self) -> None:
        """Start the file watcher for live updates."""
        self.watcher = SkillWatcher(
            file_path=self.file_path,
            callback=self._on_new_invocation,
        )
        self.watcher.start()

    def _start_session_watcher(self) -> None:
        """Start the session watcher for live session updates."""
        self.session_watcher = SessionWatcher(
            callback=self._on_session_change,
            debounce_seconds=1.0,
        )
        self.session_watcher.start()

    def _on_session_change(self) -> None:
        """Handle session changes from the watcher."""
        self.call_from_thread(self._refresh_sessions)

    def _on_new_invocation(self, invocation: SkillInvocation) -> None:
        """Handle a new invocation from the watcher."""
        # Use call_from_thread to safely update UI from watcher thread
        self.call_from_thread(self._handle_new_invocation, invocation)

    def _handle_new_invocation(self, invocation: SkillInvocation) -> None:
        """Handle a new invocation in the main thread."""
        self._invocations.append(invocation)

        # Update live feed
        self.query_one("#live-feed", LiveFeed).add_invocation(invocation)

        # Update history table
        self.query_one("#history-table", HistoryTable).add_invocation(invocation)

        # Update stats
        stats = compute_stats(self._invocations)
        self.query_one("#stats-panel", StatsPanel).update_stats(stats)

    def action_open_filter(self) -> None:
        """Open the filter dialog."""
        history = self.query_one("#history-table", HistoryTable)
        skill, sessions = history.current_filter

        # Show the first session ID in the dialog for manual editing
        session_str = sessions[0] if sessions and len(sessions) == 1 else ""

        def on_dismiss(result: tuple[str, str] | None) -> None:
            if result is not None:
                skill_filter, session_filter = result
                history.set_filter(
                    skill=skill_filter or None,
                    session=session_filter or None,
                )
                self._update_filter_status(skill_filter, session_filter)

        self.push_screen(
            FilterDialog(skill or "", session_str),
            on_dismiss,
        )

    def action_reset_filter(self) -> None:
        """Reset all filters."""
        self.query_one("#history-table", HistoryTable).clear_filter()
        self._update_filter_status("", "")

    def _update_filter_status(self, skill: str, session: str) -> None:
        """Update the filter status display."""
        status = self.query_one("#filter-status", Static)
        if skill or session:
            parts = []
            if skill:
                parts.append(f"skill: {skill}")
            if session:
                parts.append(f"session: {session}")
            status.update(f"Filter: {', '.join(parts)}")
        else:
            status.update("")

    def _refresh_sessions(self) -> None:
        """Refresh the sessions list."""
        self._sessions = self.session_reader.read_all_sessions()
        self.query_one("#sessions-panel", SessionsPanel).load_sessions(self._sessions)

    def action_refresh_sessions(self) -> None:
        """Manually refresh sessions."""
        self._refresh_sessions()

    @on(SessionsPanel.SessionSelected)
    def on_session_selected(self, event: SessionsPanel.SessionSelected) -> None:
        """Handle session selection - filter history by session group."""
        session = event.session
        history = self.query_one("#history-table", HistoryTable)
        # Filter by parent + all child (subagent) session IDs
        history.set_filter(session=session.all_session_ids)
        label = session.short_id
        if session.children:
            label += f" (+{len(session.children)} subs)"
        self._update_filter_status("", label)

    def on_unmount(self) -> None:
        """Clean up on unmount."""
        if self.watcher:
            self.watcher.stop()
        if self.session_watcher:
            self.session_watcher.stop()


def main() -> None:
    """Entry point for the Claude Skills Dashboard application."""
    app = SkillsDashboardApp()
    app.run()


if __name__ == "__main__":
    main()
