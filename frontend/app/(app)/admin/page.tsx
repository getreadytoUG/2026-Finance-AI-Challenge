"use client";

import { useEffect, useState } from "react";
import { getAdminOverview, type AdminOverview } from "@/lib/api";
import AdminGuard from "@/components/AdminGuard";
import { KpiCard, formatDateTime } from "@/components/AdminWidgets";

function OverviewContent() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getAdminOverview(token)
      .then(setOverview)
      .catch((err) => setError(err instanceof Error ? err.message : "불러오지 못했습니다."));
  }, []);

  return (
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
