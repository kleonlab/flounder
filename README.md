# Flounder

A phone-friendly web app for saving and classifying links. Paste a link (or share it
directly from any app), add an optional note, and Flounder uses Claude to classify it
into your custom buckets and logs everything to a Google Sheet.

## How it works

```
You paste/share a link  →  Flounder fetches the page
                           →  Claude classifies it into a bucket
                           →  Row added to your Google Sheet (one tab per bucket)
```

Works as a **PWA** — add it to your home screen on iPhone or Android and it
behaves like a native app. Supports **Share Target** so you can share links
from WhatsApp, Safari, Chrome, etc. directly into Flounder.

## Setup

### 1. Install

```bash
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
```

Fill in three things:

| Variable | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) |
| `GOOGLE_SHEETS_ID` | Create a Google Sheet, copy the ID from the URL |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | [Google Cloud Console](https://console.cloud.google.com/) → Service Account → JSON key |

Then share the Google Sheet with the service account email (Editor access).

### 3. Set your buckets

Edit `BUCKETS` in `.env` — comma-separated categories:

```
BUCKETS=Tech,Finance,Health,News,Shopping,Travel,Other
```

Each bucket becomes a tab in the spreadsheet. Claude uses these names to
classify links, so pick clear, descriptive names.

### 4. Run

```bash
uvicorn flounder.app:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` on your phone (or deploy and use HTTPS).

### 5. Add to home screen (PWA)

- **iPhone**: Safari → Share → "Add to Home Screen"
- **Android**: Chrome → menu → "Add to Home screen" or "Install app"

Once installed, you can share links from **any app** (WhatsApp, browser, etc.)
directly to Flounder using the system share sheet.

## Google Sheet output

| Timestamp | Bucket | URL | Title | Summary | Action | Shared By | Group |
|---|---|---|---|---|---|---|---|

- **Summary** — one-line description of the page
- **Action** — suggested next step ("Read later", "Share with team", etc.)
