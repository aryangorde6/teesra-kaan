"""The recorded warning lines: the studio saves them, the page plays them in place of the browser's voice.

Each line is `<id>.m4a` in config.voice_dir(), next to `<id>.json` with the words it was recorded
for. A line whose words have changed since is left out, so the page never speaks old words.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config
from .messages import voice_lines


def audio_path(line_id: str) -> Path:
    return config.voice_dir() / f"{line_id}.m4a"


def meta_path(line_id: str) -> Path:
    return config.voice_dir() / f"{line_id}.json"


def recorded_words(line_id: str) -> list[str] | None:
    """The words this line's saved take says, or None if it isn't recorded."""
    if not (audio_path(line_id).is_file() and meta_path(line_id).is_file()):
        return None
    return json.loads(meta_path(line_id).read_text(encoding="utf-8")).get("lines")


def playable() -> dict[str, str]:
    """Each line recorded for the words the page shows now → a version, so the browser's cache never
    plays an earlier take."""
    return {line_id: str(audio_path(line_id).stat().st_mtime_ns)
            for line_id, line in voice_lines().items() if recorded_words(line_id) == line["lines"]}
