"""
Supabase integration for persisting scraped research.

Tables required in Supabase:
  - articles: metadata + summaries
  - Storage bucket: "research-pdfs" for PDF files

Run the SQL in supabase_schema.sql to set up the tables.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from supabase import create_client, Client

from scraper.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from scraper.engine import ScrapedArticle

logger = logging.getLogger(__name__)

_client: Client | None = None
BUCKET_NAME = "research-pdfs"


def _get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env"
            )
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client


def get_known_hashes() -> set[str]:
    """Fetch all content hashes already stored, for deduplication."""
    client = _get_client()
    result = client.table("articles").select("content_hash").execute()
    return {row["content_hash"] for row in result.data}


def save_article(article: ScrapedArticle, summary: str) -> str | None:
    """
    Save a scraped article to Supabase.
    Returns the inserted row ID, or None on failure.
    """
    client = _get_client()

    row = {
        "firm_slug": article.firm_slug,
        "url": article.url,
        "title": article.title,
        "published_date": article.date or None,
        "body_text": article.body_text[:10000],  # Store first 10k chars
        "summary": summary,
        "content_hash": article.content_hash,
        "pdf_urls": article.pdf_urls,
        "pdf_storage_paths": [],
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }

    # Upload PDFs to Supabase Storage
    storage_paths = []
    for local_path_str in article.pdf_local_paths:
        local_path = Path(local_path_str)
        if local_path.exists():
            storage_path = f"{article.firm_slug}/{local_path.name}"
            try:
                with open(local_path, "rb") as f:
                    client.storage.from_(BUCKET_NAME).upload(
                        storage_path,
                        f.read(),
                        file_options={"content-type": "application/pdf"},
                    )
                storage_paths.append(storage_path)
                logger.info(f"Uploaded PDF to storage: {storage_path}")
            except Exception as e:
                # May already exist
                if "Duplicate" in str(e) or "already exists" in str(e):
                    storage_paths.append(storage_path)
                else:
                    logger.warning(f"Failed to upload PDF: {e}")

    row["pdf_storage_paths"] = storage_paths

    try:
        result = client.table("articles").insert(row).execute()
        row_id = result.data[0]["id"] if result.data else None
        logger.info(f"Saved article: {article.title} (id={row_id})")
        return row_id
    except Exception as e:
        logger.error(f"Failed to save article '{article.title}': {e}")
        return None


def get_recent_articles(limit: int = 20) -> list[dict]:
    """Fetch the most recent articles."""
    client = _get_client()
    result = (
        client.table("articles")
        .select("*")
        .order("scraped_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def get_pdf_url(storage_path: str) -> str:
    """Get a signed URL to download a PDF from Supabase Storage."""
    client = _get_client()
    result = client.storage.from_(BUCKET_NAME).create_signed_url(
        storage_path, expires_in=3600
    )
    return result["signedURL"]
