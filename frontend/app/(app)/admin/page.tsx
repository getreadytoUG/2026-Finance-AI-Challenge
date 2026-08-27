"use client";

import { useEffect, useState } from "react";
import { getAdminOverview, getAdminSignupTrend, type AdminOverview, type AdminSignupTrendResponse } from "@/lib/api";
import AdminGuard from "@/components/AdminGuard";
import { DashboardLayout } from "@/components/DashboardLayout";
import { BarRow, KpiCard, formatDateTime } from "@/components/AdminWidgets";

const TONES = ["blue", "mint", "violet"] as const;

function formatShortDate(iso: string): string {
  const [, month, day] = iso.split("-");
  return `${month}/${day}`;
}

function OverviewContent() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [trend, setTrend] = useState<AdminSignupTrendResponse | null>(null);
  const [trendError, setTrendError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getAdminOverview(token)
      .then(setOverview)
      .catch((err) => setError(err instanceof Error ? err.message : "불러오지 못했습니다."));
    getAdminSignupTrend(token, 14)
      .then(setTrend)
      .catch((err) => setTrendError(err instanceof Error ? err.message : "불러오지 못했습니다."));
  }, []);

  const maxTrendCount = trend ? Math.max(1, ...trend.points.map((p) => p.count)) : 1;

  const kpis = overview
    ? [
        { label: "전체 회원 수", value: overview.total_users },
        { label: "기혼 회원 수", value: overview.married_users },
        { label: "캐시된 정책 수", value: overview.total_policies },
        { label: "마감된 정책 수", value: overview.policies_expired },
        { label: "링크 없는 정책 수", value: overview.policies_missing_link },
        { label: "전국형(추정) 정책 수", value: overview.nationwide_template_policies },
        { label: "총 추천 알림 수", value: overview.total_recommendations },
        { label: "안 읽은 추천 알림", value: overview.unread_recommendations },
        { label: "정책 캐시 마지막 갱신", value: formatDateTime(overview.last_cache_refreshed_at) },
      ]
    : [];

  return (
    <>
      {error && <p className="text-[13px] font-bold text-rose-500">{error}</p>}
      {!overview && !error && <p className="text-[13px] text-slate-400">불러오는 중...</p>}
      {overview && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {kpis.map((kpi, i) => (
            <KpiCard key={kpi.label} label={kpi.label} value={kpi.value} tone={TONES[i % TONES.length]} />
          ))}
        </div>
      )}

      <div className="mt-6 rounded-[22px] border border-slate-200/80 bg-white p-6">
        <div className="text-[15px] font-extrabold text-ink">최근 14일 가입 추이</div>
        {trendError && <p className="mt-2 text-[13px] font-bold text-rose-500">{trendError}</p>}
        {!trend && !trendError && <p className="mt-2 text-[13px] text-slate-400">불러오는 중...</p>}
        {trend && (
          <>
            <p className="mb-4 mt-1 text-[12px] text-slate-400">
              가입일 정보가 없는 회원 {trend.unknown_signup_date_count}명은 집계에서 제외했습니다(기능 추가 이전 가입자).
            </p>
            {trend.points.map((p) => (
              <BarRow key={p.date} label={formatShortDate(p.date)} count={p.count} max={maxTrendCount} />
            ))}
          </>
        )}
      </div>
    </>
  );
}

export default function AdminOverviewPage() {
  return (
    <AdminGuard>
      <DashboardLayout eyebrow="ADMIN" title="개요">
        <OverviewContent />
      </DashboardLayout>
    </AdminGuard>
  );
}
