"use client";

import { useEffect, useState } from "react";
import { browsePolicies, getPolicyCategories } from "@/lib/api";
import type { PolicyBrowseItem, PolicyCategory } from "@/lib/api";

const PAGE_SIZE = 20;

export default function BrowsePage() {
  const [categories, setCategories] = useState<PolicyCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [items, setItems] = useState<PolicyBrowseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getPolicyCategories(token)
      .then((res) => setCategories(res.categories))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    setLoading(true);
    setError(null);
    browsePolicies(token, { category: selectedCategory ?? undefined, page, pageSize: PAGE_SIZE })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "정책을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, [selectedCategory, page]);

  function handleSelectCategory(name: string | null) {
    setSelectedCategory(name);
    setPage(1);
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <div className="page-header">
        <h1>📖 정책 읽기</h1>
        <p>조건 입력 없이 전체 정책을 카테고리별로 둘러보세요.</p>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20 }}>
        <button
          className="btn-ghost"
          onClick={() => handleSelectCategory(null)}
          style={{
            borderRadius: 999,
            background: selectedCategory === null ? "var(--primary-tint)" : undefined,
            color: selectedCategory === null ? "var(--primary)" : undefined,
          }}
        >
          전체
        </button>
        {categories.map((c) => (
          <button
            key={c.name}
            className="btn-ghost"
            onClick={() => handleSelectCategory(c.name)}
            style={{
              borderRadius: 999,
              background: selectedCategory === c.name ? "var(--primary-tint)" : undefined,
              color: selectedCategory === c.name ? "var(--primary)" : undefined,
            }}
          >
            {c.name} ({c.count})
          </button>
        ))}
      </div>

      {error && <p className="error-text">{error}</p>}
      {loading && <p>불러오는 중...</p>}
      {!loading && items.length === 0 && !error && <p className="error-text">해당하는 정책이 없습니다.</p>}

      <div className="result-list">
        {items.map((item, i) => (
          <div key={i} className="result-item">
            <div className="result-item-title">
              {item.status_emoji} {item.policy_name}
            </div>
            <div className="result-item-row">
              <span>분야</span>
              <span>{item.large_category}</span>
            </div>
            <div className="result-item-row">
              <span>상태</span>
              <span>{item.status}</span>
            </div>
            <div className="result-item-row">
              <span>신청 기간</span>
              <span>{item.application_period}</span>
            </div>
            <div style={{ marginTop: 12 }}>
              <a className="link" href={item.reference_url} target="_blank" rel="noreferrer">
                자세히 보기 →
              </a>
            </div>
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 20 }}>
          <button className="btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            이전
          </button>
          <span style={{ alignSelf: "center", fontSize: 13, color: "var(--text-muted)" }}>
            {page} / {totalPages}
          </span>
          <button className="btn-ghost" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            다음
          </button>
        </div>
      )}
    </>
  );
}
