import React from 'react';
import type { RetrievedChunk } from '../lib/api';

interface Props {
  sources: RetrievedChunk[];
}

export default function SourcePanel({ sources }: Props) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mt-4 p-2 bg-gray-100 rounded-md">
      <h3 className="font-semibold mb-2">Sources</h3>
      <ul className="space-y-2 text-sm">
        {sources.map((src) => (
          <li key={src.chunk_id} className="border-b pb-2">
            <span className="font-mono text-xs">[{src.chunk_id}]</span> {src.content.substring(0, 200)}...
          </li>
        ))}
      </ul>
    </div>
  );
}