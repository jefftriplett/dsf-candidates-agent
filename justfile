set dotenv-load := false

export JUST_UNSTABLE := "true"

# List all available commands
@_default:
    just --list

# Look up a DSF Board candidate's statement
@agent YEAR CANDIDATE *OPTS:
    uv --quiet run agent.py {{ YEAR }} "{{ CANDIDATE }}" {{ OPTS }}

# Alias for agent
@ask YEAR CANDIDATE *OPTS:
    just agent {{ YEAR }} "{{ CANDIDATE }}" {{ OPTS }}

# Install pip and uv package management tools
@bootstrap *ARGS:
    pip install --upgrade pip uv

# Run a demo looking up Jeff Triplett's 2025 statement
@demo:
    just ask 2025 "Jeff Triplett"

# Rebuild all candidate statements
@rebuild-all:
    just agent 2025 "Priya Pahwa"
    just agent 2025 "Tom Carrick"
    just agent 2025 "Abigail Afi Gbadago"
    just agent 2025 "Jeff Triplett"
    just agent 2025 "Paolo Melchiorre"
    just agent 2026 "Priya Pahwa"
    just agent 2026 "Ryan Cheley"
    just agent 2026 "Jacob Kaplan-Moss"

# Format code using just's built-in formatter
@fmt:
    just --fmt

# Run pre-commit checks on files
@lint *ARGS="--all-files":
    uv --quiet tool run --with pre-commit-uv pre-commit run {{ ARGS }}
