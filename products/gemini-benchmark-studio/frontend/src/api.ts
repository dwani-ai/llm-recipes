import { API_BASE_URL } from "./defaults";
import type { BenchmarkRequest, BenchmarkResponse, DefaultModesResponse } from "./types";

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

