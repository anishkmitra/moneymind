"""
Claude-powered research summarization.
"""

import logging

import anthropic

from scraper.config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = """\
You are an expert financial research analyst. Your job is to summarize \
institutional investment research reports concisely and accurately.

For each report, produce:
1. **Key Thesis** (1-2 sentences): The main argument or finding.
2. **Market View**: Bullish / Bearish / Neutral, and on what.
3. **Key Data Points**: Important statistics, figures, or metrics cited.
4. **Actionable Insights**: What an investor should consider based on this research.
5. **Tags**: 3-5 topic tags (e.g., "macro", "equities", "fixed-income", "volatility").

Be precise. Do not hallucinate data points — only cite what is in the source text. \
If the text is too short or vague to summarize meaningfully, say so."""


def summarize_article(
    title: str,
    body_text: str,
    firm_name: str,
    pdf_text: str = "",
) -> str:
    """
    Summarize a research article using Claude.

    Combines the article body and any extracted PDF text.
    Returns the summary as markdown.
    """
    # Build the content to summarize
    content_parts = []
    if body_text:
        content_parts.append(f"## Article Text\n\n{body_text}")
    if pdf_text:
        content_parts.append(f"## PDF Report Text\n\n{pdf_text}")

    full_content = "\n\n---\n\n".join(content_parts)

    # Truncate to ~100k chars to stay within context limits
    if len(full_content) > 100000:
        full_content = full_content[:100000] + "\n\n[... truncated]"

    if not full_content.strip():
        return "_No content available to summarize._"

    user_message = (
        f"Please summarize the following research from **{firm_name}**.\n\n"
        f"**Title**: {title}\n\n"
        f"---\n\n{full_content}"
    )

    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        summary = response.content[0].text
        logger.info(f"Generated summary for: {title}")
        return summary

    except Exception as e:
        logger.error(f"Summarization failed for '{title}': {e}")
        return f"_Summarization failed: {e}_"


def summarize_batch_digest(summaries: list[dict]) -> str:
    """
    Generate a high-level digest across multiple research summaries.

    Args:
        summaries: List of dicts with keys: firm, title, summary
    """
    if not summaries:
        return "_No new research to digest._"

    content = "\n\n---\n\n".join(
        f"### {s['firm']} — {s['title']}\n\n{s['summary']}"
        for s in summaries
    )

    user_message = (
        "Below are summaries of the latest research from multiple institutional "
        "investment managers. Please produce a **Market Intelligence Digest** that:\n\n"
        "1. Identifies **consensus themes** across firms\n"
        "2. Highlights **contrarian or divergent views**\n"
        "3. Lists the **top 3 actionable takeaways** for a portfolio manager\n"
        "4. Notes any **risks or uncertainties** flagged by multiple firms\n\n"
        f"---\n\n{content}"
    )

    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=(
                "You are a senior portfolio strategist synthesizing research "
                "from the world's top investment managers into a concise daily brief."
            ),
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Batch digest failed: {e}")
        return f"_Digest generation failed: {e}_"
