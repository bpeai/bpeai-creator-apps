from __future__ import annotations

"""Creator technical content under ``references/content/`` (lightweight RAG).

Style shells live in ``references/style/``. Source PDFs/docs are hashed, extracted,
chunked, and stored in ``references/content_index.yaml`` so portal uploads can ship
text without binaries. Retrieval is keyword overlap — a supplement to Serper, not a
replacement.
"""

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import hashlib
import re

import yaml

from .pack_bootstrap import pack_dir, write_pack_file

CONTENT_INDEX_REL = "references/content_index.yaml"
CONTENT_DIRNAME = "content"
STYLE_DIRNAME = "style"
CONTENT_SUFFIXES = {".pdf", ".md", ".txt", ".csv"}
CHUNK_CHARS = 1400
CHUNK_OVERLAP = 180
MAX_PROMPT_CHARS = 8000
DEFAULT_CHUNK_LIMIT = 6

_STOP = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "onto",
        "are",
        "was",
        "were",
        "been",
        "have",
        "has",
        "had",
        "not",
        "but",
        "use",
        "used",
        "using",
        "per",
        "via",
    }
)

CREATOR_CONTENT_GUIDANCE = (
    "The following creator-provided documents are supplemental SME material. "
    "Continue to use industrial web search results. Prefer creator content for "
    "creator-specific facts; use web sources for additional or newer public information."
)

CONTENT_FOLDER_PROMPT = (
    "If you have creator technical PDFs or documents, copy them into "
    "`py/knowledge/{pack_id}/references/content/` (optional; empty is valid; "
    ".pdf / .md / .txt / .csv — not .docx), then re-run so they are indexed "
    "as supplemental LLM context. Style PPTX/PDF shells belong in "
    "`references/style/`. At the local_chat prompt enter system name and "
    "application/domain, for example: CIP return pump, biopharmaceutical."
)


def references_root(pack_path: Path | str) -> Path:
    return Path(pack_path) / "references"


def content_dir(pack_path: Path | str) -> Path:
    return references_root(pack_path) / CONTENT_DIRNAME


def style_dir(pack_path: Path | str) -> Path:
    return references_root(pack_path) / STYLE_DIRNAME


def content_index_path(pack_path: Path | str) -> Path:
    return Path(pack_path) / "references" / "content_index.yaml"


def ensure_nested_references(
    pack_id: str,
    *,
    py_root: Path | None = None,
) -> Path:
    """Create ``references/content/`` and ``references/style/``. Returns pack root."""
    root = pack_dir(pack_id, py_root=py_root)
    root.mkdir(parents=True, exist_ok=True)
    content_dir(root).mkdir(parents=True, exist_ok=True)
    style_dir(root).mkdir(parents=True, exist_ok=True)
    return root


def migrate_legacy_references(
    pack_id: str,
    *,
    py_root: Path | None = None,
) -> List[str]:
    """Move leftover files at ``references/`` root: PPTX → style/, other docs → content/.

    Does not overwrite existing destinations. Returns relative paths that moved.
    """
    root = pack_dir(pack_id, py_root=py_root)
    ref = references_root(root)
    if not ref.is_dir():
        ensure_nested_references(pack_id, py_root=py_root)
        return []

    ensure_nested_references(pack_id, py_root=py_root)
    style = style_dir(root)
    content = content_dir(root)
    moved: List[str] = []
    try:
        entries = list(ref.iterdir())
    except OSError:
        return []

    for item in entries:
        if not item.is_file():
            continue
        name = item.name
        if name in {"content_index.yaml", "content_index.yml"}:
            continue
        suffix = item.suffix.lower()
        if suffix == ".pptx":
            dest = style / name
            rel = f"references/style/{name}"
        elif suffix in CONTENT_SUFFIXES:
            dest = content / name
            rel = f"references/content/{name}"
        else:
            continue
        if dest.exists():
            continue
        item.rename(dest)
        moved.append(rel)
    return moved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 64), b""):
            digest.update(block)
    return digest.hexdigest()


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "pypdf is required to extract creator PDFs. Install bpeai-creator-sdk dependencies."
        ) from exc
    reader = PdfReader(str(path))
    parts: List[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts)


def extract_file_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(path)
    return path.read_text(encoding="utf-8", errors="replace")


def chunk_text(text: str, *, max_chars: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    cleaned = re.sub(r"\r\n?", "\n", text or "").strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]
    chunks: List[str] = []
    start = 0
    length = len(cleaned)
    step = max(max_chars - overlap, 1)
    while start < length:
        end = min(start + max_chars, length)
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start += step
    return chunks


def _list_content_files(folder: Path) -> List[Path]:
    if not folder.is_dir():
        return []
    out: List[Path] = []
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() in CONTENT_SUFFIXES:
            out.append(path)
    return out


def _load_index(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    return raw if isinstance(raw, dict) else {}


def index_is_current(pack_path: Path, index: Mapping[str, Any] | None = None) -> bool:
    """True when on-disk content files match the stored file hashes."""
    stored = dict(index) if isinstance(index, Mapping) else _load_index(content_index_path(pack_path))
    files = stored.get("files")
    if not isinstance(files, list):
        files = []
    by_name = {
        str(row.get("name") or ""): str(row.get("sha256") or "")
        for row in files
        if isinstance(row, Mapping)
    }
    current = _list_content_files(content_dir(pack_path))
    current_names = {p.name for p in current}
    if current_names != set(by_name.keys()):
        return False
    for path in current:
        if _sha256_file(path) != by_name.get(path.name):
            return False
    return True


def build_content_index(
    pack_id: str,
    *,
    py_root: Path | None = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Extract/chunk ``references/content/`` into ``content_index.yaml`` when hashes change."""
    root = ensure_nested_references(pack_id, py_root=py_root)
    index_path = content_index_path(root)
    existing = _load_index(index_path)
    if not force and existing and index_is_current(root, existing):
        return existing

    files_meta: List[Dict[str, str]] = []
    chunks: List[Dict[str, Any]] = []
    for path in _list_content_files(content_dir(root)):
        digest = _sha256_file(path)
        files_meta.append({"name": path.name, "sha256": digest})
        try:
            text = extract_file_text(path)
        except Exception:
            continue
        for i, piece in enumerate(chunk_text(text)):
            chunks.append({"source": path.name, "index": i, "text": piece})

    payload: Dict[str, Any] = {
        "version": 1,
        "files": files_meta,
        "chunks": chunks,
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    # write_pack_file joins pack_dir / filename — filename may include subdirs
    write_pack_file(
        pack_id,
        CONTENT_INDEX_REL,
        payload,
        py_root=py_root,
        draft=False,
        overwrite=True,
    )
    return payload


def content_index_from_payload(payload: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    content = payload.get("content")
    if isinstance(content, Mapping) and isinstance(content.get("content_index"), Mapping):
        return dict(content["content_index"])
    raw = payload.get("content_index")
    if isinstance(raw, Mapping):
        return dict(raw)
    return {}


def chunks_from_index(index: Mapping[str, Any] | None) -> List[Dict[str, Any]]:
    if not isinstance(index, Mapping):
        return []
    raw = index.get("chunks")
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for row in raw:
        if isinstance(row, Mapping) and str(row.get("text") or "").strip():
            out.append(dict(row))
    return out


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [t for t in tokens if len(t) >= 3 and t not in _STOP]


def retrieve_creator_chunks(
    index: Mapping[str, Any] | None,
    query_text: str,
    *,
    limit: int = DEFAULT_CHUNK_LIMIT,
    max_chars: int = MAX_PROMPT_CHARS,
) -> List[Dict[str, Any]]:
    chunks = chunks_from_index(index)
    if not chunks:
        return []
    query_tokens = _tokenize(query_text)
    if not query_tokens:
        selected = chunks[:limit]
    else:
        scored: List[tuple[int, Dict[str, Any]]] = []
        for row in chunks:
            words = set(_tokenize(str(row.get("text") or "")))
            score = sum(1 for t in query_tokens if t in words)
            scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], str(item[1].get("source") or "")))
        selected = [row for score, row in scored if score > 0][:limit]
        if not selected:
            selected = chunks[:limit]

    out: List[Dict[str, Any]] = []
    used = 0
    for row in selected:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        if used + len(text) > max_chars:
            remain = max_chars - used
            if remain < 200:
                break
            text = text[:remain].rstrip()
        out.append({**row, "text": text})
        used += len(text)
        if used >= max_chars:
            break
    return out


def format_creator_content_block(
    chunks: Sequence[Mapping[str, Any]],
    *,
    include_guidance: bool = True,
) -> str:
    if not chunks:
        return ""
    parts: List[str] = []
    if include_guidance:
        parts.append(CREATOR_CONTENT_GUIDANCE)
        parts.append("")
    parts.append("Creator reference content:")
    for row in chunks:
        source = str(row.get("source") or "document")
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        parts.append(f"\nSource: {source}\n{text}")
    return "\n".join(parts).strip()


def creator_content_prompt_block(
    index: Mapping[str, Any] | None,
    query_parts: Iterable[Any],
    *,
    limit: int = DEFAULT_CHUNK_LIMIT,
) -> str:
    query = " ".join(str(p) for p in query_parts if p)
    chunks = retrieve_creator_chunks(index, query, limit=limit)
    return format_creator_content_block(chunks)
