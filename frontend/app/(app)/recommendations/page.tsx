"use client";

import { useEffect, useState } from "react";
import { getMe, getRecommendations, markRecommendationRead, refreshRecommendations, updateProfile } from "@/lib/api";
import type { Recommendation, UserProfile } from "@/lib/api";
import { OCCUPATION_OPTIONS, manwonToKrw, type OccupationType } from "@/lib/profileOptions";
import Pagination from "@/components/Pagination";
import PolicyDetailLink from "@/components/PolicyDetailLink";

const PAGE_SIZE = 10;

function hasCompleteProfile(profile: UserProfile | null): boolean {
  return (
    profile !== null &&
    profile.age !== null &&
    profile.is_married !== null &&
    profile.annual_income_krw !== null &&
    profile.region !== null
  );
}

export default function RecommendationsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[] | null>(null);
  const [age, setAge] = useState("29");
  const [isMarried, setIsMarried] = useState(false);
  const [income, setIncome] = useState("4000");
  const [region, setRegion] = useState("서울");
  const [occupation, setOccupation] = useState<OccupationType>("employee");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  async function loadProfileAndRecommendations() {
    const token = localStorage.getItem("token") ?? "";
    const me = await getMe(token);
    setProfile(me);
    if (hasCompleteProfile(me)) {
      const list = await getRecommendations(token);
      setRecommendations(list.recommendations);
    }
  }

  useEffect(() => {
    loadProfileAndRecommendations().catch((err) => {
      setError(err instanceof Error ? err.message : "불러오기에 실패했습니다.");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleProfileSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      await updateProfile(token, {
        age: Number(age),
        is_married: isMarried,
        annual_income_krw: manwonToKrw(Number(income)),
        region,
        occupation,
      });
      await loadProfileAndRecommendations();
    } catch (err) {
      setError(err instanceof Error ? err.message : "프로필 저장에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh() {
    setError(null);
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      await refreshRecommendations(token);
      const list = await getRecommendations(token);
      setRecommendations(list.recommendations);
      setPage(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "추천 갱신에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function handleItemClick(rec: Recommendation) {
    if (rec.is_read) return;
    const token = localStorage.getItem("token") ?? "";
    try {
      await markRecommendationRead(token, rec.id);
      setRecommendations((prev) => (prev ? prev.map((r) => (r.id === rec.id ? { ...r, is_read: true } : r)) : prev));
    } catch {
      // 읽음 처리 실패는 조용히 무시 — 목록 자체는 이미 정상 표시되어 있다.
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>🔔 맞춤 추천</h1>
        <p>프로필을 저장해두면 매일 새로 맞는 정책을 찾아 알려드립니다.</p>
      </div>

      {error && <p className="error-text" style={{ marginTop: 16 }}>{error}</p>}

      {!hasCompleteProfile(profile) && (
        <div className="card">
          <form onSubmit={handleProfileSubmit}>
            <label className="field">
              <span className="field-label">나이</span>
              <input className="input" type="number" value={age} onChange={(e) => setAge(e.target.value)} />
            </label>
            <label className="checkbox-field">
              <input type="checkbox" checked={isMarried} onChange={(e) => setIsMarried(e.target.checked)} />
              기혼
            </label>
            <label className="field">
              <span className="field-label">연소득 (만원)</span>
              <input className="input" type="number" value={income} onChange={(e) => setIncome(e.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">지역</span>
              <input className="input" type="text" value={region} onChange={(e) => setRegion(e.target.value)} />
            </label>
            <span className="field-label" style={{ display: "block" }}>
              직업 구분
            </span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
              {OCCUPATION_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  className="btn-ghost"
                  onClick={() => setOccupation(o.value)}
                  style={{
                    borderRadius: 999,
                    background: occupation === o.value ? "var(--primary-tint)" : undefined,
                    color: occupation === o.value ? "var(--primary)" : undefined,
                  }}
                >
                  {o.label}
                </button>
              ))}
            </div>
            <button className="btn" type="submit" disabled={loading}>
              {loading ? "저장 중..." : "프로필 저장하고 추천 받기"}
            </button>
          </form>
        </div>
      )}

      {hasCompleteProfile(profile) && (
        <>
          <button className="btn" onClick={handleRefresh} disabled={loading} style={{ marginBottom: 16 }}>
            {loading ? "갱신 중..." : "지금 갱신"}
          </button>

          {recommendations && recommendations.length === 0 && (
            <p className="error-text">아직 추천된 정책이 없습니다. &quot;지금 갱신&quot;을 눌러보세요.</p>
          )}

          {recommendations && recommendations.length > 0 && (
            <>
              <div className="result-list">
                {recommendations.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map((rec) => (
                  <div key={rec.id} className="result-item" onClick={() => handleItemClick(rec)} style={{ cursor: "pointer" }}>
                    <div className="result-item-title">
                      {!rec.is_read && (
                        <span
                          style={{
                            display: "inline-block",
                            width: 8,
                            height: 8,
                            borderRadius: 999,
                            background: "var(--danger)",
                            marginRight: 8,
                          }}
                        />
                      )}
                      {rec.policy_name}
                    </div>
                    <div className="result-item-row">
                      <span>지원 내용</span>
                      <span>{rec.benefit_description}</span>
                    </div>
                    <div className="result-item-row">
                      <span>신청 기간</span>
                      <span>{rec.application_period}</span>
                    </div>
                    <div style={{ marginTop: 12 }}>
                      <PolicyDetailLink url={rec.reference_url} />
                    </div>
                  </div>
                ))}
              </div>
              <Pagination
                page={page}
                totalPages={Math.max(1, Math.ceil(recommendations.length / PAGE_SIZE))}
                onPageChange={setPage}
              />
            </>
          )}
        </>
      )}
    </>
  );
}
