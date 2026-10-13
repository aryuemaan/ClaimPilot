"""Write the current demo kits (photos, bills, policy PDFs) to a folder.

Usage (from backend/):  python -m app.demo.export ../sample-data/kits
Handy for uploading the sample files from a phone during a live demo.
"""

import asyncio
import sys
from pathlib import Path

from .. import storage
from .seed import ensure_seeded


async def main(out: Path) -> None:
    await ensure_seeded()
    for kit in await storage.docs.list("samples"):
        folder = out / kit["key"]
        folder.mkdir(parents=True, exist_ok=True)
        for f in kit["files"]:
            data, _ = await storage.files.load(f["key"])
            (folder / f["name"]).write_bytes(data)
        (folder / "statement.txt").write_text(kit["statement"] + "\n", encoding="utf-8")
        policy = await storage.docs.get("policies", kit["policy_number"])
        pdf, _ = await storage.files.load(policy["pdf_key"])
        (folder / f"policy_{kit['policy_number']}.pdf").write_bytes(pdf)
        print(f"wrote {folder}")


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1] if len(sys.argv) > 1 else "../sample-data/kits").resolve()))
