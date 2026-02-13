"""Google Sheets integration — appends classified links to a spreadsheet."""

import logging
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

from flounder.config import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADER_ROW = [
    "Timestamp",
    "Bucket",
    "URL",
    "Title",
    "Summary",
    "Action",
    "Shared By",
    "Group",
]

_client: gspread.Client | None = None


def _get_client() -> gspread.Client:
    global _client
    if _client is None:
        creds = Credentials.from_service_account_file(
            settings.google_service_account_file, scopes=SCOPES
        )
        _client = gspread.authorize(creds)
    return _client


def _ensure_sheet(spreadsheet: gspread.Spreadsheet, bucket: str) -> gspread.Worksheet:
    """Get or create a worksheet tab for the given bucket."""
    try:
        ws = spreadsheet.worksheet(bucket)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=bucket, rows=1000, cols=len(HEADER_ROW))
        ws.append_row(HEADER_ROW)
    return ws


def append_link(
    bucket: str,
    url: str,
    title: str,
    summary: str,
    action: str,
    shared_by: str,
    group: str | None,
) -> None:
    """Append a classified link to the appropriate bucket tab in Google Sheets."""
    try:
        client = _get_client()
        spreadsheet = client.open_by_key(settings.google_sheets_id)
        ws = _ensure_sheet(spreadsheet, bucket)

        row = [
            datetime.now(timezone.utc).isoformat(),
            bucket,
            url,
            title,
            summary,
            action,
            shared_by,
            group or "",
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        logger.info("Appended link to [%s]: %s", bucket, url)
    except Exception as exc:
        logger.error("Failed to write to Google Sheets: %s", exc)
        raise
