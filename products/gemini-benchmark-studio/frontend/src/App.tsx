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
  PromptTokenBreakdownItem,
  PromptOptimizationVariant,
  PromptOptimizationResponse,
  RunHistoryItem,
} from "./types";

type PromptVarRow = { key: string; value: string };
type CacheStrategy = "none" | "implicit_reuse" | "explicit_cache";
type CacheIntent = "none" | "implicit_reuse" | "explicit_cache";
type BenchmarkObjective = "lowest_latency" | "balanced" | "reliability_first";
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

function modeFromCacheIntent(cacheIntent: CacheIntent, base: ModeSelection): ModeSelection {
  return {
    ...base,
    implicit_cache: cacheIntent === "implicit_reuse",
    explicit_cache: cacheIntent === "explicit_cache",
  };
}

function cacheIntentFromMode(mode: ModeSelection): CacheIntent {
  if (mode.explicit_cache) {
    return "explicit_cache";
  }
  if (mode.implicit_cache) {
    return "implicit_reuse";
  }
  return "none";
}

function toDateTimeLocalString(input: Date): string {
  const year = input.getFullYear();
  const month = String(input.getMonth() + 1).padStart(2, "0");
  const day = String(input.getDate()).padStart(2, "0");
  const hours = String(input.getHours()).padStart(2, "0");
  const minutes = String(input.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
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
  const [thinkingTokenBudget, setThinkingTokenBudget] = useState(1024);
  const [cacheIntent, setCacheIntent] = useState<CacheIntent>(cacheIntentFromMode(DEFAULT_MODE_SELECTION));
  const [benchmarkObjective, setBenchmarkObjective] = useState<BenchmarkObjective>("lowest_latency");
  const [scheduleEnabled, setScheduleEnabled] = useState(false);
  const [scheduleStartLocal, setScheduleStartLocal] = useState(
    toDateTimeLocalString(new Date(Date.now() + 5 * 60 * 1000))
  );
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
  const [tokenBreakdown, setTokenBreakdown] = useState<PromptTokenBreakdownItem[]>([]);
  const [tokenSavingsCalls, setTokenSavingsCalls] = useState(10);
  const [tokenCountNote, setTokenCountNote] = useState<string | null>(null);
  const [result, setResult] = useState<BenchmarkResponse | null>(null);
  const [optimizationResult, setOptimizationResult] = useState<PromptOptimizationResponse | null>(null);
  const [history, setHistory] = useState<RunHistoryItem[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [isOptimizingAndBenchmarking, setIsOptimizingAndBenchmarking] = useState(false);
  const [lastOptimizeBenchmarkTemplateBefore, setLastOptimizeBenchmarkTemplateBefore] = useState<string | null>(null);
  const [lastOptimizeBenchmarkTemplateAfter, setLastOptimizeBenchmarkTemplateAfter] = useState<string | null>(null);
  const [showVariantCode, setShowVariantCode] = useState(false);
  const [copiedVariantId, setCopiedVariantId] = useState<string | null>(null);
  const [highlightedScenarioId, setHighlightedScenarioId] = useState<string | null>(null);
  const [historyCompareA, setHistoryCompareA] = useState("");
  const [historyCompareB, setHistoryCompareB] = useState("");
  const [error, setError] = useState<string | null>(null);
  const stackCapabilities = useMemo(() => {
    if (stack === "google_genai") {
      return { thinking: true, explicitCache: true, note: null as string | null };
    }
    if (stack === "openai_compat") {
      return {
        thinking: false,
        explicitCache: false,
        note: "openai_compat does not expose explicit cache or thinking controls in this benchmark path.",
      };
    }
    return {
      thinking: false,
      explicitCache: false,
      note: "vertex_api OpenAI endpoint path has limited thinking/explicit cache controls.",
    };
  }, [stack]);

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
        setThinkingTokenBudget(data.defaults.thinking_token_budget ?? 1024);
        setCacheIntent(
          cacheIntentFromMode({
            streaming: data.defaults.streaming,
            thinking: data.defaults.thinking,
            implicit_cache: data.defaults.implicit_cache,
            explicit_cache: data.defaults.explicit_cache,
          })
        );
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

  useEffect(() => {
    setModeSelection((prev) => {
      let next = { ...prev };
      let changed = false;
      if (!stackCapabilities.thinking && next.thinking) {
        next = { ...next, thinking: false };
        changed = true;
      }
      if (!stackCapabilities.explicitCache && next.explicit_cache) {
        next = { ...next, explicit_cache: false };
        changed = true;
      }
      if (!changed) {
        return prev;
      }
      setCacheIntent(cacheIntentFromMode(next));
      return next;
    });
  }, [stackCapabilities]);

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
    setModeSelection((prev) => {
      const next = { ...prev, [field]: value };
      if (field === "implicit_cache" || field === "explicit_cache") {
        setCacheIntent(cacheIntentFromMode(next));
      }
      return next;
    });
  }

  function updateCacheIntent(nextIntent: CacheIntent) {
    setCacheIntent(nextIntent);
    setModeSelection((prev) => modeFromCacheIntent(nextIntent, prev));
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
    setCacheIntent(cacheIntentFromMode(sample.recommended.modeSelection));
    setThinkingTokenBudget(1024);
    setPromptPreview("");
    setPreviewMissing([]);
    setExactTokenCount(null);
    setTokenBreakdown([]);
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
        mode_selection: modeFromCacheIntent(cacheIntent, modeSelection),
        include_long_context: true,
        calls_for_savings: tokenSavingsCalls,
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
      setTokenBreakdown(response.breakdown);
      setTokenSavingsCalls(response.calls_for_savings);
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
    const cacheStrategies: CacheStrategy[] =
      cacheIntent === "none" ? ["none"] : [cacheIntent];
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
      const thinkingBudget = variation.thinking ? String(thinkingTokenBudget) : "0";
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
    if (variations.length === 0) {
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
      const bundled = variations
        .map(
          (variation) =>
            `# ${variation.label}\n\n${buildVariantPythonCode(currentVariant, variation)}`
        )
        .join("\n\n# ----\n\n");
      await navigator.clipboard.writeText(bundled);
      setCopiedVariantId(`current_template:${variations[0].id}`);
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
    if (!stackCapabilities.thinking && modeSelection.thinking) {
      return `${stack} does not support the thinking toggle in this benchmark path. Disable thinking or switch stack.`;
    }
    if (!stackCapabilities.explicitCache && modeSelection.explicit_cache) {
      return `${stack} does not support explicit cache in this benchmark path. Use implicit reuse or switch stack.`;
    }
    if (modeSelection.thinking && thinkingTokenBudget <= 0) {
      return "Thinking token budget must be greater than 0 when thinking is enabled.";
    }
    if (!apiKey.trim()) {
      return "API key is required to run benchmarks.";
    }
    if (scheduleEnabled && !scheduleStartLocal.trim()) {
      return "Select a schedule start time for the 15-minute window.";
    }
    return null;
  }

  function buildBenchmarkPayload(templateOverride?: string): BenchmarkRequest {
    const scheduleStartIso =
      scheduleEnabled && scheduleStartLocal
        ? new Date(scheduleStartLocal).toISOString()
        : undefined;
    return {
      api_key: apiKey.trim() || undefined,
      stacks: [stack],
      models: [model],
      trials,
      warmup_trials: warmupTrials,
      max_output_tokens: 128,
      temperature: 0.2,
      timeout_s: 90,
      mode_selection: modeFromCacheIntent(cacheIntent, modeSelection),
      thinking_token_budget: thinkingTokenBudget,
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
      recommendation_objective: benchmarkObjective,
      schedule_enabled: scheduleEnabled,
      schedule_start_at: scheduleStartIso,
      schedule_window_minutes: 15,
    };
  }

  function applyRecommendedSettings() {
    if (!result?.recommendation.best_scenario_id) {
      return;
    }
    const bestSummary = result.summaries.find(
      (row) => row.scenario_id === result.recommendation.best_scenario_id
    );
    if (!bestSummary) {
      setError("Could not map best scenario to summary row.");
      return;
    }
    setStack(bestSummary.stack);
    setModel(bestSummary.model);
    const nextMode: ModeSelection = {
      streaming: bestSummary.mode === "streaming",
      thinking: bestSummary.thinking,
      implicit_cache: bestSummary.cache_strategy === "implicit_reuse",
      explicit_cache: bestSummary.cache_strategy === "explicit_cache",
    };
    setModeSelection(nextMode);
    setThinkingTokenBudget(bestSummary.thinking_token_budget ?? 1024);
    setCacheIntent(cacheIntentFromMode(nextMode));
    setHighlightedScenarioId(bestSummary.scenario_id);
  }

  function scenarioStatus(row: BenchmarkResponse["summaries"][number]): string {
    if (row.ok_count <= 0) {
      return "disqualified";
    }
    if (row.error_count > 0) {
      return "unstable";
    }
    if (row.unsupported_count > 0) {
      return "partial";
    }
    return "eligible";
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
      const beforeTemplate = promptTemplate;
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
      setLastOptimizeBenchmarkTemplateBefore(beforeTemplate);
      setLastOptimizeBenchmarkTemplateAfter(combined.optimization.winner_template);
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

  const bestRankedScenario = result?.recommendation.ranked_scenarios?.[0] ?? null;
  const runnerUpScenario = result?.recommendation.ranked_scenarios?.[1] ?? null;
  const historyA = history.find((item) => item.run_id === historyCompareA);
  const historyB = history.find((item) => item.run_id === historyCompareB);

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
          <label>
            Recommendation Objective
            <select
              value={benchmarkObjective}
              onChange={(event) => setBenchmarkObjective(event.target.value as BenchmarkObjective)}
            >
              <option value="lowest_latency">lowest_latency</option>
              <option value="balanced">balanced</option>
              <option value="reliability_first">reliability_first</option>
            </select>
          </label>
          <label className="inline-toggle">
            <input
              type="checkbox"
              checked={scheduleEnabled}
              onChange={(event) => setScheduleEnabled(event.target.checked)}
            />
            Schedule across 15-minute window
          </label>
          {scheduleEnabled && (
            <label>
              Window Start Time
              <input
                type="datetime-local"
                value={scheduleStartLocal}
                onChange={(event) => setScheduleStartLocal(event.target.value)}
              />
            </label>
          )}
        </div>
        {scheduleEnabled && (
          <p className="muted">
            Trials are spread across a fixed 15-minute window so you can observe latency behavior at the
            selected time.
          </p>
        )}
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
        <h2>Mode Selection</h2>
        {stackCapabilities.note && <p className="warn">{stackCapabilities.note}</p>}
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
              disabled={!stackCapabilities.thinking}
              onChange={(event) => updateMode("thinking", event.target.checked)}
            />
            Thinking
          </label>
          <label>
            Thinking Token Budget
            <input
              type="number"
              min={0}
              max={8192}
              value={thinkingTokenBudget}
              disabled={!modeSelection.thinking}
              onChange={(event) => setThinkingTokenBudget(Math.max(0, Number(event.target.value) || 0))}
            />
          </label>
          <label>
            Cache Intent
            <select
              value={cacheIntent}
              onChange={(event) => updateCacheIntent(event.target.value as CacheIntent)}
            >
              <option value="none">none</option>
              <option value="implicit_reuse">implicit_reuse</option>
              <option value="explicit_cache" disabled={!stackCapabilities.explicitCache}>
                explicit_cache
              </option>
            </select>
          </label>
        </div>
        <p className="muted">
          Current mode: {modeSelection.streaming ? "streaming" : "non_streaming"} | thinking=
          {String(modeSelection.thinking)} | thinking_budget={thinkingTokenBudget} | cache={cacheIntent}
        </p>
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
            <label>
              Calls for savings
              <input
                type="number"
                min={1}
                max={1000}
                value={tokenSavingsCalls}
                onChange={(event) =>
                  setTokenSavingsCalls(Math.max(1, Math.min(1000, Number(event.target.value) || 1)))
                }
              />
            </label>
          )}
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
            {tokenBreakdown.length > 0 && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Prompt Type</th>
                      <th>Strategy</th>
                      <th>Baseline</th>
                      <th>Request</th>
                      <th>Cache Create</th>
                      <th>First Call</th>
                      <th>Later Calls</th>
                      <th>Savings @ {tokenSavingsCalls} calls</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tokenBreakdown.map((row) => (
                      <tr key={`${row.prompt_type}:${row.strategy}`}>
                        <td>{row.prompt_type}</td>
                        <td>{row.strategy}</td>
                        <td>{row.baseline_request_tokens}</td>
                        <td>{row.request_tokens}</td>
                        <td>{row.cache_create_tokens}</td>
                        <td>{row.first_call_total_tokens}</td>
                        <td>{row.subsequent_call_tokens}</td>
                        <td>{row.savings_vs_baseline_after_n_calls}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
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
              {optimizationResult.trace.length > 0 && (
                <>
                  <h3>Optimization Trace</h3>
                  <ul>
                    {optimizationResult.trace.map((item, idx) => (
                      <li key={`opt-trace-${idx}-${item}`}>{item}</li>
                    ))}
                  </ul>
                </>
              )}
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
          {result.artifacts.schedule_window_start && result.artifacts.schedule_window_end && (
            <p>
              <strong>Scheduled Window:</strong> {result.artifacts.schedule_window_start} to{" "}
              {result.artifacts.schedule_window_end}
            </p>
          )}
          <p>
            <strong>Best Scenario:</strong> {result.recommendation.best_scenario_id ?? "n/a"}
          </p>
          <p>
            <strong>Objective:</strong> {result.recommendation.objective} | <strong>Confidence:</strong>{" "}
            {result.recommendation.confidence} | <strong>Reliability Score:</strong>{" "}
            {result.recommendation.reliability_score.toFixed(3)}
          </p>
          <p>
            <strong>Recommendation:</strong> {result.recommendation.rationale}
          </p>
          <div className="actions">
            <button type="button" onClick={applyRecommendedSettings}>
              Apply Recommended Settings
            </button>
          </div>
          {lastOptimizeBenchmarkTemplateBefore &&
            lastOptimizeBenchmarkTemplateAfter &&
            lastOptimizeBenchmarkTemplateBefore !== lastOptimizeBenchmarkTemplateAfter && (
              <div className="preview">
                <strong>Optimize + Benchmark used an updated template.</strong>
                <p className="muted">
                  Previous: {lastOptimizeBenchmarkTemplateBefore.slice(0, 180)}
                  {lastOptimizeBenchmarkTemplateBefore.length > 180 ? "..." : ""}
                </p>
                <p className="muted">
                  Winner: {lastOptimizeBenchmarkTemplateAfter.slice(0, 180)}
                  {lastOptimizeBenchmarkTemplateAfter.length > 180 ? "..." : ""}
                </p>
              </div>
            )}

          {bestRankedScenario && (
            <div className="preview">
              <h3>Why This Won</h3>
              <p className="muted">
                Score {bestRankedScenario.score.toFixed(4)} with TTFT P50{" "}
                {bestRankedScenario.ttft_p50_s?.toFixed(3) ?? "n/a"}s and success rate{" "}
                {(bestRankedScenario.success_rate * 100).toFixed(1)}%.
              </p>
              {runnerUpScenario && (
                <p className="muted">
                  Runner-up delta: TTFT P50{" "}
                  {(
                    (runnerUpScenario.ttft_p50_s ?? 0) - (bestRankedScenario.ttft_p50_s ?? 0)
                  ).toFixed(3)}
                  s, success rate{" "}
                  {((bestRankedScenario.success_rate - runnerUpScenario.success_rate) * 100).toFixed(1)}%.
                </p>
              )}
            </div>
          )}

          {result.recommendation.ranked_scenarios.length > 0 && (
            <>
              <h3>Ranked Eligible Scenarios</h3>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Scenario</th>
                      <th>Score</th>
                      <th>TTFT P50</th>
                      <th>TTFT P95</th>
                      <th>E2E P50</th>
                      <th>Success Rate</th>
                      <th>Error Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.recommendation.ranked_scenarios.map((row) => (
                      <tr key={`ranked-${row.scenario_id}`}>
                        <td>{row.scenario_id}</td>
                        <td>{row.score.toFixed(4)}</td>
                        <td>{row.ttft_p50_s?.toFixed(3) ?? "n/a"}</td>
                        <td>{row.ttft_p95_s?.toFixed(3) ?? "n/a"}</td>
                        <td>{row.e2e_p50_s?.toFixed(3) ?? "n/a"}</td>
                        <td>{(row.success_rate * 100).toFixed(1)}%</td>
                        <td>{(row.error_rate * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {result.recommendation.disqualified_scenarios.length > 0 && (
            <>
              <h3>Disqualified Scenarios</h3>
              <ul>
                {result.recommendation.disqualified_scenarios.map((item) => (
                  <li key={`dq-${item.scenario_id}`}>
                    {item.scenario_id}: {item.reason}
                  </li>
                ))}
              </ul>
            </>
          )}

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
                  <th>Status</th>
                  <th>Stack</th>
                  <th>Model</th>
                  <th>Mode</th>
                  <th>Thinking</th>
                  <th>Thinking Budget</th>
                  <th>Cache</th>
                  <th>Prompt Type</th>
                  <th>OK</th>
                  <th>Unsupported</th>
                  <th>Errors</th>
                  <th>Samples</th>
                  <th>TTFT P50</th>
                  <th>TTFT P95</th>
                  <th>E2E P50</th>
                  <th>TPS Avg</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {result.summaries.map((row) => (
                  <tr
                    key={row.scenario_id}
                    className={
                      highlightedScenarioId === row.scenario_id
                        ? "row-highlight"
                        : `row-status-${scenarioStatus(row)}`
                    }
                  >
                    <td>{row.scenario_id}</td>
                    <td>
                      <span className={`badge badge-${scenarioStatus(row)}`}>{scenarioStatus(row)}</span>
                    </td>
                    <td>{row.stack}</td>
                    <td>{row.model}</td>
                    <td>{row.mode}</td>
                    <td>{String(row.thinking)}</td>
                    <td>{row.thinking_token_budget}</td>
                    <td>{row.cache_strategy}</td>
                    <td>{row.prompt_type}</td>
                    <td>{row.ok_count}</td>
                    <td>{row.unsupported_count}</td>
                    <td>{row.error_count}</td>
                    <td>{row.samples}</td>
                    <td>{row.ttft_p50_s?.toFixed(3) ?? "n/a"}</td>
                    <td>{row.ttft_p95_s?.toFixed(3) ?? "n/a"}</td>
                    <td>{row.e2e_p50_s?.toFixed(3) ?? "n/a"}</td>
                    <td>{row.tokens_per_s_avg?.toFixed(2) ?? "n/a"}</td>
                    <td>{row.note ?? row.ttft_definition ?? "ok"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {Object.keys(result.artifacts).length > 0 && (
            <div className="preview">
              <h3>Artifacts</h3>
              <ul>
                {Object.entries(result.artifacts).map(([key, value]) => (
                  <li key={`artifact-${key}`}>
                    <strong>{key}:</strong> {value}
                  </li>
                ))}
              </ul>
            </div>
          )}

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
          <div>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Saved At</th>
                    <th>Run ID</th>
                    <th>Best Scenario</th>
                    <th>Summaries</th>
                    <th>Request Snapshot</th>
                    <th>Artifacts</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => (
                    <tr key={`${item.saved_at}-${item.run_id}`}>
                      <td>{item.saved_at}</td>
                      <td>{item.run_id}</td>
                      <td>{item.best_scenario_id ?? "n/a"}</td>
                      <td>{item.summaries_count}</td>
                      <td>
                        <details>
                          <summary>view</summary>
                          <pre className="code-block">{JSON.stringify(item.request, null, 2)}</pre>
                        </details>
                      </td>
                      <td>
                        <details>
                          <summary>view</summary>
                          <pre className="code-block">{JSON.stringify(item.artifacts, null, 2)}</pre>
                        </details>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h3>Compare Runs</h3>
            <div className="grid">
              <label>
                Run A
                <select value={historyCompareA} onChange={(event) => setHistoryCompareA(event.target.value)}>
                  <option value="">Select run</option>
                  {history.map((item) => (
                    <option key={`a-${item.run_id}`} value={item.run_id}>
                      {item.run_id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Run B
                <select value={historyCompareB} onChange={(event) => setHistoryCompareB(event.target.value)}>
                  <option value="">Select run</option>
                  {history.map((item) => (
                    <option key={`b-${item.run_id}`} value={item.run_id}>
                      {item.run_id}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {historyA && historyB && (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>Run A</th>
                      <th>Run B</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>best_scenario_id</td>
                      <td>{historyA.best_scenario_id ?? "n/a"}</td>
                      <td>{historyB.best_scenario_id ?? "n/a"}</td>
                    </tr>
                    <tr>
                      <td>stack</td>
                      <td>{String(historyA.request.stacks ?? "n/a")}</td>
                      <td>{String(historyB.request.stacks ?? "n/a")}</td>
                    </tr>
                    <tr>
                      <td>model</td>
                      <td>{String(historyA.request.models ?? "n/a")}</td>
                      <td>{String(historyB.request.models ?? "n/a")}</td>
                    </tr>
                    <tr>
                      <td>mode_selection</td>
                      <td>{JSON.stringify(historyA.request.mode_selection ?? {})}</td>
                      <td>{JSON.stringify(historyB.request.mode_selection ?? {})}</td>
                    </tr>
                    <tr>
                      <td>recommendation_objective</td>
                      <td>{String(historyA.request.recommendation_objective ?? "lowest_latency")}</td>
                      <td>{String(historyB.request.recommendation_objective ?? "lowest_latency")}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

