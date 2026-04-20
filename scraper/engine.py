"""
Core scraping engine.

Visits each firm's research listing page, discovers new articles/PDFs,
downloads them, and returns structured results.
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx
from playwright.async_api import async_playwright, Page, Browser

from scraper.config import DOWNLOADS_DIR, MAX_CONCURRENT_SCRAPES
from scraper.firms import FirmConfig

logger = logging.getLogger(__name__)


@dataclass
class ScrapedArticle:
    """A single scraped research article."""
    firm_slug: str
    url: str
    title: str
    date: str
    body_text: str
    pdf_urls: list[str]
    pdf_local_paths: list[str]
    content_hash: str  # SHA-256 of body_text for dedup


async def _extract_article_links(page: Page, firm: FirmConfig) -> list[str]:
    """From a firm's listing page, extract all article URLs."""
    await page.goto(firm.research_url, wait_until="networkidle", timeout=30000)
    # Wait a bit for JS-rendered content
    await page.wait_for_timeout(2000)

    elements = await page.query_selector_all(firm.link_selector)
    urls: list[str] = []

    for el in elements:
        href = await el.get_attribute("href")
        if not href:
            continue
        full_url = urljoin(firm.research_url, href)
        if firm.link_filter and not re.search(firm.link_filter, full_url):
            continue
        if full_url not in urls:
            urls.append(full_url)

    logger.info(f"[{firm.slug}] Found {len(urls)} article links")
    return urls


async def _scrape_article(page: Page, firm: FirmConfig, url: str) -> ScrapedArticle | None:
    """Scrape a single article page for content and PDFs."""
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1500)
    except Exception as e:
        logger.warning(f"[{firm.slug}] Failed to load {url}: {e}")
        return None

    # Extract title
    title = ""
    for selector in firm.title_selector.split(", "):
        el = await page.query_selector(selector.strip())
        if el:
            title = (await el.inner_text()).strip()
            break
    if not title:
        title = await page.title()

    # Extract date
    date = ""
    for selector in firm.date_selector.split(", "):
        el = await page.query_selector(selector.strip())
        if el:
            date = (await el.inner_text()).strip()
            # Also try datetime attribute
            if not date:
                date = await el.get_attribute("datetime") or ""
            break

    # Extract body text
    body_text = ""
    for selector in firm.body_selector.split(", "):
        el = await page.query_selector(selector.strip())
        if el:
            body_text = (await el.inner_text()).strip()
            break
    if not body_text:
        body_text = await page.inner_text("body")

    # Truncate very long body text (we'll summarize anyway)
    if len(body_text) > 50000:
        body_text = body_text[:50000]

    # Find PDF links
    pdf_urls: list[str] = []
    pdf_elements = await page.query_selector_all(firm.pdf_selector)
    for el in pdf_elements:
        href = await el.get_attribute("href")
        if href:
            pdf_urls.append(urljoin(url, href))

    content_hash = hashlib.sha256(body_text.encode()).hexdigest()

    return ScrapedArticle(
        firm_slug=firm.slug,
        url=url,
        title=title,
        date=date,
        body_text=body_text,
        pdf_urls=pdf_urls,
        pdf_local_paths=[],
        content_hash=content_hash,
    )


async def download_pdf(url: str, firm_slug: str) -> Path | None:
    """Download a PDF to the local downloads directory."""
    firm_dir = DOWNLOADS_DIR / firm_slug
    firm_dir.mkdir(parents=True, exist_ok=True)

    # Use URL hash as filename to avoid collisions
    filename = hashlib.md5(url.encode()).hexdigest() + ".pdf"
    filepath = firm_dir / filename

    if filepath.exists():
        logger.debug(f"PDF already downloaded: {filepath}")
        return filepath

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            filepath.write_bytes(resp.content)
            logger.info(f"Downloaded PDF: {filepath}")
            return filepath
    except Exception as e:
        logger.warning(f"Failed to download PDF {url}: {e}")
        return None


async def scrape_firm(
    firm: FirmConfig,
    known_hashes: set[str] | None = None,
    browser: Browser | None = None,
) -> list[ScrapedArticle]:
    """
    Scrape all new research articles from a single firm.

    Args:
        firm: The firm configuration.
        known_hashes: Set of content hashes already in the DB (for dedup).
        browser: Reuse an existing browser instance, or launch a new one.
    """
    known_hashes = known_hashes or set()
    owns_browser = browser is None

    pw = None
    if owns_browser:
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)

    articles: list[ScrapedArticle] = []
    try:
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        # Step 1: Get article links from listing page
        article_urls = await _extract_article_links(page, firm)

        # Step 2: Scrape each article
        for url in article_urls:
            article = await _scrape_article(page, firm, url)
            if article is None:
                continue
            if article.content_hash in known_hashes:
                logger.debug(f"[{firm.slug}] Skipping duplicate: {article.title}")
                continue

            # Step 3: Download any PDFs
            for pdf_url in article.pdf_urls:
                local_path = await download_pdf(pdf_url, firm.slug)
                if local_path:
                    article.pdf_local_paths.append(str(local_path))

            articles.append(article)
            logger.info(f"[{firm.slug}] Scraped: {article.title}")

        await context.close()
    finally:
        if owns_browser and browser:
            await browser.close()
        if pw:
            await pw.stop()

    return articles


async def scrape_all_firms(
    firms: list[FirmConfig],
    known_hashes: set[str] | None = None,
) -> list[ScrapedArticle]:
    """Scrape research from all configured firms."""
    import asyncio

    known_hashes = known_hashes or set()
    all_articles: list[ScrapedArticle] = []

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)

    try:
        # Process firms with limited concurrency
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)

        async def _scrape_with_limit(firm: FirmConfig):
            async with semaphore:
                return await scrape_firm(firm, known_hashes, browser)

        results = await asyncio.gather(
            *[_scrape_with_limit(f) for f in firms],
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[{firms[i].slug}] Scrape failed: {result}")
            else:
                all_articles.extend(result)
    finally:
        await browser.close()
        await pw.stop()

    logger.info(f"Total new articles scraped: {len(all_articles)}")
    return all_articles
