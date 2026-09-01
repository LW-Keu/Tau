import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import { ChatMessage, Settings, streamChat } from "./api";

interface Session {
  id: string;
  title: string;
  messages: ChatMessage[];
}

const LS_SESSIONS = "tau.sessions";
const LS_SETTINGS = "tau.settings";

function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function newSession(): Session {
  return { id: crypto.randomUUID(), title: "新对话", messages: [] };
}

export default function App() {
  const [sessions, setSessions] = useState<Session[]>(() => {
    const saved = load<Session[]>(LS_SESSIONS, []);
    return saved.length ? saved : [newSession()];
  });
  const [activeId, setActiveId] = useState(() => sessions[0]?.id ?? "");
  const [settings, setSettings] = useState<Settings>(() =>
    load(LS_SETTINGS, { baseUrl: "", apiKey: "" }),
  );
  const [showSettings, setShowSettings] = useState(false);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem(LS_SESSIONS, JSON.stringify(sessions));
  }, [sessions]);
  useEffect(() => {
    localStorage.setItem(LS_SETTINGS, JSON.stringify(settings));
  }, [settings]);

  const active = sessions.find((s) => s.id === activeId) ?? sessions[0];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [active?.messages.length, sending]);

  function patchSession(id: string, patch: (s: Session) => Session) {
    setSessions((list) => list.map((s) => (s.id === id ? patch(s) : s)));
  }

  function createSession() {
    const s = newSession();
    setSessions((list) => [s, ...list]);
    setActiveId(s.id);
    setError("");
  }

  function removeSession(id: string) {
    setSessions((list) => {
      const rest = list.filter((s) => s.id !== id);
      const next = rest.length ? rest : [newSession()];
      if (id === activeId) setActiveId(next[0].id);
      return next;
    });
  }

  async function send() {
    const text = input.trim();
    if (!text || sending || !active) return;
    if (!settings.apiKey) {
      setError("请先在左下角设置 API Key(后端 TAU_API_KEY)");
      setShowSettings(true);
      return;
    }
    setInput("");
    setError("");
    setSending(true);
    const sessionId = active.id;
    const history = active.messages;
    const userMsg: ChatMessage = { role: "user", content: text };
    patchSession(sessionId, (s) => ({
      ...s,
      title: s.messages.length ? s.title : text.slice(0, 24),
      messages: [...s.messages, userMsg, { role: "assistant", content: "" }],
    }));
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      await streamChat({
        settings,
        messages: [...history, userMsg],
        signal: ctrl.signal,
        onDelta: (delta) =>
          patchSession(sessionId, (s) => {
            const messages = [...s.messages];
            const last = messages[messages.length - 1];
            if (last?.role === "assistant") {
              messages[messages.length - 1] = {
                ...last,
                content: last.content + delta,
              };
            }
            return { ...s, messages };
          }),
      });
    } catch (e) {
      if (!ctrl.signal.aborted) {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      // 空回复(直接 abort / 出错)不留占位气泡
      patchSession(sessionId, (s) => ({
        ...s,
        messages: s.messages.filter(
          (m, i) =>
            !(i === s.messages.length - 1 && m.role === "assistant" && !m.content),
        ),
      }));
      abortRef.current = null;
      setSending(false);
    }
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <button className="new-chat" onClick={createSession}>
          + 新建对话
        </button>
        <div className="session-list">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`session ${s.id === active?.id ? "active" : ""}`}
              onClick={() => setActiveId(s.id)}
            >
              <span className="session-title">{s.title}</span>
              <button
                className="session-del"
                title="删除"
                onClick={(e) => {
                  e.stopPropagation();
                  removeSession(s.id);
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
        <button className="settings-btn" onClick={() => setShowSettings((v) => !v)}>
          ⚙ 设置
        </button>
        {showSettings && (
          <div className="settings-panel">
            <label>
              Base URL(空 = 同源/代理)
              <input
                value={settings.baseUrl}
                placeholder="http://127.0.0.1:8642"
                onChange={(e) =>
                  setSettings({ ...settings, baseUrl: e.target.value.trim() })
                }
              />
            </label>
            <label>
              API Key
              <input
                type="password"
                value={settings.apiKey}
                onChange={(e) =>
                  setSettings({ ...settings, apiKey: e.target.value.trim() })
                }
              />
            </label>
          </div>
        )}
      </aside>
      <main className="main">
        <div className="messages">
          {active?.messages.length === 0 && (
            <div className="empty">向 Tau 提问,开始对话</div>
          )}
          {active?.messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <div className="msg-role">{m.role === "user" ? "你" : "Tau"}</div>
              <div className="msg-body">
                {m.role === "assistant" ? (
                  m.content ? (
                    <Markdown>{m.content}</Markdown>
                  ) : (
                    sending && i === active.messages.length - 1 && (
                      <span className="thinking">思考中…</span>
                    )
                  )
                ) : (
                  m.content
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        {error && <div className="error">{error}</div>}
        <div className="composer">
          <textarea
            value={input}
            placeholder="输入消息,Enter 发送,Shift+Enter 换行"
            rows={3}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                void send();
              }
            }}
          />
          {sending ? (
            <button className="stop" onClick={() => abortRef.current?.abort()}>
              停止
            </button>
          ) : (
            <button className="send" onClick={() => void send()} disabled={!input.trim()}>
              发送
            </button>
          )}
        </div>
      </main>
    </div>
  );
}
