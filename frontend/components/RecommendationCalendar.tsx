"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { SectionLabel } from "@/components/DashboardLayout";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import StatusPill from "@/components/StatusPill";
import type { Recommendation } from "@/lib/api";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function monthPrefix(year: number, month: number): string {
  // month는 0-indexed
  return `${year}${pad2(month + 1)}`;
}

function RecommendationCard({ rec }: { rec: Recommendation }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[15px] font-extrabold tracking-[-.03em] text-ink">{rec.policy_name}</span>
        <StatusPill status={rec.status} />
      </div>
      <p className="mt-2 text-[12px] leading-5 text-slate-500">{rec.benefit_description}</p>
      <div className="mt-2 text-[11px] font-semibold text-slate-400">신청 기간 {rec.application_period}</div>
      <PolicyDetailLink url={rec.reference_url} className="mt-2" />
    </div>
  );
}

export default function RecommendationCalendar({ recommendations }: { recommendations: Recommendation[] }) {
  const today = useMemo(() => new Date(), []);
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth()); // 0-indexed
  const [selectedDay, setSelectedDay] = useState<string | null>(null); // "YYYYMMDD"

  const alwaysOpen = useMemo(() => recommendations.filter((r) => !r.apply_end_ymd), [recommendations]);

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

  const selectedList = selectedDay ? (byDay.get(selectedDay) ?? []) : [];

  return (
    <div>
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
                onClick={() => setSelectedDay(dayRecs.length > 0 ? cell.ymd : null)}
                disabled={dayRecs.length === 0}
                className={`flex aspect-square flex-col items-center justify-center gap-1 rounded-xl text-[12px] font-bold transition ${
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

      {selectedDay && (
        <div className="mt-6">
          <SectionLabel>{selectedDay.slice(4, 6)}월 {selectedDay.slice(6, 8)}일 마감 정책</SectionLabel>
          <div className="grid gap-3">
            {selectedList.map((rec) => (
              <RecommendationCard key={rec.id} rec={rec} />
            ))}
          </div>
        </div>
      )}

      {alwaysOpen.length > 0 && (
        <div className="mt-6">
          <SectionLabel>상시 모집 정책 ({alwaysOpen.length})</SectionLabel>
          <div className="grid gap-3">
            {alwaysOpen.map((rec) => (
              <RecommendationCard key={rec.id} rec={rec} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
