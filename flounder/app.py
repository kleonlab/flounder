"""FastAPI application — wires WhatsApp webhook → extractor → classifier → Google Sheets."""

import asyncio
import logging

from fastapi import FastAPI

from flounder.classifier import classify
from flounder.extractor import extract_content
from flounder.sheets import append_link
from flounder.whatsapp import IncomingLink, router as whatsapp_router, set_on_links_callback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Flounder – WhatsApp Link Agent")
app.include_router(whatsapp_router)


async def _process_link(link: IncomingLink) -> None:
    """End-to-end pipeline for a single link: extract → classify → sheet."""
    logger.info("Processing %s from %s", link.url, link.sender_name)

    content = await extract_content(link.url)
    classification = await classify(content)

    append_link(
        bucket=classification["bucket"],
        url=link.url,
        title=content.get("title", ""),
        summary=classification["summary"],
        action=classification["action"],
        shared_by=link.sender_name,
        group=link.group_name,
    )


async def on_links(links: list[IncomingLink]) -> None:
    """Called by the webhook handler whenever messages with links arrive."""
    tasks = [_process_link(link) for link in links]
    await asyncio.gather(*tasks, return_exceptions=True)


# Register the callback so the webhook module can trigger processing.
set_on_links_callback(on_links)


@app.get("/health")
async def health():
    return {"status": "ok"}
