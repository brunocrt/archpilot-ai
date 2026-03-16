import React, { useState } from 'react';
import { chatQuery, AnswerResponse, RetrievedChunk } from '../lib/api';
import SourcePanel from './SourcePanel';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState('');
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState<RetrievedChunk[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function sendQuestion() {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    // append user message
    setMessages((msgs) => [...msgs, { role: 'user', content: question }]);
    try {
      const res: AnswerResponse = await chatQuery(question, conversationId);
      setConversationId(res.conversation_id);
      setMessages((msgs) => [...msgs, { role: 'assistant', content: res.answer }]);
      setSources(res.sources);
    } catch (err) {
      setError('Failed to get answer');
    } finally {
      setQuestion('');
      setLoading(false);
    }
  }

  return (
    <div className="p-4 bg-white rounded-md border shadow">
      <h2 className="text-lg font-semibold mb-4">Ask the Copilot</h2>
      <div className="space-y-3 max-h-[50vh] overflow-y-auto">
        {messages.map((msg, idx) => (
          <div key={idx} className={msg.role === 'user' ? 'text-right' : 'text-left'}>
            <div
              className={
                msg.role === 'user'
                  ? 'inline-block bg-blue-100 rounded-md px-3 py-2'
                  : 'inline-block bg-gray-100 rounded-md px-3 py-2'
              }
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="w-full p-2 border rounded-md"
          rows={3}
          placeholder="Ask a question about your architecture..."
        />
        <button
          onClick={sendQuestion}
          disabled={loading}
          className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-md"
        >
          {loading ? 'Asking...' : 'Ask'}
        </button>
        {error && <p className="mt-2 text-red-600 text-sm">{error}</p>}
      </div>
      {sources && sources.length > 0 && <SourcePanel sources={sources} />}
    </div>
  );
}