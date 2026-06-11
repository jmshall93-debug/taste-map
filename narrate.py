"""Template and optional LLM portraits from a taste brief."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum

from parse import TasteProfile


class StoryAngle(str, Enum):
    DEEP_WARREN = "deep_warren"
    ERA_LOCKED = "era_locked"
    GENRE_SCATTER = "genre_scatter"
    ARTIST_ANCHORED = "artist_anchored"
    MOOD_LED = "mood_led"
    MAINSTREAM_ADJACENT = "mainstream_adjacent"


@dataclass
class Portrait:
    title: str
    label: str
    interpretation: str
    source: str = "template"


def _top_genres_list(brief: dict, limit: int = 3) -> list[str]:
    shares = brief.get("genre_shares_top5") or {}
    return list(shares.keys())[:limit]


def _genre_phrase(brief: dict, limit: int = 3) -> str:
    genres = _top_genres_list(brief, limit)
    if not genres:
        return "a wide mix of sounds"
    if len(genres) == 1:
        return genres[0]
    if len(genres) == 2:
        return f"{genres[0]} and {genres[1]}"
    return f"{genres[0]}, {genres[1]}, and {genres[2]}"


def _genre_title(brief: dict) -> str:
    top = brief.get("top_genre")
    return top.title() if top else "Listening"


def _is_bright(brief: dict) -> bool:
    mood = brief.get("mood") or {}
    energy = mood.get("energy")
    valence = mood.get("valence")
    if energy is None or valence is None:
        return False
    return energy >= 0.6 and valence >= 0.55


def _is_quiet(brief: dict) -> bool:
    mood = brief.get("mood") or {}
    energy = mood.get("energy")
    valence = mood.get("valence")
    if energy is None:
        return False
    if energy < 0.45:
        return True
    return energy < 0.5 and (valence or 0.5) < 0.4


def _pick_story_angle(profile: TasteProfile, brief: dict) -> StoryAngle:
    s = profile.stats
    mood = brief.get("mood") or {}

    if profile.obscurity_score < 40:
        return StoryAngle.MAINSTREAM_ADJACENT

    if s.mood_contrast and mood.get("contrast"):
        contrast_lower = s.mood_contrast.lower()
        distinct_mood = _is_bright(brief) or _is_quiet(brief) or any(
            phrase in contrast_lower
            for phrase in ("inward", "kinetic but", "bright and", "quiet and", "soft but")
        )
        if distinct_mood:
            return StoryAngle.MOOD_LED

    if s.top_artist_share_pct >= 8:
        return StoryAngle.ARTIST_ANCHORED

    if brief.get("era_outlier") or s.top_era_share_pct >= 45:
        return StoryAngle.ERA_LOCKED

    if profile.obscurity_score >= 65:
        return StoryAngle.DEEP_WARREN

    if brief.get("genre_scattered"):
        return StoryAngle.GENRE_SCATTER

    return StoryAngle.ERA_LOCKED


def _title_for_angle(angle: StoryAngle, profile: TasteProfile, brief: dict) -> str:
    genre = _genre_title(brief)
    era = brief.get("top_era")

    if angle == StoryAngle.MAINSTREAM_ADJACENT:
        if era:
            return f"{genre}, {era} Favourites"
        return f"{genre} on Repeat"

    if angle == StoryAngle.MOOD_LED:
        if _is_bright(brief):
            return f"{genre} in Full Colour"
        if _is_quiet(brief):
            return f"{genre} in the Margins"
        return f"{genre}, Steady Motion"

    if angle == StoryAngle.GENRE_SCATTER:
        return f"Wide Lens, {era} Centre" if era else "A Scattered Library"

    if angle == StoryAngle.ARTIST_ANCHORED:
        artist = brief.get("top_artist")
        if artist:
            return f"{artist}, {genre} Orbit"
        return f"{genre} on Repeat"

    if angle == StoryAngle.ERA_LOCKED and era:
        return f"{genre}, {era} Weight"

    if profile.obscurity_score >= 65:
        return f"{genre} in the Margins"

    if _is_bright(brief):
        return f"{genre} in Full Colour"
    if _is_quiet(brief):
        return f"{genre} at Low Light"
    return f"{genre}, {era} Tilt" if era else f"{genre} at Low Light"


def _pick_phrase(key: str, options: list[str]) -> str:
    if not options:
        return ""
    return options[hash(key) % len(options)]


def _scatter_clause(brief: dict, angle: StoryAngle, playlist: str) -> str:
    """Mid-label genre spread hint — omitted when another story angle already leads."""
    if brief.get("genre_concentrated") and brief.get("top_genre"):
        return f"with {brief['top_genre']} carrying real weight, "
    if not brief.get("genre_scattered"):
        return ""
    if angle == StoryAngle.GENRE_SCATTER:
        return ""
    if angle in (
        StoryAngle.ERA_LOCKED,
        StoryAngle.MOOD_LED,
        StoryAngle.ARTIST_ANCHORED,
        StoryAngle.MAINSTREAM_ADJACENT,
    ):
        return ""
    options = ["", "", "several lanes in play, ", "genres kept loose, "]
    return _pick_phrase(f"scatter:{playlist}", options)


def _human_label(profile: TasteProfile, brief: dict, angle: StoryAngle) -> str:
    genres = _genre_phrase(brief, 3)
    era = brief.get("top_era")
    playlist = brief.get("playlist", "")

    era_clause = ""
    if era and brief.get("era_outlier"):
        era_clause = f"A {era}-heavy collection, "
    elif era and brief.get("top_era_share_pct", 0) >= 40:
        era_clause = f"Rooted in the {era}, "

    scatter_clause = _scatter_clause(brief, angle, playlist)

    if angle == StoryAngle.MOOD_LED and _is_quiet(brief):
        endings = ["built for low light.", "meant for quiet hours.", "a slow-burn stack."]
    elif angle == StoryAngle.MOOD_LED and _is_bright(brief):
        endings = ["sunny and kinetic throughout.", "bright end of the dial.", "more lift than gloom."]
    elif angle == StoryAngle.ERA_LOCKED:
        endings = ["decade-first, genre-second.", "era sets the frame.", "genre follows the decade."]
    elif angle == StoryAngle.GENRE_SCATTER:
        endings = ["eclectic by design.", "taste spread wide.", "built for browsing."]
    elif angle == StoryAngle.ARTIST_ANCHORED:
        endings = ["favourites on repeat.", "personal canon energy.", "names over novelty."]
    elif angle == StoryAngle.MAINSTREAM_ADJACENT:
        endings = ["chart-adjacent, familiar ground.", "hits and comfort picks.", "the accessible shelf."]
    elif angle == StoryAngle.DEEP_WARREN:
        endings = ["wide lanes, deep cuts.", "collector's spread.", "curiosity over consensus."]
    else:
        endings = ["genre-led, library-first.", "taste over trend.", "built to browse."]

    ending = _pick_phrase(playlist or genres, endings)
    text = f"{era_clause}pulled toward {genres}, {scatter_clause}{ending}".replace(" ,", ",")
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


def _depth_close(profile: TasteProfile, playlist_name: str = "") -> str:
    key = playlist_name or str(profile.obscurity_score)
    if profile.obscurity_score >= 65:
        return _pick_phrase(
            key,
            [
                "More crate than chart.",
                "Built from quieter corners, not charts.",
                "The algorithm rarely visits here.",
            ],
        )
    if profile.obscurity_score >= 40:
        return _pick_phrase(
            key,
            [
                "A balance of favourites and hidden corners.",
                "Mixes the familiar with the overlooked.",
                "Some hits, plenty of depth.",
            ],
        )
    return _pick_phrase(
        key,
        [
            "Comfortably in the mainstream lane.",
            "Anchored in well-known records.",
            "Built from the middle of the road.",
        ],
    )


def _interpretation_for_angle(
    angle: StoryAngle, profile: TasteProfile, brief: dict
) -> str:
    genres = _genre_phrase(brief, 3)
    era = brief.get("top_era")
    artist = brief.get("top_artist")
    mood = brief.get("mood") or {}
    sentences: list[str] = []

    if angle == StoryAngle.DEEP_WARREN:
        sentences.append(
            f"The centre of gravity is {genres} — a collector's map, not a chart playlist."
        )
    elif angle == StoryAngle.ERA_LOCKED and era:
        era_in_label = (
            not brief.get("era_outlier")
            and brief.get("top_era_share_pct", 0) >= 40
        )
        if era_in_label:
            sentences.append(
                f"The weight falls on {genres} — decade-first listening, not genre-hopping."
            )
        else:
            sentences.append(
                f"This playlist lives in the {era}: {genres} set the tone, decade first."
            )
    elif angle == StoryAngle.GENRE_SCATTER:
        sentences.append(
            f"No single genre owns this library — {genres} share the frame, with plenty of drift between."
        )
    elif angle == StoryAngle.ARTIST_ANCHORED and artist:
        sentences.append(
            f"{artist} keeps returning here, anchoring a {genres} collection that feels personal, not algorithmic."
        )
    elif angle == StoryAngle.MOOD_LED:
        contrast = mood.get("contrast")
        if _is_bright(brief):
            sentences.append(
                f"Bright and kinetic throughout — {genres} with more lift than gloom."
            )
        elif _is_quiet(brief):
            sentences.append(
                f"Quiet and inward — {genres} meant for low light and long listens."
            )
        elif contrast:
            sentences.append(
                f"The mood runs {contrast.lower()} — {genres} with tension between feel and tempo."
            )
        else:
            sentences.append(f"Feel leads genre here — {genres} with a consistent emotional through-line.")
    elif angle == StoryAngle.MAINSTREAM_ADJACENT:
        sentences.append(
            f"Familiar ground: {genres}, with fewer deep cuts than the rest of the library."
        )
    else:
        sentences.append(f"The centre of gravity is {genres}.")

    # Middle sentence — one woven detail, at most one number
    if angle == StoryAngle.ARTIST_ANCHORED and artist and brief.get("top_artist_tracks"):
        count = brief["top_artist_tracks"]
        sentences.append(f"{artist} shows up {count} times — a clear favourite in rotation.")
    elif angle == StoryAngle.ERA_LOCKED and era and not brief.get("era_outlier"):
        pct = brief.get("top_era_share_pct")
        if pct and pct >= 35:
            sentences.append(f"Roughly half the list was made in the {era}.")
    elif mood.get("contrast") and angle != StoryAngle.MOOD_LED:
        sentences.append(mood["contrast"].capitalize() + ".")
    elif artist and angle != StoryAngle.ARTIST_ANCHORED:
        sentences.append(f"{artist} is the most repeated name here.")

    sentences.append(_depth_close(profile, brief.get("playlist", "")))
    return " ".join(sentences)


def template_portrait(profile: TasteProfile, brief: dict) -> Portrait:
    """Editorial copy from computed stats — natural language, not stat chains."""
    angle = _pick_story_angle(profile, brief)
    return Portrait(
        title=_title_for_angle(angle, profile, brief),
        label=_human_label(profile, brief, angle),
        interpretation=_interpretation_for_angle(angle, profile, brief),
        source="template",
    )


def template_library_summary(summary: dict) -> str:
    """Brief cross-playlist overview — editorial, not a table."""
    if not summary:
        return ""

    n = summary["playlist_count"]
    tracks = summary["total_tracks"]
    lead = f"{n} playlists mapped ({tracks:,} tracks). "

    common_genre = summary.get("common_genre")
    common_era = summary.get("common_era")
    common_count = summary.get("common_genre_count", 0)

    if common_genre and common_count >= 2:
        thread = f"Most centre on {common_genre}"
        if common_era and common_count >= n // 2 + 1:
            thread += f" and the {common_era}"
        lead += thread + ". "
    elif common_era:
        lead += f"Most lean toward the {common_era}. "

    extras: list[str] = []

    outlier = summary.get("outlier_name")
    outlier_genre = summary.get("outlier_genre")
    outlier_era = summary.get("outlier_era")
    if outlier and outlier_genre:
        era_bit = f", {outlier_era}" if outlier_era and outlier_era != common_era else ""
        extras.append(f"{outlier} breaks the pattern ({outlier_genre}{era_bit})")

    quietest = summary.get("quietest")
    brightest = summary.get("brightest")
    if quietest and brightest and quietest != brightest:
        extras.append(f"{quietest} is the quietest; {brightest} the brightest")
    elif quietest:
        extras.append(f"{quietest} is the quietest stack")
    elif brightest:
        extras.append(f"{brightest} is the brightest stack")

    mainstream = summary.get("mainstream_name")
    if (
        mainstream
        and summary.get("mainstream_deep_cuts", 100) < 60
        and mainstream != outlier
    ):
        extras.append(f"{mainstream} sits closest to the mainstream")

    if extras:
        lead += ". ".join(extras) + "."

    if summary.get("avg_deep_cuts", 0) >= 70:
        lead += " " + _pick_phrase(
            str(summary.get("playlist_count", 0)),
            [
                "A collection that mostly digs, not streams.",
                "Overall, more discovery than comfort picks.",
                "Built for browsing, not background play.",
            ],
        )

    return lead.strip()


def llm_configured(groq_api_key: str | None, ollama_model: str | None) -> bool:
    return bool(groq_api_key or ollama_model)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _chat_complete(messages: list[dict], groq_api_key: str | None, ollama_model: str | None) -> tuple[str, str]:
    """Returns (body, provider name)."""
    if groq_api_key:
        payload = json.dumps(
            {
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": 0.6,
                "max_tokens": 320,
            }
        ).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"], "groq"

    assert ollama_model
    payload = json.dumps(
        {"model": ollama_model, "messages": messages, "stream": False}
    ).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    return data["message"]["content"], "ollama"


_AI_SYSTEM_PROMPT = """You write short editorial music taste portraits — like a caption in a well-edited magazine, not a dashboard summary.

Use ONLY the facts in the playlist brief. Do not invent tracks, artists, or numbers.

Return valid JSON only:
{"title": "...", "label": "...", "interpretation": "..."}

Voice rules:
- Title: 3–6 words, evocative (e.g. "Ambient in the Margins", "Art Rock, 1990s Weight").
- Label: one flowing sentence — no slash lists, no comma-separated tags.
- Interpretation: 2–3 sentences max. Lead with character and feel; weave in at most ONE number if it earns its place.
- Prefer phrases like "centre of gravity", "off the algorithm", "low light" over raw statistics.

Forbidden phrases: "genre tags", "distinct genres", "tracks sit in", "deep-cuts index", "X% of genre", "appears most (".

Example A (quiet electronic):
{"title": "Ambient in the Margins", "label": "A 2010s-heavy set pulled toward ambient and downtempo, mostly off the algorithm.", "interpretation": "Quiet and inward — music for low light and long listens. The centre of gravity is ambient and idm, with little interest in the mainstream lane. Mostly off the algorithm — more crate than chart."}

Example B (bright dance):
{"title": "Disco House in Full Colour", "label": "Pulled toward disco house and afropop, bright and kinetic throughout.", "interpretation": "Bright and driving — this is a sunny, danceable stack, not a late-night drift. Disco house and afropop set the tone. A balance of favourites and hidden corners."}
"""


def ai_portrait(
    brief: dict,
    groq_api_key: str | None = None,
    ollama_model: str | None = None,
) -> Portrait | None:
    """Optional LLM portrait. Returns None on missing config or failure."""
    if not llm_configured(groq_api_key, ollama_model):
        return None

    user = f"Playlist facts:\n{json.dumps(brief, indent=2)}"
    messages = [{"role": "system", "content": _AI_SYSTEM_PROMPT}, {"role": "user", "content": user}]

    try:
        raw, provider = _chat_complete(messages, groq_api_key, ollama_model)
        parsed = _extract_json(raw)
        return Portrait(
            title=str(parsed["title"]).strip(),
            label=str(parsed["label"]).strip(),
            interpretation=str(parsed["interpretation"]).strip(),
            source=provider,
        )
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError, TimeoutError):
        return None
