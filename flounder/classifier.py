"""Use Claude to classify link content into user-defined buckets."""

import json
import logging

import anthropic

from flounder.config import settings

logger = logging.getLogger(__name__)


def _build_prompt(content: dict, buckets: list[str]) -> str:
    bucket_str = ", ".join(buckets)
    return f"""You are a link classifier. Given the content of a web page, you must:
1. Assign it to exactly ONE of these buckets: [{bucket_str}]
2. Write a one-line summary of the page.
3. Suggest a concrete action the user should take (e.g. "Read later", "Buy before sale ends", "Share with team", "Schedule meeting", "Save recipe").

Respond ONLY with valid JSON — no markdown, no explanation:
{{"bucket": "<bucket>", "summary": "<summary>", "action": "<action>"}}

--- PAGE CONTENT ---
Title: {content.get('title', '')}
Description: {content.get('description', '')}
URL: {content.get('url', '')}
User note: {content.get('note', '(none)')}
Body (truncated):
{content.get('body', '')[:6000]}
"""


async def classify(content: dict) -> dict:
    """Return {bucket, summary, action} for the given page content."""
    buckets = settings.bucket_list
    prompt = _build_prompt(content, buckets)

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        result = json.loads(raw)

        # Validate bucket
        if result.get("bucket") not in buckets:
            result["bucket"] = buckets[-1]  # fallback to last bucket (usually "Other")

        return result

    except Exception as exc:
        logger.error("Classification failed: %s", exc)
        return {
            "bucket": buckets[-1] if buckets else "Other",
            "summary": content.get("title", content["url"]),
            "action": "Review manually",
        }
