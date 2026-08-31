"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import Pagination from "@/components/Pagination";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import StatusPill from "@/components/StatusPill";
import type { Recommendation } from "@/lib/api";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];
const PAGE_SIZE = 4;

// status.py의 STATUS_ORDER(임박-여유-상시-예정-만료)와 동일한 우선순위.
const STATUS_PRIORITY: Record<string, number> = { 임박: 0, 여유: 1, 상시: 2, 예정: 3, 만료: 4 };

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function monthPrefix(year: number, month: number): string {
  // month는 0-indexed
  return `${year}${pad2(month + 1)}`;
}

function matchesQuery(rec: Recommendation, query: string): boolean {
  if (!query) return true;
  const haystack = (rec.policy_name + rec.benefit_description).toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function RecommendationRow({ rec }: { rec: Recommendation }) {
  return (
    <div className="rounded-xl border border-slate-200/80 bg-white p-3">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[13px] font-extrabold tracking-[-.02em] text-ink">{rec.policy_name}</span>
        <StatusPill status={rec.status} />
      </div>
      {/* 실제 줄 수와 무관하게 항상 2줄 높이를 확보해 카드 높이를 균일하게 유지한다
          (짧은 설명이어도 빈 줄만큼 여백이 생기지만, 4개가 꽉 차 보이는 게 우선순위). */}
      <p className="mt-1 line-clamp-2 min-h-10 text-[11px] leading-5 text-slate-500">{rec.benefit_description}</p>
      <div className="mt-1 text-[10px] font-semibold text-slate-400">신청 기간 {rec.application_period}</div>
      <PolicyDetailLink url={rec.reference_url} className="mt-1 text-[12px]" />
    </div>
  );
}

export default function RecommendationCalendar({ recommendations }: { recommendations: Recommendation[] }) {
  const today = useMemo(() => new Date(), []);
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth()); // 0-indexed
  const [selectedDay, setSelectedDay] = useState<string | null>(null); // "YYYYMMDD"
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => recommendations.filter((r) => matchesQuery(r, query)), [recommendations, query]);

  const byDay = useMemo(() => {
    const map = new Map<string, Recommendation[]>();
    for (const rec of recommendations) {
      if (!rec.apply_end_ymd) continue;
      const list = map.get(rec.apply_end_ymd) ?? [];
      list.push(rec);
      map.set(rec.apply_end_ymd, list);
    }
    return map;
  }, [recommendations]);

  const allSorted = useMemo(
    () => [...filtered].sort((a, b) => (STATUS_PRIORITY[a.status] ?? 9) - (STATUS_PRIORITY[b.status] ?? 9)),
    [filtered]
  );

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
    setPage(1);
  }

  function selectDay(ymd: string) {
    setSelectedDay(ymd);
    setPage(1);
  }

  function clearSelectedDay() {
    setSelectedDay(null);
    setPage(1);
  }

  function handleQueryChange(value: string) {
    setQuery(value);
    setPage(1);
  }

  const selectedList = selectedDay ? (byDay.get(selectedDay) ?? []).filter((r) => matchesQuery(r, query)) : [];
  const activeList = selectedDay ? selectedList : allSorted;
  const totalPages = Math.max(1, Math.ceil(activeList.length / PAGE_SIZE));
  const pageItems = activeList.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px] lg:items-start">
      <div className="rounded-[22px] border border-slate-200/80 bg-white p-5">
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
        <div className="grid grid-cols-7 gap-1.5">
          {cells.map((cell, i) => {
            if (!cell) return <div key={`blank-${i}`} />;
            const dayRecs = byDay.get(cell.ymd) ?? [];
            const isToday = cell.ymd === todayYmd;
            const isSelected = cell.ymd === selectedDay;
            return (
              <button
                type="button"
                key={cell.ymd}
                onClick={() => (dayRecs.length > 0 ? selectDay(cell.ymd) : undefined)}
                disabled={dayRecs.length === 0}
                className={`flex h-24 flex-col items-center justify-center gap-1 rounded-xl text-[12px] font-bold transition ${
                  isSelected
                    ? "bg-[#2457d6] text-white"
                    : isToday
                      ? "bg-[#eef3ff] text-[#2457d6]"
                      : dayRecs.length > 0
                        ? "bg-[#fff2e4] text-[#d27a21] hover:bg-[#ffe6cc]"
                        : "text-slate-300"
                }`}
              >
                {cell.day}
                {dayRecs.length > 0 && (
                  <span className={`h-1.5 w-1.5 rounded-full ${isSelected ? "bg-white" : "bg-[#d27a21]"}`} />
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="rounded-[22px] border border-slate-200/80 bg-white p-4">
        <div className="relative mb-2.5">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={15} />
          <input
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            placeholder="정책명, 지원 내용으로 검색"
            className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-[12px] font-semibold outline-none transition focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
          />
        </div>

        <div className="mb-2 flex items-center justify-between">
          <div className="text-[12px] font-extrabold text-ink">
            {selectedDay ? `${selectedDay.slice(4, 6)}월 ${selectedDay.slice(6, 8)}일 마감 (${activeList.length})` : `전체 추천 (${activeList.length})`}
          </div>
          {selectedDay && (
            <button type="button" onClick={clearSelectedDay} className="text-[11px] font-bold text-[#2457d6] hover:underline">
              전체보기
            </button>
          )}
        </div>

        <div className="grid gap-2">
          {pageItems.length === 0 ? (
            <p className="text-[12px] font-bold text-slate-400">검색 조건에 맞는 정책이 없어요.</p>
          ) : (
            pageItems.map((rec) => <RecommendationRow key={rec.id} rec={rec} />)
          )}
        </div>

        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      </div>
    </div>
  );
}
