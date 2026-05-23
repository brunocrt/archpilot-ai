import React, { useEffect, useState } from 'react';
import { chatQueryStream, listProjects, Project, RetrievedChunk } from '../lib/api';
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
  const [projectId, setProjectId] = useState('');
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState<RetrievedChunk[]>([]);
  const [activeAnswer, setActiveAnswer] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setError('Failed to load projects'));
  }, []);

  async function sendQuestion() {
    if (!question.trim()) return;
    const currentQuestion = question;
    setLoading(true);
    setError(null);
    setQuestion('');
    setSources([]);
    setActiveAnswer('');
    setMessages((msgs) => [
      ...msgs,
      { role: 'user', content: currentQuestion },
      { role: 'assistant', content: '' },
    ]);
    try {
      await chatQueryStream(currentQuestion, {
        conversationId,
        projectId: projectId || undefined,
        onConversation: setConversationId,
        onSources: setSources,
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
        <label className="project-filter">
          <span>Project scope</span>
          <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
            <option value="">All projects</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
        </label>
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
      {sources && sources.length > 0 && <SourcePanel sources={sources} answer={activeAnswer} />}
    </section>
  );
}
