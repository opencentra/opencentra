export interface AgentRequest {
  input: unknown;
  session_id?: string | null;
  user_id?: string | null;
  channel?: string | null;
  [key: string]: unknown;
}

export interface AgentsRunningConfig {
  max_iters: number;
  max_input_length: number;
  /** Enable Qwen3 thinking mode (enable_thinking in chat_template_kwargs) */
  enable_qwen3_thinking?: boolean;
}
