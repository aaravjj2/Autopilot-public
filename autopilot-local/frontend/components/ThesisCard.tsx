"use client"; // data-testid="thesis-card-root"

import { useEffect, useRef, useState } from "react";
import { ArbThesis } from "@/types/arb";
import { Btn, Tag } from "@/components/terminal/ui";

interface ThesisCardProps {
  arbId: string;
  autoStart?: boolean;
}

export function ThesisCard({ arbId, autoStart = false }: ThesisCardProps) {
  const [text, setText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [parsed, setParsed] = useState<ArbThesis | null>(null);
  const [chatMessage, setChatMessage] = useState("");
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);
  const [chatting, setChatting] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const API_BASE =
    process.env.NEXT_PUBLIC_APEX_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";

  const startStream = () => {
    if (esRef.current) esRef.current.close();
    setText("");
    setParsed(null);
    setStreaming(true);
    const es = new EventSource(`${API_BASE}/api/arb/${arbId}/thesis`);
    esRef.current = es;

    es.onmessage = (e) => {
      if (e.data === "[DONE]") {
        setStreaming(false);
        es.close();
        return;
      }
      const chunk = JSON.parse(e.data).token ?? "";
      setText((prev) => prev + chunk);
    };

    es.onerror = () => {
      setStreaming(false);
      es.close();
    };
  };

  useEffect(() => {
    if (autoStart) startStream();
    return () => esRef.current?.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [arbId]);

  useEffect(() => {
    try {
      setParsed(JSON.parse(text));
    } catch {
      /* partial stream */
    }
  }, [text]);

  const chatEsRef = useRef<EventSource | null>(null);
  const [chatBuffer, setChatBuffer] = useState<string>("");

  const handleChat = async () => {
    if (!chatMessage.trim()) return;
    const userMsg = chatMessage;
    // Append user message to history
    setChatHistory((prev) => [...prev, { role: "user", content: userMsg }]);
    setChatMessage("");
    setChatting(true);
    setChatBuffer("");

    // Send POST with message and current history
    try {
      await fetch(`${API_BASE}/api/arb/${arbId}/thesis/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg, history: chatHistory.concat({ role: "user", content: userMsg }) }),
      });
    } catch (err) {
      // Network error, add to chat history and stop
      setChatHistory((prev) => [...prev, { role: "assistant", content: "Error: Network error" }]);
      setChatting(false);
      return;
    }

    // Open SSE to receive streamed assistant response
    if (chatEsRef.current) chatEsRef.current.close();
    const es = new EventSource(`${API_BASE}/api/arb/${arbId}/thesis/chat/stream`);
    chatEsRef.current = es;
    es.onmessage = (e) => {
      if (e.data === "[DONE]") {
        // Finalize message
        setChatHistory((prev) => [...prev, { role: "assistant", content: chatBuffer }]);
        setChatting(false);
        setChatBuffer("");
        es.close();
        return;
      }
      // Append incoming token to buffer
      setChatBuffer((prev) => prev + e.data);
    };
    es.onerror = () => {
      setChatHistory((prev) => [...prev, { role: "assistant", content: "Error: SSE connection failed" }]);
      setChatting(false);
      es.close();
    };
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }} data-testid="thesis-card-root">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="card-title" data-testid="thesis-title">AI Thesis</span>
        <Btn onClick={startStream} disabled={streaming} primary data-testid="generate-btn">
          {streaming ? "Generating…" : "Generate"}
        </Btn>
      </div>

      {streaming && !parsed && (
        <p style={{ fontSize: 13, color: "var(--text-muted)" }}>Streaming analysis…</p>
      )}

      {parsed ? (
        <div style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 10 }}>
          <span className="pill">{parsed.settlement_explanation}</span>
          <details>
            <summary className="kpi-up" style={{ cursor: "pointer", fontWeight: 500 }}>
              Bull Case
            </summary>
            <p style={{ marginTop: 6, color: "var(--text-muted)" }}>{parsed.bull_case}</p>
          </details>
          <details>
            <summary className="kpi-down" style={{ cursor: "pointer", fontWeight: 500 }}>
              Bear Case
            </summary>
            <p style={{ marginTop: 6, color: "var(--text-muted)" }}>{parsed.bear_case}</p>
          </details>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
            <strong>Recommended:</strong> {parsed.recommended_leg} ·{" "}
            <strong>Confidence:</strong> {parsed.confidence}
          </p>
          {Array.isArray(parsed.risk_flags) && parsed.risk_flags.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {parsed.risk_flags.map((f: string) => (
                <Tag key={f} variant="neutral">
                  {f}
                </Tag>
              ))}
            </div>
          )}
          <p style={{ fontStyle: "italic", fontSize: 12, color: "var(--text-dim)" }}>
            {parsed.one_liner}
          </p>
        </div>
      ) : null}

      {parsed && (
        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12 }}>
          {chatHistory.length > 0 && (
            <div
              style={{
                maxHeight: 140,
                overflowY: "auto",
                background: "var(--surface-2)",
                padding: 8,
                borderRadius: 6,
                marginBottom: 8,
                fontSize: 12,
              }}
              data-testid="chat-history"
            >
              {chatHistory.map((msg, idx) => (
                <div
                  key={idx}
                  style={{ textAlign: msg.role === "user" ? "right" : "left", marginBottom: 6 }}
                >
                  <span className={msg.role === "user" ? "pill live" : "pill"}>{msg.content}</span>
                </div>
              ))}
            </div>
          )}
            <div style={{ display: "flex", gap: 8 }} data-testid="chat-input-container">
              <input
                type="text"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                placeholder="Ask a follow-up…"
                disabled={chatting}
                data-testid="chat-input"
                style={{
                  flex: 1,
                  background: "var(--surface-2)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  padding: "6px 10px",
                  fontSize: 12,
                  color: "var(--text)",
                }}
              />
              <Btn onClick={handleChat} disabled={chatting || !chatMessage.trim()} primary data-testid="chat-send-btn">
                {chatting ? "…" : "Send"}
              </Btn>
            </div>
        </div>
      )}
    </div>
  );
}
