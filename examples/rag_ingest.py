"""
Build a local FAISS index + SQLite metadata from PDFs/HTML for QaAI.

- Reads from INGEST_INPUT_DIR (default: ./examples/sample_corpus)
- Chunks text, embeds with sentence-transformers (free) or OpenAI embeddings
- Saves FAISS index under INDEX_DIR, plus metadata.json sidecar

Run:
  python examples/rag_ingest.py

Prereqs:
  pip install -r examples/requirements.txt
"""

from __future__ import annotations
import json, os, pathlib, re, sqlite3, uuid
from dataclasses import dataclass, asdict
from typing import List, Dict, Iterable, Tuple
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

INGEST_INPUT_DIR = os.getenv("INGEST_INPUT_DIR", "./examples/sample_corpus")
INDEX_DIR = os.getenv("INDEX_DIR", "./data/index")
SQLITE_PATH = os.getenv("SQLITE_PATH", "./data/qaai.db")
EMBEDDINGS_BACKEND = os.getenv("EMBEDDINGS_BACKEND", "sentence-transformers")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "all-MiniLM-L6-v2")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_JURISDICTION = os.getenv("DEFAULT_JURISDICTION", "DIFC")

os.makedirs(INDEX_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)

# ---- Loaders ----
def load_text_from_pdf(path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def load_text_from_html(path: str) -> str:
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    # naive HTML tag strip:
    return re.sub("<[^>]+>", " ", raw)

def load_text(path: str) -> str:
    ext = pathlib.Path(path).suffix.lower()
    if ext == ".pdf":
        return load_text_from_pdf(path)
    elif ext in (".html", ".htm"):
        return load_text_from_html(path)
    else:
        return pathlib.Path(path).read_text(encoding="utf-8", errors="ignore")


# ---- Chunking ----
def split_text(text: str, size: int = 800, overlap: int = 120) -> List[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i : i + size]
        chunks.append(" ".join(chunk))
        i += size - overlap
        if i < 0:
            break
    return chunks


# ---- Embeddings ----
def get_embedder():
    if EMBEDDINGS_BACKEND == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        def embed(texts: List[str]) -> List[List[float]]:
            # batch up to 2048 tokens per item; keep batches small for demo
            resp = client.embeddings.create(
                model=OPENAI_EMBEDDING_MODEL,
                input=texts
            )
            return [d.embedding for d in resp.data]
        return embed
    else:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBEDDINGS_MODEL)
        def embed(texts: List[str]) -> List[List[float]]:
            return model.encode(texts, normalize_embeddings=True).tolist()
        return embed


# ---- Metadata types ----
@dataclass
class DocMeta:
    id: str
    path: str
    jurisdiction: str
    instrument_type: str  # Law|Regulation|CourtRule|Rulebook|Notice|Other
    title: str
    url: str | None
    enactment_date: str | None
    commencement_date: str | None

@dataclass
class ChunkMeta:
    id: str
    doc_id: str
    chunk_index: int
    section_ref: str | None


# ---- SQLite setup ----
def init_sqlite():
    con = sqlite3.connect(SQLITE_PATH)
    cur = con.cursor()
    cur.execute("""
      CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        title TEXT,
        path TEXT,
        jurisdiction TEXT,
        instrument_type TEXT,
        url TEXT,
        enactment_date TEXT,
        commencement_date TEXT
      )
    """)
    cur.execute("""
      CREATE TABLE IF NOT EXISTS chunks (
        id TEXT PRIMARY KEY,
        doc_id TEXT,
        chunk_index INTEGER,
        section_ref TEXT,
        FOREIGN KEY(doc_id) REFERENCES documents(id)
      )
    """)
    con.commit()
    return con


def save_metadata(con, docs: List[DocMeta], chunks: List[ChunkMeta]):
    cur = con.cursor()
    for d in docs:
        cur.execute("""
          INSERT OR REPLACE INTO documents
          (id, title, path, jurisdiction, instrument_type, url, enactment_date, commencement_date)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (d.id, d.title, d.path, d.jurisdiction, d.instrument_type, d.url, d.enactment_date, d.commencement_date))
    for c in chunks:
        cur.execute("""
          INSERT OR REPLACE INTO chunks (id, doc_id, chunk_index, section_ref)
          VALUES (?, ?, ?, ?)
        """, (c.id, c.doc_id, c.chunk_index, c.section_ref))
    con.commit()


def build_index():
    import faiss
    embed = get_embedder()
    con = init_sqlite()

    vectors = []
    vec_meta = []  # pairs (chunk_id, doc_id, chunk_index)

    docs: List[DocMeta] = []
    chunks: List[ChunkMeta] = []

    files = []
    for p in pathlib.Path(INGEST_INPUT_DIR).rglob("*"):
        if p.is_file() and p.suffix.lower() in (".pdf", ".html", ".htm", ".txt", ".md"):
            files.append(str(p))

    if not files:
        print(f"[warn] No files found in {INGEST_INPUT_DIR}")
        return

    print(f"[info] Found {len(files)} files")
    for fpath in tqdm(files, desc="Reading"):
        text = load_text(fpath)[:2_000_000]  # guard for enormous docs in demo
        doc_id = str(uuid.uuid4())
        title = pathlib.Path(fpath).stem.replace("_"," ").title()

        # naive instrument type detection (demo)
        instrument_type = "Law" if re.search(r"\bLaw\b", title, re.I) else "Other"

        dmeta = DocMeta(
            id=doc_id,
            path=fpath,
            jurisdiction=DEFAULT_JURISDICTION,
            instrument_type=instrument_type,
            title=title,
            url=None,
            enactment_date=None,
            commencement_date=None
        )
        docs.append(dmeta)

        parts = split_text(text, size=int(os.getenv("CHUNK_SIZE", "800")), overlap=int(os.getenv("CHUNK_OVERLAP","120")))
        # embed in batches
        batch_size = 32
        all_vecs = []
        for i in range(0, len(parts), batch_size):
            all_vecs.extend(embed(parts[i:i+batch_size]))
        vectors.extend(all_vecs)

        for idx in range(len(parts)):
            cid = str(uuid.uuid4())
            chunks.append(ChunkMeta(id=cid, doc_id=doc_id, chunk_index=idx, section_ref=None))
            vec_meta.append((cid, doc_id, idx))

    # Save metadata
    save_metadata(con, docs, chunks)

    # Build FAISS
    if not vectors:
        print("[warn] no vectors created")
        return
    dim = len(vectors[0])
    index = faiss.IndexFlatIP(dim)
    import numpy as np
    mat = np.array(vectors, dtype="float32")
    index.add(mat)
    faiss.write_index(index, os.path.join(INDEX_DIR, "qaai.faiss"))

    # Sidecar JSON mapping
    sidecar = {
        "vectors": [{"chunk_id": c[0], "doc_id": c[1], "chunk_index": c[2]} for c in vec_meta]
    }
    with open(os.path.join(INDEX_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(sidecar, f, ensure_ascii=False, indent=2)

    print(f"[ok] FAISS index written to {os.path.join(INDEX_DIR,'qaai.faiss')}")
    print(f"[ok] Metadata sidecar written to {os.path.join(INDEX_DIR,'metadata.json')}")
    print("[note] SQLite contains document/chunk rows for lookups.")


if __name__ == "__main__":
    build_index()
