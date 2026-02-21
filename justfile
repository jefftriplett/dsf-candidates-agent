set dotenv-load := false

export JUST_UNSTABLE := "true"

# List all available commands
@_default:
    just --list

# Look up a DSF Board candidate's statement
@ask YEAR CANDIDATE *OPTS:
    uv --quiet run src/agent.py ask {{ YEAR }} "{{ CANDIDATE }}" {{ OPTS }}

# Print the compiled system prompt for debugging
@debug YEAR="2025":
    uv --quiet run src/agent.py debug {{ YEAR }}

# Launch the agent as a web chat interface
@web *ARGS:
    uv --quiet run src/agent.py web {{ ARGS }}

# Install pip and uv package management tools
@bootstrap *ARGS:
    pip install --upgrade pip uv

# Run a demo looking up Jeff Triplett's 2025 statement
@demo:
    just ask 2025 "Jeff Triplett"

# Rebuild all candidate statements
@rebuild-all:
    just ask 2025 "Priya Pahwa"
    just ask 2025 "Tom Carrick"
    just ask 2025 "Abigail Afi Gbadago"
    just ask 2025 "Jeff Triplett"
    just ask 2025 "Paolo Melchiorre"
    just ask 2026 "Priya Pahwa"
    just ask 2026 "Ryan Cheley"
    just ask 2026 "Jacob Kaplan-Moss"

# Format code using just's built-in formatter
@fmt:
    just --fmt

# Run pre-commit hooks on all files
@lint *ARGS:
    uv --quiet tool run prek {{ ARGS }} --all-files

# Update pre-commit hooks to latest versions
@lint-autoupdate:
    uv --quiet tool run prek autoupdate
