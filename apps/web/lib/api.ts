export interface DocumentUploadResponse {
  document_id: string;
  project_id?: string;
  filename: string;
  status: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

export interface DocumentSummary {
  id: string;
  project_id?: string;
  project_name?: string;
  filename: string;
  content_type?: string;
  status: string;
  uploaded_at: string;
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

export interface LLMSettings {
  provider: 'none' | 'openai';
  model: string;
  has_api_key: boolean;
}

export interface LLMSettingsUpdate {
  provider: 'none' | 'openai';
  model: string;
  api_key?: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function uploadDocument(file: File, projectId?: string): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (projectId) {
    formData.append('project_id', projectId);
  }
  const res = await fetch(`${API_URL}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    throw new Error('Upload failed');
  }
  return await res.json();
}

export async function listProjects(): Promise<Project[]> {
  const res = await fetch(`${API_URL}/projects/`);
  if (!res.ok) {
    throw new Error('Failed to load projects');
  }
  return await res.json();
}

export async function createProject(name: string, description?: string): Promise<Project> {
  const res = await fetch(`${API_URL}/projects/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) {
    throw new Error('Failed to create project');
  }
  return await res.json();
}

export async function listDocuments(projectId?: string): Promise<DocumentSummary[]> {
  const url = new URL(`${API_URL}/documents/`);
  if (projectId) {
    url.searchParams.set('project_id', projectId);
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error('Failed to load documents');
  }
  return await res.json();
}

export async function chatQuery(
  question: string,
  conversationId?: string,
  projectId?: string,
): Promise<AnswerResponse> {
  const payload: any = { question, top_k: 5 };
  if (conversationId) payload.conversation_id = conversationId;
  if (projectId) payload.project_id = projectId;
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

export async function getLLMSettings(): Promise<LLMSettings> {
  const res = await fetch(`${API_URL}/settings/llm`);
  if (!res.ok) {
    throw new Error('Failed to load LLM settings');
  }
  return await res.json();
}

export async function updateLLMSettings(payload: LLMSettingsUpdate): Promise<LLMSettings> {
  const res = await fetch(`${API_URL}/settings/llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error('Failed to save LLM settings');
  }
  return await res.json();
}
