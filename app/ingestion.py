
import hashlib
import io
import json
import logging
import re
import threading
from pathlib import Path

import faiss
import numpy as np
import pymupdf
from docx import Document as DocxDocument

from app.config import settings


logger = logging.getLogger(__name__)

_index_lock = threading.RLock()

INDEX_FILE = settings.FAISS_INDEX_PATH / "documents.index"
METADATA_FILE = settings.FAISS_INDEX_PATH / "metadata.json"


def calculate_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def save_local_file(
    file_bytes: bytes,
    filename: str,
    document_id: str
) -> str:
    directory = settings.UPLOAD_DIR / document_id
    directory.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(
        r"[^a-zA-Z0-9._-]",
        "_",
        Path(filename).name
    )

    if not safe_name:
        safe_name = "document"

    path = directory / safe_name
    path.write_bytes(file_bytes)

    return str(path)


def delete_local_file(storage_path: str):
    path = Path(storage_path)

    if path.exists() and path.is_file():
        path.unlink()

    if path.parent.exists():
        try:
            path.parent.rmdir()
        except OSError:
            pass


def extract_text(file_bytes: bytes, filename: str) -> str:
    extension = Path(filename).suffix.lower()

    if extension == ".pdf":
        with pymupdf.open(
            stream=file_bytes,
            filetype="pdf"
        ) as pdf:
            if pdf.is_encrypted:
                raise ValueError(
                    "Password-protected PDFs are not supported."
                )

            content = "\n".join(
                page.get_text("text")
                for page in pdf
            )

    elif extension == ".docx":
        document = DocxDocument(io.BytesIO(file_bytes))

        parts = [
            paragraph.text
            for paragraph in document.paragraphs
        ]

        for table in document.tables:
            for row in table.rows:
                parts.append(
                    " | ".join(cell.text for cell in row.cells)
                )

        content = "\n".join(parts)

    elif extension == ".txt":
        try:
            content = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError(
                "Text files must use UTF-8 encoding."
            ) from error

    else:
        raise ValueError("Unsupported document format.")

    content = content.replace("\x00", "")
    content = re.sub(r"[ \t]+", " ", content)
    content = re.sub(r"\n[ \t]+", "\n", content)
    content = re.sub(r"\n{3,}", "\n\n", content).strip()

    if not content:
        raise ValueError(
            "No extractable text found. Scanned PDFs require OCR."
        )

    return content


def chunk_text(content: str) -> list[str]:
    size = settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP

    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Invalid chunk configuration.")

    chunks = []
    start = 0
    content_length = len(content)

    while start < content_length:
        end = min(start + size, content_length)

        if end < content_length:
            boundary = max(
                content.rfind("\n", start, end),
                content.rfind(". ", start, end),
                content.rfind(" ", start, end)
            )

            if boundary > start + size // 2:
                end = boundary + 1

        chunk = content[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= content_length:
            break

        start = max(end - overlap, start + 1)

    return chunks


def _tokens(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower(), flags=re.UNICODE)


def generate_embedding(content: str) -> list[float]:
    dimension = settings.EMBEDDING_DIMENSIONS

    if dimension <= 0:
        raise ValueError("Embedding dimension must be positive.")

    tokens = _tokens(content)
    vector = np.zeros(dimension, dtype=np.float32)

    features = list(tokens)

    features.extend(
        f"{tokens[index]}_{tokens[index + 1]}"
        for index in range(len(tokens) - 1)
    )

    for feature in features:
        digest = hashlib.blake2b(
            feature.encode("utf-8"),
            digest_size=8
        ).digest()

        value = int.from_bytes(digest, "little")
        position = value % dimension
        sign = 1.0 if (value >> 32) & 1 else -1.0

        vector[position] += sign

    norm = np.linalg.norm(vector)

    if norm > 0:
        vector /= norm

    return vector.tolist()


def generate_embeddings(contents: list[str]) -> list[list[float]]:
    return [
        generate_embedding(content)
        for content in contents
    ]


def _create_empty_index():
    base_index = faiss.IndexFlatIP(
        settings.EMBEDDING_DIMENSIONS
    )

    return faiss.IndexIDMap2(base_index)


def _load_index():
    if INDEX_FILE.exists():
        index = faiss.read_index(str(INDEX_FILE))

        if index.d != settings.EMBEDDING_DIMENSIONS:
            raise ValueError(
                "Existing FAISS index dimension does not match "
                "the configured embedding dimension. Remove the "
                "old index and re-index your documents."
            )

        return index

    return _create_empty_index()


def _load_metadata():
    if not METADATA_FILE.exists():
        return {}

    with METADATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def _save_index(index, metadata):
    settings.FAISS_INDEX_PATH.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary_index = INDEX_FILE.with_suffix(".tmp")
    temporary_metadata = METADATA_FILE.with_suffix(".tmp")

    faiss.write_index(index, str(temporary_index))

    with temporary_metadata.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    temporary_index.replace(INDEX_FILE)
    temporary_metadata.replace(METADATA_FILE)


def index_document(
    chunks: list[str],
    document_id: str,
    filename: str
):
    if not chunks:
        raise ValueError("No chunks supplied for indexing.")

    with _index_lock:
        index = _load_index()
        metadata = _load_metadata()

        existing_ids = [
            int(key)
            for key in metadata
            if str(key).isdigit()
        ]

        next_id = max(existing_ids, default=0) + 1

        embeddings = np.asarray(
            generate_embeddings(chunks),
            dtype=np.float32
        )

        ids = np.arange(
            next_id,
            next_id + len(chunks),
            dtype=np.int64
        )

        index.add_with_ids(embeddings, ids)

        for position, chunk in enumerate(chunks):
            chunk_id = int(ids[position])

            metadata[str(chunk_id)] = {
                "document_id": document_id,
                "filename": filename,
                "chunk_index": position,
                "text": chunk
            }

        _save_index(index, metadata)

    logger.info(
        "Indexed %s chunks for document %s",
        len(chunks),
        document_id
    )


def delete_document_vectors(document_id: str):
    with _index_lock:
        index = _load_index()
        metadata = _load_metadata()

        ids_to_delete = [
            int(key)
            for key, value in metadata.items()
            if value.get("document_id") == document_id
        ]

        if ids_to_delete:
            id_array = np.asarray(
                ids_to_delete,
                dtype=np.int64
            )

            index.remove_ids(id_array)

            for chunk_id in ids_to_delete:
                metadata.pop(str(chunk_id), None)

            _save_index(index, metadata)


def process_document(
    file_bytes: bytes,
    filename: str,
    document_id: str
) -> int:
    content = extract_text(file_bytes, filename)
    chunks = chunk_text(content)

    if not chunks:
        raise ValueError("Document contains no valid chunks.")

    index_document(
        chunks=chunks,
        document_id=document_id,
        filename=filename
    )

    return len(chunks)
