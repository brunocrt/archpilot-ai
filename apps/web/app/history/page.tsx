"use client";
import React, { useEffect, useState } from 'react';
import {
  ConversationDetail,
  ConversationSummary,
  getConversation,
  listConversations,
} from '../../lib/api';
import MarkdownContent from '../../components/MarkdownContent';

export default function HistoryPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [selected, setSelected] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listConversations()
      .then((items) => {
        setConversations(items);
        if (items.length > 0) {
          return getConversation(items[0].id).then(setSelected);
        }
      })
      .catch(() => setError('Failed to load conversation history'))
      .finally(() => setLoading(false));
  }, []);

  async function selectConversation(conversationId: string) {
    setError(null);
    try {
      setSelected(await getConversation(conversationId));
    } catch (err) {
      setError('Failed to load conversation');
    }
  }

  return (
    <main className="history-layout">
      <section className="history-list">
        <div className="panel-heading">
          <h2>Conversation History</h2>
          <p>Persisted chat sessions from the API database.</p>
        </div>
        {loading && <p className="empty-state">Loading conversations...</p>}
        {error && <p className="form-error">{error}</p>}
        {!loading && conversations.length === 0 && (
          <p className="empty-state">No conversations yet.</p>
        )}
        <div className="conversation-list">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={selected?.id === conversation.id ? 'conversation-card active' : 'conversation-card'}
              onClick={() => selectConversation(conversation.id)}
            >
              <span>{conversation.title || 'Untitled conversation'}</span>
              <small>
                {conversation.message_count} messages · {formatDate(conversation.last_message_at || conversation.created_at)}
              </small>
            </button>
          ))}
        </div>
      </section>

      <section className="history-detail">
        {selected ? (
          <>
            <div className="panel-heading">
              <h2>{selected.title || 'Conversation'}</h2>
              <p>{formatDate(selected.created_at)}</p>
            </div>
            <div className="message-list history-messages">
              {selected.messages.map((message) => (
                <div
                  key={message.id}
                  className={message.role === 'user' ? 'message-row user' : 'message-row assistant'}
                >
                  <div
                    className={
                      message.role === 'user'
                        ? 'message-bubble user'
                        : 'message-bubble assistant'
                    }
                  >
                    <MarkdownContent content={message.content} />
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className="empty-state">Select a conversation to view messages.</p>
        )}
      </section>
    </main>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}
