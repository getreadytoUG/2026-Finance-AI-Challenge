"use client";

import { useEffect, useState } from "react";
import { browsePolicies, getPolicyCategories } from "@/lib/api";
import type { PolicyBrowseItem, PolicyCategory } from "@/lib/api";

const PAGE_SIZE = 20;

const STATUS_COLORS: Record<string, string> = {
  임박: "var(--accent)",
  여유: "var(--success)",
  상시: "var(--primary)",
  예정: "var(--text-muted)",
  만료: "var(--danger)",
};

function StatusDot({ status }: { status: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 10,
        height: 10,
        borderRadius: "50%",
        background: STATUS_COLORS[status] ?? "var(--text-muted)",
        marginRight: 6,
      }}
    />
  );
}

export default function BrowsePage() {
  const [categories, setCategories] = useState<PolicyCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [items, setItems] = useState<PolicyBrowseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [pageInput, setPageInput] = useState("1");
  const [includeClosed, setIncludeClosed] = useState(false);

  useEffect(() => {
    setPageInput(String(page));
  }, [page]);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getPolicyCategories(token, { includeClosed })
      .then((res) => setCategories(res.categories))
      .catch(() => {});
  }, [includeClosed]);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    setLoading(true);
    setError(null);
    browsePolicies(token, { category: selectedCategory ?? undefined, page, pageSize: PAGE_SIZE, includeClosed })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "정책을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, [selectedCategory, page, includeClosed]);

  function handleSelectCategory(name: string | null) {
    setSelectedCategory(name);
    setPage(1);
  }

  function handleToggleIncludeClosed() {
    setIncludeClosed((v) => !v);
    setPage(1);
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function commitPageInput() {
    const parsed = Number(pageInput);
    if (Number.isInteger(parsed) && parsed >= 1 && parsed <= totalPages) {
      setPage(parsed);
    } else {
      setPageInput(String(page));
    }
  }

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

      <label className="checkbox-field">
        <input type="checkbox" checked={includeClosed} onChange={handleToggleIncludeClosed} />
        마감된 정책도 보기
      </label>

      {error && <p className="error-text">{error}</p>}
      {loading && <p>불러오는 중...</p>}
      {!loading && items.length === 0 && !error && <p className="error-text">해당하는 정책이 없습니다.</p>}

      <div className="result-list">
        {items.map((item, i) => (
          <div key={i} className="result-item">
            <div className="result-item-title">
              <StatusDot status={item.status} />
              {item.policy_name}
            </div>
            <div className="result-item-row">
              <span>분야</span>
              <span>{item.large_category}</span>
            </div>
            <div className="result-item-row">
              <span>상태</span>
              <span style={{ display: "inline-flex", alignItems: "center" }}>
                <StatusDot status={item.status} />
                {item.status}
              </span>
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
          <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13, color: "var(--text-muted)" }}>
            <input
              className="input"
              type="number"
              min={1}
              max={totalPages}
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              onBlur={commitPageInput}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  commitPageInput();
                }
              }}
              style={{ width: 52, textAlign: "center", padding: "4px 6px" }}
            />
            <span>/ {totalPages}</span>
          </span>
          <button className="btn-ghost" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            다음
          </button>
        </div>
      )}
    </>
  );
}
