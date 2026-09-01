"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Send, UserRound } from "lucide-react";
import { sendPolicyQaMessage, type PolicyQaMessage } from "@/lib/api";

type ChatTurn = { role: "user" | "assistant"; content: string };

// policy_key/policy_name만 있으면 되는 최소 형태 — PolicyBrowseItem은 물론
// PolicyOption(내 맞춤 정책 보기 탭)처럼 필드가 더 적은 타입도 그대로 넘길 수 있다.
export type PolicyQaTarget = { policy_key: string; policy_name: string };

const SUGGESTED_QUESTIONS = ["신청 자격이 되나요?", "언제까지 신청해야 하나요?", "필요한 서류가 뭔가요?"];

// 정책별 챗봇 — useAiPolicySearch의 채팅 파트와 모양은 비슷하지만 필터/칩이 없는 순수
// Q&A라 별도 컴포넌트로 둔다. item.policy_key가 바뀌면(다른 정책을 눌렀을 때) 대화를
// 새로 시작한다.
export default function PolicyQaChatPanel({ item }: { item: PolicyQaTarget }) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setTurns([
      {
        role: "assistant",
        content: `안녕하세요! ${item.policy_name}에 대해 궁금한 점을 물어보세요. 정책 설명을 직접 읽어보셔도 좋아요.`,
      },
    ]);
    setInput("");
    setError(null);
  }, [item.policy_key, item.policy_name]);

  function resizeTextarea() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }

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
    requestAnimationFrame(resizeTextarea);
    setError(null);
    setLoading(true);
    scrollToBottom();

    try {
      const token = localStorage.getItem("token") ?? "";
      const history: PolicyQaMessage[] = nextTurns.map((t) => ({ role: t.role, content: t.content }));
      const res = await sendPolicyQaMessage(token, item.policy_key, history);
      setTurns((prev) => [...prev, { role: "assistant", content: res.reply }]);
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
    <div className="flex h-full min-h-[420px] flex-col rounded-[22px] border border-slate-200/80 bg-white p-5">
      <div className="min-h-0 flex-1 space-y-3.5 overflow-y-auto pr-1" ref={listRef}>
        {turns.map((turn, i) => (
          <div key={i} className={`flex items-start gap-2 ${turn.role === "user" ? "flex-row-reverse" : ""}`}>
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#e8f0ff] text-[#2457d6]">
              {turn.role === "user" ? <UserRound size={14} /> : <Bot size={14} />}
            </span>
            <div
              className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${
                turn.role === "user" ? "rounded-br-md bg-[#2457d6] text-white" : "rounded-bl-md border border-slate-100 bg-[#f7f9fc] text-ink"
              }`}
            >
              {turn.content}
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
          placeholder="이 정책에 대해 물어보세요"
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
