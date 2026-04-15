import type { ModeSelection } from "./types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const DEFAULT_MODE_SELECTION: ModeSelection = {
  streaming: true,
  thinking: false,
  implicit_cache: true,
  explicit_cache: false,
};

export const DEFAULT_PROMPT_TEMPLATE =
  "Analyze {{dataset_name}} for {{goal}} and suggest the fastest robust benchmark mode.";

