import { useEffect, useMemo, useState, type ChangeEvent } from "react";

import { fetchDefaultModes, fetchRunHistory, previewPrompt, runBenchmark, uploadContextFile } from "./api";
import { DEFAULT_MODE_SELECTION, DEFAULT_PROMPT_TEMPLATE } from "./defaults";
import type { BenchmarkResponse, ModeSelection, RunHistoryItem } from "./types";

type PromptVarRow = { key: string; value: string };

function toVariableMap(rows: PromptVarRow[]): Record<string, string> {
  const data: Record<string, string> = {};
  for (const row of rows) {
    if (row.key.trim()) {
      data[row.key.trim()] = row.value;
    }
  }
  return data;
}

export default function App() {
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("gemini-2.5-flash");
  const [stack, setStack] = useState("google_genai");
  const [vertexProjectId, setVertexProjectId] = useState("");
  const [vertexLocation, setVertexLocation] = useState("us-central1");
  const [vertexEndpointId, setVertexEndpointId] = useState("openapi");
  const [vertexAccessToken, setVertexAccessToken] = useState("");
  const [trials, setTrials] = useState(10);
  const [warmupTrials, setWarmupTrials] = useState(2);
  const [modeSelection, setModeSelection] = useState<ModeSelection>(DEFAULT_MODE_SELECTION);
  const [promptTemplate, setPromptTemplate] = useState(DEFAULT_PROMPT_TEMPLATE);
  const [promptVars, setPromptVars] = useState<PromptVarRow[]>([
    { key: "dataset_name", value: "customer_support_logs" },
    { key: "goal", value: "reduce first token latency while preserving answer quality" },
    { key: "data_context", value: "Multilingual user support queries over the last 30 days." },
  ]);
  const [promptPreview, setPromptPreview] = useState("");
  const [previewMissing, setPreviewMissing] = useState<string[]>([]);
  const [result, setResult] = useState<BenchmarkResponse | null>(null);
  const [history, setHistory] = useState<RunHistoryItem[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchDefaultModes()
      .then((data) => {
        setModel(data.defaults.model);
        setStack(data.defaults.stack);
        setTrials(data.defaults.trials);
        setModeSelection({
          streaming: data.defaults.streaming,
          thinking: data.defaults.thinking,
          implicit_cache: data.defaults.implicit_cache,
          explicit_cache: data.defaults.explicit_cache,
        });
      })
      .catch(() => {
        // Keep local defaults if endpoint is unavailable.
      });
    void fetchRunHistory()
      .then((data) => setHistory(data.runs))
      .catch(() => {
        // Ignore history load failure on startup.
      });
  }, []);

  const variableMap = useMemo(() => toVariableMap(promptVars), [promptVars]);

  async function handlePreviewPrompt() {
    setError(null);
    try {
      const data = await previewPrompt(promptTemplate, variableMap);
      setPromptPreview(data.rendered_prompt);
      setPreviewMissing(data.missing_variables);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prompt preview failed");
    }
  }

  function updateMode(field: keyof ModeSelection, value: boolean) {
    setModeSelection((prev) => ({ ...prev, [field]: value }));
  }

  function updateVar(index: number, field: "key" | "value", value: string) {
    setPromptVars((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  }

  function addVarRow() {
    setPromptVars((prev) => [...prev, { key: "", value: "" }]);
  }

  async function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    setError(null);
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setIsUploading(true);
    try {
      const payload = await uploadContextFile(file, "data_context");
      setPromptVars((prev) => {
        const next = [...prev];
        const idx = next.findIndex((item) => item.key === payload.variable_key);
        if (idx >= 0) {
          next[idx] = { key: payload.variable_key, value: payload.context_text };
        } else {
          next.push({ key: payload.variable_key, value: payload.context_text });
        }
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Context upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  async function refreshHistory() {
    setError(null);
    try {
      const data = await fetchRunHistory();
      setHistory(data.runs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh run history");
    }
  }

  async function onRunBenchmark() {
    setError(null);
    setResult(null);
    if (stack === "vertex_api") {
      if (!vertexProjectId.trim() || !vertexLocation.trim() || !vertexEndpointId.trim()) {
        setError("Vertex Project ID, Location, and Endpoint ID are required for vertex_api.");
        return;
      }
    } else if (!apiKey.trim()) {
      setError("API key is required to run benchmarks.");
      return;
    }

    setIsRunning(true);
    try {
      const payload = {
        api_key: apiKey.trim() || undefined,
        stacks: [stack],
        models: [model],
        trials,
        warmup_trials: warmupTrials,
        max_output_tokens: 128,
        temperature: 0.2,
        timeout_s: 90,
        mode_selection: modeSelection,
        prompt_template: promptTemplate,
        prompt_variables: variableMap,
        vertex_config:
          stack === "vertex_api"
            ? {
                project_id: vertexProjectId.trim(),
                location: vertexLocation.trim(),
                endpoint_id: vertexEndpointId.trim(),
                access_token: vertexAccessToken.trim() || undefined,
              }
            : undefined,
        include_long_context: true,
      };
      const response = await runBenchmark(payload);
      setResult(response);
      await refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Benchmark failed");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <div className="container">
      <h1>Gemini Benchmark Studio</h1>
      <p className="subtitle">
        Run TTFT benchmarks with configurable modes and a supervisor-worker recommendation agent.
      </p>

      <section className="card">
        <h2>Run Settings</h2>
        <div className="grid">
          <label>
            API Key
            <input
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="Enter Gemini API key"
            />
          </label>
          <label>
            Stack
            <select value={stack} onChange={(event) => setStack(event.target.value)}>
              <option value="google_genai">google_genai</option>
              <option value="openai_compat">openai_compat</option>
              <option value="vertex_api">vertex_api</option>
            </select>
          </label>
          <label>
            Model
            <input value={model} onChange={(event) => setModel(event.target.value)} />
          </label>
          <label>
            Trials
            <input
              type="number"
              min={1}
              max={100}
              value={trials}
              onChange={(event) => setTrials(Number(event.target.value))}
            />
          </label>
          <label>
            Warmup Trials
            <input
              type="number"
              min={0}
              max={20}
              value={warmupTrials}
              onChange={(event) => setWarmupTrials(Number(event.target.value))}
            />
          </label>
        </div>
        {stack === "vertex_api" && (
          <div className="grid">
            <label>
              Vertex Project ID
              <input
                value={vertexProjectId}
                onChange={(event) => setVertexProjectId(event.target.value)}
                placeholder="your-gcp-project-id"
              />
            </label>
            <label>
              Vertex Location
              <input
                value={vertexLocation}
                onChange={(event) => setVertexLocation(event.target.value)}
                placeholder="us-central1"
              />
            </label>
            <label>
              Vertex Endpoint ID
              <input
                value={vertexEndpointId}
                onChange={(event) => setVertexEndpointId(event.target.value)}
                placeholder="openapi"
              />
            </label>
            <label>
              Vertex Access Token (optional)
              <input
                type="password"
                value={vertexAccessToken}
                onChange={(event) => setVertexAccessToken(event.target.value)}
                placeholder="Leave empty to use ADC on server"
              />
            </label>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Mode Selection (Checkboxes)</h2>
        <div className="checkboxes">
          <label>
            <input
              type="checkbox"
              checked={modeSelection.streaming}
              onChange={(event) => updateMode("streaming", event.target.checked)}
            />
            Streaming
          </label>
          <label>
            <input
              type="checkbox"
              checked={modeSelection.thinking}
              onChange={(event) => updateMode("thinking", event.target.checked)}
            />
            Thinking
          </label>
          <label>
            <input
              type="checkbox"
              checked={modeSelection.implicit_cache}
              onChange={(event) => updateMode("implicit_cache", event.target.checked)}
            />
            Implicit Cache
          </label>
          <label>
            <input
              type="checkbox"
              checked={modeSelection.explicit_cache}
              onChange={(event) => updateMode("explicit_cache", event.target.checked)}
            />
            Explicit Cache
          </label>
        </div>
      </section>

      <section className="card">
        <h2>Prompt Template for Your Data</h2>
        <label>
          Prompt Template
          <textarea
            rows={4}
            value={promptTemplate}
            onChange={(event) => setPromptTemplate(event.target.value)}
          />
        </label>
        <div className="variable-grid">
          {promptVars.map((row, index) => (
            <div key={index} className="variable-row">
              <input
                placeholder="variable key"
                value={row.key}
                onChange={(event) => updateVar(index, "key", event.target.value)}
              />
              <input
                placeholder="value"
                value={row.value}
                onChange={(event) => updateVar(index, "value", event.target.value)}
              />
            </div>
          ))}
        </div>
        <div className="actions">
          <button onClick={addVarRow} type="button">
            Add Variable
          </button>
          <button onClick={() => void handlePreviewPrompt()} type="button">
            Preview Prompt
          </button>
          <label className="file-upload">
            Upload Data File
            <input type="file" onChange={(event) => void handleFileUpload(event)} />
          </label>
          {isUploading && <span className="muted">Uploading...</span>}
        </div>
        {promptPreview && (
          <div className="preview">
            <h3>Rendered Prompt</h3>
            <p>{promptPreview}</p>
          </div>
        )}
        {previewMissing.length > 0 && (
          <p className="warn">Missing variables: {previewMissing.join(", ")}</p>
        )}
      </section>

      <div className="actions">
        <button className="primary" onClick={() => void onRunBenchmark()} disabled={isRunning}>
          {isRunning ? "Running..." : "Run Benchmark"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <section className="card">
          <h2>Results</h2>
          <p>
            <strong>Run ID:</strong> {result.run_id}
          </p>
          <p>
            <strong>Best Scenario:</strong> {result.recommendation.best_scenario_id ?? "n/a"}
          </p>
          <p>
            <strong>Recommendation:</strong> {result.recommendation.rationale}
          </p>

          <h3>Alternatives</h3>
          <ul>
            {result.recommendation.alternatives.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>

          <h3>Scenario Summaries</h3>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Scenario</th>
                  <th>TTFT P50</th>
                  <th>E2E P50</th>
                  <th>TPS Avg</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {result.summaries.map((row) => (
                  <tr key={row.scenario_id}>
                    <td>{row.scenario_id}</td>
                    <td>{row.ttft_p50_s?.toFixed(3) ?? "n/a"}</td>
                    <td>{row.e2e_p50_s?.toFixed(3) ?? "n/a"}</td>
                    <td>{row.tokens_per_s_avg?.toFixed(2) ?? "n/a"}</td>
                    <td>{row.note ?? "ok"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3>Agent Trace</h3>
          <ul>
            {result.reasoning_trace.map((item, idx) => (
              <li key={`${idx}-${item}`}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="card">
        <h2>Run History</h2>
        <div className="actions">
          <button type="button" onClick={() => void refreshHistory()}>
            Refresh History
          </button>
        </div>
        {history.length === 0 ? (
          <p className="muted">No run history yet.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Saved At</th>
                  <th>Run ID</th>
                  <th>Best Scenario</th>
                  <th>Summaries</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={`${item.saved_at}-${item.run_id}`}>
                    <td>{item.saved_at}</td>
                    <td>{item.run_id}</td>
                    <td>{item.best_scenario_id ?? "n/a"}</td>
                    <td>{item.summaries_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

