"use client";

import { useState } from "react";
import { ChevronLeft } from "lucide-react";
import AiSearchResultsPanel from "@/components/AiSearchResultsPanel";
import PolicyDetailPanel from "@/components/PolicyDetailPanel";
import PolicyQaChatPanel from "@/components/PolicyQaChatPanel";
import { useAiPolicySearch } from "@/lib/useAiPolicySearch";
import type { PolicyBrowseItem } from "@/lib/api";

// 2026-09-01 UPGRADE.md 반영: "AI 분석 리포트"는 독립 탭이 아니라 "정책 달력"
// 안의 "AI 정책 검색" 서브탭으로 흡수됐다(recommendations/page.tsx 참고).
// 같은 날 사용자 재지시로 "한눈에보기(미리보기) → 전체보기 클릭" 단계를 없애고,
// 서브탭에 들어가자마자 바로 검색 가능한 전체 목록이 뜨도록 단순화했다 — 정책을
// 클릭하면 그 정책 전용 챗봇이 옆에 뜨는 상세 화면으로만 전환한다. "정책 달력"의
// 왼쪽 범용 챗봇(RecommendationCalendar)과는 완전히 별개의 useAiPolicySearch
// 인스턴스를 쓴다 — 문서의 "기존 챗봇은 그대로 냅두기"를 만족시키기 위해서다.
export default function AiPolicySearchSection() {
  const state = useAiPolicySearch();
  const [selectedItem, setSelectedItem] = useState<PolicyBrowseItem | null>(null);

  if (selectedItem) {
    return (
      <div>
        <button
          type="button"
          onClick={() => setSelectedItem(null)}
          className="mb-4 inline-flex items-center gap-1 text-[12px] font-extrabold text-slate-500 hover:text-[#2457d6]"
        >
          <ChevronLeft size={15} /> 목록으로
        </button>
        <div className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
          <PolicyDetailPanel item={selectedItem} />
          <PolicyQaChatPanel item={selectedItem} />
        </div>
      </div>
    );
  }

  return <AiSearchResultsPanel state={state} onSelectPolicy={setSelectedItem} />;
}
