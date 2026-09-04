import { useEffect, useRef, useState } from "react";
import {
  analyzePolicy,
  fetchAiSearchResults,
  getMe,
  sendAiSearchMessage,
  type AiSearchFilters,
  type PolicyAnalysisResult,
  type PolicyBrowseItem,
  type PolicyChatMessage,
} from "@/lib/api";
import { occupationLabel } from "@/lib/profileOptions";

export type ChatTurn = { role: "user" | "assistant"; content: string };

export type AnalysisState = {
  loading: boolean;
  result: PolicyAnalysisResult | null;
  error: string | null;
  open: boolean;
};

const WELCOME_MESSAGE: ChatTurn = {
  role: "assistant",
  content: "안녕하세요! 지금은 회원님 정보 기준으로 정책을 보여드리고 있어요. 조건을 말씀해주시면 오른쪽 결과가 실시간으로 바뀝니다.",
};

const SUGGESTED_QUESTIONS = ["서울 지역 정책만 보여줘", "미혼 대상 정책만 보여줘", "창업 지원 정책 찾아줘", "마감 임박한 것만 보여줘"];

function filterChips(filters: AiSearchFilters): { key: keyof AiSearchFilters; label: string }[] {
  const chips: { key: keyof AiSearchFilters; label: string }[] = [];
  if (filters.age != null) chips.push({ key: "age", label: `${filters.age}세` });
  if (filters.is_married != null) chips.push({ key: "is_married", label: filters.is_married ? "기혼" : "미혼" });
  if (filters.region) chips.push({ key: "region", label: filters.region });
  if (filters.occupation) chips.push({ key: "occupation", label: occupationLabel(filters.occupation) });
  if (filters.category) chips.push({ key: "category", label: filters.category });
  if (filters.keyword) chips.push({ key: "keyword", label: `"${filters.keyword}"` });
  if (filters.status) chips.push({ key: "status", label: filters.status });
  if (filters.disability_target) chips.push({ key: "disability_target", label: "장애인 대상" });
  if (filters.veteran_target) chips.push({ key: "veteran_target", label: "보훈대상자 대상" });
  return chips;
}

// ai-search 페이지의 "AI 챗봇 + 조건 검색 결과" 기능 전체를 캡슐화한 훅. /ai-search
// 페이지와 추천 탭(캘린더 뷰) 양쪽에서 똑같은 상태/로직을 재사용하기 위해 페이지
// 컴포넌트에서 분리했다 — 렌더링은 각 화면이 원하는 레이아웃대로 따로 한다
// (AiSearchChatPanel/AiSearchResultsPanel 참고). pageSize는 호출하는 화면이 정한다 —
// 추천 탭 캘린더는 캘린더/챗봇과 높이를 맞추려고 4개, /ai-search는 기존대로 10개.
//
// clientPaginate=true면 매 페이지 이동마다 서버를 다시 호출하지 않고, 조건이 바뀔
// 때 한 번에 전체 결과를 받아두고("다음"은 이미 받아둔 배열을 slice만 한다).
// 추천 탭 캘린더가 이 모드를 쓴다 — (1) 페이지 넘길 때마다 CachedPolicy 풀스캔
// 왕복이 생겨 버벅였고, (2) 캘린더 마감일 표시(byDay)가 "현재 페이지 4건"에서만
// 만들어져 전체 마감일이 안 찍혔다. 두 문제를 같이 해결한다. /ai-search 페이지는
// 결과가 매우 많을 수 있어 기존 서버 페이지네이션(clientPaginate=false)을 유지한다.
const FETCH_ALL_PAGE_SIZE = 1000;

export function useAiPolicySearch(pageSize: number = 10, opts: { clientPaginate?: boolean } = {}) {
  const { clientPaginate = false } = opts;
  const fetchPageSize = clientPaginate ? FETCH_ALL_PAGE_SIZE : pageSize;
  const [filters, setFilters] = useState<AiSearchFilters | null>(null);
  // clientPaginate=false: rawItems가 곧 화면에 뿌리는 현재 페이지.
  // clientPaginate=true: allItems에 전체를 담고, 화면용 items는 아래에서 slice한다.
  const [rawItems, setRawItems] = useState<PolicyBrowseItem[]>([]);
  const [allItems, setAllItems] = useState<PolicyBrowseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [includeClosed, setIncludeClosed] = useState(false);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Record<string, AnalysisState>>({});
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
          occupation: profile.occupation,
          is_sme_employee: profile.is_sme_employee,
        };
        setFilters(initial);
        return refetch(initial, 1, false);
      })
      .catch((err) => setResultsError(err instanceof Error ? err.message : "정보를 불러오지 못했습니다."));
    // refetch가 pageSize를 캡처하지만, pageSize는 호출부(ai-search 페이지/추천
    // 캘린더)가 마운트 시점에 한 번 정해서 넘기는 값이라 컴포넌트 생애주기 동안
    // 안 바뀐다 — 최초 1회만 실행하는 이 effect에 넣을 필요가 없다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refetch(nextFilters: AiSearchFilters, nextPage: number, nextIncludeClosed: boolean) {
    setResultsLoading(true);
    setResultsError(null);
    try {
      const token = localStorage.getItem("token") ?? "";
      // clientPaginate면 조건이 바뀔 때마다 1페이지째로 전량을 받아둔다 — 이후
      // 페이지 이동은 handlePageChange가 네트워크 없이 slice만 바꾼다.
      const res = await fetchAiSearchResults(
        token,
        nextFilters,
        nextIncludeClosed,
        clientPaginate ? 1 : nextPage,
        fetchPageSize
      );
      if (clientPaginate) {
        setAllItems(res.items);
        // FETCH_ALL_PAGE_SIZE로 한 번에 다 못 받은 경우(총 결과가 그보다 많음)엔
        // 받은 만큼만 total로 잡아 존재하지 않는 뒷페이지를 만들지 않는다.
        if (res.total > res.items.length) {
          console.warn(`[useAiPolicySearch] total=${res.total} > fetched=${res.items.length}; FETCH_ALL_PAGE_SIZE를 늘려야 할 수 있음`);
        }
        setTotal(Math.min(res.total, res.items.length));
        setPage(nextPage);
      } else {
        setRawItems(res.items);
        setTotal(res.total);
        setPage(res.page);
      }
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

  // 채팅으로 조건을 "말해야만" 바뀌는 게 아니라, 드롭다운/칩을 직접 클릭해서도
  // 바로 바뀌도록 하는 범용 setter(사용자 요청, 2026-09-02) — handleRemoveChip과
  // 달리 여러 필드를 한 번에 바꿀 수도 있고 null이 아닌 값도 넣을 수 있다.
  function handleSetFilters(patch: Partial<AiSearchFilters>) {
    if (!filters) return;
    const next = { ...filters, ...patch };
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
      occupation: null,
      is_sme_employee: null,
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
    if (clientPaginate) {
      // 이미 전량을 받아뒀으므로 네트워크 없이 slice 기준점만 옮긴다.
      setPage(nextPage);
      return;
    }
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
      [policyKey]: { loading: true, result: null, error: null, open: true },
    }));
    try {
      const token = localStorage.getItem("token") ?? "";
      const result = await analyzePolicy(token, policyKey);
      setAnalysis((prev) => ({
        ...prev,
        [policyKey]: { loading: false, result, error: null, open: true },
      }));
    } catch (err) {
      setAnalysis((prev) => ({
        ...prev,
        [policyKey]: {
          loading: false,
          result: null,
          error: err instanceof Error ? err.message : "분석 리포트를 불러오지 못했습니다.",
          open: true,
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
      const history: PolicyChatMessage[] = nextTurns.filter((t) => t !== WELCOME_MESSAGE).map((t) => ({ role: t.role, content: t.content }));
      const res = await sendAiSearchMessage(token, history, filters, includeClosed, fetchPageSize);
      setTurns((prev) => [...prev, { role: "assistant", content: res.reply }]);
      setFilters(res.filters);
      if (clientPaginate) {
        setAllItems(res.items);
        setTotal(Math.min(res.total, res.items.length));
        setPage(1);
      } else {
        setRawItems(res.items);
        setTotal(res.total);
        setPage(res.page);
      }
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

  // 화면에 뿌리는 현재 페이지. clientPaginate면 전량(allItems)에서 직접 잘라낸다.
  const items = clientPaginate ? allItems.slice((page - 1) * pageSize, page * pageSize) : rawItems;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const chips = filters ? filterChips(filters) : [];
  const showSuggestions = turns.length === 1 && !chatLoading;

  return {
    // chat panel
    turns,
    chatInput,
    setChatInput,
    chatLoading,
    chatError,
    listRef,
    textareaRef,
    resizeTextarea,
    chips,
    showSuggestions,
    suggestedQuestions: SUGGESTED_QUESTIONS,
    sendText,
    handleSend,
    handleInputKeyDown,
    handleRemoveChip,
    handleSetFilters,
    handleResetFilters,
    filters,
    // results panel
    items,
    // clientPaginate 모드에서만 채워지는 "조건에 맞는 전체 결과" — 캘린더가 전체
    // 마감일을 계산하는 데 쓴다(현재 페이지 items로는 4건만 보였음).
    allItems,
    total,
    totalPages,
    page,
    includeClosed,
    resultsLoading,
    resultsError,
    keywordInput,
    setKeywordInput,
    handleKeywordSearchSubmit,
    handleToggleIncludeClosed,
    handlePageChange,
    analysis,
    handleAnalyze,
  };
}

export type AiPolicySearchState = ReturnType<typeof useAiPolicySearch>;
