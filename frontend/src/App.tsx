import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

type Message = { id: string; role: 'user' | 'assistant'; content: string; created_at: string }
type Conversation = {
  id: string; title: string; document_id: string; document_name?: string | null
  created_at: string; updated_at: string; messages?: Message[]
}

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const paths: Record<string, string> = {
    plus: 'M12 5v14M5 12h14', search: 'm21 21-4.3-4.3m2.3-5.2a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0', upload: 'M12 16V4m0 0L7 9m5-5 5 5M5 20h14', send: 'm22 2-7 20-4-9-9-4Z M22 2 11 13', file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z M14 2v6h6', menu: 'M4 6h16M4 12h16M4 18h16', logout: 'M10 17l5-5-5-5M15 12H3M21 19V5a2 2 0 0 0-2-2h-4', book: 'M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 19.5V5a2 2 0 0 1 2.5-2H20v14H6.5A2.5 2.5 0 0 0 4 19.5Z', arrow: 'M5 12h14m-6-6 6 6-6 6', close: 'M6 6l12 12M18 6 6 18', check: 'm5 12 4 4L19 6', alert: 'M12 9v4m0 4h.01M10.3 3.8 2.1 18a2 2 0 0 0 1.7 3h16.4a2 2 0 0 0 1.7-3L13.7 3.8a2 2 0 0 0-3.4 0Z',
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('rag-token') ?? '')
  const [user, setUser] = useState<{ name: string; email: string } | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [active, setActive] = useState<Conversation | null>(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const fileInput = useRef<HTMLInputElement>(null)

  const request = async (path: string, options: RequestInit = {}) => {
    const response = await fetch(`${API_URL}${path}`, { ...options, headers: { ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers } })
    if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? 'Something went wrong')
    return response
  }

  useEffect(() => {
    if (!token) return
    Promise.all([request('/auth/me'), request('/conversations')]).then(async ([me, chats]) => {
      setUser(await me.json()); setConversations(await chats.json())
    }).catch(() => { localStorage.removeItem('rag-token'); setToken('') })
  }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  const openConversation = async (conversation: Conversation) => {
    setError(''); setSidebarOpen(false)
    try { setActive(await (await request(`/conversations/${conversation.id}`)).json()) } catch (err) { setError(err instanceof Error ? err.message : 'Could not open conversation') }
  }

  const upload = async (file: File) => {
    setUploading(true); setError('')
    try {
      const form = new FormData(); form.append('file', file)
      const conversation: Conversation = await (await request('/conversations/upload', { method: 'POST', body: form })).json()
      setConversations((items) => [conversation, ...items]); setActive(conversation); setSidebarOpen(false)
    } catch (err) { setError(err instanceof Error ? err.message : 'Upload failed') } finally { setUploading(false) }
  }

  const send = async (event: FormEvent) => {
    event.preventDefault(); if (!query.trim() || !active || loading) return
    const text = query.trim(); setQuery(''); setLoading(true); setError('')
    const optimistic: Message = { id: `local-${Date.now()}`, role: 'user', content: text, created_at: new Date().toISOString() }
    setActive((current) => current ? { ...current, messages: [...(current.messages ?? []), optimistic] } : current)
    try {
      const response = await request('/chat/', { method: 'POST', body: JSON.stringify({ query: text, conversation_id: active.id }) })
      const reader = response.body?.getReader(); if (!reader) throw new Error('Streaming is not supported by this browser')
      const decoder = new TextDecoder(); let assistant = ''
      setActive((current) => current ? { ...current, messages: [...(current.messages ?? []), { id: `answer-${Date.now()}`, role: 'assistant', content: '', created_at: new Date().toISOString() }] } : current)
      while (true) {
        const { done, value } = await reader.read(); if (done) break
        for (const line of decoder.decode(value, { stream: true }).split('\n')) if (line.startsWith('data: ')) {
          const event = JSON.parse(line.slice(6)); if (event.event === 'token') { assistant += event.content; setActive((current) => current ? { ...current, messages: (current.messages ?? []).map((message) => message.id.startsWith('answer-') ? { ...message, content: assistant } : message) } : current) }
        }
      }
      setConversations((items) => items.map((item) => item.id === active.id ? { ...item, updated_at: new Date().toISOString() } : item))
    } catch (err) { setError(err instanceof Error ? err.message : 'Message failed') } finally { setLoading(false) }
  }

  const authenticate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const form = new FormData(event.currentTarget)
    try {
      const path = authMode === 'login' ? '/auth/login' : '/auth/register'
      const body = authMode === 'login' ? { email: form.get('email'), password: form.get('password') } : { name: form.get('name'), email: form.get('email'), password: form.get('password') }
      const data = await (await fetch(`${API_URL}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })).json()
      if (!data.access_token) throw new Error(data.detail ?? 'Could not sign in')
      localStorage.setItem('rag-token', data.access_token); setToken(data.access_token)
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not sign in') }
  }

  if (!token) return <main className="auth-screen"><div className="auth-card"><div className="brand-mark">R<span>/</span>G</div><p className="eyebrow">PRIVATE RESEARCH DESK</p><h1>Ask your documents<br /><em>better questions.</em></h1><p className="auth-copy">Upload the source material. Get answers grounded in what is actually there.</p><form onSubmit={authenticate} className="auth-form">{authMode === 'register' && <label>Name<input name="name" required placeholder="Your name" /></label>}<label>Email<input name="email" type="email" required placeholder="you@company.com" /></label><label>Password<input name="password" type="password" required placeholder="••••••••" /></label><button className="primary-button" type="submit">{authMode === 'login' ? 'Enter the desk' : 'Create account'} <Icon name="arrow" /></button></form><button className="text-button" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setError('') }}>{authMode === 'login' ? 'New here? Create an account' : 'Already have an account? Sign in'}</button>{error && <p className="error"><Icon name="alert" />{error}</p>}</div><div className="auth-note"><Icon name="book" /> Your files stay tied to your private workspace.</div></main>

  return <div className="app-shell"><aside className={`sidebar ${sidebarOpen ? 'is-open' : ''}`}><div className="sidebar-top"><div className="brand-mark">R<span>/</span>G</div><button className="icon-button mobile-close" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar"><Icon name="close" /></button></div><div className="sidebar-heading"><div><p className="eyebrow">WORKSPACE</p><h2>Conversations</h2></div><button className="new-button" onClick={() => fileInput.current?.click()} disabled={uploading}><Icon name="plus" /> New</button></div><div className="conversation-list">{conversations.length === 0 ? <div className="empty-sidebar"><Icon name="file" size={20} /><p>No conversations yet.</p><span>Upload a document to begin.</span></div> : conversations.map((conversation) => <button key={conversation.id} className={`conversation-item ${active?.id === conversation.id ? 'active' : ''}`} onClick={() => openConversation(conversation)}><span className="conversation-icon"><Icon name="file" size={16} /></span><span className="conversation-meta"><strong>{conversation.title}</strong><small>{conversation.document_name ?? 'Document'} · {formatDate(conversation.updated_at)}</small></span></button>)}</div><div className="sidebar-footer"><div className="user-chip"><span>{user?.name?.slice(0, 1).toUpperCase() ?? 'U'}</span><div><strong>{user?.name ?? 'Researcher'}</strong><small>{user?.email}</small></div><button className="icon-button" onClick={() => { localStorage.removeItem('rag-token'); setToken('') }} aria-label="Sign out"><Icon name="logout" size={16} /></button></div></div></aside><main className="main-panel"><header className="topbar"><button className="icon-button menu-button" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar"><Icon name="menu" /></button>{active ? <div className="document-heading"><span className="status-dot" /><div><strong>{active.title}</strong><small><Icon name="file" size={12} /> {active.document_name ?? 'Source document'}</small></div></div> : <div className="topbar-label">RAG / RESEARCH DESK</div>}<div className="topbar-right"><span className="live-label"><i /> SYSTEM READY</span></div></header>{active ? <section className="chat-view"><div className="chat-scroll"><div className="chat-intro"><div className="intro-symbol"><Icon name="book" size={24} /></div><p className="eyebrow">SOURCE LOADED</p><h1>{active.title}</h1><p>Ask anything about this document. Answers are generated from its contents only.</p></div>{(active.messages ?? []).map((message) => <article key={message.id} className={`message ${message.role}`}><div className="message-label">{message.role === 'user' ? 'YOU' : 'RAG / ASSISTANT'}</div><div className="message-body">{message.content || (loading && <span className="typing"><i /><i /><i /></span>)}</div></article>)}{loading && !(active.messages ?? []).some((message) => message.role === 'assistant' && message.id.startsWith('answer-')) && <div className="message assistant"><div className="message-label">RAG / ASSISTANT</div><div className="message-body"><span className="typing"><i /><i /><i /></span></div></div>}{error && <p className="error inline-error"><Icon name="alert" />{error}</p>}</div><form className="composer" onSubmit={send}><textarea value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask a question about your document..." rows={1} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send(event) } }} /><button className="send-button" type="submit" disabled={!query.trim() || loading}><Icon name="send" /></button><small>ENTER TO SEND · SHIFT + ENTER FOR NEW LINE</small></form></section> : <section className="welcome"><div className="welcome-grid"><div className="welcome-copy"><p className="eyebrow">YOUR DOCUMENTS, IN CONTEXT</p><h1>A clearer way<br />to <em>read deeply.</em></h1><p>Bring a report, brief, or body of research. RAG will keep every answer tethered to the source.</p><button className="primary-button" onClick={() => fileInput.current?.click()} disabled={uploading}>{uploading ? 'Indexing document...' : 'Upload a document'} <Icon name="upload" /></button></div><div className="blueprint"><div className="blueprint-ring" /><div className="blueprint-card"><Icon name="file" size={22} /><span>YOUR SOURCE</span><strong>Ready when you are.</strong><small>PDF · DOCX · TXT</small></div><div className="blueprint-line line-one" /><div className="blueprint-line line-two" /></div></div><div className="principles"><span><Icon name="check" /> Source-grounded answers</span><span><Icon name="check" /> Private workspace</span><span><Icon name="check" /> Conversation memory</span></div></section>}<input ref={fileInput} type="file" hidden accept=".pdf,.doc,.docx,.txt" onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); event.target.value = '' }} /></main></div>
}

function formatDate(date: string) { const value = new Date(date); const today = new Date(); return value.toDateString() === today.toDateString() ? value.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : value.toLocaleDateString([], { month: 'short', day: 'numeric' }) }

export default App
