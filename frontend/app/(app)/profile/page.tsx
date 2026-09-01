"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { deleteAccount, getMe, updateProfile, type ProfileInput, type UserProfile } from "@/lib/api";
import { krwToManwon, maritalStatusLabel, employmentTypeLabel, housingStatusLabel, occupationLabel } from "@/lib/profileOptions";
import { DashboardLayout } from "@/components/DashboardLayout";
import ProfileFieldsForm from "@/components/ProfileFieldsForm";

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [showWithdrawConfirm, setShowWithdrawConfirm] = useState(false);
  const [withdrawPassword, setWithdrawPassword] = useState("");
  const [withdrawing, setWithdrawing] = useState(false);
  const [withdrawError, setWithdrawError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((me) => setProfile(me))
      .catch((err) => setError(err instanceof Error ? err.message : "정보를 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, []);

  function startEditing() {
    setSaved(false);
    setError(null);
    setEditing(true);
  }

  async function handleSave(input: ProfileInput) {
    setError(null);
    const token = localStorage.getItem("token") ?? "";
    const updated = await updateProfile(token, input);
    setProfile(updated);
    setEditing(false);
    setSaved(true);
  }

  function handleLogout() {
    localStorage.removeItem("token");
    router.push("/login");
  }

  async function handleWithdraw(e: React.FormEvent) {
    e.preventDefault();
    setWithdrawError(null);
    setWithdrawing(true);
    try {
      const token = localStorage.getItem("token") ?? "";
      await deleteAccount(token, profile?.provider === "local" ? withdrawPassword : undefined);
      localStorage.removeItem("token");
      router.push("/login");
    } catch (err) {
      setWithdrawError(err instanceof Error ? err.message : "탈퇴에 실패했습니다.");
    } finally {
      setWithdrawing(false);
    }
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
          <InfoRow
            label="혼인 여부"
            value={profile.marital_status ? maritalStatusLabel(profile.marital_status) : profile.is_married ? "기혼" : "미혼"}
          />
          {profile.marital_status === "newlywed" && profile.marriage_years != null && (
            <InfoRow label="신혼 연차" value={`${profile.marriage_years}년차`} />
          )}
          {(profile.is_married || profile.marital_status === "engaged") && (
            <>
              <InfoRow label="배우자 나이" value={profile.spouse_age != null ? `${profile.spouse_age}세` : "-"} />
              <InfoRow
                label="배우자 연소득"
                value={profile.spouse_annual_income_krw != null ? `${krwToManwon(profile.spouse_annual_income_krw).toLocaleString()}만원` : "-"}
              />
              <InfoRow label="배우자 직업 구분" value={occupationLabel(profile.spouse_occupation)} />
            </>
          )}
          <InfoRow label="자녀 수" value={profile.children_count != null ? `${profile.children_count}명` : "-"} />
          <InfoRow label="임신 여부" value={profile.is_pregnant ? "임신 중" : "-"} />
          <InfoRow label="거주 지역" value={profile.region ?? "-"} />
          <InfoRow label="희망 지역" value={profile.desired_region ?? "-"} />
          <InfoRow label="연소득" value={profile.annual_income_krw != null ? `${krwToManwon(profile.annual_income_krw).toLocaleString()}만원` : "-"} />
          <InfoRow label="직업 구분" value={occupationLabel(profile.occupation)} />
          <InfoRow label="근로 형태" value={employmentTypeLabel(profile.employment_type)} />
          <InfoRow label="중소기업 재직 여부" value={profile.is_sme_employee ? "재직 중" : "-"} />
          <InfoRow label="무주택 여부" value={housingStatusLabel(profile.housing_status)} />
          <InfoRow label="순자산" value={profile.net_worth_krw != null ? `${krwToManwon(profile.net_worth_krw).toLocaleString()}만원` : "-"} />
          <InfoRow
            label="월 저축 가능 여력"
            value={profile.monthly_savings_capacity_krw != null ? `${krwToManwon(profile.monthly_savings_capacity_krw).toLocaleString()}만원` : "-"}
          />
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
          <ProfileFieldsForm initial={profile} submitLabel="저장" submittingLabel="저장 중..." onSubmit={handleSave} />
          <button
            type="button"
            onClick={() => {
              setEditing(false);
              setError(null);
            }}
            className="mt-3 h-11 rounded-xl border border-slate-200 bg-white px-6 text-[13px] font-extrabold text-slate-600 transition hover:border-slate-300"
          >
            취소
          </button>
        </div>
      )}

      <div className="mt-5 rounded-[22px] border border-slate-200/80 bg-white p-6">
        <div className="flex gap-2">
          <button onClick={handleLogout} className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-[12px] font-extrabold text-slate-600 transition hover:border-slate-300">
            로그아웃
          </button>
          <button
            onClick={() => {
              setShowWithdrawConfirm(true);
              setWithdrawError(null);
              setWithdrawPassword("");
            }}
            className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-[12px] font-extrabold text-rose-500 transition hover:border-rose-300"
          >
            회원탈퇴
          </button>
        </div>

        {showWithdrawConfirm && (
          <form onSubmit={handleWithdraw} className="mt-4 rounded-xl border border-rose-200 bg-rose-50/60 p-4">
            <p className="text-[13px] font-extrabold text-rose-600">정말 탈퇴하시겠어요?</p>
            <p className="mt-1 text-[12px] leading-5 text-slate-600">
              계정과 저장된 정보(추천 기록 등)가 모두 삭제되며 되돌릴 수 없습니다.
            </p>
            {profile?.provider === "local" && (
              <label className="mt-3 grid gap-1.5 text-[12px] font-extrabold text-slate-700">
                본인 확인을 위해 비밀번호를 입력해주세요
                <input
                  type="password"
                  value={withdrawPassword}
                  onChange={(e) => setWithdrawPassword(e.target.value)}
                  required
                  className="h-11 w-full max-w-xs rounded-xl border border-slate-200 bg-white px-4 text-[13px] font-semibold outline-none focus:border-rose-400 focus:ring-4 focus:ring-rose-400/10"
                />
              </label>
            )}
            {withdrawError && <p className="mt-2 text-[12px] font-bold text-rose-500">{withdrawError}</p>}
            <div className="mt-3 flex gap-2">
              <button
                type="submit"
                disabled={withdrawing}
                className="h-10 rounded-xl bg-rose-500 px-5 text-[12px] font-extrabold text-white transition hover:bg-rose-600 disabled:opacity-50"
              >
                {withdrawing ? "탈퇴 처리 중..." : "탈퇴하기"}
              </button>
              <button
                type="button"
                onClick={() => setShowWithdrawConfirm(false)}
                disabled={withdrawing}
                className="h-10 rounded-xl border border-slate-200 bg-white px-5 text-[12px] font-extrabold text-slate-600 transition hover:border-slate-300 disabled:opacity-50"
              >
                취소
              </button>
            </div>
          </form>
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
