"""Live feed widget for streaming skill and agent invocations."""

from textual.widgets import RichLog

from ..models import AgentInvocation, SkillInvocation


class LiveFeed(RichLog):
    """Live scrolling feed of skill and agent invocations."""

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
        """Add a new skill invocation to the feed."""
        time_str = invocation.formatted_time
        skill = invocation.skill
        args = f" [dim]{invocation.args}[/]" if invocation.args else ""

        if invocation.is_sidechain:
            self.write(
                f"[dim]{time_str}[/] [dim cyan]>sub[/] [bold green]{skill}[/]{args}"
            )
        else:
            self.write(f"[dim]{time_str}[/] [bold green]{skill}[/]{args}")

    def add_agent_invocation(self, invocation: AgentInvocation) -> None:
        """Add a new agent spawning event to the feed."""
        time_str = invocation.formatted_time
        agent_type = invocation.subagent_type
        desc = f" [dim]{invocation.description}[/]" if invocation.description else ""

        if invocation.is_sidechain:
            self.write(
                f"[dim]{time_str}[/] [dim cyan]>sub[/] "
                f"[bold magenta]Agent:{agent_type}[/]{desc}"
            )
        else:
            self.write(
                f"[dim]{time_str}[/] [bold magenta]Agent:{agent_type}[/]{desc}"
            )

    def add_invocations(self, invocations: list[SkillInvocation]) -> None:
        """Add multiple skill invocations to the feed."""
        for invocation in invocations:
            self.add_invocation(invocation)

    def add_agent_invocations(self, invocations: list[AgentInvocation]) -> None:
        """Add multiple agent invocations to the feed."""
        for invocation in invocations:
            self.add_agent_invocation(invocation)
