"""Taste Map — Streamlit UI."""

import importlib
import json
import re
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

import narrate
import parse

importlib.reload(parse)
importlib.reload(narrate)
from narrate import ai_portrait, llm_configured, template_library_summary, template_portrait
from parse import analyze, analyze_file, load_csv, narrative_brief, summarize_library

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_CSV = DATA_DIR / "Liked_Songs.csv"
SAMPLE_CSV = DATA_DIR / "sample_liked_songs.csv"
PLAYLISTS_DIR = DATA_DIR / "playlists"
TOP_GENRES = 18
CHART_HEIGHT = 430
SMALL_CHART_HEIGHT = 330

# Editorial Ember: orange heat on warm charcoal, amber for structure.
BG = "#0e0c0a"
SURFACE = "#161310"
BORDER = "#352e26"
TEXT = "#fff8f0"
MUTED = "#a08b78"
ACCENT = "#ea580c"
ACCENT_DEEP = "#7c2d12"
ACCENT_GLOW = "#f97316"
AMBER = "#c9925a"
PEACH = "#f0dcc8"
PETROL = "#123338"
PETROL_LIGHT = "#2f5d62"
PLUM = "#34243a"
CREAM = "#fff8f0"
BAR_LOW = "#431407"
BAR_HIGH = "#ea580c"
# Deep mixed palette: ember, tobacco, petrol, slate, plum.
GENRE_PALETTE = [
    "#431407",
    "#123338",
    "#7c2d12",
    "#1f2937",
    "#9a3412",
    "#243b35",
    "#34243a",
    "#a0522d",
    "#172a2f",
    "#702500",
    "#2b3645",
    "#571f0a",
    "#2f3f3a",
    "#4b2a3d",
    "#bf4f1f",
    "#162235",
    "#d4622a",
    "#1d3f45",
]

PAGE_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
.stApp {{
    background:
        radial-gradient(ellipse 90% 55% at 18% -15%, rgba(234, 88, 12, 0.10) 0%, transparent 55%),
        {BG};
    color: {TEXT};
}}
.block-container {{
    font-family: Inter, Segoe UI, system-ui, sans-serif;
    padding-top: 2.5rem;
    max-width: 1040px;
}}
#MainMenu, footer, header[data-testid="stHeader"] {{ display: none; }}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {{ display: none; }}
.control-hint {{
    color: {MUTED};
    font-size: 0.82rem;
    margin: 0 0 1.25rem 0;
}}
.library-summary {{
    color: {MUTED};
    font-size: 0.88rem;
    line-height: 1.6;
    max-width: 52rem;
    margin: 0 0 1.35rem 0;
    padding: 0.75rem 0.95rem;
    border-left: 2px solid {AMBER};
    background: rgba(22, 19, 16, 0.55);
    border-radius: 0 6px 6px 0;
}}
.library-summary-label {{
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: {AMBER};
    margin-bottom: 0.35rem;
}}

.hero-title {{
    font-size: 2.55rem;
    font-weight: 600;
    letter-spacing: -0.045em;
    margin: 0 0 0.35rem 0;
    color: {TEXT};
}}
.hero-label {{
    font-family: Inter, Segoe UI, system-ui, sans-serif;
    font-size: 1.05rem;
    font-weight: 400;
    line-height: 1.45;
    color: {PEACH};
    margin: 0 0 0.8rem 0;
    max-width: 50rem;
}}
.interpretation {{
    color: {MUTED};
    font-size: 0.98rem;
    line-height: 1.65;
    max-width: 52rem;
    margin: 0 0 1.55rem 0;
}}
.stat-strip {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1px;
    background: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 8px;
    overflow: hidden;
    margin: 1.55rem 0 1.35rem 0;
}}
@media (max-width: 720px) {{
    .block-container {{
        padding-top: 1.5rem;
        padding-left: 0.85rem;
        padding-right: 0.85rem;
    }}
    .stat-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .hero-title {{ font-size: 1.75rem; letter-spacing: -0.03em; }}
    .hero-label {{ font-size: 0.95rem; margin-bottom: 0.55rem; }}
    .interpretation {{ font-size: 0.9rem; line-height: 1.55; margin-bottom: 1rem; }}
    .stat-value {{ font-size: 1.15rem; }}
    .stat {{ padding: 0.65rem 0.75rem; }}
    .hero-caption {{ letter-spacing: 0.14em; font-size: 0.58rem; }}
    .control-hint {{ font-size: 0.76rem; margin-bottom: 0.75rem; }}
    .section-label {{ margin-top: 1.1rem; }}
    /* Stack side-by-side Streamlit columns */
    div[data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap !important;
        gap: 0.35rem !important;
    }}
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 100% !important;
    }}
    /* Compact file uploader */
    [data-testid="stFileUploaderDropzone"] {{
        padding: 0.45rem 0.6rem !important;
        min-height: 0 !important;
    }}
    [data-testid="stFileUploaderDropzone"] small {{
        display: none !important;
    }}
    [data-testid="stPlotlyChart"] {{
        padding: 0.1rem;
    }}
}}
@media (max-width: 420px) {{
    .hero-title {{ font-size: 1.45rem; }}
    .stat-label {{ font-size: 0.52rem; letter-spacing: 0.1em; }}
    .stat-value {{ font-size: 1rem; }}
}}
.stat {{
    background: rgba(20, 18, 16, 0.92);
    padding: 0.8rem 0.95rem;
}}
.stat-label {{
    color: {MUTED};
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 0.32rem;
}}
.stat-value {{
    color: {TEXT};
    font-size: 1.35rem;
    font-weight: 600;
    letter-spacing: -0.02em;
}}
.hero-caption {{
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: {ACCENT_GLOW};
    margin-bottom: 0.45rem;
}}
.section-label {{
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: {AMBER};
    margin: 1.5rem 0 0.6rem 0;
}}
[data-testid="stPlotlyChart"] {{
    background: linear-gradient(180deg, #181512 0%, {SURFACE} 100%);
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 0.2rem;
    box-shadow: inset 0 1px 0 rgba(234, 88, 12, 0.06);
}}
.footer-note {{
    color: {MUTED};
    font-size: 0.78rem;
    line-height: 1.5;
    margin: 2.2rem 0 0.5rem 0;
    padding-top: 1.2rem;
    border-top: 1px solid {BORDER};
}}
</style>
"""

CHART_LAYOUT = dict(
    margin=dict(t=48, l=12, r=12, b=12),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT, size=12, family="Segoe UI, system-ui, sans-serif"),
    title=dict(font=dict(size=13, color=ACCENT), x=0, xanchor="left"),
)


def _layout(height=CHART_HEIGHT, **extra):
    return {**CHART_LAYOUT, "height": height, **extra}


def _apply_axes(fig, show_y_grid=False):
    fig.update_xaxes(
        showgrid=False,
        linecolor=BORDER,
        tickcolor=MUTED,
        tickfont=dict(color=MUTED, size=10),
    )
    fig.update_yaxes(
        showgrid=show_y_grid,
        gridcolor=BORDER,
        gridwidth=0.5,
        zeroline=False,
        linecolor=BORDER,
        tickcolor=MUTED,
        tickfont=dict(color=MUTED, size=10),
    )
    return fig


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lerp_hex(low: str, high: str, t: float) -> str:
    r1, g1, b1 = _hex_to_rgb(low)
    r2, g2, b2 = _hex_to_rgb(high)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


def _bar_fill_colors(values: list[int] | list[float], low: str, high: str) -> list[str]:
    """Solid low-to-high ramp."""
    if not values:
        return []
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return [high] * len(values)
    return [_lerp_hex(low, high, (v - vmin) / (vmax - vmin)) for v in values]


def _profile_attr(profile, name: str):
    return getattr(profile, name, None)


def _pct(value: float) -> int:
    return round(value * 100)


def _mood_strip(profile) -> str:
    energy = _profile_attr(profile, "avg_energy")
    if energy is None:
        return ""

    tempo_val = _profile_attr(profile, "avg_tempo")
    dance_val = _profile_attr(profile, "avg_danceability")
    valence_val = _profile_attr(profile, "avg_valence")
    tempo = f"{tempo_val:.0f}" if tempo_val is not None else "—"
    dance = _pct(dance_val) if dance_val is not None else "—"
    valence = _pct(valence_val) if valence_val is not None else "—"
    return f"""
    <p class="section-label" style="margin-top: 0.25rem;">Mood fingerprint</p>
    <div class="stat-strip">
        <div class="stat">
            <div class="stat-label">Energy</div>
            <div class="stat-value">{_pct(energy)}%</div>
        </div>
        <div class="stat">
            <div class="stat-label">Danceability</div>
            <div class="stat-value">{dance}%</div>
        </div>
        <div class="stat">
            <div class="stat-label">Valence</div>
            <div class="stat-value">{valence}%</div>
        </div>
        <div class="stat">
            <div class="stat-label">Tempo</div>
            <div class="stat-value">{tempo}<span style="font-size:0.75rem;color:{MUTED};"> bpm</span></div>
        </div>
    </div>
    """


def _stat_strip(profile) -> str:
    return f"""
    <div class="stat-strip">
        <div class="stat">
            <div class="stat-label">Tracks mapped</div>
            <div class="stat-value">{profile.track_count}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Avg popularity</div>
            <div class="stat-value">{profile.avg_popularity}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Artists touched</div>
            <div class="stat-value">{profile.artist_count}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Deep-cuts index</div>
            <div class="stat-value" style="color: {ACCENT_GLOW};">{profile.obscurity_score}</div>
        </div>
    </div>
    """


def _playlist_label(path: Path) -> str:
    name = path.stem.replace("_", " ")
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)


def _playlist_choices() -> list[tuple[str, Path]]:
    choices: list[tuple[str, Path]] = []
    if SAMPLE_CSV.exists():
        choices.append(("Sample demo", SAMPLE_CSV))
    if PLAYLISTS_DIR.is_dir():
        for path in sorted(PLAYLISTS_DIR.glob("*.csv"), key=lambda p: _playlist_label(p).lower()):
            choices.append((_playlist_label(path), path))
    if DEFAULT_CSV.exists() and not (PLAYLISTS_DIR / "Liked_Songs.csv").exists():
        choices.append(("Liked songs", DEFAULT_CSV))
    return choices


def _default_playlist_index(choices: list[tuple[str, Path]]) -> int:
    labels = [label.lower() for label, _ in choices]
    for preferred in ("liked songs", "sample demo"):
        if preferred in labels:
            return labels.index(preferred)
    return 0


def _library_playlist_paths() -> list[Path]:
    if not PLAYLISTS_DIR.is_dir():
        return []
    return sorted(PLAYLISTS_DIR.glob("*.csv"), key=lambda p: _playlist_label(p).lower())


@st.cache_data(show_spinner=False)
def _cached_library_summary(path_key: tuple[str, ...]) -> str:
    paths = [Path(p) for p in path_key]
    entries = [(_playlist_label(path), analyze_file(path)) for path in paths]
    summary = summarize_library(entries)
    return template_library_summary(summary)


def _llm_settings() -> tuple[str | None, str | None]:
    groq_key = None
    ollama_model = None
    try:
        groq_key = st.secrets.get("GROQ_API_KEY")
        ollama_model = st.secrets.get("OLLAMA_MODEL")
    except (FileNotFoundError, AttributeError, KeyError):
        pass
    return groq_key, ollama_model


@st.cache_data(show_spinner="Writing AI portrait…")
def _cached_ai_portrait(brief_json: str, groq_key: str | None, ollama_model: str | None):
    brief = json.loads(brief_json)
    return ai_portrait(brief, groq_api_key=groq_key, ollama_model=ollama_model)


def _resolve_portrait(profile, source_label: str, use_ai: bool):
    brief = narrative_brief(profile, source_label)
    portrait = template_portrait(profile, brief)
    if not use_ai:
        return portrait, brief

    groq_key, ollama_model = _llm_settings()
    ai = _cached_ai_portrait(json.dumps(brief, sort_keys=True), groq_key, ollama_model)
    if ai:
        return ai, brief
    st.warning("AI portrait unavailable — using local template. Check API key or Ollama.")
    return portrait, brief


def _load_profile():
    choices = _playlist_choices()
    if not choices:
        st.error("No CSV found. Add sample data or upload an Exportify CSV.")
        st.stop()

    labels = [label for label, _ in choices]
    groq_key, ollama_model = _llm_settings()
    ai_available = llm_configured(groq_key, ollama_model)

    if ai_available:
        pick_col, upload_col, ai_col = st.columns([4, 4, 2])
    else:
        pick_col, upload_col = st.columns([5, 4])
        ai_col = None
    with pick_col:
        picked = st.selectbox(
            "Playlist",
            labels,
            index=_default_playlist_index(choices),
        )
    with upload_col:
        uploaded = st.file_uploader(
            "Upload CSV",
            type=["csv"],
            help="Optional — overrides the playlist picker for this session.",
        )
    use_ai = False
    if ai_available:
        with ai_col:
            use_ai = st.checkbox("AI portrait", value=False)

    if uploaded is not None:
        try:
            profile = analyze(load_csv(uploaded))
            return profile, "Uploaded export", use_ai, True
        except Exception as exc:
            st.error(f"Could not read uploaded CSV: {exc}")
            st.stop()

    path = dict(choices)[picked]
    return analyze_file(path), picked, use_ai, False


def genre_treemap(profile):
    weights = profile.genre_weights.head(TOP_GENRES)
    if weights.empty:
        return None

    genres = weights.index.tolist()
    counts = weights.values.tolist()
    colors = [GENRE_PALETTE[i % len(GENRE_PALETTE)] for i in range(len(genres))]

    fig = go.Figure(
        go.Treemap(
            labels=genres,
            parents=[""] * len(genres),
            values=counts,
            branchvalues="total",
            marker=dict(colors=colors, line=dict(color=BG, width=1.25)),
            textfont=dict(color=CREAM, size=12, family="Segoe UI, system-ui, sans-serif"),
            texttemplate="%{label}<br>%{percentRoot:.0%}",
            textinfo="text",
            insidetextfont=dict(color=CREAM, size=12),
            tiling=dict(pad=4),
        )
    )
    fig.update_layout(
        height=CHART_HEIGHT,
        margin=dict(t=48, l=8, r=8, b=8),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=TEXT, size=12, family="Segoe UI, system-ui, sans-serif"),
        title=dict(text="Genre composition", font=dict(size=13, color=ACCENT), x=0, xanchor="left"),
    )
    return fig


def era_bar(profile):
    buckets = profile.era_buckets
    if buckets.empty:
        return None

    values = buckets.values.tolist()
    fig = go.Figure(
        go.Bar(
            x=buckets.index.tolist(),
            y=values,
            marker=dict(color=_bar_fill_colors(values, "#172a2f", ACCENT), line=dict(width=0)),
        )
    )
    fig.update_layout(
        **_layout(
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            xaxis_title=None,
            yaxis_title=None,
        )
    )
    fig.update_layout(title=dict(text="When the music was made", font=dict(size=13, color=MUTED), x=0, xanchor="left"))
    return _apply_axes(fig)


def top_artists_bar(profile, limit: int = 10):
    artists = profile.top_artists.head(limit)
    if artists.empty:
        return None

    values = artists.values.tolist()
    fig = go.Figure(
        go.Bar(
            x=values,
            y=artists.index.tolist(),
            orientation="h",
            marker=dict(color=_bar_fill_colors(values, "#162235", ACCENT), line=dict(width=0)),
        )
    )
    fig.update_layout(
        **_layout(
            height=SMALL_CHART_HEIGHT,
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            yaxis=dict(categoryorder="total ascending"),
        )
    )
    fig.update_layout(title=dict(text=f"Top {limit} artists", font=dict(size=13, color=MUTED), x=0, xanchor="left"))
    return _apply_axes(fig)


st.set_page_config(
    page_title="Taste Map",
    layout="wide",
    page_icon="♪",
    initial_sidebar_state="collapsed",
)

st.markdown(PAGE_CSS, unsafe_allow_html=True)

profile, source_label, use_ai, from_upload = _load_profile()
portrait, _brief = _resolve_portrait(profile, source_label, use_ai)

library_paths = _library_playlist_paths()
library_summary = ""
if not from_upload and len(library_paths) >= 2:
    path_key = tuple(str(p.resolve()) for p in library_paths)
    library_summary = _cached_library_summary(path_key)

ai_note = f" · {portrait.source} portrait" if portrait.source != "template" else ""

st.markdown(
    '<p class="control-hint">Switch playlist above, or upload a fresh '
    '<a href="https://exportify.net" style="color:#f97316;">Exportify</a> CSV.</p>',
    unsafe_allow_html=True,
)

if library_summary:
    st.markdown(
        f'<p class="library-summary-label">Your library</p>'
        f'<p class="library-summary">{library_summary}</p>',
        unsafe_allow_html=True,
    )

st.markdown(
    f'<p class="hero-caption">Taste Map / {source_label}{ai_note}</p>',
    unsafe_allow_html=True,
)
st.markdown(f'<p class="hero-title">{portrait.title}</p>', unsafe_allow_html=True)
st.markdown(f'<p class="hero-label">{portrait.label}</p>', unsafe_allow_html=True)
st.markdown(f'<p class="interpretation">{portrait.interpretation}</p>', unsafe_allow_html=True)
st.markdown(_stat_strip(profile), unsafe_allow_html=True)
st.markdown(_mood_strip(profile), unsafe_allow_html=True)

st.markdown('<p class="section-label">Composition</p>', unsafe_allow_html=True)
genre_fig = genre_treemap(profile)
if genre_fig is None:
    st.warning("No genre data in this export.")
else:
    st.plotly_chart(
        genre_fig,
        width="stretch",
        height=CHART_HEIGHT,
        theme=None,
        config={"displayModeBar": False, "responsive": True},
    )

st.markdown('<p class="section-label">Structure</p>', unsafe_allow_html=True)
left, right = st.columns(2)
with left:
    artists_fig = top_artists_bar(profile)
    if artists_fig is None:
        st.warning("No artist data in this export.")
    else:
        st.plotly_chart(artists_fig, width="stretch", theme=None, config={"displayModeBar": False})

with right:
    era_fig = era_bar(profile)
    if era_fig is None:
        st.warning("No release dates in this export.")
    else:
        st.plotly_chart(era_fig, width="stretch", theme=None, config={"displayModeBar": False})

st.markdown(
    '<p class="footer-note">Deep-cuts index = 100 minus average Spotify popularity '
    "(higher means deeper cuts). Built as a portfolio demo — "
    '<a href="https://github.com/jmshall93-debug/taste-map" style="color: #f97316;">source on GitHub</a>.</p>',
    unsafe_allow_html=True,
)
