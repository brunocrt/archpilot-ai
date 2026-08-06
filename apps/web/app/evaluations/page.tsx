'use client';

import { useEffect, useState } from 'react';
import {
  createEvaluationCase,
  createEvaluationDataset,
  createEvaluationRun,
  EvaluationDataset,
  EvaluationRunDetail,
  EvaluationRunSummary,
  getEvaluationRun,
  listEvaluationDatasets,
  listEvaluationRuns,
} from '../../lib/api';

export default function EvaluationsPage() {
  const [datasets, setDatasets] = useState<EvaluationDataset[]>([]);
  const [runs, setRuns] = useState<EvaluationRunSummary[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [selectedRun, setSelectedRun] = useState<EvaluationRunDetail | null>(null);
  const [datasetName, setDatasetName] = useState('');
  const [datasetDescription, setDatasetDescription] = useState('');
  const [question, setQuestion] = useState('');
  const [expectedFacts, setExpectedFacts] = useState('');
  const [expectedChunkIds, setExpectedChunkIds] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  async function refresh() {
    const [nextDatasets, nextRuns] = await Promise.all([
      listEvaluationDatasets(),
      listEvaluationRuns(),
    ]);
    setDatasets(nextDatasets);
    setRuns(nextRuns);
    if (!selectedDatasetId && nextDatasets[0]) {
      setSelectedDatasetId(nextDatasets[0].id);
    }
  }

  useEffect(() => {
    refresh().catch(() => setError('Failed to load evaluations'));
  }, []);

  async function addDataset(event: React.FormEvent) {
    event.preventDefault();
    setError('');
    setStatus('Creating dataset...');
    try {
      const dataset = await createEvaluationDataset(datasetName, datasetDescription || undefined);
      setDatasetName('');
      setDatasetDescription('');
      setSelectedDatasetId(dataset.id);
      await refresh();
      setStatus('Dataset created');
    } catch {
      setError('Failed to create dataset');
      setStatus('');
    }
  }

  async function addCase(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedDatasetId) return;
    setError('');
    setStatus('Adding case...');
    try {
      await createEvaluationCase(
        selectedDatasetId,
        question,
        splitLines(expectedFacts),
        splitLines(expectedChunkIds),
      );
      setQuestion('');
      setExpectedFacts('');
      setExpectedChunkIds('');
      await refresh();
      setStatus('Case added');
    } catch {
      setError('Failed to add case');
      setStatus('');
    }
  }

  async function runEvaluation() {
    if (!selectedDatasetId) return;
    setError('');
    setStatus('Running evaluation...');
    try {
      const run = await createEvaluationRun(selectedDatasetId);
      setSelectedRun(run);
      await refresh();
      setStatus('Evaluation completed');
    } catch {
      setError('Failed to run evaluation');
      setStatus('');
    }
  }

  async function selectRun(runId: string) {
    setError('');
    try {
      setSelectedRun(await getEvaluationRun(runId));
    } catch {
      setError('Failed to load evaluation run');
    }
  }

  return (
    <main className="evaluation-layout">
      <section className="evaluation-panel">
        <div className="panel-heading">
          <h2>Evaluations</h2>
          <p>Run local retrieval and answer checks against saved test cases.</p>
        </div>

        <form className="evaluation-form" onSubmit={addDataset}>
          <label>
            <span>Dataset name</span>
            <input value={datasetName} onChange={(event) => setDatasetName(event.target.value)} required />
          </label>
          <label>
            <span>Description</span>
            <input value={datasetDescription} onChange={(event) => setDatasetDescription(event.target.value)} />
          </label>
          <button type="submit">Create dataset</button>
        </form>

        <form className="evaluation-form" onSubmit={addCase}>
          <label>
            <span>Dataset</span>
            <select value={selectedDatasetId} onChange={(event) => setSelectedDatasetId(event.target.value)}>
              <option value="">Select dataset</option>
              {datasets.map((dataset) => (
                <option key={dataset.id} value={dataset.id}>
                  {dataset.name} ({dataset.case_count})
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Question</span>
            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={3} required />
          </label>
          <label>
            <span>Expected facts</span>
            <textarea value={expectedFacts} onChange={(event) => setExpectedFacts(event.target.value)} rows={3} />
          </label>
          <label>
            <span>Expected chunk IDs</span>
            <textarea value={expectedChunkIds} onChange={(event) => setExpectedChunkIds(event.target.value)} rows={2} />
          </label>
          <div className="evaluation-actions">
            <button type="submit" disabled={!selectedDatasetId}>Add case</button>
            <button type="button" onClick={runEvaluation} disabled={!selectedDatasetId}>Run</button>
          </div>
        </form>

        {error && <p className="form-error">{error}</p>}
        {status && <p className="form-success">{status}</p>}
      </section>

      <section className="evaluation-panel">
        <div className="panel-heading">
          <h2>Runs</h2>
          <p>Review aggregate scores and failing cases.</p>
        </div>
        <div className="evaluation-run-list">
          {runs.length === 0 && <p className="empty-state">No evaluation runs yet.</p>}
          {runs.map((run) => (
            <button key={run.id} className="evaluation-run-card" onClick={() => selectRun(run.id)}>
              <span>{run.dataset_name}</span>
              <small>{formatPercent(run.aggregate_metrics.pass_rate)} pass rate</small>
              <small>{new Date(run.started_at).toLocaleString()}</small>
            </button>
          ))}
        </div>

        {selectedRun && (
          <div className="evaluation-results">
            <h3>{selectedRun.dataset_name}</h3>
            <div className="metric-grid">
              <Metric label="Pass" value={formatPercent(selectedRun.aggregate_metrics.pass_rate)} />
              <Metric label="Recall" value={formatNumber(selectedRun.aggregate_metrics.average_context_recall)} />
              <Metric label="Citations" value={formatNumber(selectedRun.aggregate_metrics.average_citation_coverage)} />
              <Metric label="Latency" value={`${formatNumber(selectedRun.aggregate_metrics.average_retrieval_latency_ms)} ms`} />
            </div>
            <table>
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Question</th>
                  <th>Completeness</th>
                  <th>Recall</th>
                </tr>
              </thead>
              <tbody>
                {selectedRun.results.map((result) => (
                  <tr key={result.id}>
                    <td>{result.status}</td>
                    <td>{result.question}</td>
                    <td>{formatNumber(result.answer_metrics.answer_completeness)}</td>
                    <td>{formatNumber(result.retrieval_metrics.context_recall)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

function splitLines(value: string): string[] {
  return value.split('\n').map((line) => line.trim()).filter(Boolean);
}

function formatNumber(value: any): string {
  return typeof value === 'number' ? value.toFixed(2) : '0.00';
}

function formatPercent(value: any): string {
  return `${Math.round((typeof value === 'number' ? value : 0) * 100)}%`;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
