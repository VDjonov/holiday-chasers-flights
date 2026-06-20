# Holiday Chasers Cork — Setup Guide

## What you have

| File | What it does |
|---|---|
| `index.html` | The public website — hosts free, works 24/7 |
| `deals_cache.json` | Pre-scanned deal boards — auto-refreshed weekly |
| `backend.py` | FastAPI server on YOUR PC — powers live search |
| `refresh_deals.py` | Weekly deal scanner — runs via GitHub Actions |
| `.github/workflows/refresh_deals.yml` | Automated schedule for the scanner |
| `requirements.txt` | Python dependencies |
| `serpapi_key.txt` | Your API keys (local only, never pushed) |

## Step 1 — Deploy the website (free, always on)

### Option A: Netlify (you have an account)
1. Create a new folder with `index.html` and `deals_cache.json`
2. Go to app.netlify.com → Add new site → Deploy manually
3. Drag the folder in → done. You get a URL like `amazing-site-123.netlify.app`

### Option B: GitHub Pages (free)
1. Push `index.html` and `deals_cache.json` to your GitHub repo
2. Repo Settings → Pages → Source: main branch → Save
3. Your site is live at `yourusername.github.io/repo-name`

## Step 2 — Set up the backend on your PC

### Install dependencies
```
pip install fastapi uvicorn requests
```

### Make sure your API keys are in serpapi_key.txt
One key per line:
```
your_first_key_here
your_second_key_here
your_third_key_here
```

### Start the backend
```
python backend.py
```
You'll see:
```
🛫 Holiday Chasers Cork backend starting...
Keys loaded: 3
```

### Test it
Open http://localhost:8000/api/health in your browser.
You should see `{"status":"online","keys":3,...}`

## Step 3 — Connect your PC to the internet via Cloudflare Tunnel

### Install cloudflared (one time)
Go to: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
Download the Windows installer → run it.

### Start the tunnel (each time you want live search)
Open a NEW PowerShell window (keep the backend running in the first one):
```
cloudflared tunnel --url http://localhost:8000
```

It prints something like:
```
Your quick Tunnel has been created! Visit it at:
https://something-random-words.trycloudflare.com
```

Copy that URL — that's your backend's public address.

### Tell the website about your tunnel
1. Open your website in a browser
2. Press Ctrl+Shift+B
3. Paste the tunnel URL (e.g. https://something-random-words.trycloudflare.com)
4. The status badge in the nav bar changes from "● Live search off" to "● Live search on"
5. The Direct and Europe tabs now work

Note: The tunnel URL changes every time you restart cloudflared.
For a permanent URL, set up a named tunnel (free, requires a Cloudflare account):
https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/

## Step 4 — Automated deal refresh (GitHub Actions)

This keeps your deal boards fresh even when your PC is off.

1. Push all files to your GitHub repo
2. Create `.github/workflows/refresh_deals.yml` in the repo
3. Add secrets in repo Settings → Secrets → Actions:
   - `SERPAPI_KEY` = your first key
   - `SERPAPI_KEY2` = your second key
   - `SERPAPI_KEY3` = your third key
4. Go to Actions tab → "Refresh flight deals" → Run workflow
5. It scans all destinations, commits deals_cache.json
6. Your website (if on GitHub Pages) auto-updates
7. If on Netlify, set up auto-deploy from the same repo

## How it all fits together

```
Visitor opens website (always works)
  → sees deal boards from deals_cache.json
  → boards refresh automatically every Monday via GitHub Actions

Visitor clicks "Direct Flights" or "Anywhere in Europe"
  → website pings your PC via Cloudflare Tunnel
  → if PC is on: live search works, real-time results
  → if PC is off: polite "Live search offline" message,
    deal boards still fully functional
```

## Daily usage

### When you want live search available:
1. Open PowerShell → `cd "D:\Aplications\Cork Flight Checker"`
2. `python backend.py` (keep this window open)
3. Open another PowerShell → `cloudflared tunnel --url http://localhost:8000`
4. Copy the URL → press Ctrl+Shift+B on your website → paste

### When you don't:
Do nothing. The website still shows the deal boards 24/7.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Live search off" | Start backend.py + cloudflared |
| Deal board empty | Run refresh_deals.py manually, or trigger the GitHub Action |
| "SerpApi error" | Check your keys in serpapi_key.txt |
| Tunnel URL changed | Press Ctrl+Shift+B on the website, paste the new URL |
