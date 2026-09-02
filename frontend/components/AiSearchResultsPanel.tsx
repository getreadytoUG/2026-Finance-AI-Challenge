"use client";

import { Search, Sparkles, WalletCards } from "lucide-react";
import AiSearchFilterBar from "@/components/AiSearchFilterBar";
import Pagination from "@/components/Pagination";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import StatusPill from "@/components/StatusPill";
import type { AiPolicySearchState } from "@/lib/useAiPolicySearch";
import type { PolicyBrowseItem } from "@/lib/api";

// compact=true는 추천 탭 캘린더 뷰의 4칸 레이아웃용 축소 스타일 — /ai-search 페이지는
// 기본값(compact=false, 넉넉한 폭)을 쓴다.
// onSelectPolicy가 있으면(=/ai-search의 새 "전체보기" 화면) 카드 전체가 클릭 가능해지고
// 카드별 "AI 분석 리포트 보기" 펼침 분석은 렌더링하지 않는다(정책별 챗봇으로 대체됐으므로).
// 없으면(=RecommendationCalendar) 기존 펼침 분석 동작을 그대로 유지한다.
// hideFilterBar가 true면 이 컴포넌트 안에서는 AiSearchFilterBar를 렌더링하지 않는다
// — RecommendationCalendar가 캘린더 위에 필터바를 넓게 따로 배치할 때 쓴다
// (사용자 요청, 2026-09-02: "필터기능은 달력 위에 길게 늘려라").
export default function AiSearchResultsPanel({
  state,
  compact = false,
  onSelectPolicy,
  hideFilterBar = false,
}: {
  state: AiPolicySearchState;
  compact?: boolean;
  onSelectPolicy?: (item: PolicyBrowseItem) => void;
  hideFilterBar?: boolean;
}) {
  const {
    keywordInput,
    setKeywordInput,
    handleKeywordSearchSubmit,
    total,
    resultsError,
    resultsLoading,
    items,
    analysis,
    handleAnalyze,
    page,
    totalPages,
    handlePageChange,
  } = state;

  // 2026-09-02 QA에서 발견: 위 AI 챗봇(자연어) 입력창과 이 단순 키워드 검색창을
  // 실제로 혼동하기 쉬웠다 — "정책명/내용 검색"이라는 placeholder만으로는 "이건
  // 문장이 아니라 키워드로만 매칭된다"는 게 잘 안 와닿았다. 소제목으로 구분을
  // 강조하고, 결과가 0건일 때 AI 챗봇 쪽으로 안내한다.
  const showAiChatHint = !resultsLoading && items.length === 0 && keywordInput.trim().length > 0;

  return (
    <div className={compact ? "flex h-full flex-col" : undefined}>
      <div className="mb-1.5 shrink-0 text-[11px] font-extrabold uppercase tracking-[.08em] text-slate-400">
        키워드로 직접 검색
      </div>
      <form
        onSubmit={handleKeywordSearchSubmit}
        className="mb-4 flex shrink-0 items-center gap-1.5 rounded-full border border-slate-200 bg-white p-1.5 pl-4 shadow-[0_1px_2px_rgba(20,30,60,.04)] transition focus-within:border-[#2457d6] focus-within:ring-4 focus-within:ring-[#2457d6]/10"
      >
        <Search size={16} className="text-slate-400" />
        <input
          className="min-w-0 flex-1 border-none bg-transparent py-2.5 text-[14px] text-ink outline-none placeholder:text-slate-400"
          placeholder="정책명 일부만 입력 (문장 X)"
          value={keywordInput}
          onChange={(e) => setKeywordInput(e.target.value)}
          disabled={!state.filters}
        />
        <button type="submit" className="shrink-0 rounded-full bg-[#2457d6] px-5 py-2.5 text-[13px] font-extrabold text-white transition hover:bg-[#1949c1] disabled:bg-slate-200" disabled={!state.filters}>
          검색
        </button>
      </form>

      {!hideFilterBar && <AiSearchFilterBar state={state} compact={compact} />}

      <div className={`mb-4 shrink-0 ${compact ? "text-[13px]" : "text-[15px]"} font-extrabold text-ink`}>
        맞춤 검색 결과: <span className="text-[#2457d6]">{total}개</span>
      </div>

      <div className={compact ? "flex-1" : undefined}>
        {resultsError && <p className="text-[13px] font-bold text-rose-500">{resultsError}</p>}
        {resultsLoading && <p className="text-[13px] text-slate-400">불러오는 중...</p>}
        {!resultsLoading && items.length === 0 && !resultsError && (
          <div className="rounded-2xl border border-dashed border-slate-300 p-10 text-center text-[13px] font-bold text-slate-400">
            조건에 맞는 정책이 없습니다.
            {showAiChatHint && (
              <p className="mt-2 text-[12px] font-semibold text-slate-400">
                문장으로 물어보고 싶다면 이 키워드 검색 대신 AI 챗봇에게 말해보세요.
              </p>
            )}
          </div>
        )}

        <div className="grid gap-3">
          {items.map((item, i) => (
            <ResultCard
              key={i}
              item={item}
              state={analysis[item.policy_key]}
              onAnalyze={() => handleAnalyze(item.policy_key)}
              compact={compact}
              onSelectPolicy={onSelectPolicy}
            />
          ))}
        </div>
      </div>

      <Pagination page={page} totalPages={totalPages} onPageChange={handlePageChange} />
    </div>
  );
}

export function ResultCard({
  item,
  state,
  onAnalyze,
  compact,
  onSelectPolicy,
}: {
  item: PolicyBrowseItem;
  state: AiPolicySearchState["analysis"][string] | undefined;
  onAnalyze: () => void;
  compact: boolean;
  onSelectPolicy?: (item: PolicyBrowseItem) => void;
}) {
  return (
    <div
      className={`rounded-2xl border border-slate-200/80 bg-white transition hover:border-[#cddafb] hover:shadow-[0_14px_30px_rgba(28,50,88,.07)] ${compact ? "p-4" : "p-5"} ${
        onSelectPolicy ? "cursor-pointer" : ""
      }`}
      onClick={onSelectPolicy ? () => onSelectPolicy(item) : undefined}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className={`font-extrabold tracking-[-.03em] text-ink ${compact ? "line-clamp-2 text-[13px]" : "text-[15px]"}`}>{item.policy_name}</span>
        <StatusPill status={item.status} />
      </div>
      <div className="mt-1.5 text-[11px] font-semibold text-slate-400">{item.large_category}</div>
      <div className="mt-1 text-[11px] font-semibold text-slate-400">신청 기간 {item.application_period}</div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span onClick={onSelectPolicy ? (e) => e.stopPropagation() : undefined}>
          <PolicyDetailLink url={item.reference_url} />
        </span>
        {onSelectPolicy ? (
          <span className="inline-flex items-center gap-1.5 text-[11px] font-extrabold text-[#2457d6]">
            <Sparkles size={12} />이 정책 물어보기 →
          </span>
        ) : (
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-full border border-[#2457d6] px-3 py-1.5 text-[11px] font-extrabold text-[#2457d6] transition hover:bg-[#2457d6] hover:text-white disabled:opacity-50"
            disabled={state?.loading}
            onClick={onAnalyze}
          >
            <Sparkles size={12} />
            {state?.loading ? "분석 중..." : state?.result ? (state.open ? "AI 분석 리포트 접기" : "AI 분석 리포트 다시 보기") : "AI 분석 리포트 보기"}
          </button>
        )}
      </div>
      {!onSelectPolicy && state?.error && <p className="mt-2 text-[12px] font-bold text-rose-500">{state.error}</p>}
      {!onSelectPolicy && state?.loading && (
        <div className="mt-3 flex items-center gap-2 rounded-xl bg-[#f7f9fc] px-3.5 py-3 text-[12px] text-slate-500">
          <span>AI가 리포트를 생성하고 있어요...</span>
          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
          </span>
        </div>
      )}
      {!onSelectPolicy && state?.open && state.result && (
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
              <div className="mt-2">
                <span className="inline-flex items-center gap-1.5 text-[13px] font-extrabold text-ink">
                  <WalletCards size={14} className="text-[#159c8d]" />
                  예상 월 혜택: {state.result.estimated_monthly_benefit_krw.toLocaleString()}원
                </span>
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
}
