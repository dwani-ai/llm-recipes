import type { ModeSelection } from "./types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const DEFAULT_MODE_SELECTION: ModeSelection = {
  streaming: false,
  thinking: true,
  implicit_cache: false,
  explicit_cache: true,
};

export const DEFAULT_PROMPT_TEMPLATE =
  "Using {{dataset_name}}, produce a detailed, evidence-backed decision memo for {{goal}}. Return: (1) top findings, (2) trade-offs, (3) prioritized actions, and (4) measurable success criteria.";

