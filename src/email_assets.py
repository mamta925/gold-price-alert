from __future__ import annotations

from pathlib import Path

GOLD_HEADER_CID = "gold-header@gold-price-alert"
GOLD_HEADER_FILENAME = "gold-header.png"
GOLD_HEADER_PATH = Path(__file__).resolve().parent.parent / "assets" / GOLD_HEADER_FILENAME
GOLD_HEADER_IMAGE_SRC = f"cid:{GOLD_HEADER_CID}"
