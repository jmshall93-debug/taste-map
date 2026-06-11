"""Load Exportify-style Spotify CSV exports and derive taste-map stats."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# Column names we expect (Exportify); loader maps variants to these.
COL_TRACK = "track_name"
COL_ARTIST = "artist_names"
COL_RELEASE = "release_date"
COL_POPULARITY = "popularity"
COL_GENRES = "genres"
COL_ENERGY = "energy"
COL_DANCEABILITY = "danceability"
COL_VALENCE = "valence"
COL_TEMPO = "tempo"

_COLUMN_ALIASES = {
    "track name": COL_TRACK,
    "artist name(s)": COL_ARTIST,
    "artist names": COL_ARTIST,
    "release date": COL_RELEASE,
    "popularity": COL_POPULARITY,
    "genres": COL_GENRES,
    "energy": COL_ENERGY,
    "danceability": COL_DANCEABILITY,
    "valence": COL_VALENCE,
    "tempo": COL_TEMPO,
}


@dataclass
class TasteStats:
    """Derived concentration and mood stats for copy + LLM briefs."""

    top_genre: str | None
    top_genre_share_pct: float
    genre_shares_top5: dict[str, float]
    unique_genres: int
    top_era: str | None
    top_era_share_pct: float
    era_span_decades: int
    top_artist: str | None
    top_artist_tracks: int
    top_artist_share_pct: float
    top5_artists_share_pct: float
    tracks_per_artist: float
    obscurity_tier: str
    mood_energy: str | None
    mood_valence: str | None
    mood_contrast: str | None


@dataclass
class TasteProfile:
    """Computed stats ready for charts and copy."""

    track_count: int
    genre_weights: pd.Series  # genre -> number of tracks tagged
    era_buckets: pd.Series  # decade label -> track count
    top_artists: pd.Series  # artist -> track count
    artist_count: int
    avg_popularity: float
    obscurity_score: float  # 100 - avg popularity (higher = deeper cuts)
    taste_label: str
    stats: TasteStats
    avg_energy: float | None = None
    avg_danceability: float | None = None
    avg_valence: float | None = None
    avg_tempo: float | None = None


def load_csv(path: str | Path) -> pd.DataFrame:
    """Read CSV and normalize column names."""
    df = pd.read_csv(path)
    rename = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in _COLUMN_ALIASES:
            rename[col] = _COLUMN_ALIASES[key]
    df = df.rename(columns=rename)

    missing = {COL_TRACK, COL_ARTIST, COL_RELEASE, COL_GENRES} - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {', '.join(sorted(missing))}")

    if COL_POPULARITY not in df.columns:
        df[COL_POPULARITY] = 0

    df[COL_POPULARITY] = pd.to_numeric(df[COL_POPULARITY], errors="coerce").fillna(0)
    df[COL_RELEASE] = pd.to_datetime(df[COL_RELEASE], errors="coerce")
    return df


def _split_list(value: object, sep: str) -> list[str]:
    if pd.isna(value) or not str(value).strip():
        return []
    return [part.strip() for part in str(value).split(sep) if part.strip()]


def _genre_weights(df: pd.DataFrame) -> pd.Series:
    rows: list[str] = []
    for raw in df[COL_GENRES]:
        rows.extend(_split_list(raw, ","))
    if not rows:
        return pd.Series(dtype=int)
    counts = pd.Series(rows).value_counts()
    return counts.sort_values(ascending=False)


def _era_buckets(df: pd.DataFrame) -> pd.Series:
    years = df[COL_RELEASE].dt.year.dropna().astype(int)
    if years.empty:
        return pd.Series(dtype=int)

    decades = (years // 10) * 10
    labels = decades.astype(str) + "s"
    return labels.value_counts().sort_index()


def _all_artists(df: pd.DataFrame) -> list[str]:
    rows: list[str] = []
    for raw in df[COL_ARTIST]:
        rows.extend(_split_list(raw, ";"))
    return rows


def _top_artists(df: pd.DataFrame, limit: int = 15) -> pd.Series:
    rows = _all_artists(df)
    if not rows:
        return pd.Series(dtype=int)
    return pd.Series(rows).value_counts().head(limit)


def _dominant_decade(era_buckets: pd.Series) -> str:
    if era_buckets.empty:
        return "mixed eras"
    decade = era_buckets.idxmax()
    return f"{decade}-leaning"


def _obscurity_tier(score: float) -> str:
    if score >= 65:
        return "deep-cut listener"
    if score >= 40:
        return "balanced crate-digger"
    return "mainstream-leaning"


def _avg_feature(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return None
    return round(float(values.mean()), 2)


def _mood_energy_label(value: float | None) -> str | None:
    if value is None:
        return None
    if value < 0.4:
        return "low"
    if value < 0.65:
        return "medium"
    return "high"


def _mood_valence_label(value: float | None) -> str | None:
    if value is None:
        return None
    if value < 0.35:
        return "dark"
    if value < 0.55:
        return "neutral"
    return "bright"


def _mood_contrast(energy: float | None, valence: float | None) -> str | None:
    if energy is None or valence is None:
        return None
    if energy >= 0.6 and valence < 0.4:
        return "kinetic but inward — high energy, low valence"
    if energy >= 0.6 and valence >= 0.6:
        return "bright and driving — high energy and valence"
    if energy < 0.45 and valence < 0.4:
        return "quiet and inward — low energy, low valence"
    if energy < 0.45 and valence >= 0.55:
        return "soft but warm — low energy, higher valence"
    if energy >= 0.55 and valence < 0.45:
        return "forward motion without much glow"
    return None


def _compute_stats(
    track_count: int,
    genre_weights: pd.Series,
    era_buckets: pd.Series,
    top_artists: pd.Series,
    artist_count: int,
    obscurity_score: float,
    avg_energy: float | None,
    avg_valence: float | None,
) -> TasteStats:
    if genre_weights.empty:
        top_genre = None
        top_genre_share = 0.0
        genre_top5: dict[str, float] = {}
        unique_genres = 0
    else:
        total_tags = float(genre_weights.sum())
        shares = (genre_weights / total_tags * 100).round(1)
        top_genre = str(shares.index[0])
        top_genre_share = float(shares.iloc[0])
        genre_top5 = {str(k): float(v) for k, v in shares.head(5).items()}
        unique_genres = len(genre_weights)

    if era_buckets.empty:
        top_era = None
        top_era_share = 0.0
        era_span = 0
    else:
        top_era = str(era_buckets.idxmax())
        top_era_share = round(float(era_buckets.max()) / track_count * 100, 1)
        era_span = len(era_buckets)

    if top_artists.empty:
        top_artist = None
        top_artist_tracks = 0
        top_artist_share = 0.0
        top5_share = 0.0
    else:
        top_artist = str(top_artists.index[0])
        top_artist_tracks = int(top_artists.iloc[0])
        top_artist_share = round(top_artist_tracks / track_count * 100, 1)
        top5_share = round(float(top_artists.head(5).sum()) / track_count * 100, 1)

    tracks_per_artist = round(track_count / artist_count, 1) if artist_count else 0.0

    return TasteStats(
        top_genre=top_genre,
        top_genre_share_pct=top_genre_share,
        genre_shares_top5=genre_top5,
        unique_genres=unique_genres,
        top_era=top_era,
        top_era_share_pct=top_era_share,
        era_span_decades=era_span,
        top_artist=top_artist,
        top_artist_tracks=top_artist_tracks,
        top_artist_share_pct=top_artist_share,
        top5_artists_share_pct=top5_share,
        tracks_per_artist=tracks_per_artist,
        obscurity_tier=_obscurity_tier(obscurity_score),
        mood_energy=_mood_energy_label(avg_energy),
        mood_valence=_mood_valence_label(avg_valence),
        mood_contrast=_mood_contrast(avg_energy, avg_valence),
    )


def _taste_label(genre_weights: pd.Series, era_buckets: pd.Series, obscurity_score: float) -> str:
    if genre_weights.empty:
        return "Listening library portrait"

    top_genres = genre_weights.head(3).index.tolist()
    genre_phrase = " / ".join(top_genres)
    decade_phrase = _dominant_decade(era_buckets)
    tier = _obscurity_tier(obscurity_score)
    return f"{decade_phrase}, {genre_phrase}, {tier}"


def narrative_brief(profile: TasteProfile, playlist_name: str) -> dict:
    """Structured facts for templates and optional LLM — no raw track rows."""
    s = profile.stats
    brief = {
        "playlist": playlist_name,
        "track_count": profile.track_count,
        "artist_count": profile.artist_count,
        "tracks_per_artist": s.tracks_per_artist,
        "avg_popularity": profile.avg_popularity,
        "deep_cuts_index": profile.obscurity_score,
        "obscurity_tier": s.obscurity_tier,
        "top_genre": s.top_genre,
        "top_genre_share_pct": s.top_genre_share_pct,
        "genre_shares_top5": s.genre_shares_top5,
        "unique_genres": s.unique_genres,
        "top_era": s.top_era,
        "top_era_share_pct": s.top_era_share_pct,
        "era_span_decades": s.era_span_decades,
        "era_distribution": {str(k): int(v) for k, v in profile.era_buckets.items()},
        "top_artist": s.top_artist,
        "top_artist_tracks": s.top_artist_tracks,
        "top_artist_share_pct": s.top_artist_share_pct,
        "top5_artists_share_pct": s.top5_artists_share_pct,
        "top_artists": {str(k): int(v) for k, v in profile.top_artists.head(8).items()},
        "genre_concentrated": s.top_genre_share_pct >= 20,
        "genre_scattered": s.top_genre_share_pct < 15,
        "era_outlier": s.top_era_share_pct >= 50,
    }
    if profile.avg_energy is not None:
        brief["mood"] = {
            "energy": profile.avg_energy,
            "danceability": profile.avg_danceability,
            "valence": profile.avg_valence,
            "tempo_bpm": profile.avg_tempo,
            "energy_tier": s.mood_energy,
            "valence_tier": s.mood_valence,
            "contrast": s.mood_contrast,
        }
    return brief


def summarize_library(entries: list[tuple[str, TasteProfile]]) -> dict:
    """Cross-playlist facts when multiple exports are available locally."""
    if len(entries) < 2:
        return {}

    briefs = [(name, narrative_brief(profile, name)) for name, profile in entries]
    total_tracks = sum(b["track_count"] for _, b in briefs)
    avg_deep_cuts = round(
        sum(b["deep_cuts_index"] for _, b in briefs) / len(briefs), 1
    )

    top_genres = [b["top_genre"] for _, b in briefs if b.get("top_genre")]
    genre_counts = Counter(top_genres)
    common_genre = genre_counts.most_common(1)[0][0] if genre_counts else None

    top_eras = [b["top_era"] for _, b in briefs if b.get("top_era")]
    era_counts = Counter(top_eras)
    common_era = era_counts.most_common(1)[0][0] if era_counts else None

    outlier_name = None
    outlier_genre = None
    outlier_era = None
    for name, brief in briefs:
        genre = brief.get("top_genre")
        if genre and genre_counts[genre] == 1:
            outlier_name = name
            outlier_genre = genre
            outlier_era = brief.get("top_era")
            break

    quietest = None
    quietest_energy = None
    brightest = None
    brightest_valence = None
    for name, brief in briefs:
        mood = brief.get("mood") or {}
        energy = mood.get("energy")
        valence = mood.get("valence")
        if energy is not None and (quietest_energy is None or energy < quietest_energy):
            quietest = name
            quietest_energy = energy
        if valence is not None and (brightest_valence is None or valence > brightest_valence):
            brightest = name
            brightest_valence = valence

    mainstream = min(briefs, key=lambda item: item[1]["deep_cuts_index"])

    return {
        "playlist_count": len(briefs),
        "total_tracks": total_tracks,
        "avg_deep_cuts": avg_deep_cuts,
        "common_genre": common_genre,
        "common_era": common_era,
        "common_genre_count": genre_counts[common_genre] if common_genre else 0,
        "outlier_name": outlier_name,
        "outlier_genre": outlier_genre,
        "outlier_era": outlier_era,
        "quietest": quietest,
        "brightest": brightest,
        "mainstream_name": mainstream[0],
        "mainstream_deep_cuts": mainstream[1]["deep_cuts_index"],
        "playlist_names": [name for name, _ in briefs],
    }


def analyze(df: pd.DataFrame) -> TasteProfile:
    """Turn a normalized dataframe into chart-ready stats."""
    genre_weights = _genre_weights(df)
    era_buckets = _era_buckets(df)
    top_artists = _top_artists(df)
    artists = _all_artists(df)
    avg_popularity = float(df[COL_POPULARITY].mean())
    obscurity_score = round(100 - avg_popularity, 1)
    avg_energy = _avg_feature(df, COL_ENERGY)
    avg_valence = _avg_feature(df, COL_VALENCE)

    return TasteProfile(
        track_count=len(df),
        genre_weights=genre_weights,
        era_buckets=era_buckets,
        top_artists=top_artists,
        artist_count=len(set(artists)),
        avg_popularity=round(avg_popularity, 1),
        obscurity_score=obscurity_score,
        taste_label=_taste_label(genre_weights, era_buckets, obscurity_score),
        stats=_compute_stats(
            len(df),
            genre_weights,
            era_buckets,
            top_artists,
            len(set(artists)),
            obscurity_score,
            avg_energy,
            avg_valence,
        ),
        avg_energy=avg_energy,
        avg_danceability=_avg_feature(df, COL_DANCEABILITY),
        avg_valence=avg_valence,
        avg_tempo=_avg_feature(df, COL_TEMPO),
    )


def analyze_file(path: str | Path) -> TasteProfile:
    return analyze(load_csv(path))


if __name__ == "__main__":
    default = Path(__file__).parent / "data" / "Liked_Songs.csv"
    profile = analyze_file(default)
    brief = narrative_brief(profile, "Liked Songs")
    print(f"Tracks: {profile.track_count}")
    print(f"Label:  {profile.taste_label}")
    print(f"Top genre share: {profile.stats.top_genre_share_pct}%")
    print(f"Brief keys: {list(brief.keys())}")
