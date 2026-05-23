export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  status: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  document_filename: string;
  chunk_index: number;
  score?: number;
  content: string;
}

export interface AnswerResponse {
  conversation_id: string;
  answer: string;
  sources: RetrievedChunk[];
  retrieved_chunks: RetrievedChunk[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_URL}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    throw new Error('Upload failed');
  }
  return await res.json();
}

export async function chatQuery(question: string, conversationId?: string): Promise<AnswerResponse> {
  const payload: any = { question, top_k: 5 };
  if (conversationId) payload.conversation_id = conversationId;
  const res = await fetch(`${API_URL}/chat/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error('Chat failed');
  }
  return await res.json();
}
