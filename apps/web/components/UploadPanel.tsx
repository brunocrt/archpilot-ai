import React, { useEffect, useState } from 'react';
import { createProject, listProjects, Project, uploadDocument } from '../lib/api';

const ACCEPTED_TYPES = new Set([
  'application/json',
  'application/pdf',
  'text/markdown',
  'text/plain',
]);
const ACCEPTED_EXTENSIONS = ['.json', '.md', '.markdown', '.pdf', '.txt'];

export default function UploadPanel() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState('');
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
    </section>
  );
}
