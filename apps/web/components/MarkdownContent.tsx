import React from 'react';
import type { RetrievedChunk } from '../lib/api';

interface Props {
  content: string;
  sources?: RetrievedChunk[];
}

export default function MarkdownContent({ content, sources = [] }: Props) {
  const citationMap = new Map(sources.map((source, index) => [source.chunk_id, index + 1]));
  const lines = content.split(/\r?\n/);
  const blocks: React.ReactNode[] = [];
  let listItems: string[] = [];

  function flushList() {
    if (listItems.length === 0) return;
    const items = listItems;
    listItems = [];
    blocks.push(
      <ul key={`list-${blocks.length}`}>
        {items.map((item, index) => (
          <li key={index}>{renderInline(item, citationMap)}</li>
        ))}
      </ul>,
    );
  }

  lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      return;
    }
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      listItems.push(trimmed.slice(2));
      return;
    }
    flushList();
    if (trimmed.startsWith('### ')) {
      blocks.push(<h4 key={index}>{renderInline(trimmed.slice(4), citationMap)}</h4>);
    } else if (trimmed.startsWith('## ')) {
      blocks.push(<h3 key={index}>{renderInline(trimmed.slice(3), citationMap)}</h3>);
    } else {
      blocks.push(<p key={index}>{renderInline(trimmed, citationMap)}</p>);
    }
  });
  flushList();

  return <div className="markdown-content">{blocks}</div>;
}

function renderInline(text: string, citationMap: Map<string, number>): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[0-9a-fA-F-]{36}\])/g);
  return parts.map((part, index) => {
    const citationId = part.match(/^\[([0-9a-fA-F-]{36})\]$/)?.[1];
    if (citationId && citationMap.has(citationId)) {
      const citationNumber = citationMap.get(citationId);
      return (
        <a key={index} className="citation-link" href={`#citation-${citationId}`}>
          [{citationNumber}]
        </a>
      );
    }
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={index}>{part.slice(1, -1)}</code>;
    }
    return part;
  });
}
