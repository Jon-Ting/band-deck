"""Regenerate all marp.md files from canonical YAML files in data/songs/.

Usage: uv run python scripts/regenerate_marp.py
Requires: uv sync (run from project root)"""

import glob
import os

import yaml

from src.utils.marp_generator import MarpOptions, generate_marp
from src.utils.preview import _song_from_payload


def _build_flat_song(raw: dict) -> dict:
    meta = raw.get("metadata", {})
    chordpro = raw.get("normalised_chordpro", {})
    arr = raw.get("arrangement", {})

    song = dict(meta)
    song["sections"] = chordpro.get("sections", {})

    seq = arr.get("sequence", [])
    song["arrangement"] = [
        e["section"] if isinstance(e, dict) else e for e in seq
    ]

    sources = raw.get("sources", {}).get("lyrics_chords") or []
    song["source_urls"] = [s["url"] for s in sources if s.get("url")]

    return song


def regenerate_all(songs_glob: str = "data/songs/**/*.yaml") -> list[str]:
    paths = []
    for path in sorted(glob.glob(songs_glob, recursive=True)):
        with open(path) as f:
            raw = yaml.safe_load(f)

        flat = _build_flat_song(raw)

        try:
            song = _song_from_payload({"song": flat})
        except (ValueError, KeyError, TypeError) as e:
            print(f"ERROR {path}: {e}")
            continue

        style = (raw.get("deck") or {}).get("style", "practice")
        marp = generate_marp(song, style=style, options=MarpOptions())

        out = os.path.splitext(path)[0] + ".marp.md"
        with open(out, "w") as f:
            f.write(marp)
        print(f"Wrote {out}")
        paths.append(out)

    return paths


if __name__ == "__main__":
    regenerate_all()
