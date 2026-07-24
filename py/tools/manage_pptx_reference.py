#!/usr/bin/env python3
"""List or replace SME knowledge-pack reference PPTX decks.

Examples (PowerShell):

  python py/tools/manage_pptx_reference.py --pack mixing list
  python py/tools/manage_pptx_reference.py --pack mixing replace `
    --src .\\attachments\\media_preparation_vessel_mixing_evaluation.pptx `
    --name media_preparation_vessel_mixing_evaluation.pptx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap() -> Path:
    tools = Path(__file__).resolve().parent
    py_root = tools.parent
    sdk = py_root / "libs" / "bpeai_creator_sdk" / "src"
    for p in (str(py_root), str(sdk)):
        if p not in sys.path:
            sys.path.insert(0, p)
    return py_root


def main() -> int:
    py_root = _bootstrap()
    from bpeai_creator_sdk.artifacts.reference_decks import (
        list_reference_decks,
        replace_reference_deck,
        resolve_reference_deck,
    )
    from bpeai_creator_sdk.sme import load_knowledge_pack

    parser = argparse.ArgumentParser(description="Manage knowledge-pack reference PPTX decks")
    parser.add_argument("--pack", default="mixing", help="Knowledge pack id (default: mixing)")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List reference decks for the pack")

    p_get = sub.add_parser("resolve", help="Resolve a deck path by name")
    p_get.add_argument("name", help="File name or relative path")

    p_rep = sub.add_parser("replace", help="Copy a PPTX into pack references/")
    p_rep.add_argument("--src", required=True, help="Source .pptx path")
    p_rep.add_argument("--name", default=None, help="Destination file name (default: source name)")
    p_rep.add_argument(
        "--no-outline",
        action="store_true",
        help="Do not update pptx_outline.yaml reference_decks",
    )

    args = parser.parse_args()
    pack = load_knowledge_pack(args.pack, py_root=py_root)

    if args.cmd == "list":
        rows = list_reference_decks(pack.path, outline=pack.pptx_outline)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"Pack: {pack.pack_id} ({pack.path})")
            for row in rows:
                flag = "declared" if row["declared"] else "extra"
                status = "ok" if row["exists"] else "MISSING"
                print(f"  [{status}/{flag}] {row['relative_path']}")
                print(f"             {row['path']}")
        return 0

    if args.cmd == "resolve":
        path = resolve_reference_deck(pack.path, args.name, outline=pack.pptx_outline)
        print(path)
        return 0

    if args.cmd == "replace":
        dest = replace_reference_deck(
            pack.path,
            args.src,
            dest_name=args.name,
            register_in_outline=not args.no_outline,
        )
        print(f"Replaced/updated: {dest}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
