"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Check, CircleHelp, ShieldCheck } from "lucide-react";
import { signup, login, checkEmailAvailable } from "@/lib/api";
import PasswordField from "@/components/PasswordField";
import SocialLoginButtons from "@/components/SocialLoginButtons";
import { BrandMark } from "@/components/BrandMark";
import { OCCUPATION_OPTIONS, REGIONS, manwonToKrw, type OccupationType } from "@/lib/profileOptions";

function pillClass(active: boolean) {
  return `rounded-lg px-3.5 py-2 text-[11px] font-extrabold transition ${
    active ? "bg-[#2457d6] text-white" : "bg-[#eef3f9] text-slate-500 hover:bg-[#e3eaf6]"
  }`;
}

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [age, setAge] = useState("");
  const [income, setIncome] = useState("");
  const [occupation, setOccupation] = useState<OccupationType | "">("");
  const [region, setRegion] = useState<string | null>(null);
  const [isMarried, setIsMarried] = useState(false);
  const [spouseAge, setSpouseAge] = useState("");
  const [spouseIncome, setSpouseIncome] = useState("");
  const [spouseOccupation, setSpouseOccupation] = useState<OccupationType | "">("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [emailCheckStatus, setEmailCheckStatus] = useState<"idle" | "checking" | "available" | "taken">("idle");
  const router = useRouter();

  async function handleCheckEmail() {
    if (!email) return;
    setEmailCheckStatus("checking");
    try {
      const available = await checkEmailAvailable(email);
      setEmailCheckStatus(available ? "available" : "taken");
    } catch {
      setEmailCheckStatus("idle");
      setError("이메일 확인에 실패했습니다. 다시 시도해주세요.");
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!region || !occupation || emailCheckStatus !== "available") return;
    setError(null);
    setLoading(true);
    try {
      await signup({
        email,
        password,
        age: Number(age),
        is_married: isMarried,
        annual_income_krw: manwonToKrw(Number(income)),
        region,
        occupation,
        spouse_age: isMarried && spouseAge ? Number(spouseAge) : null,
        spouse_annual_income_krw: isMarried && spouseIncome ? manwonToKrw(Number(spouseIncome)) : null,
        spouse_occupation: isMarried && spouseOccupation ? spouseOccupation : null,
      });
      const token = await login(email, password);
      localStorage.setItem("token", token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "회원가입에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f7f9fc] text-ink">
      <header className="border-b border-slate-100 bg-white">
        <div className="mx-auto flex max-w-[1180px] items-center justify-between px-5 py-4 lg:px-0">
          <Link href="/">
            <BrandMark size="sm" />
          </Link>
          <Link href="/login" className="text-[13px] font-bold text-slate-500">
            이미 계정이 있나요? <span className="text-[#2457d6]">로그인</span>
          </Link>
        </div>
      </header>
      <main className="mx-auto grid max-w-[1180px] gap-12 px-5 py-14 lg:grid-cols-[.8fr_1.2fr] lg:items-center lg:px-0 lg:py-20">
        <section>
          <div className="section-kicker">START YOUR BRIEFING</div>
          <h1 className="mt-4 text-[36px] font-extrabold leading-[1.18] tracking-[-.07em] sm:text-[48px]">
            내 조건을 알려주면,
            <br />
            <span className="text-[#2457d6]">받을 수 있는 것부터</span>
            <br />
            정리해드릴게요.
          </h1>
          <p className="mt-5 max-w-[400px] text-[14px] leading-7 text-slate-500">
            복잡한 정책 용어 대신, 나에게 필요한 지원과 저축 계획을 한 번에 확인해요.
          </p>
          <div className="mt-9 grid gap-3 text-[12px] font-bold text-slate-500">
            <span className="flex items-center gap-3">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-[#e3f7f4] text-[#159c8d]">
                <Check size={14} />
              </span>
              3분이면 충분한 간단한 프로필
            </span>
            <span className="flex items-center gap-3">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-[#e3edff] text-[#2457d6]">
                <ShieldCheck size={14} />
              </span>
              입력한 정보는 정책 매칭에만 사용
            </span>
          </div>
        </section>
        <section className="rounded-[26px] border border-slate-200/80 bg-white p-6 shadow-[0_20px_55px_rgba(22,45,84,.08)] sm:p-9">
          <div className="mb-8">
            <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#2457d6]">PROFILE</div>
            <h2 className="mt-2 text-[22px] font-extrabold tracking-[-.05em]">기본 프로필을 입력해 주세요</h2>
          </div>
          <div className="mb-7">
            <SocialLoginButtons action="가입" />
            <p className="mt-2 text-[11px] text-slate-400">소셜 계정으로 가입하면 다음 화면에서 프로필만 입력하면 돼요.</p>
          </div>
          <form onSubmit={handleSubmit} className="grid gap-5">
            <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
              이메일
              <div className="flex gap-2">
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setEmailCheckStatus("idle");
                  }}
                  required
                  className="h-12 flex-1 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
                />
                <button
                  type="button"
                  onClick={handleCheckEmail}
                  disabled={!email || emailCheckStatus === "checking"}
                  className="shrink-0 rounded-xl border border-slate-200 bg-white px-4 text-[12px] font-extrabold text-slate-600 transition hover:border-[#2457d6] hover:text-[#2457d6] disabled:opacity-50"
                >
                  {emailCheckStatus === "checking" ? "확인 중..." : "중복확인"}
                </button>
              </div>
              {emailCheckStatus === "taken" && <p className="text-[12px] font-bold text-rose-500">이미 가입된 계정입니다.</p>}
              {emailCheckStatus === "available" && <p className="text-[12px] font-bold text-[#159c8d]">사용 가능한 이메일입니다.</p>}
            </label>
            <PasswordField label="비밀번호" value={password} onChange={setPassword} />

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
                나이
                <input
                  type="number"
                  min={0}
                  placeholder="29"
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
                  placeholder="4000"
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
                    <button
                      key={o.value}
                      type="button"
                      className={pillClass(spouseOccupation === o.value)}
                      onClick={() => setSpouseOccupation(o.value)}
                    >
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-start gap-2 rounded-xl bg-[#f5f8fd] p-3.5 text-[11px] leading-5 text-slate-500">
              <CircleHelp size={15} className="mt-0.5 shrink-0 text-[#2457d6]" />
              입력한 정보는 정책 매칭·저축플랜 계산에만 쓰이고, 언제든 내 정보 화면에서 다시 수정할 수 있어요.
            </div>

            {error && <p className="text-[12px] font-bold text-rose-500">{error}</p>}
            <button
              type="submit"
              disabled={loading || !region || !occupation || emailCheckStatus !== "available"}
              className="group mt-1 flex h-12 items-center justify-center gap-2 rounded-xl bg-[#2457d6] text-[13px] font-extrabold text-white shadow-[0_12px_22px_rgba(36,87,214,.2)] transition hover:-translate-y-0.5 hover:bg-[#1949c1] disabled:opacity-50"
            >
              {loading ? "가입 중..." : "회원가입"} <ArrowRight size={16} className="transition group-hover:translate-x-1" />
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
