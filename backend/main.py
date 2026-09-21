import os
import pickle
import uuid
from typing import List, Optional

import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import google.generativeai as genai


from utils.extract import extract_text
from utils.chunk import chunk_text

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Set GEMINI_API_KEY in backend/.env (copy .env.example)")

genai.configure(api_key=GEMINI_API_KEY)

# Update these if Google renames/deprecates a model on your account.
EMBED_MODEL = "models/gemini-embedding-001"
CHAT_MODEL = "gemini-3.1-flash-lite"

app = FastAPI(title="Mini RAG Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory vector store (demo-scale only — resets on restart):
# { doc_id: {"name": str, "chunks": [str], "embeddings": np.ndarray} }
# In-memory vector store, backed by a pickle file on disk so uploads survive
# server restarts (demo-scale only — swap for a real vector DB for production):
# { doc_id: {"name": str, "chunks": [str], "embeddings": np.ndarray} }
DATA_FILE = os.path.join(os.path.dirname(__file__), "docs_store.pkl")


def load_docs() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "rb") as f:
            return pickle.load(f)
    return {}


def save_docs():
    with open(DATA_FILE, "wb") as f:
        pickle.dump(DOCS, f)


DOCS: dict = load_docs()


def embed_texts(texts: List[str], task_type: str) -> np.ndarray:
    vectors = []
    for t in texts:
        res = genai.embed_content(model=EMBED_MODEL, content=t, task_type=task_type)
        vectors.append(res["embedding"])
    return np.array(vectors, dtype="float32")


@app.post("/upload")
async def upload_doc(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        text = extract_text(file.filename, raw)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if not text.strip():
        raise HTTPException(400, "No extractable text found in this file.")

    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(400, "Could not split this file into any chunks.")

    embeddings = embed_texts(chunks, task_type="retrieval_document")

    doc_id = str(uuid.uuid4())[:8]
    DOCS[doc_id] = {"name": file.filename, "chunks": chunks, "embeddings": embeddings}
    save_docs()
    return {"doc_id": doc_id, "filename": file.filename, "chunks": len(chunks)}


@app.get("/documents")
def list_documents():
    return [
        {"doc_id": doc_id, "filename": d["name"], "chunks": len(d["chunks"])}
        for doc_id, d in DOCS.items()
    ]


def retrieve(query_vec: np.ndarray, doc_ids: List[str], top_k: int = 5):
    results = []
    for doc_id in doc_ids:
        d = DOCS.get(doc_id)
        if not d or len(d["chunks"]) == 0:
            continue
        sims = d["embeddings"] @ query_vec / (
            np.linalg.norm(d["embeddings"], axis=1) * np.linalg.norm(query_vec) + 1e-8
        )
        for idx, score in enumerate(sims):
            results.append((float(score), d["name"], d["chunks"][idx]))
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_k]


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    if doc_id not in DOCS:
        raise HTTPException(404, "Document not found.")
    del DOCS[doc_id]
    save_docs()
    return {"deleted": doc_id}

@app.post("/chat")
async def chat(message: str = Form(...), doc_ids: Optional[str] = Form(None)):
    if not DOCS:
        raise HTTPException(400, "Upload at least one document first.")

    if not doc_ids or doc_ids == "all":
        selected = list(DOCS.keys())
    else:
        selected = [d for d in doc_ids.split(",") if d in DOCS]
        if not selected:
            raise HTTPException(400, "No valid document selected.")

    query_vec = embed_texts([message], task_type="retrieval_query")[0]
    top_chunks = retrieve(query_vec, selected, top_k=5)

    if not top_chunks:
        raise HTTPException(400, "Selected document(s) have no content to search.")

    context = "\n\n".join(f"[Source: {name}]\n{chunk}" for _, name, chunk in top_chunks)

    prompt = f"""You are a helpful assistant answering questions using ONLY the context below.
Answer in complete, well-formed sentences. If the answer isn't in the context, say so clearly instead of guessing.

Context:
{context}

Question: {message}

Answer:"""

    model = genai.GenerativeModel(CHAT_MODEL)
    response = model.generate_content(prompt)

    sources = sorted(set(name for _, name, _ in top_chunks))
    return {"answer": response.text, "sources": sources}


@app.get("/")
def health():
    return {"status": "ok", "docs_loaded": len(DOCS)}
