"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import AiSearchChatPanel from "@/components/AiSearchChatPanel";
import AiSearchFilterBar from "@/components/AiSearchFilterBar";
import AiSearchResultsPanel from "@/components/AiSearchResultsPanel";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import StatusPill from "@/components/StatusPill";
import { useAiPolicySearch } from "@/lib/useAiPolicySearch";
import type { PolicyBrowseItem } from "@/lib/api";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function monthPrefix(year: number, month: number): string {
  // month는 0-indexed
  return `${year}${pad2(month + 1)}`;
}

function DayItemRow({ item }: { item: PolicyBrowseItem }) {
  return (
    <div className="rounded-xl border border-slate-200/80 bg-white p-3">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[13px] font-extrabold tracking-[-.02em] text-ink">{item.policy_name}</span>
        <StatusPill status={item.status} />
      </div>
      <p className="mt-1 line-clamp-2 text-[11px] leading-5 text-slate-500">{item.benefit_description}</p>
      <div className="mt-1 text-[10px] font-semibold text-slate-400">신청 기간 {item.application_period}</div>
      <PolicyDetailLink url={item.reference_url} className="mt-1 text-[12px]" />
    </div>
  );
}

// AI 분석 리포트 탭의 챗봇+검색결과를 그대로 이식한 3칸 구성: AI 챗봇 | 캘린더 | 검색결과.
// 세 패널이 같은 useAiPolicySearch 훅 인스턴스를 공유하므로, 챗봇에서 건 필터가 곧
// 캘린더에 꽂히는 날짜 데이터와 오른쪽 검색결과 둘 다에 동일하게 반영된다(사용자 요청).
// 그래서 캘린더는 더 이상 "내 추천 알림"이 아니라 "지금 AI 검색 결과 중 마감일이
// 있는 것들"을 보여준다 — 원래의 개인화 추천 목록(읽음/안읽음 포함)은 "리스트" 탭에
// 그대로 남아있다.
export default function RecommendationCalendar() {
  // 챗봇/캘린더/검색결과 세 칸의 높이를 똑같이 맞추기 위해, 검색결과를 4개씩
  // 페이지네이션한다(카드 4개 높이가 이 세 칸 전체 높이의 기준이 된다).
  const aiSearch = useAiPolicySearch(4);
  const today = useMemo(() => new Date(), []);
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth()); // 0-indexed
  const [selectedDay, setSelectedDay] = useState<string | null>(null); // "YYYYMMDD"

  const items = aiSearch.items;

  const byDay = useMemo(() => {
    const map = new Map<string, PolicyBrowseItem[]>();
    for (const item of items) {
      if (!item.apply_end_ymd) continue;
      const list = map.get(item.apply_end_ymd) ?? [];
      list.push(item);
      map.set(item.apply_end_ymd, list);
    }
    return map;
  }, [items]);

  const alwaysOpen = useMemo(() => items.filter((item) => !item.apply_end_ymd), [items]);

  const prefix = monthPrefix(viewYear, viewMonth);
  const firstOfMonth = new Date(viewYear, viewMonth, 1);
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const leadingBlanks = firstOfMonth.getDay();

  const cells: Array<{ day: number; ymd: string } | null> = [
    ...Array.from({ length: leadingBlanks }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) => ({ day: i + 1, ymd: `${prefix}${pad2(i + 1)}` })),
  ];

  const todayYmd = `${today.getFullYear()}${pad2(today.getMonth() + 1)}${pad2(today.getDate())}`;

  function goToMonth(delta: number) {
    const next = new Date(viewYear, viewMonth + delta, 1);
    setViewYear(next.getFullYear());
    setViewMonth(next.getMonth());
    setSelectedDay(null);
  }

  function selectDay(ymd: string) {
    setSelectedDay(ymd);
  }

  const selectedItems = selectedDay ? (byDay.get(selectedDay) ?? []) : [];

  return (
    <div>
      {/* 예전엔 오른쪽 검색결과 칸 안(좁은 폭)에 끼어 있었는데, 캘린더 위로 꺼내
          한 줄로 넓게 펼친다(사용자 요청, 2026-09-02) — 검색결과 패널에는
          hideFilterBar로 중복 렌더링을 막는다. */}
      <AiSearchFilterBar state={aiSearch} />
      <div className="grid gap-4 xl:grid-cols-2 2xl:grid-cols-[320px_minmax(440px,1.4fr)_minmax(300px,0.7fr)]">
        <AiSearchChatPanel state={aiSearch} compact />

        <div className="flex flex-col rounded-[22px] border border-slate-200/80 bg-white p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="text-[15px] font-extrabold tracking-[-.03em] text-ink">
              {viewYear}년 {viewMonth + 1}월
            </div>
            <div className="flex gap-1">
              <button
                type="button"
                onClick={() => goToMonth(-1)}
                className="grid h-8 w-8 place-items-center rounded-lg bg-[#eef3f9] text-slate-500 transition hover:bg-[#e3eaf6]"
                aria-label="이전 달"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                type="button"
                onClick={() => goToMonth(1)}
                className="grid h-8 w-8 place-items-center rounded-lg bg-[#eef3f9] text-slate-500 transition hover:bg-[#e3eaf6]"
                aria-label="다음 달"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-1.5 text-center text-[11px] font-extrabold text-slate-400">
            {WEEKDAYS.map((w) => (
              <div key={w} className="pb-1">
                {w}
              </div>
            ))}
          </div>
          {/* auto-rows-fr + flex-1: 날짜 칸 자체가 늘어난 카드 높이만큼 커진다 —
              이전엔 칸은 h-16 고정이고 뒤쪽 흰 배경만 늘어나서 빈 공간이 생겼었다. */}
          <div className="grid flex-1 auto-rows-fr grid-cols-7 gap-1.5">
            {cells.map((cell, i) => {
              if (!cell) return <div key={`blank-${i}`} className="h-full" />;
              const dayItems = byDay.get(cell.ymd) ?? [];
              const isToday = cell.ymd === todayYmd;
              const isSelected = cell.ymd === selectedDay;
              return (
                <button
                  type="button"
                  key={cell.ymd}
                  onClick={() => (dayItems.length > 0 ? selectDay(cell.ymd) : undefined)}
                  disabled={dayItems.length === 0}
                  title={dayItems.map((item) => item.policy_name).join(", ")}
                  className={`flex h-full flex-col items-center justify-center gap-0.5 rounded-xl px-1 py-1 text-center transition ${
                    isSelected
                      ? "bg-[#2457d6] text-white"
                      : isToday
                        ? "bg-[#eef3ff] text-[#2457d6]"
                        : dayItems.length > 0
                          ? "bg-[#fff2e4] text-[#d27a21] hover:bg-[#ffe6cc]"
                          : "text-slate-300"
                  }`}
                >
                  <span className="text-[12px] font-bold">{cell.day}</span>
                  {/* 예전엔 마감일이 있다는 걸 점(dot)으로만 표시했는데, 어떤 정책인지
                      누르기 전엔 알 수 없었다 — 첫 정책명을 칸 안에 바로 보여준다. */}
                  {dayItems.length > 0 && (
                    <span className="line-clamp-2 w-full break-keep text-[9px] font-semibold leading-[1.2]">
                      {dayItems[0].policy_name}
                      {dayItems.length > 1 && ` 외 ${dayItems.length - 1}건`}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="mt-4">
            {selectedDay ? (
              <>
                <div className="mb-2 flex items-center justify-between">
                  <div className="text-[12px] font-extrabold text-ink">
                    {selectedDay.slice(4, 6)}월 {selectedDay.slice(6, 8)}일 마감 ({selectedItems.length})
                  </div>
                  <button type="button" onClick={() => setSelectedDay(null)} className="text-[11px] font-bold text-[#2457d6] hover:underline">
                    전체보기
                  </button>
                </div>
                <div className="grid gap-2">
                  {selectedItems.map((item) => (
                    <DayItemRow key={item.policy_key} item={item} />
                  ))}
                </div>
              </>
            ) : (
              alwaysOpen.length > 0 && (
                <p className="text-[11px] font-semibold text-slate-400">
                  상시 모집 {alwaysOpen.length}건은 마감일이 없어 캘린더에 표시되지 않아요 — 오른쪽 검색결과에서 확인하세요.
                </p>
              )
            )}
          </div>
        </div>

        <AiSearchResultsPanel state={aiSearch} compact hideFilterBar />
      </div>
    </div>
  );
}
