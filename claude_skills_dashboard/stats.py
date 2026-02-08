"""Statistics and aggregation for skill usage data."""

from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from .models import AgentInvocation, SkillInvocation, SkillStats


def compute_stats(
    invocations: list[SkillInvocation],
    agents: list[AgentInvocation] | None = None,
) -> SkillStats:
    """Compute aggregate statistics from skill and agent invocations."""
    agents = agents or []

    if not invocations and not agents:
        return SkillStats()

    skill_counts = Counter(inv.skill for inv in invocations)
    # Merge sessions from both skills and agents
    all_sessions = [inv.session for inv in invocations] + [a.session for a in agents]
    session_counts = Counter(all_sessions)
    agent_counts = Counter(a.subagent_type for a in agents)

    return SkillStats(
        total_invocations=len(invocations),
        unique_skills=len(skill_counts),
        unique_sessions=len(session_counts),
        skill_counts=dict(skill_counts),
        session_counts=dict(session_counts),
        total_agent_invocations=len(agents),
        agent_counts=dict(agent_counts),
    )


def get_daily_counts(
    invocations: list[SkillInvocation],
) -> dict[str, int]:
    """Get invocation counts grouped by date (YYYY-MM-DD)."""
    daily = Counter(inv.timestamp.strftime("%Y-%m-%d") for inv in invocations)
    return dict(sorted(daily.items()))


def get_hourly_counts(
    invocations: list[SkillInvocation], date: Optional[datetime] = None
) -> dict[int, int]:
    """Get invocation counts grouped by hour (0-23).

    If date is provided, only count invocations from that day.
    """
    if date:
        date_str = date.strftime("%Y-%m-%d")
        filtered = [
            inv for inv in invocations if inv.timestamp.strftime("%Y-%m-%d") == date_str
        ]
    else:
        filtered = invocations

    hourly = Counter(inv.timestamp.hour for inv in filtered)
    return dict(sorted(hourly.items()))


def get_recent_activity(
    invocations: list[SkillInvocation], hours: int = 24
) -> list[SkillInvocation]:
    """Get invocations from the last N hours."""
    cutoff = datetime.now(invocations[0].timestamp.tzinfo if invocations else None) - timedelta(hours=hours)
    return [inv for inv in invocations if inv.timestamp >= cutoff]


def format_stats_text(stats: SkillStats, max_skills: int = 5) -> str:
    """Format statistics as displayable text."""
    lines = [
        f"Total: {stats.total_invocations}",
        f"Skills: {stats.unique_skills}",
        f"Sessions: {stats.unique_sessions}",
        "",
        "Top Skills:",
    ]

    for skill, count in stats.top_skills[:max_skills]:
        lines.append(f"  {skill} ({count})")

    return "\n".join(lines)
