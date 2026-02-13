"""Fetch a URL and extract its main textual content."""

import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; FlounderBot/1.0; +https://github.com/kleonlab/flounder)"
    ),
}

MAX_CONTENT_LENGTH = 12_000  # characters sent to the classifier


async def extract_content(url: str) -> dict:
    """Fetch *url* and return a dict with title, description, and body text.

    Returns a partial result on failure so the pipeline can still log the link.
    """
    result = {"url": url, "title": "", "description": "", "body": ""}

    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15.0, headers=_HEADERS
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        result["body"] = f"[Could not fetch: {exc}]"
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    if soup.title and soup.title.string:
        result["title"] = soup.title.string.strip()

    # Meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        result["description"] = meta["content"].strip()

    # Body text — strip scripts/styles, then grab text
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    result["body"] = text[:MAX_CONTENT_LENGTH]

    return result
