import React from 'react';
import type { RetrievedChunk } from '../lib/api';

interface Props {
  sources: RetrievedChunk[];
}

export default function SourcePanel({ sources }: Props) {
  if (!sources || sources.length === 0) return null;
  return (
    <aside className="source-panel">
      <div className="source-heading">
        <h3>Citations</h3>
        <span>{sources.length} retrieved</span>
      </div>
      <ul className="source-list">
        {sources.map((src, index) => (
          <li key={src.chunk_id} className="source-item">
            <div className="source-meta">
              <span className="source-number">[{index + 1}]</span>
              <span>{src.document_filename}</span>
              <span>Chunk {src.chunk_index + 1}</span>
              {typeof src.score === 'number' && <span>{Math.round(src.score * 100)}%</span>}
            </div>
            <p>{src.content.substring(0, 320)}{src.content.length > 320 ? '...' : ''}</p>
          </li>
        ))}
      </ul>
    </aside>
  );
}
