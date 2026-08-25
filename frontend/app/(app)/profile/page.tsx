"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getMe, updateProfile, type UserProfile } from "@/lib/api";
import {
  OCCUPATION_OPTIONS,
  REGIONS,
  krwToManwon,
  manwonToKrw,
  occupationLabel,
  type OccupationType,
} from "@/lib/profileOptions";

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [showWithdrawNotice, setShowWithdrawNotice] = useState(false);
  const router = useRouter();

  const [age, setAge] = useState("");
  const [income, setIncome] = useState("");
  const [occupation, setOccupation] = useState<OccupationType | "">("");
  const [region, setRegion] = useState<string | null>(null);
  const [isMarried, setIsMarried] = useState(false);
  const [spouseAge, setSpouseAge] = useState("");
  const [spouseIncome, setSpouseIncome] = useState("");
  const [spouseOccupation, setSpouseOccupation] = useState<OccupationType | "">("");

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((me) => {
        setProfile(me);
        fillFormFrom(me);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "정보를 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, []);

  function fillFormFrom(me: UserProfile) {
    setAge(me.age?.toString() ?? "");
    setIncome(me.annual_income_krw != null ? String(krwToManwon(me.annual_income_krw)) : "");
    setOccupation(me.occupation ?? "");
    setRegion(me.region ?? null);
    setIsMarried(me.is_married ?? false);
    setSpouseAge(me.spouse_age?.toString() ?? "");
    setSpouseIncome(
      me.spouse_annual_income_krw != null ? String(krwToManwon(me.spouse_annual_income_krw)) : ""
    );
    setSpouseOccupation(me.spouse_occupation ?? "");
  }

  function startEditing() {
    if (profile) fillFormFrom(profile);
    setSaved(false);
    setError(null);
    setEditing(true);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!region || !occupation) return;
    setSaving(true);
    setError(null);
    try {
      const token = localStorage.getItem("token") ?? "";
      const updated = await updateProfile(token, {
        age: Number(age),
        is_married: isMarried,
        annual_income_krw: manwonToKrw(Number(income)),
        region,
        occupation,
        spouse_age: isMarried && spouseAge ? Number(spouseAge) : null,
        spouse_annual_income_krw: isMarried && spouseIncome ? manwonToKrw(Number(spouseIncome)) : null,
        spouse_occupation: isMarried && spouseOccupation ? spouseOccupation : null,
      });
      setProfile(updated);
      setEditing(false);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("token");
    router.push("/login");
  }

  if (loading) return null;

  return (
    <>
      <div className="page-header">
        <h1>👤 내 정보</h1>
        <p>가입 시 입력한 정보를 확인하고 수정할 수 있습니다.</p>
      </div>

      {error && <p className="error-text">{error}</p>}
      {saved && !editing && (
        <p style={{ color: "var(--success)", fontSize: 13, marginBottom: 12 }}>저장되었습니다.</p>
      )}

      {profile && !editing && (
        <div className="card">
          <InfoRow label="이메일" value={profile.email} />
          <InfoRow label="나이" value={profile.age != null ? `${profile.age}세` : "-"} />
          <InfoRow
            label="연소득"
            value={profile.annual_income_krw != null ? `${krwToManwon(profile.annual_income_krw).toLocaleString()}만원` : "-"}
          />
          <InfoRow label="직업 구분" value={occupationLabel(profile.occupation)} />
          <InfoRow label="지역" value={profile.region ?? "-"} />
          <InfoRow label="기혼 여부" value={profile.is_married ? "기혼" : "미혼"} />
          {profile.is_married && (
            <>
              <InfoRow label="배우자 나이" value={profile.spouse_age != null ? `${profile.spouse_age}세` : "-"} />
              <InfoRow
                label="배우자 연소득"
                value={
                  profile.spouse_annual_income_krw != null
                    ? `${krwToManwon(profile.spouse_annual_income_krw).toLocaleString()}만원`
                    : "-"
                }
              />
              <InfoRow label="배우자 직업 구분" value={occupationLabel(profile.spouse_occupation)} />
            </>
          )}
          <button className="btn" style={{ marginTop: 8 }} onClick={startEditing}>
            정보 수정
          </button>
        </div>
      )}

      {profile && editing && (
        <div className="card">
          <form onSubmit={handleSave}>
            <label className="field">
              <span className="field-label">나이</span>
              <input className="input" type="number" min={0} value={age} onChange={(e) => setAge(e.target.value)} required />
            </label>
            <label className="field">
              <span className="field-label">연소득 (만원)</span>
              <input
                className="input"
                type="number"
                min={0}
                value={income}
                onChange={(e) => setIncome(e.target.value)}
                required
              />
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

            <span className="field-label" style={{ display: "block" }}>
              지역
            </span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
              {REGIONS.map((r) => (
                <button
                  key={r}
                  type="button"
                  className="btn-ghost"
                  onClick={() => setRegion(r)}
                  style={{
                    borderRadius: 999,
                    background: region === r ? "var(--primary-tint)" : undefined,
                    color: region === r ? "var(--primary)" : undefined,
                  }}
                >
                  {r}
                </button>
              ))}
            </div>

            <label className="checkbox-field">
              <input type="checkbox" checked={isMarried} onChange={(e) => setIsMarried(e.target.checked)} />
              기혼
            </label>

            {isMarried && (
              <div
                style={{
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  padding: 16,
                  marginBottom: 16,
                }}
              >
                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-muted)", marginBottom: 12 }}>
                  배우자 정보 (선택)
                </p>
                <label className="field">
                  <span className="field-label">배우자 나이</span>
                  <input
                    className="input"
                    type="number"
                    min={0}
                    value={spouseAge}
                    onChange={(e) => setSpouseAge(e.target.value)}
                  />
                </label>
                <label className="field">
                  <span className="field-label">배우자 연소득 (만원)</span>
                  <input
                    className="input"
                    type="number"
                    min={0}
                    value={spouseIncome}
                    onChange={(e) => setSpouseIncome(e.target.value)}
                  />
                </label>
                <span className="field-label" style={{ display: "block" }}>
                  배우자 직업 구분
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {OCCUPATION_OPTIONS.map((o) => (
                    <button
                      key={o.value}
                      type="button"
                      className="btn-ghost"
                      onClick={() => setSpouseOccupation(o.value)}
                      style={{
                        borderRadius: 999,
                        background: spouseOccupation === o.value ? "var(--primary-tint)" : undefined,
                        color: spouseOccupation === o.value ? "var(--primary)" : undefined,
                      }}
                    >
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {error && <p className="error-text">{error}</p>}
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn" type="submit" disabled={saving || !region || !occupation}>
                {saving ? "저장 중..." : "저장"}
              </button>
              <button
                className="btn btn-ghost"
                type="button"
                style={{ width: "auto" }}
                onClick={() => {
                  setEditing(false);
                  setError(null);
                }}
              >
                취소
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <button className="btn btn-ghost" style={{ width: "auto" }} onClick={handleLogout}>
            로그아웃
          </button>
          <button
            className="btn btn-ghost"
            style={{ width: "auto", color: "var(--danger)" }}
            onClick={() => setShowWithdrawNotice(true)}
          >
            회원탈퇴
          </button>
        </div>
        {showWithdrawNotice && (
          <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
            * 회원탈퇴는 아직 구현되지 않은 기능입니다. (현재 별도 DB 저장소가 없어 계정 삭제 로직이 연결되어 있지 않습니다)
          </p>
        )}
      </div>
    </>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="result-item-row" style={{ marginTop: 0, marginBottom: 12 }}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
