# DSF Candidates Agent (Unofficial)

An AI-powered assistant for looking up Django Software Foundation (DSF) Board candidate statements.

This is an unofficial tool and should not be used as official election advice.

## Usage

```shell
# Look up a candidate's statement
just ask 2025 "Jeff Triplett"

# Or use uv directly
uv run src/agent.py ask 2025 "Jeff Triplett"
```

## Available Election Years

- 2026
- 2025
- 2024
- 2023

## Available Commands

| Command | Description |
|---------|-------------|
| `just` | List all available commands |
| `just ask <year> "<candidate>"` | Look up a candidate's statement |
| `just web [year]` | Launch the agent as a web chat interface |
| `just debug [year]` | Print the compiled system prompt for debugging (default: 2025) |
| `just demo` | Run a demo looking up Jeff Triplett's 2025 statement |
| `just rebuild-all` | Fetch statements for multiple candidates |
| `just bootstrap` | Install pip and uv |
| `just fmt` | Format code |
| `just lint` | Run pre-commit hooks on all files |
| `just lint-autoupdate` | Update pre-commit hooks to latest versions |

## How It Works

The agent fetches candidate statements from the Django website using Jina.ai's reader API and caches them locally as markdown files. When you look up a candidate, it uses an LLM to extract their specific statement from the cached page.

## Requirements

- Python 3.12+
- OpenAI API key (set `OPENAI_API_KEY` environment variable)

## Installation

```shell
just bootstrap
```
