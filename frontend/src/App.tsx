import { useMemo, useState } from 'react';
import { fetchAnalysis } from './services/api';

const sampleNotes = `On Monday, the team approved the marketing launch budget for Q3.
By Wednesday, leadership rejected the launch budget after cost overruns surfaced.
Later, the committee reconsidered the budget and restored the launch plan.`;

type Candidate = {
  text: string;
  topic: string;
  status: string;
  confidence: number;
  reversal: boolean;
  evidence: string[];
};

type Reversal = {
  topic: string;
  relationship: string;
  previous: string;
  current: string;
  similarity: number;
  confidence: number;
  confidence_basis: string;
  limitations: string[];
  original_decision: EvidenceDecision;
  intermediate_updates: EvidenceDecision[];
  latest_decision: EvidenceDecision;
  timeline: EvidenceDecision[];
  evidence: EvidenceSnippet[];
  nlp_signals: {
    original: Record<string, unknown>;
    latest: Record<string, unknown>;
  };
};

type EvidenceDecision = {
  text: string;
  option: string | null;
  status: string;
  timestamp: string | null;
  speaker: string | null;
  source_text: string;
  char_start: number;
  char_end: number;
};

type EvidenceSnippet = EvidenceDecision & { record_id: string | null };

type TraceStage = {
  stage: string;
  status: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  explanation: string;
};

type ProcessingTrace = {
  record_id: string;
  source_text: string;
  sentence_index: number;
  source_spans: { start: number; end: number }[];
  warnings: string[];
  stages: TraceStage[];
};

export default function App() {
  const [notes, setNotes] = useState(sampleNotes);
  const [result, setResult] = useState<{
    candidates: Candidate[];
    reversed_decisions: Reversal[];
    summary: string;
    traces: ProcessingTrace[];
    processing_summary: Record<string, number>;
  } | null>(null);
  const [selectedReversal, setSelectedReversal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parsedNotes = useMemo(
    () => notes.split(/\n+/).map((line) => line.trim()).filter(Boolean),
    [notes],
  );

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchAnalysis(parsedNotes);
      setResult(payload);
      setSelectedReversal(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen px-6 py-10 text-slate-100">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl border border-slate-700 bg-slate-900/80 p-6 shadow-xl">
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">DecisionTrace</p>
          <h1 className="mt-2 text-3xl font-bold">Meeting decision reversal detector</h1>
          <p className="mt-3 max-w-3xl text-slate-300">
            Paste meeting notes and identify where a decision is changed, reversed, or restored.
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-2xl border border-slate-700 bg-slate-900/80 p-5">
            <label htmlFor="notes" className="mb-2 block text-sm font-medium text-slate-200">
              Meeting notes
            </label>
            <textarea
              id="notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              className="h-64 w-full resize-none rounded-xl border border-slate-700 bg-slate-950 p-4 text-slate-100 outline-none ring-0 transition focus:border-cyan-500"
              placeholder="Paste each meeting note on its own line"
            />
            <div className="mt-4 flex items-center justify-between gap-3">
              <span className="text-sm text-slate-400">{parsedNotes.length} entries</span>
              <button
                onClick={runAnalysis}
                disabled={loading}
                className="rounded-xl bg-cyan-600 px-4 py-2 font-medium text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? 'Analyzing...' : 'Analyze decisions'}
              </button>
            </div>
            {error && <p className="mt-4 text-sm text-rose-400">{error}</p>}
          </section>

          <section className="rounded-2xl border border-slate-700 bg-slate-900/80 p-5">
            <h2 className="text-lg font-semibold">Detected outcomes</h2>
            {result ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                  <p className="text-sm text-slate-300">Summary</p>
                  <p className="mt-2 text-base font-medium text-cyan-300">{result.summary}</p>
                </div>
                <div className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                  <p className="text-sm text-slate-300">Reversals</p>
                  <div className="mt-3 space-y-2 text-sm text-slate-200">
                    {result.reversed_decisions.length > 0 ? (
                      result.reversed_decisions.map((item, index) => (
                        <button
                          key={`${item.topic}-${index}`}
                          onClick={() => setSelectedReversal(index)}
                          className={`block w-full rounded-lg border p-3 text-left ${selectedReversal === index ? 'border-cyan-400 bg-cyan-500/10' : 'border-amber-500/40 bg-amber-500/5'}`}
                        >
                          <p className="font-medium text-amber-300">{item.topic}</p>
                          <p>{item.original_decision.option ?? 'Unspecified'} → {item.latest_decision.option ?? 'Unspecified'}</p>
                          <p className="text-xs text-slate-400">Similarity signal: {item.similarity}</p>
                        </button>
                      ))
                    ) : (
                      <p className="text-slate-400">No reversal events found.</p>
                    )}
                  </div>
                </div>
                {result.reversed_decisions[selectedReversal] && (
                  <EvidenceExplorer reversal={result.reversed_decisions[selectedReversal]} />
                )}
              </div>
            ) : (
              <p className="mt-4 text-slate-400">No analysis yet.</p>
            )}
          </section>
        </div>
        {result && <ProcessingPipeline traces={result.traces} summary={result.processing_summary} />}
      </div>
    </main>
  );
}

function ProcessingPipeline({
  traces,
  summary,
}: {
  traces: ProcessingTrace[];
  summary: Record<string, number>;
}) {
  const [selected, setSelected] = useState(0);
  const [stageIndex, setStageIndex] = useState(0);
  const trace = traces[selected];
  const stage = trace ? trace.stages[stageIndex] : undefined;

  return (
    <section className="rounded-2xl border border-slate-700 bg-slate-900/80 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-400">Traceable backend evidence</p>
          <h2 className="mt-1 text-2xl font-semibold">How DecisionTrace Works</h2>
          <p className="mt-2 text-sm text-slate-400">
            Select an entry to inspect the actual outputs produced by each NLP stage.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
          {Object.entries(summary).map(([key, value]) => (
            <div key={key} className="rounded-lg border border-slate-700 bg-slate-950 p-2">
              <p className="text-slate-500">{key.split('_').join(' ')}</p>
              <p className="mt-1 text-lg font-semibold text-cyan-300">{value}</p>
            </div>
          ))}
        </div>
      </div>
      {trace ? (
        <div className="mt-5 grid gap-4 lg:grid-cols-[220px_1fr]">
          <div className="space-y-2">
            {traces.map((item, index) => (
              <button
                key={`${item.record_id}-${item.sentence_index}`}
                onClick={() => { setSelected(index); setStageIndex(0); }}
                className={`w-full rounded-lg border p-3 text-left text-sm ${selected === index ? 'border-cyan-400 bg-cyan-500/10' : 'border-slate-700 bg-slate-950/50'}`}
              >
                <p className="font-medium text-slate-200">{item.record_id}</p>
                <p className="mt-1 line-clamp-2 text-xs text-slate-400">{item.source_text}</p>
              </button>
            ))}
          </div>
          <div>
            <div className="flex flex-wrap gap-2">
              {trace.stages.map((item, index) => (
                <button
                  key={item.stage}
                  onClick={() => setStageIndex(index)}
                  className={`rounded-full border px-3 py-1.5 text-xs ${stageIndex === index ? 'border-cyan-400 bg-cyan-500/10 text-cyan-200' : 'border-slate-700 text-slate-400'}`}
                >
                  {index + 1}. {item.stage.split('_').join(' ')}
                </button>
              ))}
            </div>
            {stage && (
              <div className="mt-4 rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-lg font-semibold text-cyan-300">{stage.stage.split('_').join(' ')}</h3>
                  <span className="rounded-full border border-emerald-500/40 px-2 py-1 text-xs text-emerald-300">{stage.status}</span>
                </div>
                <p className="mt-2 text-sm text-slate-300">{stage.explanation}</p>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <TraceData title="Inputs" value={stage.inputs} />
                  <TraceData title="Actual outputs" value={stage.outputs} />
                </div>
                {trace.warnings.length > 0 && (
                  <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm text-amber-200">
                    <p className="font-medium">Warnings</p>
                    <ul className="mt-1 list-disc pl-5">{trace.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        <p className="mt-5 text-sm text-slate-400">No parsed entries were available to trace.</p>
      )}
    </section>
  );
}

function TraceData({ title, value }: { title: string; value: unknown }) {
  return (
    <div>
      <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">{title}</p>
      <pre className="max-h-72 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-300">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

function EvidenceExplorer({ reversal }: { reversal: Reversal }) {
  return (
    <div className="space-y-4 rounded-xl border border-cyan-500/30 bg-slate-950/60 p-4">
      <div>
        <h3 className="text-lg font-semibold text-cyan-300">Decision Evidence Explorer</h3>
        <p className="mt-1 text-sm text-slate-400">{reversal.confidence_basis}</p>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <EvidenceCard title="Original decision" item={reversal.original_decision} />
        <EvidenceCard title="Latest decision" item={reversal.latest_decision} />
        <div className="rounded-lg border border-slate-700 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-400">Confidence</p>
          <p className="mt-1 text-xl font-semibold text-white">{reversal.confidence}</p>
          <p className="mt-1 text-xs text-slate-400">Supported signal, not a probability.</p>
        </div>
      </div>
      <div>
        <p className="mb-2 text-sm font-medium text-slate-200">Decision timeline</p>
        <div className="space-y-2">
          {reversal.timeline.map((item, index) => (
            <EvidenceCard key={`${item.text}-${index}`} title={`${index + 1}. ${item.status}`} item={item} />
          ))}
        </div>
      </div>
      <div>
        <p className="mb-2 text-sm font-medium text-slate-200">NLP signals</p>
        <pre className="max-h-48 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-300">
          {JSON.stringify(reversal.nlp_signals, null, 2)}
        </pre>
      </div>
      <div>
        <p className="mb-2 text-sm font-medium text-slate-200">Limitations</p>
        <ul className="list-disc space-y-1 pl-5 text-xs text-slate-400">
          {reversal.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
        </ul>
      </div>
    </div>
  );
}

function EvidenceCard({ title, item }: { title: string; item: EvidenceDecision }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-400">{title}</p>
      <p className="mt-1 text-sm text-slate-100">{item.text}</p>
      <p className="mt-2 text-xs text-slate-400">
        {item.speaker ? `Speaker: ${item.speaker} · ` : ''}
        {item.timestamp ? `Time: ${item.timestamp}` : 'Timestamp unavailable'}
      </p>
      <p className="mt-1 text-xs text-slate-500">
        Exact source span: characters {item.char_start}–{item.char_end}
      </p>
    </div>
  );
}
