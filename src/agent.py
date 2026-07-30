#!/usr/bin/env -S uv --quiet run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx2",
#     "environs",
#     "fastmcp",
#     "pydantic-ai-slim[openai,web]>=2,<3",
#     "rich",
#     "typer",
#     "uvicorn",
# ]
# ///

import time

import httpx2
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
PYDANTIC_AI_MODEL: str = env.str("PYDANTIC_AI_MODEL", default="openai:gpt-5.4-nano")

CACHE_MAX_AGE_HOURS: float = env.float("CACHE_MAX_AGE_HOURS", default=24.0)

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


def cache_is_fresh(filename: Path, max_age_hours: float) -> bool:
    """Return True if the cache file exists and is younger than max_age_hours."""
    if not filename.exists() or max_age_hours <= 0:
        return False

    return (time.time() - filename.stat().st_mtime) < (max_age_hours * 3600)


def fetch_and_cache(
    *,
    url: str,
    cache_file: str,
    timeout: float = 10.0,
    max_age_hours: float = CACHE_MAX_AGE_HOURS,
    refresh: bool = False,
):
    filename = Path(OUTPUT_DIR, cache_file)
    if not refresh and cache_is_fresh(filename, max_age_hours):
        return filename.read_text()

    try:
        response = httpx2.get(f"https://r.jina.ai/{url}", timeout=timeout, follow_redirects=True)
        response.raise_for_status()
    except httpx2.HTTPError as exc:
        if filename.exists():
            console.print(f"[yellow]Could not refresh {filename}: {exc}. Using the cached copy.[/yellow]")
            return filename.read_text()
        raise

    contents = response.text

    filename.write_text(contents)

    return contents


def load_data(year: int, *, refresh: bool = False):
    """Load candidate statements for a specific election year."""
    if year not in CANDIDATE_URLS:
        raise ValueError(f"No candidate data for year {year}. Available years: {list(CANDIDATE_URLS.keys())}")

    statements = fetch_and_cache(
        url=CANDIDATE_URLS[year],
        cache_file=f"dsf-candidates-{year}.md",
        refresh=refresh,
    )
    return {"year": year, "statements": statements}


def get_agent(year: int, *, output_type=Output, refresh: bool = False):
    """Create the DSF candidates agent for a specific election year."""
    data = load_data(year, refresh=refresh)

    agent = Agent(
        model=PYDANTIC_AI_MODEL,
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
    refresh: bool = typer.Option(False, help="Re-fetch the candidate statements, ignoring the cache."),
):
    """Look up a DSF Board candidate's statement by year and name."""
    if year not in CANDIDATE_URLS:
        console.print(f"[red]No candidate data for year {year}.[/red]")
        console.print(f"[yellow]Available years:[/yellow] {', '.join(map(str, sorted(CANDIDATE_URLS.keys())))}")
        raise typer.Exit(1)

    agent = get_agent(year, refresh=refresh)

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
    refresh: bool = typer.Option(False, help="Re-fetch the candidate statements, ignoring the cache."),
):
    """Launch the candidates agent as a web chat interface."""
    if year not in CANDIDATE_URLS:
        console.print(f"[red]No candidate data for year {year}.[/red]")
        console.print(f"[yellow]Available years:[/yellow] {', '.join(map(str, sorted(CANDIDATE_URLS.keys())))}")
        raise typer.Exit(1)

    # output_type=str keeps replies conversational. Pydantic AI v2 rejects None here —
    # it reads it as "no output types provided" and raises UserError.
    agent = get_agent(year, output_type=str, refresh=refresh)
    web_app = agent.to_web()

    console.print(f"[bold green]Starting web interface at http://{host}:{port}[/bold green]")
    uvicorn.run(web_app, host=host, port=port)


@app.command()
def debug(
    year: int = typer.Argument(2025, help="Election year (e.g., 2025)"),
    refresh: bool = typer.Option(False, help="Re-fetch the candidate statements, ignoring the cache."),
):
    """Print the compiled system prompt for debugging."""
    if year not in CANDIDATE_URLS:
        console.print(f"[red]No candidate data for year {year}.[/red]")
        console.print(f"[yellow]Available years:[/yellow] {', '.join(map(str, sorted(CANDIDATE_URLS.keys())))}")
        raise typer.Exit(1)

    data = load_data(year, refresh=refresh)

    console.print("[bold cyan]===== SYSTEM PROMPT =====[/bold cyan]\n")
    console.print(SYSTEM_PROMPT)
    console.print("\n[bold cyan]===== INSTRUCTIONS =====[/bold cyan]\n")
    console.print(f"<election_year>{data['year']}</election_year>")
    console.print(f"\n<candidate_statements_page>\n\n{data['statements']}\n\n</candidate_statements_page>")
    console.print("\n[bold cyan]=========================[/bold cyan]")


@app.command()
def mcp(
    year: int = typer.Option(2025, "--year", "-y", help="Election year (e.g., 2025)"),
    refresh: bool = typer.Option(False, help="Re-fetch the candidate statements, ignoring the cache."),
    transport: str = typer.Option("stdio", help="MCP transport: stdio or http"),
    host: str = "127.0.0.1",
    port: int = 8000,
):
    """Serve this agent as an MCP server so other agents can ask it questions.

    Pydantic AI is an MCP client, not a server, so FastMCP handles the server side.
    """
    from fastmcp import FastMCP

    server = FastMCP("dsf-candidates-agent")
    cached = {}

    def build_agent():
        """Build on first use — loading the documents up front would stall the handshake."""
        if "agent" not in cached:
            cached["agent"] = get_agent(year, refresh=refresh)
        return cached["agent"]

    @server.tool
    async def dsf_candidate_question(question: str) -> Output:
        """Answer a question about DSF Board candidate statements for an election year."""
        result = await build_agent().run(question)
        return result.output

    # stdio transport speaks JSON-RPC on stdout — log to stderr so we don't corrupt it.
    Console(stderr=True).print(f"[bold green]Serving MCP over {transport}[/bold green]")

    if transport == "http":
        server.run(transport="http", host=host, port=port)
    else:
        server.run()


if __name__ == "__main__":
    app()
