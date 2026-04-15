import { Fragment, useEffect, useMemo, useState, type ChangeEvent } from "react";

import {
  fetchDefaultModes,
  fetchExactTokenCount,
  fetchRunHistory,
  optimizeAndBenchmark,
  optimizePrompt,
  previewPrompt,
  runBenchmark,
  uploadContextFile,
} from "./api";
import { DEFAULT_MODE_SELECTION, DEFAULT_PROMPT_TEMPLATE } from "./defaults";
import type {
  BenchmarkRequest,
  BenchmarkResponse,
  ModeSelection,
  PromptOptimizationVariant,
  PromptOptimizationResponse,
  RunHistoryItem,
} from "./types";

type PromptVarRow = { key: string; value: string };
type CacheStrategy = "none" | "implicit_reuse" | "explicit_cache";
type CodeVariation = {
  id: string;
  label: string;
  streaming: boolean;
  thinking: boolean;
  cacheStrategy: CacheStrategy;
};

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
  const [optimizationObjective, setOptimizationObjective] =
    useState<"lowest_latency" | "highest_quality" | "balanced">("balanced");
  const [optimizationVariantCount, setOptimizationVariantCount] = useState(3);
  const [lockedPhrases, setLockedPhrases] = useState("");
  const [promptVars, setPromptVars] = useState<PromptVarRow[]>([
    { key: "dataset_name", value: "customer_support_logs" },
    { key: "goal", value: "reduce first token latency while preserving answer quality" },
    { key: "data_context", value: "Multilingual user support queries over the last 30 days." },
  ]);
  const [promptPreview, setPromptPreview] = useState("");
  const [previewMissing, setPreviewMissing] = useState<string[]>([]);
  const [showTokenCount, setShowTokenCount] = useState(false);
  const [isCountingTokens, setIsCountingTokens] = useState(false);
  const [exactTokenCount, setExactTokenCount] = useState<number | null>(null);
  const [tokenCountNote, setTokenCountNote] = useState<string | null>(null);
  const [result, setResult] = useState<BenchmarkResponse | null>(null);
  const [optimizationResult, setOptimizationResult] = useState<PromptOptimizationResponse | null>(null);
  const [history, setHistory] = useState<RunHistoryItem[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [isOptimizingAndBenchmarking, setIsOptimizingAndBenchmarking] = useState(false);
  const [showVariantCode, setShowVariantCode] = useState(false);
  const [copiedVariantId, setCopiedVariantId] = useState<string | null>(null);
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

  async function handleOptimizePrompt() {
    setError(null);
    setIsOptimizing(true);
    try {
      const response = await optimizePrompt({
        template: promptTemplate,
        variables: variableMap,
        objective: optimizationObjective,
        variant_count: optimizationVariantCount,
        locked_phrases: lockedPhrases
          .split(",")
          .map((item) => item.trim())
          .filter((item) => item.length > 0),
      });
      setOptimizationResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prompt optimization failed");
    } finally {
      setIsOptimizing(false);
    }
  }

  function applyWinnerTemplate() {
    if (!optimizationResult) {
      return;
    }
    setPromptTemplate(optimizationResult.winner_template);
  }

  function pythonSafeString(value: string): string {
    return value.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
  }

  async function handleExactTokenCount() {
    setError(null);
    setIsCountingTokens(true);
    try {
      const response = await fetchExactTokenCount({
        stack,
        model,
        api_key: apiKey.trim() || undefined,
        template: promptTemplate,
        variables: variableMap,
        vertex_config:
          stack === "vertex_api"
            ? {
                project_id: vertexProjectId.trim(),
                location: vertexLocation.trim(),
                endpoint_id: vertexEndpointId.trim(),
                access_token: vertexAccessToken.trim() || undefined,
              }
            : undefined,
      });
      setExactTokenCount(response.token_count);
      setTokenCountNote(response.note ?? null);
      if (response.rendered_prompt && !promptPreview) {
        setPromptPreview(response.rendered_prompt);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Exact token count failed");
    } finally {
      setIsCountingTokens(false);
    }
  }

  function buildCodeVariations(): CodeVariation[] {
    const cacheStrategies: CacheStrategy[] = ["none"];
    if (modeSelection.implicit_cache) {
      cacheStrategies.push("implicit_reuse");
    }
    if (modeSelection.explicit_cache) {
      cacheStrategies.push("explicit_cache");
    }
    return cacheStrategies.map((cacheStrategy) => {
      const modeLabel = modeSelection.streaming ? "streaming" : "non_streaming";
      const thinkingLabel = modeSelection.thinking ? "thinking_on" : "thinking_off";
      return {
        id: `${modeLabel}_${thinkingLabel}_${cacheStrategy}`,
        label: `${modeLabel} | ${thinkingLabel} | cache=${cacheStrategy}`,
        streaming: modeSelection.streaming,
        thinking: modeSelection.thinking,
        cacheStrategy,
      };
    });
  }

  function buildVariantPythonCode(variant: PromptOptimizationVariant, variation: CodeVariation): string {
    const variableEntries = Object.entries(variableMap)
      .map(([key, value]) => `    '${pythonSafeString(key)}': '${pythonSafeString(value)}'`)
      .join(",\n");
    const renderedPromptExpr =
      "prompt = prompt_template\nfor k, v in prompt_variables.items():\n    prompt = prompt.replace('{{' + k + '}}', str(v))";

    if (stack === "google_genai") {
      const thinkingBudget = variation.thinking ? "1024" : "0";
      const promptPreparation = [
        "shared_prefix = prompt_variables.get('data_context', '')",
        "if " + (variation.cacheStrategy === "implicit_reuse" ? "True" : "False") + ":",
        "    prompt = (shared_prefix + '\\n' + prompt).strip() if shared_prefix else prompt",
      ].join("\n");
      const explicitCacheBlock = variation.cacheStrategy === "explicit_cache"
        ? [
            "cache_obj = client.caches.create(",
            "    model=model,",
            "    config={",
            "        'contents': [{'role': 'user', 'parts': [{'text': shared_prefix or 'benchmark context'}]}],",
            "        'ttl': '3600s',",
            "    },",
            ")",
            "config['cached_content'] = cache_obj.name",
          ].join("\n")
        : "# explicit cache disabled";
      const streamBlock = variation.streaming
        ? "stream = client.models.generate_content_stream(\n    model=model,\n    contents=[{'role': 'user', 'parts': [{'text': prompt}]}],\n    config=config,\n)\nfor chunk in stream:\n    print(getattr(chunk, 'text', '') or '', end='')\nprint()"
        : "response = client.models.generate_content(\n    model=model,\n    contents=[{'role': 'user', 'parts': [{'text': prompt}]}],\n    config=config,\n)\nprint(response.text)";
      return [
        "from google import genai",
        "",
        "api_key = 'YOUR_GEMINI_API_KEY'",
        `model = '${pythonSafeString(model)}'`,
        `prompt_template = '${pythonSafeString(variant.template)}'`,
        "prompt_variables = {",
        variableEntries || "    # add prompt variables",
        "}",
        "",
        renderedPromptExpr,
        promptPreparation,
        "",
        "client = genai.Client(api_key=api_key)",
        "config = {",
        `    'max_output_tokens': 128,`,
        `    'temperature': 0.2,`,
        `    'thinking_config': {'thinking_budget': ${thinkingBudget}}`,
        "}",
        explicitCacheBlock,
        "",
        streamBlock,
        "",
      ].join("\n");
    }

    if (stack === "openai_compat") {
      const streamFlag = variation.streaming ? "True" : "False";
      const unsupportedHints = [
        variation.cacheStrategy === "explicit_cache"
          ? "# NOTE: explicit cache selection is not supported on openai_compat endpoint."
          : "# explicit cache not selected",
        variation.thinking
          ? "# NOTE: thinking toggle is not supported on openai_compat endpoint."
          : "# thinking disabled",
        variation.cacheStrategy === "implicit_reuse"
          ? "shared_prefix = prompt_variables.get('data_context', '')\nif shared_prefix:\n    prompt = (shared_prefix + '\\n' + prompt).strip()"
          : "# implicit cache-style prompt reuse disabled",
      ].join("\n");
      const streamBlock = variation.streaming
        ? "stream = client.chat.completions.create(\n    model=model,\n    messages=messages,\n    stream=True,\n    max_tokens=128,\n    temperature=0.2,\n)\nfor chunk in stream:\n    text = chunk.choices[0].delta.content or ''\n    print(text, end='')\nprint()"
        : "response = client.chat.completions.create(\n    model=model,\n    messages=messages,\n    stream=False,\n    max_tokens=128,\n    temperature=0.2,\n)\nprint(response.choices[0].message.content)";
      return [
        "from openai import OpenAI",
        "",
        "api_key = 'YOUR_GEMINI_API_KEY'",
        "base_url = 'https://generativelanguage.googleapis.com/v1beta/openai/'",
        `model = '${pythonSafeString(model)}'`,
        `prompt_template = '${pythonSafeString(variant.template)}'`,
        "prompt_variables = {",
        variableEntries || "    # add prompt variables",
        "}",
        "",
        renderedPromptExpr,
        unsupportedHints,
        "",
        "client = OpenAI(api_key=api_key, base_url=base_url)",
        "messages = [{'role': 'user', 'content': prompt}]",
        `# streaming=${streamFlag}`,
        streamBlock,
        "",
      ].join("\n");
    }

    const vertexTokenBlock = vertexAccessToken.trim()
      ? `access_token = '${pythonSafeString(vertexAccessToken.trim())}'`
      : [
          "from google.auth import default",
          "from google.auth.transport.requests import Request",
          "credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])",
          "credentials.refresh(Request())",
          "access_token = credentials.token",
        ].join("\n");
    const vertexStreamBlockByVariation = variation.streaming
      ? "stream = client.chat.completions.create(\n    model=model,\n    messages=messages,\n    stream=True,\n    max_tokens=128,\n    temperature=0.2,\n)\nfor chunk in stream:\n    text = chunk.choices[0].delta.content or ''\n    print(text, end='')\nprint()"
      : "response = client.chat.completions.create(\n    model=model,\n    messages=messages,\n    stream=False,\n    max_tokens=128,\n    temperature=0.2,\n)\nprint(response.choices[0].message.content)";
    const vertexHints = [
      variation.cacheStrategy === "explicit_cache"
        ? "# NOTE: explicit cache control is not exposed via Vertex OpenAI endpoint path."
        : "# explicit cache not selected",
      variation.thinking
        ? "# NOTE: thinking toggle is not directly available on this endpoint format."
        : "# thinking disabled",
      variation.cacheStrategy === "implicit_reuse"
        ? "shared_prefix = prompt_variables.get('data_context', '')\nif shared_prefix:\n    prompt = (shared_prefix + '\\n' + prompt).strip()"
        : "# implicit cache-style prompt reuse disabled",
    ].join("\n");
    return [
      "from openai import OpenAI",
      "",
      `project_id = '${pythonSafeString(vertexProjectId || "YOUR_PROJECT_ID")}'`,
      `location = '${pythonSafeString(vertexLocation || "us-central1")}'`,
      `endpoint_id = '${pythonSafeString(vertexEndpointId || "openapi")}'`,
      "base_url = f'https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/endpoints/{endpoint_id}'",
      "",
      vertexTokenBlock,
      "",
      `model = '${pythonSafeString(model)}'`,
      `prompt_template = '${pythonSafeString(variant.template)}'`,
      "prompt_variables = {",
      variableEntries || "    # add prompt variables",
      "}",
      "",
      renderedPromptExpr,
      vertexHints,
      "",
      "client = OpenAI(api_key=access_token, base_url=base_url)",
      "messages = [{'role': 'user', 'content': prompt}]",
      vertexStreamBlockByVariation,
      "",
    ].join("\n");
  }

  async function copyVariantCode(variant: PromptOptimizationVariant, variation: CodeVariation) {
    const key = `${variant.variant_id}:${variation.id}`;
    try {
      await navigator.clipboard.writeText(buildVariantPythonCode(variant, variation));
      setCopiedVariantId(key);
      setTimeout(() => setCopiedVariantId(null), 1400);
    } catch {
      setError("Failed to copy code to clipboard.");
    }
  }

  async function copyCurrentTemplateCode() {
    const variations = buildCodeVariations();
    const selectedVariation = variations[0];
    if (!selectedVariation) {
      return;
    }
    const currentVariant: PromptOptimizationVariant = {
      variant_id: "current_template",
      template: promptTemplate,
      rendered_prompt: promptPreview || promptTemplate,
      quality_proxy_score: 0,
      reasoning: "Current template preview",
    };
    try {
      await navigator.clipboard.writeText(buildVariantPythonCode(currentVariant, selectedVariation));
      setCopiedVariantId(`current_template:${selectedVariation.id}`);
      setTimeout(() => setCopiedVariantId(null), 1400);
    } catch {
      setError("Failed to copy code to clipboard.");
    }
  }

  function validateRunInputs(): string | null {
    if (stack === "vertex_api") {
      if (!vertexProjectId.trim() || !vertexLocation.trim() || !vertexEndpointId.trim()) {
        return "Vertex Project ID, Location, and Endpoint ID are required for vertex_api.";
      }
      return null;
    }
    if (!apiKey.trim()) {
      return "API key is required to run benchmarks.";
    }
    return null;
  }

  function buildBenchmarkPayload(templateOverride?: string): BenchmarkRequest {
    return {
      api_key: apiKey.trim() || undefined,
      stacks: [stack],
      models: [model],
      trials,
      warmup_trials: warmupTrials,
      max_output_tokens: 128,
      temperature: 0.2,
      timeout_s: 90,
      mode_selection: modeSelection,
      prompt_template: templateOverride ?? promptTemplate,
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
  }

  async function handleOptimizeAndBenchmark() {
    setError(null);
    setResult(null);
    const validationError = validateRunInputs();
    if (validationError) {
      setError(validationError);
      return;
    }
    setIsOptimizingAndBenchmarking(true);
    try {
      const combined = await optimizeAndBenchmark({
        benchmark: buildBenchmarkPayload(),
        optimization: {
          template: promptTemplate,
          variables: variableMap,
          objective: optimizationObjective,
          variant_count: optimizationVariantCount,
          locked_phrases: lockedPhrases
            .split(",")
            .map((item) => item.trim())
            .filter((item) => item.length > 0),
        },
        use_winner_template: true,
      });
      setOptimizationResult(combined.optimization);
      setPromptTemplate(combined.optimization.winner_template);
      setResult(combined.benchmark);
      await refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Optimize + benchmark failed");
    } finally {
      setIsOptimizingAndBenchmarking(false);
    }
  }

  async function onRunBenchmark() {
    setError(null);
    setResult(null);
    const validationError = validateRunInputs();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsRunning(true);
    try {
      const response = await runBenchmark(buildBenchmarkPayload());
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
          <label className="inline-toggle">
            <input
              type="checkbox"
              checked={showTokenCount}
              onChange={(event) => setShowTokenCount(event.target.checked)}
            />
            Show token count
          </label>
          {showTokenCount && (
            <button type="button" onClick={() => void handleExactTokenCount()} disabled={isCountingTokens}>
              {isCountingTokens ? "Counting..." : "Get Exact Token Count"}
            </button>
          )}
          <label className="file-upload">
            Upload Data File
            <input type="file" onChange={(event) => void handleFileUpload(event)} />
          </label>
          {isUploading && <span className="muted">Uploading...</span>}
        </div>
        {showTokenCount && (
          <div>
            <p className="muted">
              Exact tokens for selected prompt: {exactTokenCount ?? "not computed yet"}
            </p>
            {tokenCountNote && <p className="muted">{tokenCountNote}</p>}
          </div>
        )}
        {promptPreview && (
          <div className="preview">
            <h3>Rendered Prompt</h3>
            <p>{promptPreview}</p>
          </div>
        )}
        {previewMissing.length > 0 && (
          <p className="warn">Missing variables: {previewMissing.join(", ")}</p>
        )}

        <div className="optimize-box">
          <h3>Prompt Optimization Agent</h3>
          <div className="grid">
            <label>
              Objective
              <select
                value={optimizationObjective}
                onChange={(event) =>
                  setOptimizationObjective(
                    event.target.value as "lowest_latency" | "highest_quality" | "balanced"
                  )
                }
              >
                <option value="balanced">balanced</option>
                <option value="lowest_latency">lowest_latency</option>
                <option value="highest_quality">highest_quality</option>
              </select>
            </label>
            <label>
              Variant Count
              <input
                type="number"
                min={2}
                max={8}
                value={optimizationVariantCount}
                onChange={(event) => setOptimizationVariantCount(Number(event.target.value))}
              />
            </label>
            <label>
              Locked Phrases (comma-separated)
              <input
                value={lockedPhrases}
                onChange={(event) => setLockedPhrases(event.target.value)}
                placeholder="domain term, SLA, compliance"
              />
            </label>
          </div>
          <div className="actions">
            <button type="button" onClick={() => void handleOptimizePrompt()} disabled={isOptimizing}>
              {isOptimizing ? "Optimizing..." : "Optimize Prompt"}
            </button>
            <button
              type="button"
              onClick={() => void handleOptimizeAndBenchmark()}
              disabled={isOptimizingAndBenchmarking || isRunning}
            >
              {isOptimizingAndBenchmarking ? "Optimizing + Benchmarking..." : "Optimize + Benchmark"}
            </button>
            <button type="button" onClick={applyWinnerTemplate} disabled={!optimizationResult}>
              Use Winning Template
            </button>
            <label className="inline-toggle">
              <input
                type="checkbox"
                checked={showVariantCode}
                onChange={(event) => setShowVariantCode(event.target.checked)}
              />
              Show project-ready Python code
            </label>
          </div>
          {optimizationResult && (
            <>
              <p>
                <strong>Winner:</strong> {optimizationResult.winner_variant_id}
              </p>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Variant</th>
                      <th>Quality Proxy</th>
                      <th>Reasoning</th>
                    </tr>
                  </thead>
                  <tbody>
                    {optimizationResult.variants.map((variant) => (
                      <Fragment key={variant.variant_id}>
                        <tr key={variant.variant_id}>
                          <td>{variant.variant_id}</td>
                          <td>{variant.quality_proxy_score.toFixed(2)}</td>
                          <td>{variant.reasoning}</td>
                        </tr>
                        {showVariantCode && (
                          <tr key={`${variant.variant_id}-code`}>
                            <td colSpan={3}>
                              <div className="variant-code-head">
                                <strong>Python snippet for your project ({variant.variant_id})</strong>
                              </div>
                              {buildCodeVariations().map((variation) => (
                                <div key={`${variant.variant_id}:${variation.id}`} className="code-option">
                                  <div className="variant-code-head">
                                    <span className="muted">{variation.label}</span>
                                    <button type="button" onClick={() => void copyVariantCode(variant, variation)}>
                                      {copiedVariantId === `${variant.variant_id}:${variation.id}`
                                        ? "Copied"
                                        : "Copy Code"}
                                    </button>
                                  </div>
                                  <pre className="code-block">{buildVariantPythonCode(variant, variation)}</pre>
                                </div>
                              ))}
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          {showVariantCode && !optimizationResult && (
            <div className="preview">
              <div className="variant-code-head">
                <strong>Python snippet for your project (current template)</strong>
                <button type="button" onClick={() => void copyCurrentTemplateCode()}>
                  {copiedVariantId?.startsWith("current_template:") ? "Copied" : "Copy First Code Option"}
                </button>
              </div>
              <p className="muted">
                Run Optimize Prompt to see per-variant snippets. This block is generated from your current template.
              </p>
              {buildCodeVariations().map((variation) => (
                <div key={`current_template:${variation.id}`} className="code-option">
                  <div className="variant-code-head">
                    <span className="muted">{variation.label}</span>
                  </div>
                  <pre
                    className="code-block"
                  >{buildVariantPythonCode(
                    {
                      variant_id: "current_template",
                      template: promptTemplate,
                      rendered_prompt: promptPreview || promptTemplate,
                      quality_proxy_score: 0,
                      reasoning: "Current template preview",
                    },
                    variation
                  )}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
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

