import React, { useEffect, useState } from 'react';
import {
  chatQueryStream,
  listDocuments,
  listProjects,
  DocumentSummary,
  Project,
  RetrievalDiagnostics,
  RetrievedChunk,
} from '../lib/api';
import SourcePanel from './SourcePanel';
import MarkdownContent from './MarkdownContent';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState('');
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [projects, setProjects] = useState<Project[]>([]);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [projectId, setProjectId] = useState('');
  const [documentFilename, setDocumentFilename] = useState('');
  const [contentType, setContentType] = useState('');
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState<RetrievedChunk[]>([]);
  const [activeAnswer, setActiveAnswer] = useState('');
  const [retrieval, setRetrieval] = useState<RetrievalDiagnostics | undefined>();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setError('Failed to load projects'));
  }, []);

  useEffect(() => {
    setDocumentFilename('');
    setContentType('');
    listDocuments(projectId || undefined)
      .then(setDocuments)
      .catch(() => setError('Failed to load retrieval filters'));
  }, [projectId]);

  async function sendQuestion() {
    if (!question.trim()) return;
    const currentQuestion = question;
    setLoading(true);
    setError(null);
    setQuestion('');
    setSources([]);
    setActiveAnswer('');
    setRetrieval(undefined);
    setMessages((msgs) => [
      ...msgs,
      { role: 'user', content: currentQuestion },
      { role: 'assistant', content: '' },
    ]);
    try {
      await chatQueryStream(currentQuestion, {
        conversationId,
        projectId: projectId || undefined,
        documentFilename: documentFilename || undefined,
        contentType: contentType || undefined,
        onConversation: setConversationId,
        onSources: setSources,
        onRetrieval: setRetrieval,
        onDelta: (text) => {
          setMessages((msgs) => {
            const next = [...msgs];
            const lastIndex = next.length - 1;
            next[lastIndex] = {
              ...next[lastIndex],
              content: `${next[lastIndex].content}${text}`,
            };
            return next;
          });
        },
        onDone: (res) => {
          setConversationId(res.conversation_id);
          setActiveAnswer(res.answer);
          setRetrieval(res.retrieval);
          setMessages((msgs) => {
            const next = [...msgs];
            const lastIndex = next.length - 1;
            next[lastIndex] = { role: 'assistant', content: res.answer };
            return next;
          });
        },
      });
    } catch (err) {
      setError('Failed to get answer');
      setMessages((msgs) => msgs.filter((_, index) => index < msgs.length - 1));
    } finally {
      setLoading(false);
    }
  }

  const contentTypes = Array.from(
    new Set(documents.map((document) => document.content_type).filter(Boolean) as string[]),
  ).sort();
  const selectedProject = projects.find((project) => project.id === projectId);
  const scopeItems = [
    selectedProject ? `Project: ${selectedProject.name}` : 'Project: All',
    documentFilename ? `File: ${documentFilename}` : 'File: Any',
    contentType ? `Format: ${formatContentType(contentType)}` : 'Format: Any',
    retrieval ? `Mode: ${formatRetrievalMode(retrieval.mode)}` : null,
  ].filter((item): item is string => Boolean(item));

  return (
    <section className="chat-panel">
      <div className="panel-heading">
        <h2>Ask the Copilot</h2>
        <p>Grounded answers from uploaded architecture documents.</p>
      </div>
      <div className="message-list">
        {messages.map((msg, idx) => (
          <div key={idx} className={msg.role === 'user' ? 'message-row user' : 'message-row assistant'}>
            <div
              className={
                msg.role === 'user'
                  ? 'message-bubble user'
                  : 'message-bubble assistant'
              }
            >
              <MarkdownContent content={msg.content || (loading && idx === messages.length - 1 ? 'Thinking...' : '')} sources={sources} />
            </div>
          </div>
        ))}
      </div>
      <div className="composer">
        <div className="retrieval-filters">
          <label className="project-filter">
            <span>Project scope</span>
            <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
              <option value="">All projects</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.name}</option>
              ))}
            </select>
          </label>
          <label className="project-filter">
            <span>File</span>
            <select value={documentFilename} onChange={(event) => setDocumentFilename(event.target.value)}>
              <option value="">Any file</option>
              {documents.map((document) => (
                <option key={document.id} value={document.filename}>{document.filename}</option>
              ))}
            </select>
          </label>
          <label className="project-filter">
            <span>Format</span>
            <select value={contentType} onChange={(event) => setContentType(event.target.value)}>
              <option value="">Any format</option>
              {contentTypes.map((type) => (
                <option key={type} value={type}>{formatContentType(type)}</option>
              ))}
            </select>
          </label>
        </div>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          placeholder="Ask a question about your architecture..."
        />
        <button
          onClick={sendQuestion}
          disabled={loading}
        >
          {loading ? 'Asking...' : 'Ask'}
        </button>
        {error && <p className="form-error">{error}</p>}
      </div>
      {(activeAnswer || retrieval) && (
        <div className="retrieval-summary">
          {scopeItems.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      )}
      {sources && sources.length > 0 && <SourcePanel sources={sources} answer={activeAnswer} />}
    </section>
  );
}

function formatContentType(contentType: string): string {
  const labels: Record<string, string> = {
    'application/json': 'JSON',
    'application/pdf': 'PDF',
    'text/markdown': 'Markdown',
    'text/plain': 'Text',
  };
  return labels[contentType] || contentType;
}

function formatRetrievalMode(mode: string): string {
  const labels: Record<string, string> = {
    hybrid: 'Hybrid',
    keyword: 'Keyword',
    latest: 'Latest',
    none: 'No matches',
    vector: 'Vector',
  };
  return labels[mode] || mode;
}
