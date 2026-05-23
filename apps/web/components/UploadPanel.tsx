import React, { useState } from 'react';
import { uploadDocument } from '../lib/api';

export default function UploadPanel() {
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    const file = files[0];
    setStatus(null);
    setError(null);
    try {
      const res = await uploadDocument(file);
      setStatus(`Uploaded ${res.filename} successfully.`);
    } catch (err) {
      setError('Upload failed');
    }
  }

  return (
    <section className="upload-panel">
      <div className="panel-heading">
        <h2>Upload Document</h2>
        <p>Add text, markdown, JSON, or PDF files to the knowledge base.</p>
      </div>
      <input type="file" onChange={handleUpload} />
      {status && <p className="form-success">{status}</p>}
      {error && <p className="form-error">{error}</p>}
    </section>
  );
}
