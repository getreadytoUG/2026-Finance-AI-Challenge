"use client";

import { useRef, useState } from "react";
import { sendPolicyChatMessage } from "@/lib/api";
import type { PolicyChatMessage, PolicyChatOption } from "@/lib/api";

type ChatTurn = {
  role: "user" | "assistant";
  content: string;
  policies?: PolicyChatOption[];
};

const WELCOME_MESSAGE: ChatTurn = {
  role: "assistant",
  content:
    "안녕하세요! 어떤 정책을 찾고 계신가요? 예를 들어 \"전세자금 대출 관련 정책 있어?\"처럼 자유롭게 물어보세요.",
};

const SUGGESTED_QUESTIONS = [
  "전세자금 대출 관련 정책 있어?",
  "신혼부부 지원금 알려줘",
  "청년 창업 지원금 있어?",
  "월세 지원 정책 찾아줘",
];

export default function PolicyChat() {
  const [turns, setTurns] = useState<ChatTurn[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  function scrollToBottom() {
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
    });
  }

  async function sendText(text: string) {
    if (!text.trim() || loading) return;

    const nextTurns = [...turns, { role: "user" as const, content: text }];
    setTurns(nextTurns);
    setInput("");
    setError(null);
    setLoading(true);
    scrollToBottom();

    try {
      const token = localStorage.getItem("token") ?? "";
      // 웰컴 메시지는 화면 전용 안내라 대화 이력에서 제외하고 보낸다.
      const history: PolicyChatMessage[] = nextTurns
        .filter((t) => t !== WELCOME_MESSAGE)
        .map((t) => ({ role: t.role, content: t.content }));
      const res = await sendPolicyChatMessage(token, history);
      setTurns((prev) => [...prev, { role: "assistant", content: res.reply, policies: res.policies }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "답변을 받지 못했습니다.");
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  }

  function handleSend(e: React.FormEvent) {
    e.preventDefault();
    sendText(input);
  }

  const showSuggestions = turns.length === 1 && !loading;

  return (
    <div className="card chat-panel">
      <div style={{ fontWeight: 700, marginBottom: 12 }}>💬 정책 챗봇</div>
      <div className="chat-message-list" ref={listRef}>
        {turns.map((turn, i) => (
          <div key={i} className={`chat-row ${turn.role === "user" ? "chat-row-user" : "chat-row-assistant"}`}>
            <span className="chat-avatar">{turn.role === "user" ? "🙋" : "🤖"}</span>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
              <div className={`chat-bubble ${turn.role === "user" ? "chat-bubble-user" : "chat-bubble-assistant"}`}>
                {turn.content}
              </div>
              {turn.policies && turn.policies.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {turn.policies.map((p, j) => (
                    <div key={j} className="chat-policy-card">
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                        <div style={{ fontWeight: 700, fontSize: 13 }}>
                          {p.is_newlywed_policy && (
                            <span className="badge badge-success" style={{ marginRight: 6 }}>
                              💍 신혼부부
                            </span>
                          )}
                          {p.policy_name}
                        </div>
                        <span style={{ fontSize: 11, color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                          {p.status_emoji} {p.status}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{p.benefit_description}</div>
                      <div className="result-item-row" style={{ marginTop: 6, fontSize: 12 }}>
                        <span>신청 기간</span>
                        <span>{p.application_period}</span>
                      </div>
                      <a className="link" href={p.reference_url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>
                        자세히 보기 →
                      </a>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-row chat-row-assistant">
            <span className="chat-avatar">🤖</span>
            <div className="chat-bubble chat-bubble-assistant chat-typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
      </div>

      {showSuggestions && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              className="btn-ghost"
              style={{ borderRadius: 999, fontSize: 12 }}
              onClick={() => sendText(q)}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {error && <p className="error-text" style={{ marginTop: 8 }}>{error}</p>}
      <form onSubmit={handleSend} style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <input
          className="input"
          type="text"
          placeholder="예: 신혼부부 전세자금 대출 있어?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button className="btn" type="submit" style={{ width: "auto", flexShrink: 0 }} disabled={loading || !input.trim()}>
          전송
        </button>
      </form>
    </div>
  );
}
