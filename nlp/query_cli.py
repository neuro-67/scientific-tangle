"""CLI to test QuerySpec parsing."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Make imports work when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from nlp.query.parser import QuerySpecParser


def _load_env_file(path: Path) -> None:
    """Minimal .env loader without extra dependencies."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a natural-language question into QuerySpec")
    parser.add_argument("question", help="Question to parse")
    args = parser.parse_args()

    _load_env_file(Path(__file__).parent.parent / ".env")

    # Force UTF-8 output on Windows terminals
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    spec = QuerySpecParser().parse(args.question)
    print(json.dumps(spec.model_dump(by_alias=True), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
