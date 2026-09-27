"""Чтение чека: фото или голос, подчистка, запись в ml, JSON для кладовой.

Примеры:
    python -m receipts photo --group 2 --file чек.jpg
    python -m receipts voice --group 2 --file чек.wav
"""

from __future__ import annotations

import argparse
import json
import sys

from receipts.normalize import normalize_lines
from receipts.payload import to_payload
from receipts.photo import read_lines as read_photo
from receipts.store import DatabaseUnavailable, save_receipt
from receipts.voice import read_lines as read_voice


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m receipts",
        description="Чек с фото или голоса в схему ml",
    )
    sub = parser.add_subparsers(dest="source", required=True)

    for name, help_text in (("photo", "Фото чека"), ("voice", "Голосовой чек")):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--group", type=int, required=True, help="id_user_group")
        command.add_argument("--file", required=True, help="Путь к фото или аудио")

    args = parser.parse_args(argv)
    reader = read_photo if args.source == "photo" else read_voice
    try:
        lines = reader(args.file)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    items = normalize_lines(lines)
    payload = to_payload(items)

    try:
        payload["receipt_id"] = save_receipt(args.group, args.source, "\n".join(lines), items)
    except DatabaseUnavailable as exc:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        print(exc, file=sys.stderr)
        return 1

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
