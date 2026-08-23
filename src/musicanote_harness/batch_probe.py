from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from .core import MusicHarness


def probe(path: str | Path) -> dict:
    path = Path(path)
    started = time.perf_counter()
    result = MusicHarness().parse(path)
    ir = result["score"]
    return {
        "status": "valid" if result["validation"]["valid"] else "invalid",
        "seconds": round(time.perf_counter() - started, 4),
        "validation": result["validation"],
        "metrics": {
            "parts": len(ir["parts"]),
            "measures": len(ir["measure_grid"]),
            "segments": len(ir["notated_note_segments"]),
            "sounding_events": len(ir["sounding_events"]),
            "harmonic_atoms": len(ir["harmonic_atoms"]),
        },
    }


def main() -> None:
    try:
        print(json.dumps(probe(sys.argv[1]), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "exception", "exception": type(exc).__name__, "message": str(exc)[:1000]}, ensure_ascii=False))
        raise SystemExit(2)


if __name__ == "__main__":
    main()

