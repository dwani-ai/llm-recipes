import { API_BASE_URL } from "./defaults";
import type {
  BenchmarkRequest,
  BenchmarkResponse,
  DefaultModesResponse,
  PromptOptimizeBenchmarkRequest,
  PromptOptimizeBenchmarkResponse,
  PromptTokenCountRequest,
  PromptTokenCountResponse,
  PromptOptimizationRequest,
  PromptOptimizationResponse,
  RunHistoryResponse,
} from "./types";

export async function fetchDefaultModes(): Promise<DefaultModesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/benchmark/default-modes`);
  if (!response.ok) {
    throw new Error("Failed to load default modes");
  }
  return response.json();
}

export async function previewPrompt(template: string, variables: Record<string, string>): Promise<{
  rendered_prompt: string;
  missing_variables: string[];
}> {
  const response = await fetch(`${API_BASE_URL}/api/prompt/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ template, variables }),
  });
  if (!response.ok) {
    throw new Error("Failed to preview prompt");
  }
  return response.json();
}

export async function runBenchmark(payload: BenchmarkRequest): Promise<BenchmarkResponse> {
  const response = await fetch(`${API_BASE_URL}/api/benchmark/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Benchmark run failed: ${text}`);
  }
  return response.json();
}

export async function uploadContextFile(file: File, variableKey = "data_context"): Promise<{
  variable_key: string;
  bytes_received: number;
  chars_extracted: number;
  context_text: string;
  preview: string;
}> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(
    `${API_BASE_URL}/api/prompt/upload-context?variable_key=${encodeURIComponent(variableKey)}`,
    {
      method: "POST",
      body: form,
    }
  );
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`File upload failed: ${text}`);
  }
  return response.json();
}

export async function fetchRunHistory(limit = 25): Promise<RunHistoryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/benchmark/history?limit=${limit}`);
  if (!response.ok) {
    throw new Error("Failed to load run history");
  }
  return response.json();
}

export async function optimizePrompt(
  payload: PromptOptimizationRequest
): Promise<PromptOptimizationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/prompt/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Prompt optimization failed: ${text}`);
  }
  return response.json();
}

export async function optimizeAndBenchmark(
  payload: PromptOptimizeBenchmarkRequest
): Promise<PromptOptimizeBenchmarkResponse> {
  const response = await fetch(`${API_BASE_URL}/api/prompt/optimize-and-benchmark`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Optimize + benchmark failed: ${text}`);
  }
  return response.json();
}

export async function fetchExactTokenCount(
  payload: PromptTokenCountRequest
): Promise<PromptTokenCountResponse> {
  const response = await fetch(`${API_BASE_URL}/api/prompt/token-count`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Exact token count failed: ${text}`);
  }
  return response.json();
}

