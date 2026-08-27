"use client";

import { useEffect, useState } from "react";
import { getAdminPolicyList, getPolicyCategories, type AdminPolicyItem, type PolicyCategory } from "@/lib/api";
import AdminGuard from "@/components/AdminGuard";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import Pagination from "@/components/Pagination";
import { ExpandableCell, formatDateTime } from "@/components/AdminWidgets";

const PAGE_SIZE = 20;

const STATUS_OPTIONS = ["임박", "여유", "상시", "예정", "만료"];

function PoliciesListContent() {
  const [categories, setCategories] = useState<PolicyCategory[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const [items, setItems] = useState<AdminPolicyItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getPolicyCategories(token)
      .then((res) => setCategories(res.categories))
      .catch(() => {});
  }, []);

  function load(nextPage: number, nextKeyword: string, nextCategory: string | null, nextStatus: string | null) {
    setLoading(true);
    setError(null);
    const token = localStorage.getItem("token") ?? "";
    getAdminPolicyList(token, {
      keyword: nextKeyword || undefined,
      category: nextCategory ?? undefined,
      status: nextStatus ?? undefined,
      page: nextPage,
      pageSize: PAGE_SIZE,
    })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
        setPage(res.page);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load(1, keyword, category, status);
  }, [keyword, category, status]);

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setKeyword(keywordInput.trim());
  }

  function handleSelectCategory(name: string) {
    setCategory((prev) => (prev === name ? null : name));
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="card">
      <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input
          className="input"
          placeholder="정책명 검색"
          value={keywordInput}
          onChange={(e) => setKeywordInput(e.target.value)}
          style={{ maxWidth: 280 }}
        />
        <button type="submit" className="btn-ghost">
          검색
        </button>
      </form>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
        {categories.map((c) => (
          <button
            key={c.name}
            type="button"
            className="btn-ghost"
            onClick={() => handleSelectCategory(c.name)}
            style={{
              borderRadius: 999,
              fontSize: 12,
              borderColor: category === c.name ? "var(--primary)" : undefined,
              color: category === c.name ? "var(--primary)" : undefined,
            }}
          >
            {c.name} ({c.count})
          </button>
        ))}
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 16 }}>
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            type="button"
            className="btn-ghost"
            onClick={() => setStatus((prev) => (prev === s ? null : s))}
            style={{
              borderRadius: 999,
              fontSize: 12,
              borderColor: status === s ? "var(--primary)" : undefined,
              color: status === s ? "var(--primary)" : undefined,
            }}
          >
            {s}
          </button>
        ))}
      </div>

      <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 12 }}>총 {total}건</div>

      {error && <p className="error-text">{error}</p>}
      {loading && <p>불러오는 중...</p>}

      {!loading && items.length > 0 && (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>정책명</th>
                <th>정책 내용</th>
                <th>분야</th>
                <th>상태</th>
                <th>신청 기간</th>
                <th>지역 코드</th>
                <th>링크</th>
                <th>갱신 시각</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.policy_key}>
                  <td>{p.policy_name}</td>
                  <td>
                    <ExpandableCell text={p.description} maxLength={30} />
                  </td>
                  <td>{p.large_category}</td>
                  <td>{p.status}</td>
                  <td>{p.application_period}</td>
                  <td>
                    <ExpandableCell text={p.region_code} maxLength={20} />
                  </td>
                  <td>
                    <PolicyDetailLink url={p.apply_url} style={{ fontSize: 12 }} />
                  </td>
                  <td>{formatDateTime(p.refreshed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Pagination page={page} totalPages={totalPages} onPageChange={(next) => load(next, keyword, category, status)} />
    </div>
  );
}

export default function AdminPoliciesListPage() {
  return (
    <AdminGuard>
      <div className="page-header">
        <h1>📋 정책 목록</h1>
        <p>캐시된 정책을 검색하고 개별 데이터를 확인하세요.</p>
      </div>
      <PoliciesListContent />
    </AdminGuard>
  );
}
