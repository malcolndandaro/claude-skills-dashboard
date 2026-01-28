"""Live feed widget for streaming skill invocations."""

from textual.widgets import RichLog

from ..models import SkillInvocation


class LiveFeed(RichLog):
    """Live scrolling feed of skill invocations."""

    DEFAULT_CSS = """
    LiveFeed {
        width: 100%;
        height: 100%;
        border: solid $primary;
        background: $surface;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(
            highlight=True,
            markup=True,
            wrap=True,
            max_lines=500,
            **kwargs,
        )

    def add_invocation(self, invocation: SkillInvocation) -> None:
        """Add a new invocation to the feed."""
        time_str = invocation.formatted_time
        skill = invocation.skill
        args = f" [dim]{invocation.args}[/]" if invocation.args else ""

        self.write(f"[dim]{time_str}[/] [bold green]{skill}[/]{args}")

    def add_invocations(self, invocations: list[SkillInvocation]) -> None:
        """Add multiple invocations to the feed."""
        for invocation in invocations:
            self.add_invocation(invocation)
