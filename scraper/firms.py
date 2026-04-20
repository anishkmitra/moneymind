"""
Registry of institutional investment managers and their research pages.

Each firm entry defines:
  - name: Display name
  - slug: URL-safe identifier (used for storage paths)
  - research_url: The page listing research/insights
  - scrape_strategy: How to extract article links from the listing page
    - "css": Use CSS selectors to find article links
    - "api": Hit a JSON API endpoint directly
  - selectors: CSS selectors for extracting links/titles/dates from the listing page
  - article_selectors: CSS selectors for extracting content from individual article pages
  - pdf_selectors: CSS selectors for finding PDF download links on article pages (optional)
"""

from dataclasses import dataclass, field


@dataclass
class FirmConfig:
    name: str
    slug: str
    research_url: str
    scrape_strategy: str = "css"
    # For the listing page: find all article links
    link_selector: str = "a"
    link_filter: str = ""  # regex to filter href values
    # For individual article pages
    title_selector: str = "h1"
    date_selector: str = "time"
    body_selector: str = "article"
    pdf_selector: str = "a[href$='.pdf']"
    # Optional API config
    api_url: str = ""
    api_headers: dict = field(default_factory=dict)


# ──────────────────────────────────────────────
# V1 Firm Registry
# ──────────────────────────────────────────────

FIRMS: list[FirmConfig] = [
    FirmConfig(
        name="Citadel Securities",
        slug="citadel-securities",
        research_url="https://www.citadelsecurities.com/news-and-insights/category/market-insights/",
        link_selector="a[href*='/news-and-insights/']",
        link_filter=r"/news-and-insights/(?!category)[\w-]+",
        title_selector="h1",
        date_selector="time, .date, .post-date",
        body_selector="article, .post-content, .entry-content, main",
        pdf_selector="a[href$='.pdf']",
    ),
    FirmConfig(
        name="Bridgewater Associates",
        slug="bridgewater",
        research_url="https://www.bridgewater.com/research-and-insights",
        link_selector="a[href*='/research-and-insights/']",
        link_filter=r"/research-and-insights/[\w-]+",
        title_selector="h1",
        date_selector="time, .date",
        body_selector="article, .content, main",
        pdf_selector="a[href$='.pdf']",
    ),
    FirmConfig(
        name="BlackRock Investment Institute",
        slug="blackrock",
        research_url="https://www.blackrock.com/corporate/insights",
        link_selector="a[href*='/insights/']",
        link_filter=r"/insights/[\w-]+",
        title_selector="h1",
        date_selector="time, .date, .publish-date",
        body_selector="article, .article-content, main",
        pdf_selector="a[href$='.pdf']",
    ),
    FirmConfig(
        name="AQR Capital Management",
        slug="aqr",
        research_url="https://www.aqr.com/Insights/Research",
        link_selector="a[href*='/Insights/']",
        link_filter=r"/Insights/Research/[\w-]+",
        title_selector="h1",
        date_selector="time, .date",
        body_selector="article, .article-body, main",
        pdf_selector="a[href$='.pdf']",
    ),
    FirmConfig(
        name="Two Sigma",
        slug="two-sigma",
        research_url="https://www.twosigma.com/articles/",
        link_selector="a[href*='/articles/']",
        link_filter=r"/articles/[\w-]+",
        title_selector="h1",
        date_selector="time, .date",
        body_selector="article, .post-content, main",
        pdf_selector="a[href$='.pdf']",
    ),
    FirmConfig(
        name="Man Group",
        slug="man-group",
        research_url="https://www.man.com/insights",
        link_selector="a[href*='/insights/']",
        link_filter=r"/insights/[\w-]+",
        title_selector="h1",
        date_selector="time, .date",
        body_selector="article, .article-content, main",
        pdf_selector="a[href$='.pdf']",
    ),
    FirmConfig(
        name="Renaissance Technologies (via public filings)",
        slug="renaissance",
        research_url="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=renaissance+technologies&CIK=&type=13F&dateb=&owner=include&count=10&search_text=&action=getcompany",
        scrape_strategy="css",
        link_selector="a[href*='Archives/edgar']",
        link_filter=r"Archives/edgar",
        title_selector="h1",
        date_selector=".info",
        body_selector="body",
        pdf_selector="a[href$='.pdf'], a[href$='.txt']",
    ),
    FirmConfig(
        name="D.E. Shaw",
        slug="de-shaw",
        research_url="https://www.deshaw.com/articles",
        link_selector="a[href*='/articles/']",
        link_filter=r"/articles/[\w-]+",
        title_selector="h1",
        date_selector="time, .date",
        body_selector="article, .content, main",
        pdf_selector="a[href$='.pdf']",
    ),
    FirmConfig(
        name="JPMorgan Asset Management",
        slug="jpmorgan-am",
        research_url="https://am.jpmorgan.com/us/en/asset-management/institutional/insights/market-insights/",
        link_selector="a[href*='/insights/']",
        link_filter=r"/insights/[\w-]+",
        title_selector="h1",
        date_selector="time, .date",
        body_selector="article, .article-content, main",
        pdf_selector="a[href$='.pdf']",
    ),
    FirmConfig(
        name="Goldman Sachs Asset Management",
        slug="goldman-sachs-am",
        research_url="https://www.gsam.com/content/gsam/us/en/institutions/market-insights.html",
        link_selector="a[href*='/market-insights/']",
        link_filter=r"/market-insights/[\w-]+",
        title_selector="h1",
        date_selector="time, .date",
        body_selector="article, .content, main",
        pdf_selector="a[href$='.pdf']",
    ),
]


def get_firm(slug: str) -> FirmConfig | None:
    """Look up a firm by slug."""
    return next((f for f in FIRMS if f.slug == slug), None)


def list_firms() -> list[str]:
    """Return all firm slugs."""
    return [f.slug for f in FIRMS]
