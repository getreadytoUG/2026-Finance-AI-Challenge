"use client";

import { Bot, Send, UserRound } from "lucide-react";
import type { AiPolicySearchState } from "@/lib/useAiPolicySearch";

// compact=true는 추천 탭 캘린더 뷰처럼 4칸 레이아웃 안에 끼워 넣을 때 쓰는 축소
// 스타일이다 — /ai-search 페이지(단독, 넉넉한 2칸 레이아웃)는 기본값(compact=false)을 쓴다.
export default function AiSearchChatPanel({ state, compact = false }: { state: AiPolicySearchState; compact?: boolean }) {
  const {
    chips,
    turns,
    chatLoading,
    chatError,
    listRef,
    textareaRef,
    chatInput,
    setChatInput,
    resizeTextarea,
    handleInputKeyDown,
    handleSend,
    showSuggestions,
    suggestedQuestions,
    sendText,
    handleRemoveChip,
    handleResetFilters,
    filters,
  } = state;

  return (
    <div
      className={`flex flex-col rounded-[22px] border border-slate-200/80 bg-white ${
        // compact 모드는 캘린더/검색결과와 그리드 stretch로 높이를 맞춘다(고정 높이를
        // 주면 stretch와 충돌해서 셋의 높이가 어긋난다) — 넉넉한 폭에서만 쓰이므로
        // 최소 높이만 방어적으로 둔다.
        compact ? "h-full min-h-[560px] p-4" : "max-h-[720px] min-h-[520px] p-5"
      }`}
    >
      {chips.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-1.5">
          {chips.map((chip) => (
            <span
              key={chip.key}
              className={`inline-flex items-center gap-1.5 rounded-full border border-[#2457d6] bg-[#eef3ff] font-bold text-[#2457d6] ${
                compact ? "px-2.5 py-1 text-[11px]" : "px-3 py-1.5 text-[12px]"
              }`}
            >
              {chip.label}
              <button type="button" onClick={() => handleRemoveChip(chip.key)} aria-label={`${chip.label} 필터 제거`} className="text-[#2457d6]/70 hover:text-[#2457d6]">
                ×
              </button>
            </span>
          ))}
          {!compact && (
            <button type="button" className="rounded-full border border-slate-200 px-2.5 py-1 text-[11px] font-bold text-slate-400 hover:border-slate-300 hover:text-slate-600" onClick={handleResetFilters}>
              조건 전체 초기화
            </button>
          )}
        </div>
      )}

      <div className="min-h-0 flex-1 space-y-3.5 overflow-y-auto pr-1" ref={listRef}>
        {turns.map((turn, i) => (
          <div key={i} className={`flex items-start gap-2 ${turn.role === "user" ? "flex-row-reverse" : ""}`}>
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#e8f0ff] text-[#2457d6]">
              {turn.role === "user" ? <UserRound size={14} /> : <Bot size={14} />}
            </span>
            <div
              className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 leading-relaxed ${compact ? "text-[12px]" : "text-[13px]"} ${
                turn.role === "user" ? "rounded-br-md bg-[#2457d6] text-white" : "rounded-bl-md border border-slate-100 bg-[#f7f9fc] text-ink"
              }`}
            >
              {turn.content}
            </div>
          </div>
        ))}
        {chatLoading && (
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
          {suggestedQuestions.map((q) => (
            <button
              key={q}
              type="button"
              className={`rounded-full border border-slate-200 bg-white font-bold text-slate-500 transition hover:border-[#2457d6] hover:text-[#2457d6] ${
                compact ? "px-2.5 py-1 text-[10px]" : "px-3 py-1.5 text-[11px]"
              }`}
              onClick={() => sendText(q)}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {chatError && <p className="mt-2 text-[12px] font-bold text-rose-500">{chatError}</p>}
      <form onSubmit={handleSend} className="mt-3 flex items-end gap-1.5 rounded-[22px] border border-slate-200 bg-[#f7f9fc] p-1.5 pl-4 transition focus-within:border-[#2457d6] focus-within:bg-white">
        <textarea
          ref={textareaRef}
          className="max-h-[88px] min-w-0 flex-1 resize-none border-none bg-transparent py-2 text-[13px] text-ink outline-none placeholder:text-slate-400"
          rows={1}
          placeholder={compact ? "정책 조건을 물어보세요" : "예: 서울 지역 정책만 보여줘"}
          value={chatInput}
          onChange={(e) => {
            setChatInput(e.target.value);
            resizeTextarea();
          }}
          onKeyDown={handleInputKeyDown}
          disabled={chatLoading || !filters}
        />
        <button
          className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#2457d6] text-white transition hover:bg-[#1949c1] disabled:bg-slate-200 disabled:text-slate-400"
          type="submit"
          aria-label="전송"
          disabled={chatLoading || !chatInput.trim() || !filters}
        >
          <Send size={15} />
        </button>
      </form>
    </div>
  );
}
