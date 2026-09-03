"use client";

import { useRef, useState } from "react";
import { Bot, Heart, MessageCircle, Send, UserRound } from "lucide-react";
import { sendPolicyChatMessage } from "@/lib/api";
import type { PolicyChatMessage, PolicyChatOption } from "@/lib/api";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import { formatApplicationPeriod } from "@/lib/policyFormat";

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
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function scrollToBottom() {
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
    });
  }

  function resizeTextarea() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }

  async function sendText(text: string) {
    if (!text.trim() || loading) return;

    const nextTurns = [...turns, { role: "user" as const, content: text }];
    setTurns(nextTurns);
    setInput("");
    requestAnimationFrame(resizeTextarea);
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

  function handleInputKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendText(input);
    }
  }

  const showSuggestions = turns.length === 1 && !loading;

  return (
    <div className="flex max-h-[560px] min-h-[420px] flex-col overflow-hidden rounded-[22px] border border-slate-200/80 bg-white p-5 shadow-[0_24px_55px_rgba(16,35,71,.18)]">
      <div className="mb-3 flex items-center gap-2 text-[13px] font-extrabold text-ink">
        <MessageCircle size={16} className="text-[#2457d6]" />
        정책 챗봇
      </div>
      <div className="flex-1 min-h-0 space-y-3.5 overflow-y-auto pr-1" ref={listRef}>
        {turns.map((turn, i) => (
          <div key={i} className={`flex items-start gap-2 ${turn.role === "user" ? "flex-row-reverse" : ""}`}>
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#e8f0ff] text-[#2457d6]">
              {turn.role === "user" ? <UserRound size={14} /> : <Bot size={14} />}
            </span>
            <div className="flex min-w-0 flex-col gap-2">
              <div
                className={`max-w-full whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${
                  turn.role === "user"
                    ? "rounded-br-md bg-[#2457d6] text-white"
                    : "rounded-bl-md border border-slate-100 bg-[#f7f9fc] text-ink"
                }`}
              >
                {turn.content}
              </div>
              {turn.policies && turn.policies.length > 0 && (
                <div className="flex flex-col gap-2">
                  {turn.policies.map((p, j) => (
                    <div key={j} className="rounded-xl border border-slate-200/80 bg-white p-3">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-[13px] font-extrabold text-ink">
                          {p.is_newlywed_policy && (
                            <span className="mr-1.5 inline-flex items-center gap-1 rounded-full bg-[#e7f8f5] px-2 py-0.5 text-[10px] font-extrabold text-[#159c8d]">
                              <Heart size={11} /> 신혼부부
                            </span>
                          )}
                          {p.policy_name}
                        </div>
                        <span className="whitespace-nowrap text-[11px] text-slate-400">
                          {/* status="상시"는 실제로 "신청 마감일 데이터 없음"이라 StatusPill과
                              동일하게 붉은 계열 + "기간 확인 필요"로 보여준다. */}
                          {p.status === "상시" ? "🔴 기간 확인 필요" : `${p.status_emoji} ${p.status}`}
                        </span>
                      </div>
                      <div className="mt-1 text-[12px] text-slate-500">{p.benefit_description}</div>
                      <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-400">
                        <span>신청 기간</span>
                        <span>{formatApplicationPeriod(p.application_period)}</span>
                      </div>
                      <PolicyDetailLink url={p.reference_url} className="mt-1.5 text-[12px]" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-start gap-2">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#e8f0ff] text-[#2457d6]">
              <Bot size={14} />
            </span>
            <div className="flex items-center gap-1 rounded-2xl rounded-bl-md border border-slate-100 bg-[#f7f9fc] px-4 py-3.5">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
            </div>
          </div>
        )}
      </div>

      {showSuggestions && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-bold text-slate-500 transition hover:border-[#2457d6] hover:text-[#2457d6]"
              onClick={() => sendText(q)}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {error && <p className="mt-2 text-[12px] font-bold text-rose-500">{error}</p>}
      <form onSubmit={handleSend} className="mt-3 flex items-end gap-1.5 rounded-[22px] border border-slate-200 bg-[#f7f9fc] p-1.5 pl-4 transition focus-within:border-[#2457d6] focus-within:bg-white">
        <textarea
          ref={textareaRef}
          className="max-h-[88px] min-w-0 flex-1 resize-none border-none bg-transparent py-2 text-[13px] text-ink outline-none placeholder:text-slate-400"
          rows={1}
          placeholder="예: 신혼부부 전세자금 대출 있어?"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            resizeTextarea();
          }}
          onKeyDown={handleInputKeyDown}
          disabled={loading}
        />
        <button
          className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#2457d6] text-white transition hover:bg-[#1949c1] disabled:bg-slate-200 disabled:text-slate-400"
          type="submit"
          aria-label="전송"
          disabled={loading || !input.trim()}
        >
          <Send size={15} />
        </button>
      </form>
    </div>
  );
}
