import { useState, useEffect, useRef } from 'react'

const API = 'http://localhost:8000'

export default function App() {
  const [docs, setDocs] = useState([])
  const [selected, setSelected] = useState(new Set()) // empty set = "All documents"
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [uploading, setUploading] = useState(false)
  const [asking, setAsking] = useState(false)
  const fileInputRef = useRef(null)

  useEffect(() => {
    loadDocs()
  }, [])

  async function loadDocs() {
    try {
      const res = await fetch(`${API}/documents`)
      setDocs(await res.json())
    } catch {
      // backend not reachable yet — ignore, user will see empty list
    }
  }

  async function handleFiles(e) {
    const files = Array.from(e.target.files)
    if (files.length === 0) return
    setUploading(true)
    for (const file of files) {
      const form = new FormData()
      form.append('file', file)
      try {
        const res = await fetch(`${API}/upload`, { method: 'POST', body: form })
        if (!res.ok) {
          const err = await res.json()
          alert(`${file.name}: ${err.detail || 'upload failed'}`)
        }
      } catch {
        alert(`Could not reach backend while uploading ${file.name}`)
      }
    }
    setUploading(false)
    fileInputRef.current.value = ''
    loadDocs()
  }

  function toggleDoc(docId) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(docId)) next.delete(docId)
      else next.add(docId)
      return next
    })
  }
    async function deleteDoc(docId) {
    await fetch(`${API}/documents/${docId}`, { method: 'DELETE' })
    setSelected(prev => {
      const next = new Set(prev)
      next.delete(docId)
      return next
    })
    loadDocs()
  }
  async function sendMessage() {
    const text = input.trim()
    if (!text || asking) return
    setMessages(m => [...m, { role: 'user', text }])
    setInput('')
    setAsking(true)

    const form = new FormData()
    form.append('message', text)
    form.append('doc_ids', selected.size === 0 ? 'all' : Array.from(selected).join(','))

    try {
      const res = await fetch(`${API}/chat`, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Something went wrong')
      setMessages(m => [...m, { role: 'bot', text: data.answer, sources: data.sources }])
    } catch (err) {
      setMessages(m => [...m, { role: 'bot', text: `Error: ${err.message}`, error: true }])
    } finally {
      setAsking(false)
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h2>Documents</h2>
        <input
          type="file"
          multiple
          ref={fileInputRef}
          onChange={handleFiles}
          accept=".pdf,.docx,.txt"
        />
        {uploading && <p className="hint">Uploading & indexing…</p>}

        <div className="doc-list">
          <label className="doc-item all">
            <input
              type="checkbox"
              checked={selected.size === 0}
              readOnly
              onClick={() => setSelected(new Set())}
            />
            All documents
          </label>
          {docs.map(d => (
  <label key={d.doc_id} className="doc-item">
    <input
      type="checkbox"
      checked={selected.has(d.doc_id)}
      onChange={() => toggleDoc(d.doc_id)}
    />
    <span className="doc-name">{d.filename} <span className="chunks">({d.chunks} chunks)</span></span>
    <button
      type="button"
      className="delete-btn"
      onClick={(e) => { e.preventDefault(); deleteDoc(d.doc_id) }}
      title="Remove document"
    >
      ✕
    </button>
  </label>
))}
          {docs.length === 0 && <p className="hint">No documents uploaded yet.</p>}
        </div>
      </aside>

      <main className="chat">
        <h1>Mini RAG Chatbot</h1>
        <div className="messages">
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role} ${m.error ? 'error' : ''}`}>
              <p>{m.text}</p>
              {m.sources && m.sources.length > 0 && (
                <p className="sources">Sources: {m.sources.join(', ')}</p>
              )}
            </div>
          ))}
          {messages.length === 0 && (
            <p className="hint">Upload a document, pick it (or "All documents"), and ask a question.</p>
          )}
        </div>
        <div className="input-row">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            placeholder="Ask something about your documents…"
          />
          <button onClick={sendMessage} disabled={asking}>
            {asking ? '…' : 'Send'}
          </button>
        </div>
      </main>
    </div>
  )
}
