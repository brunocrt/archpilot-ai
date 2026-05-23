import React, { useEffect, useState } from 'react';
import {
  createProject,
  listDocuments,
  listProjects,
  DocumentSummary,
  Project,
  uploadDocument,
} from '../lib/api';

const ACCEPTED_TYPES = new Set([
  'application/json',
  'application/pdf',
  'text/markdown',
  'text/plain',
]);
const ACCEPTED_EXTENSIONS = ['.json', '.md', '.markdown', '.pdf', '.txt'];
const PAGE_SIZE = 8;

export default function UploadPanel() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState('');
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentPage, setDocumentPage] = useState(1);
  const [newProjectName, setNewProjectName] = useState('');
  const [creatingProject, setCreatingProject] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<string[]>([]);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => setError('Failed to load projects'));
  }, []);

  useEffect(() => {
    refreshDocuments(projectId);
  }, [projectId]);

  async function refreshDocuments(selectedProjectId = projectId) {
    try {
      const loadedDocuments = await listDocuments(selectedProjectId || undefined);
      setDocuments(loadedDocuments);
      setDocumentPage(1);
    } catch (err) {
      setError('Failed to load uploaded files');
    }
  }

  async function handleCreateProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newProjectName.trim()) return;
    setCreatingProject(true);
    setStatus(null);
    setError(null);
    try {
      const project = await createProject(newProjectName.trim());
      setProjects((current) => [...current, project].sort((a, b) => a.name.localeCompare(b.name)));
      setProjectId(project.id);
      setNewProjectName('');
      setStatus(`Created project ${project.name}.`);
    } catch (err) {
      setError('Failed to create project');
    } finally {
      setCreatingProject(false);
    }
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    const selectedFiles = Array.from(files);
    const validFiles = selectedFiles.filter(isAcceptedFile);
    const rejectedFiles = selectedFiles.filter((file) => !isAcceptedFile(file));
    event.target.value = '';
    setStatus(null);
    setError(null);
    setResults([]);
    if (rejectedFiles.length > 0) {
      setError(`Skipped unsupported files: ${rejectedFiles.map((file) => file.name).join(', ')}`);
    }
    if (validFiles.length === 0) return;
    setUploading(true);
    const project = projects.find((item) => item.id === projectId);
    const uploaded: string[] = [];
    const failed: string[] = [];
    try {
      for (const file of validFiles) {
        try {
          const res = await uploadDocument(file, projectId || undefined);
          uploaded.push(res.filename);
        } catch (err) {
          failed.push(file.name);
        }
      }
      if (uploaded.length > 0) {
        setStatus(`Uploaded ${uploaded.length} file${uploaded.length === 1 ? '' : 's'}${project ? ` to ${project.name}` : ''}.`);
        setResults(uploaded);
        await refreshDocuments();
      }
      if (failed.length > 0) {
        setError(`Failed to upload: ${failed.join(', ')}`);
      }
    } finally {
      setUploading(false);
    }
  }

  function isAcceptedFile(file: File) {
    const filename = file.name.toLowerCase();
    return ACCEPTED_TYPES.has(file.type) || ACCEPTED_EXTENSIONS.some((extension) => filename.endsWith(extension));
  }

  function formatUploadedAt(uploadedAt: string) {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(uploadedAt));
  }

  const pageCount = Math.max(1, Math.ceil(documents.length / PAGE_SIZE));
  const currentPage = Math.min(documentPage, pageCount);
  const pageStart = documents.length === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1;
  const pageEnd = Math.min(currentPage * PAGE_SIZE, documents.length);
  const visibleDocuments = documents.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  return (
    <section className="upload-panel">
      <div className="panel-heading">
        <h2>Upload Document</h2>
        <p>Add text, markdown, JSON, or PDF files to a project knowledge base.</p>
      </div>
      <div className="upload-controls">
        <label>
          <span>Project</span>
          <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
            <option value="">Unassigned</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
        </label>

        <form className="inline-form" onSubmit={handleCreateProject}>
          <input
            value={newProjectName}
            onChange={(event) => setNewProjectName(event.target.value)}
            placeholder="New project name"
          />
          <button type="submit" disabled={creatingProject}>
            {creatingProject ? 'Creating...' : 'Create'}
          </button>
        </form>

        <input
          type="file"
          accept=".txt,.md,.markdown,.json,.pdf,text/plain,text/markdown,application/json,application/pdf"
          multiple
          onChange={handleUpload}
          disabled={uploading}
        />
      </div>
      {status && <p className="form-success">{status}</p>}
      {error && <p className="form-error">{error}</p>}
      {results.length > 0 && (
        <ul className="upload-results">
          {results.map((filename) => (
            <li key={filename}>{filename}</li>
          ))}
        </ul>
      )}
      <div className="document-list">
        <div className="source-heading">
          <h3>Uploaded Files</h3>
          <span>{documents.length === 0 ? '0 shown' : `${pageStart}-${pageEnd} of ${documents.length}`}</span>
        </div>
        {documents.length === 0 ? (
          <p className="empty-state">No files uploaded for this project yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>File</th>
                <th>Project</th>
                <th>Status</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {visibleDocuments.map((document) => (
                <tr key={document.id}>
                  <td>{document.filename}</td>
                  <td>{document.project_name || 'Unassigned'}</td>
                  <td>{document.status}</td>
                  <td>{formatUploadedAt(document.uploaded_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {documents.length > PAGE_SIZE && (
          <div className="pagination">
            <button
              type="button"
              onClick={() => setDocumentPage((page) => Math.max(1, page - 1))}
              disabled={currentPage === 1}
            >
              Previous
            </button>
            <span>Page {currentPage} of {pageCount}</span>
            <button
              type="button"
              onClick={() => setDocumentPage((page) => Math.min(pageCount, page + 1))}
              disabled={currentPage === pageCount}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
