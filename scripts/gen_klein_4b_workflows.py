#!/usr/bin/env python3
"""Deprecated: Klein 4B/9B variants are unified in klein-t2i.json and klein-edit.json.

Entrypoint selects 4B vs 9B model filenames from VRAM tier at startup.
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "[INFO] gen_klein_4b_workflows.py is deprecated; "
        "use workflows/flux2/klein-t2i.json and klein-edit.json.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
