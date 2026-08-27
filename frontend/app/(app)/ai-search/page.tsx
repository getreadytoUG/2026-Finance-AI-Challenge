"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Check, Search, Send, Sparkles, UserRound, WalletCards } from "lucide-react";
import {
  analyzePolicy,
  fetchAiSearchResults,
  getMe,
  linkSavingsBenefit,
  listSavingsLinkedBenefits,
  sendAiSearchMessage,
  type AiSearchFilters,
  type PolicyAnalysisResult,
  type PolicyBrowseItem,
  type PolicyChatMessage,
} from "@/lib/api";
import { DashboardLayout } from "@/components/DashboardLayout";
import Pagination from "@/components/Pagination";
import PolicyDetailLink from "@/components/PolicyDetailLink";

const PAGE_SIZE = 10;

const STATUS_PILL: Record<string, string> = {
  임박: "urgent",
  만료: "urgent",
  여유: "available",
  상시: "available",
  예정: "neutral",
};

function StatusPill({ status }: { status: string }) {
  return (
    <span className={`policy-status ${STATUS_PILL[status] ?? "neutral"}`}>
      <span />
      {status}
    </span>
  );
}

type ChatTurn = { role: "user" | "assistant"; content: string };

type AnalysisState = {
  loading: boolean;
  result: PolicyAnalysisResult | null;
  error: string | null;
  open: boolean;
  linked: boolean;
  linking: boolean;
};

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
  if (filters.status) chips.push({ key: "status", label: filters.status });
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
  const [analysis, setAnalysis] = useState<Record<string, AnalysisState>>({});
  const [linkedPolicyKeys, setLinkedPolicyKeys] = useState<Set<string>>(new Set());
  const [keywordInput, setKeywordInput] = useState("");

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

    listSavingsLinkedBenefits(token)
      .then((res) => setLinkedPolicyKeys(new Set(res.items.map((b) => b.policy_key))))
      .catch(() => {});
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

  function handleResetFilters() {
    const next: AiSearchFilters = {
      age: null,
      is_married: null,
      annual_income_krw: null,
      spouse_annual_income_krw: null,
      region: null,
      category: null,
      keyword: null,
      status: null,
    };
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

  // 채팅이나 필터 칩 제거로 keyword가 바뀔 수도 있으니, 검색창 값도 항상
  // 현재 filters.keyword와 맞춰둔다.
  useEffect(() => {
    setKeywordInput(filters?.keyword ?? "");
  }, [filters?.keyword]);

  function handleKeywordSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!filters) return;
    const next = { ...filters, keyword: keywordInput.trim() || null };
    setFilters(next);
    refetch(next, 1, includeClosed);
  }

  async function handleAnalyze(policyKey: string) {
    const existing = analysis[policyKey];
    if (existing?.result) {
      setAnalysis((prev) => ({ ...prev, [policyKey]: { ...existing, open: !existing.open } }));
      return;
    }
    setAnalysis((prev) => ({
      ...prev,
      [policyKey]: { loading: true, result: null, error: null, open: true, linked: false, linking: false },
    }));
    try {
      const token = localStorage.getItem("token") ?? "";
      const result = await analyzePolicy(token, policyKey);
      setAnalysis((prev) => ({
        ...prev,
        [policyKey]: {
          loading: false,
          result,
          error: null,
          open: true,
          linked: linkedPolicyKeys.has(policyKey),
          linking: false,
        },
      }));
    } catch (err) {
      setAnalysis((prev) => ({
        ...prev,
        [policyKey]: {
          loading: false,
          result: null,
          error: err instanceof Error ? err.message : "분석 리포트를 불러오지 못했습니다.",
          open: true,
          linked: false,
          linking: false,
        },
      }));
    }
  }

  async function handleLinkBenefit(item: PolicyBrowseItem) {
    const state = analysis[item.policy_key];
    const amount = state?.result?.estimated_monthly_benefit_krw;
    if (amount == null) return;
    setAnalysis((prev) => ({ ...prev, [item.policy_key]: { ...prev[item.policy_key], linking: true } }));
    try {
      const token = localStorage.getItem("token") ?? "";
      await linkSavingsBenefit(token, item.policy_key, item.policy_name, amount);
      setLinkedPolicyKeys((prev) => new Set(prev).add(item.policy_key));
      setAnalysis((prev) => ({ ...prev, [item.policy_key]: { ...prev[item.policy_key], linking: false, linked: true } }));
    } catch (err) {
      setAnalysis((prev) => ({
        ...prev,
        [item.policy_key]: {
          ...prev[item.policy_key],
          linking: false,
          error: err instanceof Error ? err.message : "저축플랜에 반영하지 못했습니다.",
        },
      }));
    }
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
    <DashboardLayout eyebrow="AI ANALYSIS REPORT" title="AI 분석 리포트">
      <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
        <div className="flex max-h-[720px] min-h-[520px] flex-col rounded-[22px] border border-slate-200/80 bg-white p-5">
          {chips.length > 0 && (
            <div className="mb-3 flex flex-wrap items-center gap-1.5">
              {chips.map((chip) => (
                <span key={chip.key} className="inline-flex items-center gap-1.5 rounded-full border border-[#2457d6] bg-[#eef3ff] px-3 py-1.5 text-[12px] font-bold text-[#2457d6]">
                  {chip.label}
                  <button type="button" onClick={() => handleRemoveChip(chip.key)} aria-label={`${chip.label} 필터 제거`} className="text-[#2457d6]/70 hover:text-[#2457d6]">
                    ×
                  </button>
                </span>
              ))}
              <button type="button" className="rounded-full border border-slate-200 px-2.5 py-1 text-[11px] font-bold text-slate-400 hover:border-slate-300 hover:text-slate-600" onClick={handleResetFilters}>
                조건 전체 초기화
              </button>
            </div>
          )}

          <div className="flex-1 min-h-0 space-y-3.5 overflow-y-auto pr-1" ref={listRef}>
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

          {chatError && <p className="mt-2 text-[12px] font-bold text-rose-500">{chatError}</p>}
          <form onSubmit={handleSend} className="mt-3 flex items-end gap-1.5 rounded-[22px] border border-slate-200 bg-[#f7f9fc] p-1.5 pl-4 transition focus-within:border-[#2457d6] focus-within:bg-white">
            <textarea
              ref={textareaRef}
              className="max-h-[88px] min-w-0 flex-1 resize-none border-none bg-transparent py-2 text-[13px] text-ink outline-none placeholder:text-slate-400"
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
              className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#2457d6] text-white transition hover:bg-[#1949c1] disabled:bg-slate-200 disabled:text-slate-400"
              type="submit"
              aria-label="전송"
              disabled={chatLoading || !chatInput.trim() || !filters}
            >
              <Send size={15} />
            </button>
          </form>
        </div>

        <div>
          <form onSubmit={handleKeywordSearchSubmit} className="mb-4 flex items-center gap-1.5 rounded-full border border-slate-200 bg-white p-1.5 pl-4 shadow-[0_1px_2px_rgba(20,30,60,.04)] transition focus-within:border-[#2457d6] focus-within:ring-4 focus-within:ring-[#2457d6]/10">
            <Search size={16} className="text-slate-400" />
            <input
              className="min-w-0 flex-1 border-none bg-transparent py-2.5 text-[14px] text-ink outline-none placeholder:text-slate-400"
              placeholder="정책명/내용 검색"
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              disabled={!filters}
            />
            <button type="submit" className="shrink-0 rounded-full bg-[#2457d6] px-5 py-2.5 text-[13px] font-extrabold text-white transition hover:bg-[#1949c1] disabled:bg-slate-200" disabled={!filters}>
              검색
            </button>
          </form>

          <div className="mb-4 flex items-center justify-between">
            <div className="text-[15px] font-extrabold text-ink">
              맞춤 검색 결과: <span className="text-[#2457d6]">{total}개</span>
            </div>
            <label className="flex items-center gap-2 text-[12px] font-bold text-slate-500">
              <input type="checkbox" checked={includeClosed} onChange={handleToggleIncludeClosed} className="h-4 w-4 accent-[#2457d6]" />
              마감된 정책도 보기
            </label>
          </div>

          {resultsError && <p className="text-[13px] font-bold text-rose-500">{resultsError}</p>}
          {resultsLoading && <p className="text-[13px] text-slate-400">불러오는 중...</p>}
          {!resultsLoading && items.length === 0 && !resultsError && (
            <div className="rounded-2xl border border-dashed border-slate-300 p-10 text-center text-[13px] font-bold text-slate-400">조건에 맞는 정책이 없습니다.</div>
          )}

          <div className="grid gap-3">
            {items.map((item, i) => {
              const state = analysis[item.policy_key];
              return (
                <div key={i} className="rounded-2xl border border-slate-200/80 bg-white p-5 transition hover:border-[#cddafb] hover:shadow-[0_14px_30px_rgba(28,50,88,.07)]">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[15px] font-extrabold tracking-[-.03em] text-ink">{item.policy_name}</span>
                    <StatusPill status={item.status} />
                  </div>
                  <div className="mt-1.5 text-[11px] font-semibold text-slate-400">{item.large_category}</div>
                  <div className="mt-1 text-[11px] font-semibold text-slate-400">신청 기간 {item.application_period}</div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <PolicyDetailLink url={item.reference_url} />
                    <button
                      type="button"
                      className="inline-flex items-center gap-1.5 rounded-full border border-[#2457d6] px-3 py-1.5 text-[11px] font-extrabold text-[#2457d6] transition hover:bg-[#2457d6] hover:text-white disabled:opacity-50"
                      disabled={state?.loading}
                      onClick={() => handleAnalyze(item.policy_key)}
                    >
                      <Sparkles size={12} />
                      {state?.loading ? "분석 중..." : state?.result ? (state.open ? "AI 분석 리포트 접기" : "AI 분석 리포트 다시 보기") : "AI 분석 리포트 보기"}
                    </button>
                  </div>
                  {state?.error && <p className="mt-2 text-[12px] font-bold text-rose-500">{state.error}</p>}
                  {state?.loading && (
                    <div className="mt-3 flex items-center gap-2 rounded-xl bg-[#f7f9fc] px-3.5 py-3 text-[12px] text-slate-500">
                      <span>AI가 리포트를 생성하고 있어요...</span>
                      <span className="flex items-center gap-1">
                        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
                        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
                        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
                      </span>
                    </div>
                  )}
                  {state?.open && state.result && (
                    <div className="mt-3 rounded-xl bg-[#f7f9fc] p-4 text-[13px] leading-relaxed">
                      <div className="flex items-center gap-2">
                        <span className={`h-3 w-3 rounded-full ${state.result.fit === "적합" ? "bg-[#1eb8a6]" : "bg-rose-400"}`} />
                        <span className="font-extrabold text-ink">{state.result.fit}</span>
                      </div>
                      {state.result.fit === "부적합" && state.result.concerns && (
                        <div className="mt-2.5">
                          <div className="text-[11px] font-extrabold text-slate-400">우려되는 지점</div>
                          <div className="mt-0.5 text-slate-600">{state.result.concerns}</div>
                        </div>
                      )}
                      <div className="mt-2.5">
                        <div className="text-[11px] font-extrabold text-slate-400">예상 혜택</div>
                        <div className="mt-0.5 text-slate-600">{state.result.benefit_summary}</div>
                        {state.result.estimated_monthly_benefit_krw != null && (
                          <div className="mt-2 flex flex-wrap items-center gap-2">
                            <span className="inline-flex items-center gap-1.5 text-[13px] font-extrabold text-ink">
                              <WalletCards size={14} className="text-[#159c8d]" />
                              예상 월 혜택: {state.result.estimated_monthly_benefit_krw.toLocaleString()}원
                            </span>
                            <button
                              type="button"
                              className="inline-flex items-center gap-1.5 rounded-full border border-[#2457d6] px-3 py-1.5 text-[11px] font-extrabold text-[#2457d6] transition hover:bg-[#2457d6] hover:text-white disabled:opacity-60"
                              disabled={state.linking || state.linked}
                              onClick={() => handleLinkBenefit(item)}
                            >
                              {state.linked ? (
                                <>
                                  <Check size={12} /> 저축플랜에 반영됨
                                </>
                              ) : state.linking ? (
                                "반영 중..."
                              ) : (
                                "저축플랜에 반영하기"
                              )}
                            </button>
                          </div>
                        )}
                      </div>
                      <div className="mt-2.5">
                        <div className="text-[11px] font-extrabold text-slate-400">신청 시 유의사항</div>
                        <div className="mt-0.5 text-slate-600">{state.result.application_notes}</div>
                        {state.result.required_documents.length > 0 && (
                          <ul className="mt-1.5 list-disc pl-5 text-slate-600">
                            {state.result.required_documents.map((doc, i) => (
                              <li key={i} className="mt-0.5">
                                {doc}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <Pagination page={page} totalPages={totalPages} onPageChange={handlePageChange} />
        </div>
      </div>
    </DashboardLayout>
  );
}
