# Claude Skills Dashboard

A beautiful TUI (Terminal User Interface) dashboard for monitoring and analyzing Claude Code skill usage in real-time.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- **Live Feed**: Watch skill and agent invocations as they happen in real-time
- **Session Tracking**: Monitor active Claude Code sessions across all projects
- **Agent Tracking**: See subagent spawning events (Explore, pipeline-developer, etc.) parsed directly from session transcripts
- **Sidechain Visibility**: Skills invoked by subagents are marked with `>sub` in the live feed
- **Statistics Panel**: View aggregated usage stats for both skills and agents (top skills + top agents)
- **History Table**: Browse and filter unified skill + agent history with Type/Name/Details columns
- **Keyboard Navigation**: Full keyboard support for efficient navigation

## Screenshots

![Claude Skills Dashboard](gif2_dashboard.gif)

## Requirements

- Python 3.10 or higher
- Claude Code CLI

## Installation

### Quick Install (recommended)

Install with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/malcolndandaro/claude-skills-dashboard/main/setup.sh | bash
```

No hooks or configuration needed. The dashboard reads directly from Claude Code's session JSONL files.

### From Source

```bash
git clone https://github.com/malcolndandaro/claude-skills-dashboard.git
cd claude-skills-dashboard
pip install -e .
```

## Usage

```bash
# Run the dashboard
claude-skills-dashboard
```

### Key Bindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `f` | Open filter dialog |
| `r` | Reset filters |
| `s` | Refresh sessions |
| `Tab` / `Shift+Tab` | Switch between panels |
| `j` / `k` or arrows | Navigate tables |
| `Enter` | Select session (filters history) |

## Data Sources

The dashboard reads from two data sources — no hooks required:

1. **Session JSONL Transcripts** (`~/.claude/projects/*/*.jsonl`):
   - Parses assistant messages for `Skill` and `Task` tool_use blocks
   - Discovers skills invoked by subagents (`projects/*/subagents/agent-*.jsonl`)
   - Tracks agent spawning events (Task tool with subagent type, description)
   - Incremental scanning via byte position tracking (efficient, no re-scanning)

2. **Session Metadata** (`~/.claude/projects/*/sessions-index.json`):
   - Scans all project directories for session information
   - Detects active sessions (modified within last 5 minutes)
   - Shows project name, summary, message count, and timestamps
   - Groups sidechain (subagent) sessions under their parent

## Architecture

```
claude_skills_dashboard/
├── __init__.py          # Package initialization
├── app.py               # Main Textual application
├── models.py            # Pydantic data models
├── reader.py            # Session JSONL parsing and tool scanning
├── stats.py             # Statistics computation
├── watcher.py           # File system monitoring (watchdog)
└── widgets/
    ├── __init__.py
    ├── live_feed.py     # Real-time feed widget
    ├── stats_panel.py   # Statistics display
    ├── sessions_panel.py # Session tracking
    └── history_table.py  # Filterable history table
```

## Dependencies

- [textual](https://textual.textualize.io/) - TUI framework
- [pydantic](https://pydantic.dev/) - Data validation
- [watchdog](https://python-watchdog.readthedocs.io/) - File system monitoring
- [python-dateutil](https://dateutil.readthedocs.io/) - Date parsing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Textual](https://textual.textualize.io/) by Textualize
- Designed for use with [Claude Code](https://claude.ai/claude-code) by Anthropic
