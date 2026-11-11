"""Published-only lexical retrieval with indexed terms and explicit provenance."""

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import threading
import unicodedata
from collections import Counter
from pathlib import Path
from uuid import uuid4

from app.modules.ai.infrastructure.providers import AiError

SLOTS = threading.BoundedSemaphore(1)
STOP = set("para como donde cuando cual cuales los las del una unos unas con por que este esta estos estas tengo quiero saber sobre informacion el la de y o a en es un se me mi al".split())


def terms(text):
    plain = "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))
    return [t for t in re.findall(r"[a-z0-9]{2,64}", plain) if t not in STOP]


def extract(data, name):
    if not data or len(data) > 5_000_000:
        raise AiError("knowledge_size_limit", 413)
    if not SLOTS.acquire(blocking=False):
        raise AiError("knowledge_inspection_busy", 429)
    try:
        if name.lower().endswith(".txt") and not data.startswith(b"%PDF-"):
            try:
                text = data.decode("utf-8-sig")
            except UnicodeError:
                raise AiError("knowledge_utf8_required", 415) from None
            if "\x00" in text or len(text) > 300_000 or not text.strip():
                raise AiError("knowledge_text_invalid", 415)
            return [{"page": 1, "text": text}]
        if not name.lower().endswith(".pdf") or not data.startswith(b"%PDF-"):
            raise AiError("knowledge_pdf_or_txt_required", 415)
        # Reuse the existing active-content policy; the private temporary file is
        # removed before returning and never used as a second project/copy.
        from app.modules.inbox.infrastructure.media_files import inspect_pdf

        with tempfile.TemporaryDirectory(prefix="crm-knowledge-") as folder:
            source = Path(folder) / "source.pdf"
            source.write_bytes(data)
            inspect_pdf(source)
        result = subprocess.run([sys.executable, "-m", "app.modules.knowledge.extract"], input=data, capture_output=True, timeout=10, check=False)
        if result.returncode == 3:
            raise AiError("knowledge_pdf_no_text_ocr_required", 415)
        if result.returncode or len(result.stdout) > 2_000_000:
            raise AiError("knowledge_pdf_limit_or_invalid", 415)
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        raise AiError("knowledge_pdf_limit_or_invalid", 415) from None
    finally:
        SLOTS.release()


def add_document(cursor, name, title, data, pages, identifier=None):
    if cursor.execute("SELECT COUNT(*) FROM crm_ai.KnowledgeDocument WHERE State<>'deleted'").fetchval() >= 100:
        raise AiError("knowledge_document_limit", 409)
    identifier = identifier or str(uuid4())
    chunks = []
    for page in pages:
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", page["text"])
        text = re.sub(r"\s+", " ", text).strip()
        start = 0
        while start < len(text):
            end = min(len(text), start + 1600)
            if end < len(text):
                boundary = text.rfind(" ", start + 800, end)
                if boundary > start:
                    end = boundary
            chunks.append((page["page"], text[start:end]))
            if len(chunks) > 250:
                raise AiError("knowledge_chunk_limit", 413)
            if end == len(text):
                break
            start = max(start + 1, end - 120)
    if not chunks:
        raise AiError("knowledge_empty", 415)
    cursor.execute("INSERT crm_ai.KnowledgeDocument(DocumentId,Title,FileName,ContentHash,ByteLength,State) VALUES(?,?,?,?,?,'draft')", identifier, title, name, hashlib.sha256(data).digest(), len(data))
    for ordinal, (page, body) in enumerate(chunks):
        chunk = str(uuid4())
        cursor.execute("INSERT crm_ai.KnowledgeChunk(ChunkId,DocumentId,Ordinal,PageNumber,Body) VALUES(?,?,?,?,?)", chunk, identifier, ordinal, page, body)
        for term, frequency in Counter(terms(body)).items():
            cursor.execute("INSERT crm_ai.KnowledgeTerm(Term,ChunkId,Frequency) VALUES(?,?,?)", term, chunk, min(32767, frequency))
    return identifier


def search(cursor, query, limit=5):
    tokens = list(dict.fromkeys(terms(query)))[:24]
    if not tokens:
        return []
    placeholders = ",".join("?" for _ in tokens)
    found = cursor.execute(
        "SELECT TOP(?) c.ChunkId,c.DocumentId,d.Title,c.PageNumber,c.Body,d.Revision,COUNT(*) AS hits,SUM(t.Frequency) AS frequency "
        "FROM crm_ai.KnowledgeTerm t JOIN crm_ai.KnowledgeChunk c ON c.ChunkId=t.ChunkId "
        "JOIN crm_ai.KnowledgeDocument d ON d.DocumentId=c.DocumentId AND d.State='published' "
        f"WHERE t.Term IN({placeholders}) GROUP BY c.ChunkId,c.DocumentId,d.Title,c.PageNumber,c.Body,d.Revision "
        "ORDER BY hits DESC,frequency DESC,c.ChunkId", limit, *tokens).fetchall()
    return [{"id": str(r[0]), "document_id": str(r[1]), "title": r[2], "page": r[3], "text": r[4], "revision": r[5], "matched_terms": r[6]} for r in found]
