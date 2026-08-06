import React from 'react';
import type { RetrievedChunk } from '../lib/api';

interface Props {
  sources: RetrievedChunk[];
  answer?: string;
}

export default function SourcePanel({ sources, answer = '' }: Props) {
  if (!sources || sources.length === 0) return null;
  const referencedIds = new Set(
    Array.from(answer.matchAll(/\[([0-9a-fA-F-]{36})\]/g)).map((match) => match[1]),
  );
  return (
    <aside className="source-panel">
      <div className="source-heading">
        <h3>Citations</h3>
        <span>{sources.length} retrieved</span>
      </div>
      <ul className="source-list">
        {sources.map((src, index) => (
          <li
            key={src.chunk_id}
            id={`citation-${src.chunk_id}`}
            className={referencedIds.has(src.chunk_id) ? 'source-item cited' : 'source-item'}
          >
            <div className="source-meta">
              <span className="source-number">[{index + 1}]</span>
              <strong>{src.document_filename}</strong>
              {src.document_project_name && <span>{src.document_project_name}</span>}
              {src.document_content_type && <span>{formatContentType(src.document_content_type)}</span>}
              <span>Chunk {src.chunk_index + 1}</span>
              {typeof src.score === 'number' && <span>{Math.round(src.score * 100)}%</span>}
              {src.retrieval_signal && <span className="source-signal">{formatSignal(src.retrieval_signal)}</span>}
            </div>
            <div className="source-id">{src.chunk_id}</div>
            <p>{src.content.substring(0, 320)}{src.content.length > 320 ? '...' : ''}</p>
          </li>
        ))}
      </ul>
    </aside>
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

function formatSignal(signal: string): string {
  const labels: Record<string, string> = {
    hybrid: 'Hybrid',
    keyword: 'Keyword',
    latest: 'Latest',
    vector: 'Vector',
  };
  return labels[signal] || signal;
}
