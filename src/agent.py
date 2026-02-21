#!/usr/bin/env -S uv --quiet run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx",
#     "environs",
#     "pydantic-ai-slim[openai]",
#     "pydantic-ai-slim[web]",
#     "rich",
#     "typer",
#     "uvicorn",
# ]
# ///

import httpx
import typer
import uvicorn

from environs import env
from pathlib import Path
from pydantic import BaseModel
from pydantic import Field
from pydantic_ai import Agent
from rich.console import Console

console = Console()

OPENAI_API_KEY: str = env.str("OPENAI_API_KEY")
OPENAI_MODEL_NAME: str = env.str("OPENAI_MODEL_NAME", default="gpt-5-mini")

OUTPUT_DIR: Path = Path(__file__).parent / "statements"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# DSF Board Candidate statements URLs by year
CANDIDATE_URLS = {
    2026: "https://www.djangoproject.com/weblog/2025/nov/05/2026-dsf-board-candidates/",
    2025: "https://www.djangoproject.com/weblog/2024/oct/28/2025-dsf-board-candidates/",
    2024: "https://www.djangoproject.com/weblog/2023/nov/09/2024-dsf-board-candidates/",
    2023: "https://www.djangoproject.com/weblog/2022/nov/15/2023-dsf-board-candidates/",
}

SYSTEM_PROMPT = """
<system_context>

You are a Django Software Foundation (DSF) Board election assistant.
Your job is to extract and return a specific candidate's statement from the provided election page.

</system_context>

<behavior_guidelines>

- Find and extract the candidate statement for the requested candidate.
- Return their complete statement as written on the page.
- If the candidate is not found, indicate that they were not a candidate in that year.
- Be accurate and return the statement verbatim.

</behavior_guidelines>
"""


class Output(BaseModel):
    candidate_name: str = Field(description="The full name of the candidate")
    statement: str = Field(description="The candidate's complete statement")
    found: bool = Field(description="Whether the candidate was found in the election year")


def fetch_and_cache(
    *,
    url: str,
    cache_file: str,
    timeout: float = 10.0,
):
    filename = OUTPUT_DIR / cache_file
    if filename.exists():
        return filename.read_text()

    response = httpx.get(f"https://r.jina.ai/{url}", timeout=timeout)
    response.raise_for_status()

    contents = response.text

    filename.write_text(contents)

    return contents


def load_data(year: int):
    """Load candidate statements for a specific election year."""
    if year not in CANDIDATE_URLS:
        raise ValueError(f"No candidate data for year {year}. Available years: {list(CANDIDATE_URLS.keys())}")

    statements = fetch_and_cache(
        url=CANDIDATE_URLS[year],
        cache_file=f"dsf-candidates-{year}.md",
    )
    return {"year": year, "statements": statements}


def get_agent(year: int, *, output_type=Output):
    """Create the DSF candidates agent for a specific election year."""
    data = load_data(year)

    agent = Agent(
        model=OPENAI_MODEL_NAME,
        output_type=output_type,
        system_prompt=SYSTEM_PROMPT,
    )

    @agent.instructions
    def add_election_year() -> str:
        return f"<election_year>{data['year']}</election_year>"

    @agent.instructions
    def add_candidate_statements() -> str:
        return f"<candidate_statements_page>\n\n{data['statements']}\n\n</candidate_statements_page>"

    return agent


def slugify(text: str) -> str:
    """Convert text to a filename-safe slug."""
    return text.lower().replace(" ", "-")


app = typer.Typer(
    help="DSF Candidates Agent - Look up DSF Board candidate statements",
    no_args_is_help=True,
)


@app.command()
def ask(
    year: int = typer.Argument(..., help="Election year (e.g., 2025)"),
    candidate: str = typer.Argument(..., help="Candidate name to look up"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save statement to disk"),
):
    """Look up a DSF Board candidate's statement by year and name."""
    if year not in CANDIDATE_URLS:
        console.print(f"[red]No candidate data for year {year}.[/red]")
        console.print(f"[yellow]Available years:[/yellow] {', '.join(map(str, sorted(CANDIDATE_URLS.keys())))}")
        raise typer.Exit(1)

    agent = get_agent(year)

    result = agent.run_sync(f"Find the candidate statement for: {candidate}")

    if result.output.found:
        console.print(f"[green][bold]{result.output.candidate_name}[/bold][/green] ({year} DSF Board Election)\n")
        console.print(result.output.statement)

        if save:
            filename = OUTPUT_DIR / f"{slugify(result.output.candidate_name)}-{year}.md"
            filename.write_text(f"# {result.output.candidate_name} ({year})\n\n{result.output.statement}\n")
            console.print(f"\n[dim]Saved to {filename}[/dim]")
    else:
        console.print(f"[red]Candidate '{candidate}' not found in {year} election.[/red]")


@app.command()
def web(
    year: int = typer.Argument(2025, help="Election year (e.g., 2025)"),
    host: str = "127.0.0.1",
    port: int = 8080,
):
    """Launch the candidates agent as a web chat interface."""
    if year not in CANDIDATE_URLS:
        console.print(f"[red]No candidate data for year {year}.[/red]")
        console.print(f"[yellow]Available years:[/yellow] {', '.join(map(str, sorted(CANDIDATE_URLS.keys())))}")
        raise typer.Exit(1)

    agent = get_agent(year, output_type=None)
    web_app = agent.to_web()

    console.print(f"[bold green]Starting web interface at http://{host}:{port}[/bold green]")
    uvicorn.run(web_app, host=host, port=port)


@app.command()
def debug(
    year: int = typer.Argument(2025, help="Election year (e.g., 2025)"),
):
    """Print the compiled system prompt for debugging."""
    if year not in CANDIDATE_URLS:
        console.print(f"[red]No candidate data for year {year}.[/red]")
        console.print(f"[yellow]Available years:[/yellow] {', '.join(map(str, sorted(CANDIDATE_URLS.keys())))}")
        raise typer.Exit(1)

    data = load_data(year)

    console.print("[bold cyan]===== SYSTEM PROMPT =====[/bold cyan]\n")
    console.print(SYSTEM_PROMPT)
    console.print("\n[bold cyan]===== INSTRUCTIONS =====[/bold cyan]\n")
    console.print(f"<election_year>{data['year']}</election_year>")
    console.print(f"\n<candidate_statements_page>\n\n{data['statements']}\n\n</candidate_statements_page>")
    console.print("\n[bold cyan]=========================[/bold cyan]")


if __name__ == "__main__":
    app()
