"""Statistics panel widget."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ..models import SkillStats


class StatsPanel(Static):
    """Panel displaying aggregated skill usage statistics."""

    DEFAULT_CSS = """
    StatsPanel {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    StatsPanel .stats-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    StatsPanel .stats-section {
        margin-top: 1;
    }

    StatsPanel .stats-label {
        color: $text-muted;
    }

    StatsPanel .stats-value {
        color: $text;
        text-style: bold;
    }

    StatsPanel .skill-item {
        color: $success;
    }

    StatsPanel .skill-count {
        color: $text-muted;
    }
    """

    def __init__(self, stats: SkillStats | None = None, **kwargs):
        super().__init__(**kwargs)
        self._stats = stats or SkillStats()

    def compose(self) -> ComposeResult:
        yield Static("Statistics", classes="stats-title")
        yield Static(self._format_summary(), id="stats-summary")
        yield Static("", classes="stats-section")
        yield Static("Top Skills:", classes="stats-label")
        yield Static(self._format_top_skills(), id="stats-top-skills")

    def _format_summary(self) -> str:
        """Format the summary statistics."""
        return (
            f"Total: [bold]{self._stats.total_invocations}[/]\n"
            f"Skills: [bold]{self._stats.unique_skills}[/]\n"
            f"Sessions: [bold]{self._stats.unique_sessions}[/]"
        )

    def _format_top_skills(self, max_skills: int = 8) -> str:
        """Format the top skills list."""
        if not self._stats.skill_counts:
            return "[dim]No data[/]"

        lines = []
        for skill, count in self._stats.top_skills[:max_skills]:
            lines.append(f"[green]{skill}[/] [dim]({count})[/]")
        return "\n".join(lines)

    def update_stats(self, stats: SkillStats) -> None:
        """Update the displayed statistics."""
        self._stats = stats
        summary = self.query_one("#stats-summary", Static)
        summary.update(self._format_summary())
        top_skills = self.query_one("#stats-top-skills", Static)
        top_skills.update(self._format_top_skills())
