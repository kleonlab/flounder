# Flounder — WhatsApp Link Agent

Flounder watches a WhatsApp group for shared links, fetches and digests
their content, classifies each link into a user-defined bucket using Claude,
and logs everything to a Google Sheet (one tab per bucket).

## How it works

```
WhatsApp Group → Meta Webhook → Flounder API
                                   ├─ Fetch & extract page content
                                   ├─ Classify with Claude (bucket + summary + action)
                                   └─ Append row to Google Sheet tab
```

## Quickstart

### 1. Prerequisites

- Python 3.11+
- A [Meta Developer](https://developers.facebook.com/) app with WhatsApp Cloud API enabled
- A [Google Cloud service account](https://console.cloud.google.com/) with Sheets API access
- An [Anthropic API key](https://console.anthropic.com/)

### 2. Install

```bash
pip install -e .
```

### 3. Configure

```bash
cp .env.example .env
# Fill in your API keys and settings
```

| Variable | Description |
|---|---|
| `WHATSAPP_VERIFY_TOKEN` | Any secret string — used to verify the Meta webhook |
| `WHATSAPP_API_TOKEN` | Your WhatsApp Cloud API access token |
| `WHATSAPP_PHONE_NUMBER_ID` | The phone number ID from Meta dashboard |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `GOOGLE_SHEETS_ID` | The spreadsheet ID from the Google Sheets URL |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to the service-account JSON key |
| `BUCKETS` | Comma-separated category names (e.g. `Tech,Finance,Health,News,Other`) |

### 4. Google Sheets setup

1. Create a new Google Sheet.
2. Share it with your service account email (the `client_email` in your JSON key file) — give **Editor** access.
3. Copy the spreadsheet ID from the URL and put it in `.env`.

Flounder will automatically create a tab for each bucket on first use.

### 5. Run

```bash
uvicorn flounder.app:app --host 0.0.0.0 --port 8000
```

For local development, expose the server with [ngrok](https://ngrok.com/):

```bash
ngrok http 8000
```

Then set the webhook URL in your Meta app to `https://<ngrok-url>/webhook`.

### 6. WhatsApp webhook setup

1. Go to your Meta app → WhatsApp → Configuration.
2. Set **Callback URL** to `https://your-domain/webhook`.
3. Set **Verify Token** to the same value as `WHATSAPP_VERIFY_TOKEN` in `.env`.
4. Subscribe to the `messages` webhook field.
5. Add your WhatsApp bot number to the group you want to monitor.

## Customising buckets

Edit the `BUCKETS` variable in `.env`. Each bucket becomes a separate tab
in your Google Sheet. Claude uses these bucket names when classifying links,
so use descriptive names.

Example:

```
BUCKETS=AI/ML,Frontend,Backend,DevOps,Design,Career,Other
```

## Google Sheet output

Each bucket tab has these columns:

| Timestamp | Bucket | URL | Title | Summary | Action | Shared By | Group |
|---|---|---|---|---|---|---|---|

- **Summary** — one-line description of the page content
- **Action** — suggested next step (e.g. "Read later", "Share with team")
