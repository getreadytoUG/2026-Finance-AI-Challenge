"use client";

import { useEffect, useRef, useState } from "react";
import {
  fetchAiSearchResults,
  getMe,
  sendAiSearchMessage,
  type AiSearchFilters,
  type PolicyBrowseItem,
  type PolicyChatMessage,
} from "@/lib/api";
import Pagination from "@/components/Pagination";
import PolicyDetailLink from "@/components/PolicyDetailLink";

const PAGE_SIZE = 10;

const STATUS_COLORS: Record<string, string> = {
  임박: "var(--accent)",
  여유: "var(--success)",
  상시: "var(--primary)",
  예정: "var(--text-muted)",
  만료: "var(--danger)",
};

const STATUS_EMOJI: Record<string, string> = {
  임박: "🟡",
  여유: "🟢",
  상시: "🟢",
  예정: "⚪",
  만료: "🔴",
};

function StatusDot({ status }: { status: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 10,
        height: 10,
        borderRadius: "50%",
        background: STATUS_COLORS[status] ?? "var(--text-muted)",
        marginRight: 6,
      }}
    />
  );
}

type ChatTurn = { role: "user" | "assistant"; content: string };

const WELCOME_MESSAGE: ChatTurn = {
  role: "assistant",
  content:
    "안녕하세요! 지금은 회원님 정보 기준으로 정책을 보여드리고 있어요. 조건을 말씀해주시면 오른쪽 결과가 실시간으로 바뀝니다.",
};

const SUGGESTED_QUESTIONS = [
  "서울 지역 정책만 보여줘",
  "미혼 대상 정책만 보여줘",
  "창업 지원 정책 찾아줘",
  "마감 임박한 것만 보여줘",
];

function filterChips(filters: AiSearchFilters): { key: keyof AiSearchFilters; label: string }[] {
  const chips: { key: keyof AiSearchFilters; label: string }[] = [];
  if (filters.age != null) chips.push({ key: "age", label: `${filters.age}세` });
  if (filters.is_married != null) chips.push({ key: "is_married", label: filters.is_married ? "기혼" : "미혼" });
  if (filters.region) chips.push({ key: "region", label: filters.region });
  if (filters.category) chips.push({ key: "category", label: filters.category });
  if (filters.keyword) chips.push({ key: "keyword", label: `"${filters.keyword}"` });
  if (filters.status) chips.push({ key: "status", label: `${STATUS_EMOJI[filters.status] ?? ""} ${filters.status}` });
  return chips;
}

export default function AiSearchPage() {
  const [filters, setFilters] = useState<AiSearchFilters | null>(null);
  const [items, setItems] = useState<PolicyBrowseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [includeClosed, setIncludeClosed] = useState(false);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState<string | null>(null);

  const [turns, setTurns] = useState<ChatTurn[]>([WELCOME_MESSAGE]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function resizeTextarea() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((profile) => {
        const initial: AiSearchFilters = {
          age: profile.age,
          is_married: profile.is_married,
          annual_income_krw: profile.annual_income_krw,
          spouse_annual_income_krw: profile.spouse_annual_income_krw,
          region: profile.region,
        };
        setFilters(initial);
        return refetch(initial, 1, false);
      })
      .catch((err) => setResultsError(err instanceof Error ? err.message : "정보를 불러오지 못했습니다."));
  }, []);

  async function refetch(nextFilters: AiSearchFilters, nextPage: number, nextIncludeClosed: boolean) {
    setResultsLoading(true);
    setResultsError(null);
    try {
      const token = localStorage.getItem("token") ?? "";
      const res = await fetchAiSearchResults(token, nextFilters, nextIncludeClosed, nextPage, PAGE_SIZE);
      setItems(res.items);
      setTotal(res.total);
      setPage(res.page);
    } catch (err) {
      setResultsError(err instanceof Error ? err.message : "결과를 불러오지 못했습니다.");
    } finally {
      setResultsLoading(false);
    }
  }

  function handleRemoveChip(key: keyof AiSearchFilters) {
    if (!filters) return;
    const next = { ...filters, [key]: null };
    setFilters(next);
    refetch(next, 1, includeClosed);
  }

  function handleToggleIncludeClosed() {
    const next = !includeClosed;
    setIncludeClosed(next);
    if (filters) refetch(filters, 1, next);
  }

  function handlePageChange(nextPage: number) {
    if (!filters) return;
    refetch(filters, nextPage, includeClosed);
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
    });
  }

  async function sendText(text: string) {
    if (!text.trim() || chatLoading || !filters) return;

    const nextTurns = [...turns, { role: "user" as const, content: text }];
    setTurns(nextTurns);
    setChatInput("");
    requestAnimationFrame(resizeTextarea);
    setChatError(null);
    setChatLoading(true);
    scrollToBottom();

    try {
      const token = localStorage.getItem("token") ?? "";
      const history: PolicyChatMessage[] = nextTurns
        .filter((t) => t !== WELCOME_MESSAGE)
        .map((t) => ({ role: t.role, content: t.content }));
      const res = await sendAiSearchMessage(token, history, filters, includeClosed, PAGE_SIZE);
      setTurns((prev) => [...prev, { role: "assistant", content: res.reply }]);
      setFilters(res.filters);
      setItems(res.items);
      setTotal(res.total);
      setPage(res.page);
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "답변을 받지 못했습니다.");
    } finally {
      setChatLoading(false);
      scrollToBottom();
    }
  }

  function handleSend(e: React.FormEvent) {
    e.preventDefault();
    sendText(chatInput);
  }

  function handleInputKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendText(chatInput);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const chips = filters ? filterChips(filters) : [];
  const showSuggestions = turns.length === 1 && !chatLoading;

  return (
    <>
      <div className="page-header">
        <h1>✨ AI로 정책 알기</h1>
        <p>대화로 조건을 좁혀가며 나에게 맞는 정책을 실시간으로 찾아보세요.</p>
      </div>

      <div className="ai-search-grid">
        <div className="card chat-panel">
          {chips.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
              {chips.map((chip) => (
                <span key={chip.key} className="filter-chip">
                  {chip.label}
                  <button type="button" onClick={() => handleRemoveChip(chip.key)} aria-label={`${chip.label} 필터 제거`}>
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}

          <div className="chat-message-list" ref={listRef}>
            {turns.map((turn, i) => (
              <div key={i} className={`chat-row ${turn.role === "user" ? "chat-row-user" : "chat-row-assistant"}`}>
                <span className="chat-avatar">{turn.role === "user" ? "🙋" : "🤖"}</span>
                <div className={`chat-bubble ${turn.role === "user" ? "chat-bubble-user" : "chat-bubble-assistant"}`}>
                  {turn.content}
                </div>
              </div>
            ))}
            {chatLoading && (
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

          {chatError && <p className="error-text" style={{ marginTop: 8 }}>{chatError}</p>}
          <form onSubmit={handleSend} className="chat-input-bar" style={{ marginTop: 12 }}>
            <textarea
              ref={textareaRef}
              className="chat-input-textarea"
              rows={1}
              placeholder="예: 서울 지역 정책만 보여줘"
              value={chatInput}
              onChange={(e) => {
                setChatInput(e.target.value);
                resizeTextarea();
              }}
              onKeyDown={handleInputKeyDown}
              disabled={chatLoading || !filters}
            />
            <button
              className="chat-input-send"
              type="submit"
              aria-label="전송"
              disabled={chatLoading || !chatInput.trim() || !filters}
            >
              ➤
            </button>
          </form>
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <div style={{ fontWeight: 700, fontSize: 16 }}>
              맞춤 검색 결과: <span style={{ color: "var(--primary)" }}>{total}개</span>
            </div>
          </div>

          <label className="checkbox-field">
            <input type="checkbox" checked={includeClosed} onChange={handleToggleIncludeClosed} />
            마감된 정책도 보기
          </label>

          {resultsError && <p className="error-text">{resultsError}</p>}
          {resultsLoading && <p>불러오는 중...</p>}
          {!resultsLoading && items.length === 0 && !resultsError && (
            <p className="error-text">조건에 맞는 정책이 없습니다.</p>
          )}

          <div className="result-list">
            {items.map((item, i) => (
              <div key={i} className="result-item">
                <div className="result-item-title">
                  <StatusDot status={item.status} />
                  {item.policy_name}
                </div>
                <div className="result-item-row">
                  <span>분야</span>
                  <span>{item.large_category}</span>
                </div>
                <div className="result-item-row">
                  <span>상태</span>
                  <span style={{ display: "inline-flex", alignItems: "center" }}>
                    <StatusDot status={item.status} />
                    {item.status}
                  </span>
                </div>
                <div className="result-item-row">
                  <span>신청 기간</span>
                  <span>{item.application_period}</span>
                </div>
                <div style={{ marginTop: 12 }}>
                  <PolicyDetailLink url={item.reference_url} />
                </div>
              </div>
            ))}
          </div>

          <Pagination page={page} totalPages={totalPages} onPageChange={handlePageChange} />
        </div>
      </div>
    </>
  );
}
