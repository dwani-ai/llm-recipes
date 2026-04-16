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
type SampleUseCase = {
  id: string;
  title: string;
  promptTemplate: string;
  variables: Record<string, string>;
  recommended: {
    stack: "google_genai" | "openai_compat" | "vertex_api";
    model: string;
    modeSelection: ModeSelection;
  };
};

const SAMPLE_USE_CASES: SampleUseCase[] = [
  {
    id: "support_streaming_none",
    title: "Support Ops - Streaming + No Cache",
    promptTemplate: "Analyze {{dataset_name}} and provide a concise action plan for {{goal}} in 4 bullets.",
    variables: {
      dataset_name: "customer_support_tickets_q2",
      goal: "reduce repeat escalation rate",
      data_context: `Ticket sample (Q2):
ticket_id,channel,region,product,issue_category,priority,sentiment,first_response_min,resolution_hours,escalated,reopen_count,agent_tier
T-1001,email,US,CoreApp,Billing,high,-0.62,47,31.2,yes,2,tier_1
T-1002,chat,IN,MobileSDK,Login,medium,-0.18,4,2.8,no,0,tier_1
T-1003,email,UK,CoreApp,Performance,high,-0.74,39,28.5,yes,1,tier_2
T-1004,web,DE,AdminConsole,Permissions,medium,-0.22,13,7.1,no,0,tier_2
T-1005,chat,US,CoreApp,DataSync,high,-0.68,6,19.4,yes,1,tier_2
T-1006,email,AU,MobileSDK,Crash,critical,-0.83,52,41.0,yes,3,tier_3
Notes:
- Reopened escalations are concentrated in Billing + Crash.
- Tier_1 handoffs to Tier_2 add average 5.3h cycle delay.
- Customers with sentiment below -0.60 have 2.4x escalation probability.`,
    },
    recommended: {
      stack: "google_genai",
      model: "gemini-2.5-flash",
      modeSelection: { streaming: true, thinking: false, implicit_cache: false, explicit_cache: false },
    },
  },
  {
    id: "fraud_streaming_thinking",
    title: "Fraud Analysis - Streaming + Thinking",
    promptTemplate:
      "For {{dataset_name}}, reason step-by-step and propose a prioritized strategy for {{goal}} with assumptions and risks.",
    variables: {
      dataset_name: "fraud_detection_alerts_weekly",
      goal: "cut false positives while preserving recall",
      data_context: `Fraud alerts (weekly extract):
alert_id,merchant_segment,txn_amount_usd,geo_velocity_flag,device_mismatch,score_band,manual_review,outcome,chargeback_within_30d
F-901,marketplace,1240,true,true,0.92,approve,legit,false
F-902,subscription,89,false,false,0.44,approve,legit,false
F-903,digital_goods,410,true,false,0.77,decline,fraud,true
F-904,travel,2200,true,true,0.95,decline,fraud,true
F-905,retail,130,false,true,0.63,approve,legit,false
F-906,subscription,310,false,false,0.52,approve,legit,false
F-907,digital_goods,980,true,true,0.88,decline,fraud,true
F-908,retail,75,false,false,0.29,approve,legit,false
Policy notes:
- Current threshold 0.60 triggers manual review.
- False positives are highest in retail low-ticket transactions.
- Geo velocity + device mismatch together predict confirmed fraud strongly.`,
    },
    recommended: {
      stack: "google_genai",
      model: "gemini-2.5-flash",
      modeSelection: { streaming: true, thinking: true, implicit_cache: false, explicit_cache: false },
    },
  },
  {
    id: "incident_streaming_implicit",
    title: "Platform Incidents - Streaming + Implicit Cache",
    promptTemplate: "Using the context for {{dataset_name}}, provide the top 5 operational fixes for {{goal}}.",
    variables: {
      dataset_name: "incident_postmortems_platform_ops",
      goal: "reduce mean time to recovery",
      data_context: `Incident postmortems:
[INC-221] API timeout storm
- Start: 2026-02-03 09:12 UTC
- Blast radius: 34% of /search requests
- Root cause: cache node eviction + connection pool exhaustion
- Detection lag: 11m
- MTTR: 74m
- Action items: warm pool on deploy, add p95 saturation alerts

[INC-227] Auth token validation backlog
- Start: 2026-02-21 18:42 UTC
- Blast radius: login failures in eu-west
- Root cause: regional Kafka lag + retry amplification
- Detection lag: 7m
- MTTR: 49m
- Action items: bounded retries, consumer lag SLOs

[INC-233] Feature flag rollout regression
- Start: 2026-03-10 02:10 UTC
- Blast radius: admin console 500s
- Root cause: schema mismatch in canary path
- Detection lag: 15m
- MTTR: 96m
- Action items: pre-rollout schema contract checks, rollback guardrails`,
    },
    recommended: {
      stack: "google_genai",
      model: "gemini-2.5-flash",
      modeSelection: { streaming: true, thinking: false, implicit_cache: true, explicit_cache: false },
    },
  },
  {
    id: "docs_streaming_explicit",
    title: "Documentation QA - Streaming + Explicit Cache",
    promptTemplate:
      "From {{dataset_name}}, return concise recommendations for {{goal}} with one metric per recommendation.",
    variables: {
      dataset_name: "product_docs_and_runbooks",
      goal: "improve support deflection rate",
      data_context:
        `Docs corpus excerpt:
[Onboarding Guide v4]
1. Create tenant and assign org admin.
2. Configure SSO (SAML/OIDC), then enforce MFA.
3. Install agent package on at least 3 representative hosts.
4. Validate ingestion in Data Health dashboard.

[Troubleshooting Runbook: Data Sync Lag]
- Symptom: dashboard freshness > 15 min
- Checks:
  a) verify connector heartbeat
  b) inspect ingestion queue depth
  c) confirm API quota utilization below 85%
- Mitigations:
  a) trigger incremental resync
  b) scale ingest workers +1
  c) rotate connector token if auth retries > 20

[Release Notes 2026.3]
- New: adaptive backoff for connector retries
- Changed: default retention from 30d to 45d
- Known issue: legacy OAuth scopes may fail on older connectors

[FAQ snippets]
Q: Why is report generation delayed?
A: Usually quota throttling or failed incremental checkpoints.`,
    },
    recommended: {
      stack: "google_genai",
      model: "gemini-2.5-flash",
      modeSelection: { streaming: true, thinking: false, implicit_cache: false, explicit_cache: true },
    },
  },
  {
    id: "marketing_batch_none",
    title: "Marketing Weekly - Non-Streaming + No Cache",
    promptTemplate: "Summarize {{dataset_name}} and produce a compact action checklist for {{goal}}.",
    variables: {
      dataset_name: "weekly_marketing_performance",
      goal: "improve paid channel efficiency",
      data_context: `Campaign weekly metrics:
week,channel,region,spend_usd,impressions,clicks,ctr,landing_cv_rate,mql_rate,pipeline_usd,cac_usd
2026-W10,search,US,92000,2.1M,104000,4.95,0.082,0.214,1.32M,780
2026-W10,social,US,61000,4.8M,72000,1.50,0.029,0.132,0.41M,1120
2026-W10,display,EU,38000,6.2M,41000,0.66,0.018,0.089,0.19M,1490
2026-W11,search,US,97000,2.3M,110000,4.78,0.079,0.201,1.28M,810
2026-W11,social,EU,54000,4.2M,68000,1.62,0.031,0.126,0.36M,1195
2026-W11,partners,APAC,29000,0.9M,21000,2.33,0.067,0.241,0.52M,640
Notes:
- Search drives largest pipeline but CAC drifted +4%.
- Social has high impression volume with weak downstream conversion.
- Partner channel in APAC is efficient but limited scale.`,
    },
    recommended: {
      stack: "openai_compat",
      model: "gemini-2.5-flash",
      modeSelection: { streaming: false, thinking: false, implicit_cache: false, explicit_cache: false },
    },
  },
  {
    id: "finance_batch_thinking",
    title: "Finance Close - Non-Streaming + Thinking",
    promptTemplate:
      "For {{dataset_name}}, provide a reasoned diagnosis and remediation plan for {{goal}}, including assumptions.",
    variables: {
      dataset_name: "finance_close_cycle_exceptions",
      goal: "reduce month-end reconciliation delays",
      data_context: `Close-cycle exception log:
exception_id,ledger_domain,amount_usd,owner_team,age_days,root_cause,status
E-3001,revenue_recognition,182000,revops,6,contract_term_mismatch,open
E-3002,intercompany,74000,corp_finance,4,fx_rate_timing,resolved
E-3003,accruals,129000,fp&a,9,missing_approver,open
E-3004,ap_clearing,51000,shared_services,3,duplicate_invoice,resolved
E-3005,revenue_recognition,221000,revops,11,manual_override_without_audit,open
E-3006,bank_recon,39000,treasury,8,statement_import_delay,open
E-3007,intercompany,87000,corp_finance,10,counterparty_mapping_gap,open
Control observations:
- 63% of exceptions over 7 days involve revops + corp_finance handoffs.
- Missing approvals and manual overrides are the largest recurring contributors.
- SLA breach threshold is 8 days; current median is 8.6 days.`,
    },
    recommended: {
      stack: "google_genai",
      model: "gemini-2.5-pro",
      modeSelection: { streaming: false, thinking: true, implicit_cache: false, explicit_cache: false },
    },
  },
  {
    id: "kb_batch_implicit",
    title: "Knowledge Base Audit - Non-Streaming + Implicit Cache",
    promptTemplate: "Using {{dataset_name}}, generate a deterministic summary and recommendations for {{goal}}.",
    variables: {
      dataset_name: "knowledge_base_quality_audit",
      goal: "identify stale articles and ownership gaps",
      data_context: `KB quality audit snapshot:
article_id,topic,last_updated_days,broken_links,helpful_ratio,negative_feedback_count,owner_team,owner_assigned
KB-11,SSO setup,410,3,0.61,42,identity,false
KB-18,Billing exports,96,0,0.84,6,finance_tools,true
KB-24,Agent install Linux,290,2,0.69,27,platform,true
KB-31,Data retention policy,505,1,0.58,33,security,false
KB-37,API pagination,77,0,0.88,4,developer_experience,true
KB-44,Webhook retries,340,4,0.55,51,integrations,false
KB-52,Role permissions matrix,220,1,0.66,19,admin_console,true
Findings:
- Articles older than 300 days account for most negative feedback.
- Ownership missing on critical policy and integration docs.
- Broken links cluster around migration guides after 2026.1 release.`,
    },
    recommended: {
      stack: "vertex_api",
      model: "gemini-2.5-flash",
      modeSelection: { streaming: false, thinking: false, implicit_cache: true, explicit_cache: false },
    },
  },
  {
    id: "security_batch_explicit",
    title: "Security Compliance - Non-Streaming + Explicit Cache",
    promptTemplate:
      "Use {{dataset_name}} to produce a detailed compliance readiness assessment for {{goal}} with phased remediation.",
    variables: {
      dataset_name: "security_control_evidence_repository",
      goal: "prepare SOC2 gap-closure plan",
      data_context: `Security evidence bundle:
[Control CC6.1 - Access Reviews]
- Current cadence: quarterly
- Last completed: 2026-01-10
- Exceptions: 17 stale privileged accounts, 6 unresolved manager attestations

[Control CC7.2 - Incident Response]
- Runbook exists; tabletop completed 2025-11
- Gap: no documented post-incident retrospective SLA
- Evidence missing for two severity-2 incidents

[Control A1.2 - Change Management]
- CI/CD approvals enforced for production branches
- Gap: emergency change pathway bypass logs not centrally archived

[Auditor Notes]
- Need stronger linkage between policy exceptions and compensating controls.
- Vendor risk reviews are inconsistent across critical sub-processors.
- Monitoring dashboards present, but retention for alert evidence only 30 days.

[Ownership map]
- Identity: security_platform
- Infra logging: sre_core
- Vendor risk: compliance_ops
- Evidence collection automation: security_eng`,
    },
    recommended: {
      stack: "google_genai",
      model: "gemini-2.5-pro",
      modeSelection: { streaming: false, thinking: true, implicit_cache: false, explicit_cache: true },
    },
  },
];

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
  const [selectedUseCaseId, setSelectedUseCaseId] = useState("");
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

  function applySampleUseCase() {
    const sample = SAMPLE_USE_CASES.find((item) => item.id === selectedUseCaseId);
    if (!sample) {
      return;
    }
    setPromptTemplate(sample.promptTemplate);
    setPromptVars(Object.entries(sample.variables).map(([key, value]) => ({ key, value })));
    setStack(sample.recommended.stack);
    setModel(sample.recommended.model);
    setModeSelection(sample.recommended.modeSelection);
    setPromptPreview("");
    setPreviewMissing([]);
    setExactTokenCount(null);
    setTokenCountNote(null);
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
        <div className="actions">
          <label>
            Use Case Examples
            <select value={selectedUseCaseId} onChange={(event) => setSelectedUseCaseId(event.target.value)}>
              <option value="">Select sample prompt + data</option>
              {SAMPLE_USE_CASES.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={applySampleUseCase} disabled={!selectedUseCaseId}>
            Apply Example
          </button>
        </div>
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

