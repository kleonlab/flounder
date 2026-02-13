"""WhatsApp Cloud API webhook handler — receives group messages and extracts links."""

import re
from dataclasses import dataclass

from fastapi import APIRouter, Query, Request, Response

router = APIRouter()

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


@dataclass
class IncomingLink:
    url: str
    sender_name: str
    sender_phone: str
    group_name: str | None
    raw_message: str
    timestamp: str


def _extract_links(text: str) -> list[str]:
    """Pull all URLs out of a message body."""
    return URL_PATTERN.findall(text)


def _parse_webhook_payload(body: dict) -> list[IncomingLink]:
    """Walk Meta's nested webhook payload and return any messages that contain links."""
    links: list[IncomingLink] = []

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {c["wa_id"]: c.get("profile", {}).get("name", "Unknown")
                        for c in value.get("contacts", [])}

            for msg in value.get("messages", []):
                text_body = ""
                if msg.get("type") == "text":
                    text_body = msg["text"].get("body", "")

                urls = _extract_links(text_body)
                if not urls:
                    continue

                sender_phone = msg.get("from", "")
                sender_name = contacts.get(sender_phone, "Unknown")
                # Group context comes from the metadata or the groupSubject field
                group_name = value.get("metadata", {}).get("display_phone_number", None)
                timestamp = msg.get("timestamp", "")

                for url in urls:
                    links.append(IncomingLink(
                        url=url,
                        sender_name=sender_name,
                        sender_phone=sender_phone,
                        group_name=group_name,
                        raw_message=text_body,
                        timestamp=timestamp,
                    ))

    return links


# Stored callback so the main app can wire up the processing pipeline.
_on_links_callback = None


def set_on_links_callback(callback):
    global _on_links_callback
    _on_links_callback = callback


# ── Webhook endpoints ────────────────────────────────────────────────────────

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta sends a GET to verify the webhook URL."""
    from flounder.config import settings

    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("/webhook")
async def receive_message(request: Request):
    """Meta sends a POST for every incoming message."""
    body = await request.json()
    links = _parse_webhook_payload(body)

    if links and _on_links_callback:
        await _on_links_callback(links)

    # Always return 200 so Meta doesn't retry.
    return {"status": "ok"}
