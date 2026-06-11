# Taste Map

Upload a Spotify playlist export and get a one-page portrait of what you listen to — genre weight, release-era shape, artist concentration, and how deep your cuts run.

Small portfolio build: runs locally or on Streamlit Cloud, sample data included, no private tracks in the repo.

## What's in the report

- Genre treemap, decade bars, top artists
- Mood fingerprint (energy, danceability, valence, tempo) when the export includes audio features
- Headline and short interpretation from your stats — works offline, no API required
- Optional AI rewrite via Groq or local Ollama

## How it works

```text
CSV → parse.py → taste profile + brief → app.py (Streamlit + Plotly)
```

`parse.py` normalises Exportify columns, splits genres and artists, buckets years, and scores popularity. `narrate.py` turns the brief into copy. `app.py` renders the page.

## Run locally

Double-click `run.bat`, or from PowerShell:

```powershell
cd "C:\AI dreams\business\taste-map"
.\run.bat
```

Opens at **http://localhost:8501**.

First-time setup:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Your data

| File | Purpose |
|---|---|
| `data/sample_liked_songs.csv` | Bundled demo — safe to commit |
| `data/Liked_Songs.csv` | Your private export — gitignored |
| `data/playlists/*.csv` | Local multi-playlist folder — gitignored |

Load order: **upload on the main page** → playlist picker → sample CSV.

Useful Exportify columns: `Track Name`, `Artist Name(s)`, `Release Date`, `Popularity`, `Genres`. Audio feature columns improve the mood strip.

## Optional AI portrait

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set one of:

- `GROQ_API_KEY` — free tier at [console.groq.com](https://console.groq.com)
- `OLLAMA_MODEL` — e.g. `llama3.2` with [Ollama](https://ollama.com) running locally

Only the stat brief goes to the model, not raw track lists. No key → template copy.

## Deploy on Streamlit Community Cloud

Repo: [github.com/jmshall93-debug/taste-map](https://github.com/jmshall93-debug/taste-map)

1. Push the latest `main` branch to GitHub.
2. Open [share.streamlit.io](https://share.streamlit.io) → **Create app**.
3. Select the repo, branch **`main`**, main file path **`app.py`**.
4. Deploy. The live app loads the bundled sample CSV; visitors can upload their own export from the main page.

For AI portrait on Cloud: app **Settings → Secrets** — same keys as `secrets.toml`.

## Portfolio blurb

**Listening Taste Map** — visual taste portrait from a Spotify/Exportify CSV. Genre map, era shape, artist concentration, deep-cuts index. Python, Streamlit, Plotly. Sample data and source included.

## Handover

You get full source, demo data, and run instructions. Private exports stay local. The parsing layer is separate from the UI, so charts, copy, or branding can change without touching the core logic.
