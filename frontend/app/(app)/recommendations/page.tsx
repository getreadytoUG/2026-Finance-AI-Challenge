"use client";

import { useEffect, useState } from "react";
import { getMe, getRecommendations, refreshRecommendations, updateProfile } from "@/lib/api";
import type { Recommendation, UserProfile } from "@/lib/api";

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
  const [income, setIncome] = useState("40000000");
  const [region, setRegion] = useState("서울");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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
        annual_income_krw: Number(income),
        region,
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "추천 갱신에 실패했습니다.");
    } finally {
      setLoading(false);
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
              <span className="field-label">연소득 (원)</span>
              <input className="input" type="number" value={income} onChange={(e) => setIncome(e.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">지역</span>
              <input className="input" type="text" value={region} onChange={(e) => setRegion(e.target.value)} />
            </label>
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
            <div className="result-list">
              {recommendations.map((rec, i) => (
                <div key={i} className="result-item">
                  <div className="result-item-title">{rec.policy_name}</div>
                  <div className="result-item-row">
                    <span>지원 내용</span>
                    <span>{rec.benefit_description}</span>
                  </div>
                  <div className="result-item-row">
                    <span>신청 기간</span>
                    <span>{rec.application_period}</span>
                  </div>
                  <div style={{ marginTop: 12 }}>
                    <a className="link" href={rec.reference_url} target="_blank" rel="noreferrer">
                      자세히 보기 →
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}
