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
    <div className="p-4 bg-white rounded-md border shadow">
      <h2 className="text-lg font-semibold mb-2">Upload Document</h2>
      <input type="file" onChange={handleUpload} />
      {status && <p className="mt-2 text-green-600 text-sm">{status}</p>}
      {error && <p className="mt-2 text-red-600 text-sm">{error}</p>}
    </div>
  );
}