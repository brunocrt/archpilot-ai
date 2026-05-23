import React, { useEffect, useState } from 'react';
import { createProject, listProjects, Project, uploadDocument } from '../lib/api';

export default function UploadPanel() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState('');
  const [newProjectName, setNewProjectName] = useState('');
  const [creatingProject, setCreatingProject] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    const file = files[0];
    setStatus(null);
    setError(null);
    try {
      const res = await uploadDocument(file, projectId || undefined);
      const project = projects.find((item) => item.id === res.project_id);
      setStatus(`Uploaded ${res.filename}${project ? ` to ${project.name}` : ''} successfully.`);
    } catch (err) {
      setError('Upload failed');
    }
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

        <input type="file" onChange={handleUpload} />
      </div>
      {status && <p className="form-success">{status}</p>}
      {error && <p className="form-error">{error}</p>}
    </section>
  );
}
