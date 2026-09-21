# Mini RAG Chatbot (Gemini)

A small, self-contained RAG demo:
- Upload PDF / DOCX / TXT files
- Each file is chunked and embedded with Gemini's embedding model
- Chat with **one selected document** or **all of them** — retrieval finds the
  most relevant chunks, then Gemini answers in full sentences using only that context

This is intentionally minimal (in-memory vector store, no auth, no persistence) —
built to demonstrate the RAG flow end to end, not for production use.

## 1. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env          # then paste your Gemini API key into .env
# Get a key at https://aistudio.google.com/apikey

uvicorn main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`.

## 2. Frontend setup

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

## 3. Use it

1. Open the frontend in your browser.
2. Upload one or more PDF/DOCX/TXT files (sidebar).
3. Either leave **"All documents"** checked, or tick specific files to scope
   the chat to just those.
4. Ask a question — the answer is generated from only the retrieved chunks,
   with the source filename(s) shown underneath.

## How it works

- **Ingestion**: `backend/utils/extract.py` pulls raw text out of PDF (`pypdf`),
  DOCX (`python-docx`), or TXT files.
- **Chunking**: `backend/utils/chunk.py` splits text into ~180-word overlapping chunks.
- **Embedding**: each chunk is embedded via Gemini's `text-embedding-004` model
  and kept in memory as a NumPy array per document.
- **Retrieval**: a query is embedded the same way, then cosine similarity picks
  the top 5 chunks across whichever document(s) are selected.
- **Generation**: the top chunks are stuffed into a prompt and sent to
  `gemini-2.0-flash`, which is instructed to answer only from that context.

## Notes / things to extend if you take this further

- Storage is in-memory — restarting the backend clears uploaded documents.
- If Google renames/retires a model, update `EMBED_MODEL` / `CHAT_MODEL` at
  the top of `backend/main.py`.
- For a real project you'd swap the in-memory store for something like
  Chroma/FAISS + disk persistence.
