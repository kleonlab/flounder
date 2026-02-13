"""FastAPI app — mobile-friendly link classifier that logs to Google Sheets."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from flounder.classifier import classify
from flounder.extractor import extract_content
from flounder.sheets import append_link
from flounder.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Flounder")


# ── PWA manifest ─────────────────────────────────────────────────────

MANIFEST = {
    "name": "Flounder",
    "short_name": "Flounder",
    "description": "Classify and save links to Google Sheets",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#f5f5f5",
    "theme_color": "#111111",
    "icons": [
        {"src": "/icon", "sizes": "512x512", "type": "image/svg+xml", "purpose": "any maskable"}
    ],
    "share_target": {
        "action": "/share",
        "method": "GET",
        "params": {"url": "url", "text": "text", "title": "title"},
    },
}


# ── SVG icon (no external files needed) ──────────────────────────────

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" rx="96" fill="#111"/>
<text x="256" y="340" text-anchor="middle" font-size="280"
      font-family="system-ui" fill="#fff">F</text>
</svg>"""


# ── HTML ─────────────────────────────────────────────────────────────

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#111111">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/icon" type="image/svg+xml">
<title>Flounder</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: system-ui, -apple-system, sans-serif;
    background: #f5f5f5; color: #111;
    min-height: 100dvh;
    padding: env(safe-area-inset-top) 1rem 1rem;
  }
  .app { max-width: 480px; margin: 0 auto; padding-top: 1rem; }

  h1 { font-size: 1.3rem; margin-bottom: .2rem; }
  .sub { color: #888; font-size: .82rem; margin-bottom: 1.2rem; }

  .input-group { margin-bottom: .8rem; }
  label { font-weight: 600; font-size: .8rem; display: block; margin-bottom: .3rem; color: #555; }
  input, textarea {
    width: 100%; padding: .65rem .8rem; border: 1.5px solid #ddd;
    border-radius: 10px; font-size: 1rem; background: #fff;
    -webkit-appearance: none;
  }
  input:focus, textarea:focus { outline: none; border-color: #111; }
  textarea { resize: vertical; min-height: 70px; font-family: inherit; }

  .btn {
    background: #111; color: #fff; border: none; border-radius: 10px;
    padding: .75rem; font-size: 1rem; cursor: pointer; width: 100%;
    font-weight: 600; margin-top: .4rem;
    -webkit-tap-highlight-color: transparent;
  }
  .btn:active { transform: scale(.98); }
  .btn:disabled { background: #999; cursor: wait; }

  .result {
    margin-top: 1rem; padding: 1rem; border-radius: 10px; font-size: .88rem;
    animation: fadeIn .3s;
  }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; } }
  .result.ok { background: #e8f5e9; border: 1px solid #a5d6a7; }
  .result.err { background: #fce4ec; border: 1px solid #ef9a9a; }
  .tag {
    display: inline-block; background: #e3f2fd; color: #1565c0; padding: 2px 10px;
    border-radius: 99px; font-size: .78rem; font-weight: 700; margin-bottom: .5rem;
  }
  .field { margin-bottom: .4rem; }
  .field b { font-weight: 600; }
  .saved { color: #388e3c; font-size: .8rem; margin-top: .4rem; }

  .history { margin-top: 1.5rem; }
  .history h2 { font-size: .95rem; color: #888; margin-bottom: .6rem; }
  .history-item {
    background: #fff; border-radius: 10px; padding: .8rem; margin-bottom: .6rem;
    border: 1px solid #eee;
  }
  .history-item .tag { font-size: .7rem; }
  .history-item .url { font-size: .78rem; color: #1976d2; word-break: break-all; }
  .history-item .summary { font-size: .82rem; color: #555; margin-top: .3rem; }
</style>
</head>
<body>
<div class="app">
  <h1>Flounder</h1>
  <p class="sub">Paste a link, add a note. Classified & saved to your sheet.</p>

  <form id="f">
    <div class="input-group">
      <label for="url">Link</label>
      <input id="url" name="url" type="url" placeholder="https://..." required autofocus>
    </div>
    <div class="input-group">
      <label for="note">Note (optional)</label>
      <textarea id="note" name="note" placeholder="Why this is interesting, who it's for..."></textarea>
    </div>
    <div class="input-group">
      <label for="who">From</label>
      <input id="who" name="shared_by" placeholder="Your name">
    </div>
    <button type="submit" class="btn" id="btn">Classify & Save</button>
  </form>

  <div id="out"></div>

  <div class="history" id="history-section" style="display:none">
    <h2>Recent</h2>
    <div id="history"></div>
  </div>
</div>
<script>
// Persist name
const whoEl = document.getElementById('who');
whoEl.value = localStorage.getItem('flounder_name') || '';
whoEl.addEventListener('change', () => localStorage.setItem('flounder_name', whoEl.value));

// History
let history = JSON.parse(localStorage.getItem('flounder_history') || '[]');
function renderHistory() {
  const el = document.getElementById('history');
  const sec = document.getElementById('history-section');
  if (!history.length) { sec.style.display = 'none'; return; }
  sec.style.display = 'block';
  el.innerHTML = history.slice(0, 20).map(h => `
    <div class="history-item">
      <div class="tag">${h.bucket}</div>
      <div class="url">${h.url}</div>
      <div class="summary">${h.summary}</div>
    </div>`).join('');
}
renderHistory();

// Handle share target (URL params from share intent)
const params = new URLSearchParams(window.location.search);
if (params.get('url')) document.getElementById('url').value = params.get('url');
if (params.get('text')) document.getElementById('note').value = params.get('text');

// Submit
document.getElementById('f').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('btn');
  const out = document.getElementById('out');
  btn.disabled = true; btn.textContent = 'Processing...'; out.innerHTML = '';
  try {
    const res = await fetch('/api/classify', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        url: document.getElementById('url').value,
        note: document.getElementById('note').value,
        shared_by: whoEl.value || 'anonymous'
      })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    out.innerHTML = `<div class="result ok">
      <div class="tag">${data.bucket}</div>
      <div class="field"><b>Summary:</b> ${data.summary}</div>
      <div class="field"><b>Action:</b> ${data.action}</div>
      <div class="saved">Saved to Google Sheet</div>
    </div>`;
    history.unshift({ bucket: data.bucket, url: document.getElementById('url').value, summary: data.summary });
    localStorage.setItem('flounder_history', JSON.stringify(history.slice(0, 50)));
    renderHistory();
    document.getElementById('url').value = '';
    document.getElementById('note').value = '';
  } catch (err) {
    out.innerHTML = `<div class="result err">${err.message}</div>`;
  }
  btn.disabled = false; btn.textContent = 'Classify & Save';
});
</script>
</body>
</html>"""


# ── Routes ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PAGE


@app.get("/share", response_class=HTMLResponse)
async def share_target():
    """Web Share Target — when you share a link from another app, it lands here."""
    return HTML_PAGE


@app.get("/manifest.json")
async def manifest():
    return JSONResponse(MANIFEST)


@app.get("/icon")
async def icon():
    return HTMLResponse(content=ICON_SVG, media_type="image/svg+xml")


@app.post("/api/classify")
async def classify_link(request: Request):
    body = await request.json()
    url = body.get("url", "").strip()
    note = body.get("note", "").strip()
    shared_by = body.get("shared_by", "anonymous").strip()

    if not url:
        return {"error": "No URL provided"}

    try:
        content = await extract_content(url)
        if note:
            content["note"] = note

        classification = await classify(content)

        append_link(
            bucket=classification["bucket"],
            url=url,
            title=content.get("title", ""),
            summary=classification["summary"],
            action=classification["action"],
            shared_by=shared_by,
            group=None,
        )

        return {
            "bucket": classification["bucket"],
            "summary": classification["summary"],
            "action": classification["action"],
        }
    except Exception as exc:
        logger.error("Failed to process %s: %s", url, exc)
        return {"error": str(exc)}


@app.get("/api/buckets")
async def get_buckets():
    return {"buckets": settings.bucket_list}


@app.get("/health")
async def health():
    return {"status": "ok"}
