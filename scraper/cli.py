"""
CLI entrypoint for the market research scraper.
"""

import asyncio
import logging
import sys

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from scraper.config import LOG_LEVEL
from scraper.firms import FIRMS, get_firm, list_firms
from scraper.engine import scrape_firm, scrape_all_firms
from scraper.pdf_extract import extract_text_from_pdf
from scraper.summarizer import summarize_article, summarize_batch_digest

console = Console()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@click.group()
def main():
    """Market Research Scraper — institutional investment intelligence."""
    pass


@main.command()
def firms():
    """List all configured firms."""
    table = Table(title="Configured Firms")
    table.add_column("Slug", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Research URL")

    for firm in FIRMS:
        table.add_row(firm.slug, firm.name, firm.research_url)

    console.print(table)


@main.command()
@click.option("--firm", "-f", help="Scrape a specific firm by slug (default: all)")
@click.option("--no-summarize", is_flag=True, help="Skip summarization")
@click.option("--no-store", is_flag=True, help="Skip Supabase storage")
def scrape(firm: str | None, no_summarize: bool, no_store: bool):
    """Scrape new research from configured firms."""
    asyncio.run(_scrape(firm, no_summarize, no_store))


async def _scrape(firm_slug: str | None, no_summarize: bool, no_store: bool):
    # Determine which firms to scrape
    if firm_slug:
        firm = get_firm(firm_slug)
        if not firm:
            console.print(f"[red]Unknown firm: {firm_slug}[/red]")
            console.print(f"Available: {', '.join(list_firms())}")
            sys.exit(1)
        target_firms = [firm]
    else:
        target_firms = FIRMS

    console.print(
        f"[bold]Scraping {len(target_firms)} firm(s)...[/bold]"
    )

    # Get known hashes for dedup (if using storage)
    known_hashes: set[str] = set()
    if not no_store:
        try:
            from scraper.storage import get_known_hashes
            known_hashes = get_known_hashes()
            console.print(f"Found {len(known_hashes)} existing articles in DB")
        except Exception as e:
            console.print(f"[yellow]Supabase not configured, skipping dedup: {e}[/yellow]")
            no_store = True

    # Scrape
    articles = await scrape_all_firms(target_firms, known_hashes)
    console.print(f"\n[green]Scraped {len(articles)} new article(s)[/green]\n")

    if not articles:
        console.print("No new research found.")
        return

    # Summarize + store each article
    summaries_for_digest: list[dict] = []

    for article in articles:
        console.print(f"\n[cyan]── {article.firm_slug}[/cyan]")
        console.print(f"[bold]{article.title}[/bold]")
        console.print(f"URL: {article.url}")
        if article.date:
            console.print(f"Date: {article.date}")
        console.print(f"PDFs found: {len(article.pdf_urls)}")

        # Extract PDF text
        pdf_text = ""
        for local_path in article.pdf_local_paths:
            pdf_text += extract_text_from_pdf(local_path) + "\n\n"

        # Summarize
        summary = ""
        if not no_summarize:
            console.print("[dim]Generating summary...[/dim]")
            firm_config = get_firm(article.firm_slug)
            firm_name = firm_config.name if firm_config else article.firm_slug
            summary = summarize_article(
                title=article.title,
                body_text=article.body_text,
                firm_name=firm_name,
                pdf_text=pdf_text.strip(),
            )
            console.print(Panel(Markdown(summary), title="Summary"))

            summaries_for_digest.append({
                "firm": firm_name,
                "title": article.title,
                "summary": summary,
            })

        # Store in Supabase
        if not no_store:
            try:
                from scraper.storage import save_article
                row_id = save_article(article, summary)
                if row_id:
                    console.print(f"[green]Saved to DB (id: {row_id})[/green]")
            except Exception as e:
                console.print(f"[red]Failed to save: {e}[/red]")

    # Generate cross-firm digest
    if summaries_for_digest and len(summaries_for_digest) > 1:
        console.print("\n[bold]Generating Market Intelligence Digest...[/bold]\n")
        digest = summarize_batch_digest(summaries_for_digest)
        console.print(Panel(Markdown(digest), title="📊 Market Intelligence Digest"))


@main.command()
@click.option("--limit", "-n", default=20, help="Number of articles to show")
def recent(limit: int):
    """Show recently scraped articles from the database."""
    try:
        from scraper.storage import get_recent_articles
    except Exception as e:
        console.print(f"[red]Supabase not configured: {e}[/red]")
        sys.exit(1)

    articles = get_recent_articles(limit)

    if not articles:
        console.print("No articles in database yet. Run 'scraper scrape' first.")
        return

    table = Table(title=f"Recent Articles (last {limit})")
    table.add_column("Date", style="dim")
    table.add_column("Firm", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("PDFs", justify="right")

    for a in articles:
        table.add_row(
            a.get("published_date", "")[:10] or a["scraped_at"][:10],
            a["firm_slug"],
            a["title"][:60],
            str(len(a.get("pdf_storage_paths", []))),
        )

    console.print(table)


@main.command()
@click.argument("hours", default=24, type=int)
def watch(hours: int):
    """Run the scraper on a recurring schedule."""
    import time

    console.print(f"[bold]Running scraper every {hours} hour(s). Ctrl+C to stop.[/bold]\n")

    while True:
        try:
            asyncio.run(_scrape(None, False, False))
        except Exception as e:
            console.print(f"[red]Scrape cycle failed: {e}[/red]")

        console.print(f"\n[dim]Next run in {hours} hour(s)...[/dim]\n")
        time.sleep(hours * 3600)


if __name__ == "__main__":
    main()
