# DSF Candidates Agent

An AI-powered assistant for looking up Django Software Foundation (DSF) Board candidate statements.

## Usage

```shell
# Look up a candidate's statement
just agent 2025 "Jeff Triplett"

# Or use the ask alias
just ask 2026 "Paolo Melchiorre"

# Direct script usage
uv run agent.py 2025 "Jacob Kaplan-Moss"
```

## Available Election Years

- 2026
- 2025
- 2024
- 2023

## Requirements

- Python 3.12+
- OpenAI API key (set `OPENAI_API_KEY` environment variable)

## Installation

```shell
just bootstrap
```

## How It Works

The agent fetches candidate statements from the Django website using Jina.ai's reader API and caches them locally as markdown files. When you look up a candidate, it uses an LLM to extract their specific statement from the cached page.

## Disclaimer

This is an unofficial tool and should not be used as official election advice.
