"use client";

import { useEffect, useState } from "react";
import { getAdminOverview, getAdminSignupTrend, type AdminOverview, type AdminSignupTrendResponse } from "@/lib/api";
import AdminGuard from "@/components/AdminGuard";
import { BarRow, KpiCard, formatDateTime } from "@/components/AdminWidgets";

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

  return (
    <>
      <div className="card">
        {error && <p className="error-text">{error}</p>}
        {!overview && !error && <p>불러오는 중...</p>}
        {overview && (
          <div className="admin-kpi-grid">
            <KpiCard label="전체 회원 수" value={overview.total_users} />
            <KpiCard label="기혼 회원 수" value={overview.married_users} />
            <KpiCard label="캐시된 정책 수" value={overview.total_policies} />
            <KpiCard label="마감된 정책 수" value={overview.policies_expired} />
            <KpiCard label="링크 없는 정책 수" value={overview.policies_missing_link} />
            <KpiCard label="전국형(추정) 정책 수" value={overview.nationwide_template_policies} />
            <KpiCard label="총 추천 알림 수" value={overview.total_recommendations} />
            <KpiCard label="안 읽은 추천 알림" value={overview.unread_recommendations} />
            <KpiCard label="정책 캐시 마지막 갱신" value={formatDateTime(overview.last_cache_refreshed_at)} />
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div style={{ fontWeight: 700, marginBottom: 4 }}>최근 14일 가입 추이</div>
        {trendError && <p className="error-text">{trendError}</p>}
        {!trend && !trendError && <p>불러오는 중...</p>}
        {trend && (
          <>
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 16 }}>
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
      <div className="page-header">
        <h1>📊 개요</h1>
        <p>서비스 전체 현황을 한눈에 확인하세요.</p>
      </div>
      <OverviewContent />
    </AdminGuard>
  );
}
