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
  document_project_name?: string;
  document_content_type?: string;
  chunk_index: number;
  score?: number;
  retrieval_signal?: string;
  content: string;
}

export interface RetrievalDiagnostics {
  mode: string;
  project_id?: string;
  document_filename?: string;
  content_type?: string;
  top_k: number;
}

export interface AnswerResponse {
  conversation_id: string;
  answer: string;
  sources: RetrievedChunk[];
  retrieved_chunks: RetrievedChunk[];
  retrieval?: RetrievalDiagnostics;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title?: string;
  created_at: string;
  message_count: number;
  last_message_at?: string;
}

export interface ConversationDetail {
  id: string;
  title?: string;
  created_at: string;
  messages: MessageResponse[];
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

export interface EvaluationDataset {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  case_count: number;
}

export interface EvaluationCase {
  id: string;
  dataset_id: string;
  question: string;
  expected_answer?: string;
  expected_facts: string[];
  expected_chunk_ids: string[];
  created_at: string;
}

export interface EvaluationRunSummary {
  id: string;
  dataset_id: string;
  dataset_name: string;
  status: string;
  provider?: string;
  model?: string;
  aggregate_metrics: Record<string, any>;
  started_at: string;
  completed_at?: string;
  result_count: number;
}

export interface EvaluationResult {
  id: string;
  case_id: string;
  question: string;
  generated_answer: string;
  retrieved_chunks: any[];
  retrieval_metrics: Record<string, any>;
  answer_metrics: Record<string, any>;
  provider?: string;
  model?: string;
  status: string;
  created_at: string;
}

export interface EvaluationRunDetail extends EvaluationRunSummary {
  results: EvaluationResult[];
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
  filters?: { documentFilename?: string; contentType?: string },
): Promise<AnswerResponse> {
  const payload: any = { question, top_k: 5 };
  if (conversationId) payload.conversation_id = conversationId;
  if (projectId) payload.project_id = projectId;
  if (filters?.documentFilename) payload.document_filename = filters.documentFilename;
  if (filters?.contentType) payload.content_type = filters.contentType;
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

export async function chatQueryStream(
  question: string,
  handlers: {
    conversationId?: string;
    projectId?: string;
    documentFilename?: string;
    contentType?: string;
    onConversation?: (conversationId: string) => void;
    onSources?: (sources: RetrievedChunk[]) => void;
    onRetrieval?: (retrieval: RetrievalDiagnostics) => void;
    onDelta?: (text: string) => void;
    onDone?: (response: AnswerResponse) => void;
  },
): Promise<void> {
  const payload: any = { question, top_k: 5 };
  if (handlers.conversationId) payload.conversation_id = handlers.conversationId;
  if (handlers.projectId) payload.project_id = handlers.projectId;
  if (handlers.documentFilename) payload.document_filename = handlers.documentFilename;
  if (handlers.contentType) payload.content_type = handlers.contentType;
  const res = await fetch(`${API_URL}/chat/query/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok || !res.body) {
    throw new Error('Streaming chat failed');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let conversationId = handlers.conversationId || '';
  let sources: RetrievedChunk[] = [];
  let retrieval: RetrievalDiagnostics | undefined;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';
    for (const eventText of events) {
      const parsed = parseSseEvent(eventText);
      if (!parsed) continue;
      if (parsed.event === 'conversation') {
        conversationId = parsed.data.conversation_id;
        handlers.onConversation?.(conversationId);
      } else if (parsed.event === 'sources') {
        sources = parsed.data;
        handlers.onSources?.(sources);
      } else if (parsed.event === 'retrieval') {
        retrieval = parsed.data;
        handlers.onRetrieval?.(retrieval);
      } else if (parsed.event === 'delta') {
        handlers.onDelta?.(parsed.data.text);
      } else if (parsed.event === 'done') {
        retrieval = parsed.data.retrieval || retrieval;
        handlers.onDone?.({
          conversation_id: parsed.data.conversation_id || conversationId,
          answer: parsed.data.answer,
          sources,
          retrieved_chunks: sources,
          retrieval,
        });
      }
    }
  }
}

function parseSseEvent(eventText: string): { event: string; data: any } | null {
  const eventLine = eventText.split('\n').find((line) => line.startsWith('event: '));
  const dataLine = eventText.split('\n').find((line) => line.startsWith('data: '));
  if (!eventLine || !dataLine) return null;
  return {
    event: eventLine.replace('event: ', '').trim(),
    data: JSON.parse(dataLine.replace('data: ', '')),
  };
}

export async function listConversations(): Promise<ConversationSummary[]> {
  const res = await fetch(`${API_URL}/chat/conversations`);
  if (!res.ok) {
    throw new Error('Failed to load conversations');
  }
  return await res.json();
}

export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  const res = await fetch(`${API_URL}/chat/conversations/${conversationId}`);
  if (!res.ok) {
    throw new Error('Failed to load conversation');
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

export async function listEvaluationDatasets(): Promise<EvaluationDataset[]> {
  const res = await fetch(`${API_URL}/evaluations/datasets`);
  if (!res.ok) {
    throw new Error('Failed to load evaluation datasets');
  }
  return await res.json();
}

export async function createEvaluationDataset(name: string, description?: string): Promise<EvaluationDataset> {
  const res = await fetch(`${API_URL}/evaluations/datasets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) {
    throw new Error('Failed to create evaluation dataset');
  }
  return await res.json();
}

export async function createEvaluationCase(
  datasetId: string,
  question: string,
  expectedFacts: string[],
  expectedChunkIds: string[],
): Promise<EvaluationCase> {
  const res = await fetch(`${API_URL}/evaluations/datasets/${datasetId}/cases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      expected_facts: expectedFacts,
      expected_chunk_ids: expectedChunkIds,
    }),
  });
  if (!res.ok) {
    throw new Error('Failed to create evaluation case');
  }
  return await res.json();
}

export async function listEvaluationRuns(): Promise<EvaluationRunSummary[]> {
  const res = await fetch(`${API_URL}/evaluations/runs`);
  if (!res.ok) {
    throw new Error('Failed to load evaluation runs');
  }
  return await res.json();
}

export async function createEvaluationRun(datasetId: string, topK = 5): Promise<EvaluationRunDetail> {
  const res = await fetch(`${API_URL}/evaluations/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId, top_k: topK }),
  });
  if (!res.ok) {
    throw new Error('Failed to run evaluation');
  }
  return await res.json();
}

export async function getEvaluationRun(runId: string): Promise<EvaluationRunDetail> {
  const res = await fetch(`${API_URL}/evaluations/runs/${runId}`);
  if (!res.ok) {
    throw new Error('Failed to load evaluation run');
  }
  return await res.json();
}
