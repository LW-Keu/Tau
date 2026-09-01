export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface Settings {
  baseUrl: string; // 空串 = 同源(vite 代理或静态托管于 API 同域)
  apiKey: string;
}

/** 增量解析 SSE 缓冲:按空行分块,取出 data: 行,残片留在 rest。 */
export function parseSSE(buffer: string): { events: string[]; rest: string } {
  const events: string[] = [];
  let rest = buffer;
  let idx: number;
  while ((idx = rest.indexOf("\n\n")) >= 0) {
    const block = rest.slice(0, idx);
    rest = rest.slice(idx + 2);
    for (const line of block.split("\n")) {
      if (line.startsWith("data: ")) events.push(line.slice(6));
    }
  }
  return { events, rest };
}

/** POST /v1/chat/completions(stream),逐段回调 assistant 增量文本。 */
export async function streamChat(opts: {
  settings: Settings;
  messages: ChatMessage[];
  signal: AbortSignal;
  onDelta: (text: string) => void;
}): Promise<void> {
  const res = await fetch(`${opts.settings.baseUrl}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${opts.settings.apiKey}`,
    },
    body: JSON.stringify({
      model: "tau-agent",
      messages: opts.messages,
      stream: true,
    }),
    signal: opts.signal,
  });
  if (!res.ok || !res.body) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body?.error?.message ?? message;
    } catch {
      // 非 JSON 错误体,保留 HTTP 状态码
    }
    throw new Error(message);
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) return;
    const { events, rest } = parseSSE(buffer + value);
    buffer = rest;
    for (const data of events) {
      if (data === "[DONE]") return;
      const payload = JSON.parse(data);
      if (payload.error) throw new Error(payload.error.message);
      const delta = payload.choices?.[0]?.delta?.content;
      if (typeof delta === "string" && delta) opts.onDelta(delta);
    }
  }
}
