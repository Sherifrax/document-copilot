"""Convert downloaded HTML filings to Markdown with Docling."""

from __future__ import annotations

import json
from pathlib import Path

from docling.document_converter import DocumentConverter

DATA_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = DATA_DIR / "downloads"
MARKDOWN_DIR = DATA_DIR / "markdown"
MANIFEST_NAME = "manifest.json"


def markdown_path(source_path: Path) -> Path:
    relative_path = source_path.relative_to(DOWNLOADS_DIR)
    return (MARKDOWN_DIR / relative_path).with_suffix(".md")


def convert_filings() -> int:
    source_paths = sorted(
        path
        for path in DOWNLOADS_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in {".htm", ".html"}
    )
    converter = DocumentConverter()

    for index, source_path in enumerate(source_paths, start=1):
        output_path = markdown_path(source_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[{index}/{len(source_paths)}] {source_path.relative_to(DOWNLOADS_DIR)}")
        converter.convert(source_path).document.save_as_markdown(output_path)

    return len(source_paths)


def write_markdown_manifest() -> None:
    source_manifest_path = DOWNLOADS_DIR / MANIFEST_NAME
    manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))

    for filing in manifest["filings"]:
        filing["local_path"] = str(Path(filing["local_path"]).with_suffix(".md"))

    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    (MARKDOWN_DIR / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    converted_count = convert_filings()
    write_markdown_manifest()
    print(f"Converted {converted_count} files into {MARKDOWN_DIR}")


if __name__ == "__main__":
    main()
