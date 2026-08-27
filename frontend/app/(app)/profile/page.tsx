"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { PiggyBank } from "lucide-react";
import {
  getMe,
  listSavingsLinkedBenefits,
  unlinkSavingsBenefit,
  updateProfile,
  type LinkedBenefit,
  type UserProfile,
} from "@/lib/api";
import {
  OCCUPATION_OPTIONS,
  REGIONS,
  krwToManwon,
  manwonToKrw,
  occupationLabel,
  type OccupationType,
} from "@/lib/profileOptions";
import { DashboardLayout } from "@/components/DashboardLayout";

function pillClass(active: boolean) {
  return `rounded-lg px-3.5 py-2 text-[11px] font-extrabold transition ${
    active ? "bg-[#2457d6] text-white" : "bg-[#eef3f9] text-slate-500 hover:bg-[#e3eaf6]"
  }`;
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [showWithdrawNotice, setShowWithdrawNotice] = useState(false);
  const [linkedBenefits, setLinkedBenefits] = useState<LinkedBenefit[]>([]);
  const [totalLinkedBenefitKrw, setTotalLinkedBenefitKrw] = useState(0);
  const [unlinkingId, setUnlinkingId] = useState<number | null>(null);
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

    listSavingsLinkedBenefits(token)
      .then((res) => {
        setLinkedBenefits(res.items);
        setTotalLinkedBenefitKrw(res.total_monthly_benefit_krw);
      })
      .catch(() => {});
  }, []);

  async function handleUnlinkBenefit(id: number) {
    setUnlinkingId(id);
    try {
      const token = localStorage.getItem("token") ?? "";
      await unlinkSavingsBenefit(token, id);
      setLinkedBenefits((prev) => {
        const next = prev.filter((b) => b.id !== id);
        setTotalLinkedBenefitKrw(next.reduce((sum, b) => sum + b.estimated_monthly_benefit_krw, 0));
        return next;
      });
    } finally {
      setUnlinkingId(null);
    }
  }

  function fillFormFrom(me: UserProfile) {
    setAge(me.age?.toString() ?? "");
    setIncome(me.annual_income_krw != null ? String(krwToManwon(me.annual_income_krw)) : "");
    setOccupation(me.occupation ?? "");
    setRegion(me.region ?? null);
    setIsMarried(me.is_married ?? false);
    setSpouseAge(me.spouse_age?.toString() ?? "");
    setSpouseIncome(me.spouse_annual_income_krw != null ? String(krwToManwon(me.spouse_annual_income_krw)) : "");
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
    <DashboardLayout eyebrow="MY PROFILE" title="내 정보">
      {error && <p className="mb-4 text-[13px] font-bold text-rose-500">{error}</p>}
      {saved && !editing && <p className="mb-3 text-[13px] font-bold text-[#159c8d]">저장되었습니다.</p>}

      {profile && !editing && (
        <div className="rounded-[22px] border border-slate-200/80 bg-white p-6">
          <InfoRow label="이메일" value={profile.email} />
          <InfoRow label="나이" value={profile.age != null ? `${profile.age}세` : "-"} />
          <InfoRow label="연소득" value={profile.annual_income_krw != null ? `${krwToManwon(profile.annual_income_krw).toLocaleString()}만원` : "-"} />
          <InfoRow label="직업 구분" value={occupationLabel(profile.occupation)} />
          <InfoRow label="지역" value={profile.region ?? "-"} />
          <InfoRow label="기혼 여부" value={profile.is_married ? "기혼" : "미혼"} />
          {profile.is_married && (
            <>
              <InfoRow label="배우자 나이" value={profile.spouse_age != null ? `${profile.spouse_age}세` : "-"} />
              <InfoRow
                label="배우자 연소득"
                value={profile.spouse_annual_income_krw != null ? `${krwToManwon(profile.spouse_annual_income_krw).toLocaleString()}만원` : "-"}
              />
              <InfoRow label="배우자 직업 구분" value={occupationLabel(profile.spouse_occupation)} />
            </>
          )}
          <button
            onClick={startEditing}
            className="mt-4 h-11 rounded-xl bg-[#2457d6] px-6 text-[13px] font-extrabold text-white shadow-[0_10px_20px_rgba(36,87,214,.18)] transition hover:bg-[#1949c1]"
          >
            정보 수정
          </button>
        </div>
      )}

      {profile && editing && (
        <div className="rounded-[22px] border border-slate-200/80 bg-white p-6">
          <form onSubmit={handleSave} className="grid gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
                나이
                <input
                  type="number"
                  min={0}
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  required
                  className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
                />
              </label>
              <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
                연소득 (만원)
                <input
                  type="number"
                  min={0}
                  value={income}
                  onChange={(e) => setIncome(e.target.value)}
                  required
                  className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
                />
              </label>
            </div>

            <div>
              <div className="mb-2 text-[12px] font-extrabold text-slate-700">직업 구분</div>
              <div className="flex flex-wrap gap-2">
                {OCCUPATION_OPTIONS.map((o) => (
                  <button key={o.value} type="button" className={pillClass(occupation === o.value)} onClick={() => setOccupation(o.value)}>
                    {o.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="mb-2 text-[12px] font-extrabold text-slate-700">지역</div>
              <div className="flex flex-wrap gap-2">
                {REGIONS.map((r) => (
                  <button key={r} type="button" className={pillClass(region === r)} onClick={() => setRegion(r)}>
                    {r}
                  </button>
                ))}
              </div>
            </div>

            <label className="flex items-center gap-2 text-[13px] font-bold text-slate-700">
              <input type="checkbox" checked={isMarried} onChange={(e) => setIsMarried(e.target.checked)} className="h-4 w-4 accent-[#2457d6]" />
              기혼
            </label>

            {isMarried && (
              <div className="rounded-xl bg-[#f5f8fd] p-4">
                <p className="mb-3 text-[12px] font-bold text-slate-500">배우자 정보 (선택)</p>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
                    배우자 나이
                    <input
                      type="number"
                      min={0}
                      value={spouseAge}
                      onChange={(e) => setSpouseAge(e.target.value)}
                      className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6]"
                    />
                  </label>
                  <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
                    배우자 연소득 (만원)
                    <input
                      type="number"
                      min={0}
                      value={spouseIncome}
                      onChange={(e) => setSpouseIncome(e.target.value)}
                      className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6]"
                    />
                  </label>
                </div>
                <div className="mt-3 text-[12px] font-extrabold text-slate-700">배우자 직업 구분</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {OCCUPATION_OPTIONS.map((o) => (
                    <button key={o.value} type="button" className={pillClass(spouseOccupation === o.value)} onClick={() => setSpouseOccupation(o.value)}>
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {error && <p className="text-[13px] font-bold text-rose-500">{error}</p>}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={saving || !region || !occupation}
                className="h-11 rounded-xl bg-[#2457d6] px-6 text-[13px] font-extrabold text-white shadow-[0_10px_20px_rgba(36,87,214,.18)] transition hover:bg-[#1949c1] disabled:opacity-50"
              >
                {saving ? "저장 중..." : "저장"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setEditing(false);
                  setError(null);
                }}
                className="h-11 rounded-xl border border-slate-200 bg-white px-6 text-[13px] font-extrabold text-slate-600 transition hover:border-slate-300"
              >
                취소
              </button>
            </div>
          </form>
        </div>
      )}

      {linkedBenefits.length > 0 && (
        <div className="mt-5 rounded-[22px] border border-slate-200/80 bg-white p-6">
          <div className="mb-4 flex items-baseline justify-between">
            <h3 className="flex items-center gap-2 text-[15px] font-extrabold text-ink">
              <PiggyBank size={16} className="text-[#2457d6]" />
              저축플랜에 반영된 정책
            </h3>
            <span className="text-[13px] font-bold text-slate-400">합계 월 {totalLinkedBenefitKrw.toLocaleString()}원</span>
          </div>
          <div className="grid gap-3">
            {linkedBenefits.map((b) => (
              <div key={b.id} className="flex items-center justify-between rounded-xl bg-[#f7f9fc] px-4 py-3">
                <span className="text-[13px] font-bold text-slate-600">{b.policy_name}</span>
                <span className="flex items-center gap-3">
                  <strong className="text-[13px] font-extrabold text-ink">{b.estimated_monthly_benefit_krw.toLocaleString()}원/월</strong>
                  <button
                    type="button"
                    disabled={unlinkingId === b.id}
                    onClick={() => handleUnlinkBenefit(b.id)}
                    className="text-[12px] font-bold text-[#2457d6] hover:underline disabled:opacity-50"
                  >
                    {unlinkingId === b.id ? "제거 중..." : "제거"}
                  </button>
                </span>
              </div>
            ))}
          </div>
          <Link href="/savings" className="mt-4 inline-block text-[12px] font-extrabold text-[#2457d6] hover:underline">
            저축플랜에서 보기 →
          </Link>
        </div>
      )}

      <div className="mt-5 rounded-[22px] border border-slate-200/80 bg-white p-6">
        <div className="flex gap-2">
          <button onClick={handleLogout} className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-[12px] font-extrabold text-slate-600 transition hover:border-slate-300">
            로그아웃
          </button>
          <button
            onClick={() => setShowWithdrawNotice(true)}
            className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-[12px] font-extrabold text-rose-500 transition hover:border-rose-300"
          >
            회원탈퇴
          </button>
        </div>
        {showWithdrawNotice && (
          <p className="mt-3 text-[12px] text-slate-500">
            * 회원탈퇴는 아직 구현되지 않은 기능입니다. (현재 별도 DB 저장소가 없어 계정 삭제 로직이 연결되어 있지 않습니다)
          </p>
        )}
      </div>
    </DashboardLayout>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 py-3 text-[13px] last:border-0">
      <span className="text-slate-500">{label}</span>
      <strong className="font-extrabold text-ink">{value}</strong>
    </div>
  );
}
