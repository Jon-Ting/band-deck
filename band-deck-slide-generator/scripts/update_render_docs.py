#!/usr/bin/env python3
"""Update render-option documentation and schema from shared script constants.

Run this from the repository root after changing values in
``band_deck_generator.render_options``:

    python band-deck-slide-generator/scripts/update_render_docs.py
"""

from band_deck_generator.update_render_docs import update_render_contract


def main() -> int:
    """Run the render contract sync and report changed files."""
    changed = update_render_contract()
    for path in changed:
        print(f"updated: {path}")
    if not changed:
        print("render docs already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
