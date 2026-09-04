"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CircleHelp,
  Mail,
  ShieldCheck,
} from "lucide-react";
import {
  signup,
  login,
  checkEmailAvailable,
  refreshRecommendations,
} from "@/lib/api";
import PasswordField from "@/components/PasswordField";
import SocialLoginButtons from "@/components/SocialLoginButtons";
import InfoTooltip from "@/components/InfoTooltip";
import { BrandMark } from "@/components/BrandMark";
import {
  EMPLOYMENT_TYPE_OPTIONS,
  HOUSING_STATUS_OPTIONS,
  MARITAL_STATUS_OPTIONS,
  OCCUPATION_OPTIONS,
  REGIONS,
  manwonToKrw,
  type EmploymentType,
  type HousingStatusType,
  type MaritalStatusType,
  type OccupationType,
} from "@/lib/profileOptions";

function pillClass(active: boolean) {
  return `rounded-lg px-3.5 py-2 text-[11px] font-extrabold transition ${
    active
      ? "bg-[#2457d6] text-white"
      : "bg-[#eef3f9] text-slate-500 hover:bg-[#e3eaf6]"
  }`;
}

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [age, setAge] = useState("");
  const [income, setIncome] = useState("");
  const [occupation, setOccupation] = useState<OccupationType | "">("");
  const [region, setRegion] = useState<string | null>(null);
  const [spouseAge, setSpouseAge] = useState("");
  const [spouseIncome, setSpouseIncome] = useState("");
  const [spouseOccupation, setSpouseOccupation] = useState<OccupationType | "">(
    "",
  );
  // 2026-09-01 UPGRADE.md 반영: 확장 프로필 필드. 전부 선택 입력이라 미입력이어도
  // 제출을 막지 않는다(아래 disabled 조건에 안 들어감).
  const [maritalStatus, setMaritalStatus] = useState<MaritalStatusType | "">(
    "",
  );
  const [marriageYears, setMarriageYears] = useState("");
  const [childrenCount, setChildrenCount] = useState("");
  const [isPregnant, setIsPregnant] = useState(false);
  const [desiredRegion, setDesiredRegion] = useState<string | null>(null);
  const [employmentType, setEmploymentType] = useState<EmploymentType | "">("");
  const [isSmeEmployee, setIsSmeEmployee] = useState(false);
  const [housingStatus, setHousingStatus] = useState<HousingStatusType | "">(
    "",
  );
  const [netWorth, setNetWorth] = useState("");
  const [monthlySavings, setMonthlySavings] = useState("");
  // 2026-09-02 추가: 장애인/국가보훈대상자 전용 정책이 있어 수집(선택 입력).
  const [hasDisability, setHasDisability] = useState(false);
  const [isVeteran, setIsVeteran] = useState(false);
  const isMarried = maritalStatus === "married";
  const [error, setError] = useState<string | null>(null);
  // 예전엔 필수값이 비면 "회원가입" 버튼 자체를 disabled 처리해서, 사용자가 뭘
  // 안 채웠는지 알 수 없었다(사용자 요청, 2026-09-02: 버튼은 항상 누를 수 있게
  // 하고, 누르면 빠진 항목을 알려주는 방향). validate()가 채우는 안내 목록.
  const [fieldErrors, setFieldErrors] = useState<string[]>([]);
  const errorSummaryRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(false);
  const [emailCheckStatus, setEmailCheckStatus] = useState<
    "idle" | "checking" | "available" | "taken"
  >("idle");
  // 회원가입 방식을 먼저 고르게 한다 — "이메일로 가입하기"를 눌러야 아래 프로필
  // 입력 폼이 나타난다(소셜은 버튼 클릭 즉시 OAuth로 이동하므로 이 상태와 무관).
  const [method, setMethod] = useState<"choose" | "email">("choose");
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

  // 빠졌거나 범위를 벗어난 필수 항목을 폼 위에서 아래 순서대로 모아 문장으로 돌려준다.
  function validate(): string[] {
    const msgs: string[] = [];
    const emailFormatOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

    if (!email.trim()) msgs.push("이메일을 입력해주세요.");
    else if (!emailFormatOk) msgs.push("이메일 형식이 올바르지 않습니다.");
    else if (emailCheckStatus === "taken")
      msgs.push("이미 가입된 이메일입니다. 다른 이메일을 사용해주세요.");
    else if (emailCheckStatus !== "available")
      msgs.push("이메일 중복확인을 완료해주세요.");

    if (!password) msgs.push("비밀번호를 입력해주세요.");

    const ageNum = Number(age);
    if (!age.trim()) msgs.push("나이를 입력해주세요.");
    else if (!Number.isFinite(ageNum) || ageNum < 0 || ageNum > 130)
      msgs.push("나이는 0~130세 사이로 입력해주세요.");

    const incomeNum = Number(income);
    if (!income.trim()) msgs.push("연소득을 입력해주세요.");
    else if (!Number.isFinite(incomeNum) || incomeNum < 0 || incomeNum > 200000)
      msgs.push("연소득은 0~200,000만원 사이로 입력해주세요.");

    if (!region) msgs.push("거주 지역을 선택해주세요.");
    if (!occupation) msgs.push("직업 구분을 선택해주세요.");

    return msgs;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const problems = validate();
    setFieldErrors(problems);
    if (problems.length > 0) {
      requestAnimationFrame(() =>
        errorSummaryRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "center",
        }),
      );
      return;
    }
    // validate()가 이미 보장하지만, region/occupation 타입을 좁히기 위해 한 번 더.
    if (!region || !occupation) return;
    setLoading(true);
    try {
      await signup({
        email,
        password,
        age: Number(age),
        is_married: maritalStatus === "married",
        annual_income_krw: manwonToKrw(Number(income)),
        region,
        occupation,
        spouse_age: isMarried && spouseAge ? Number(spouseAge) : null,
        spouse_annual_income_krw:
          isMarried && spouseIncome ? manwonToKrw(Number(spouseIncome)) : null,
        spouse_occupation:
          isMarried && spouseOccupation ? spouseOccupation : null,
        marital_status: maritalStatus || null,
        marriage_years:
          maritalStatus === "married" && marriageYears
            ? Number(marriageYears)
            : null,
        children_count: childrenCount ? Number(childrenCount) : null,
        is_pregnant: isPregnant,
        desired_region: desiredRegion,
        employment_type: employmentType || null,
        is_sme_employee: isSmeEmployee,
        housing_status: housingStatus || null,
        net_worth_krw: netWorth ? manwonToKrw(Number(netWorth)) : null,
        monthly_savings_capacity_krw: monthlySavings
          ? manwonToKrw(Number(monthlySavings))
          : null,
        has_disability: hasDisability,
        is_veteran: isVeteran,
      });
      const token = await login(email, password);
      localStorage.setItem("token", token);
      try {
        // 가입 직후엔 새벽 배치가 아직 한 번도 안 돌아 "최근 추천"이 비어 보인다
        // — 가입 시점에 프로필이 이미 다 채워져 있으니 그 자리에서 한 번 돌려서
        // 대시보드에 도착했을 때 바로 뭔가 보이게 한다(사용자 요청, 2026-09-02).
        // 실패해도 가입 자체를 막을 일은 아니라 조용히 무시 — 최악의 경우 새벽
        // 배치가 대신 채워준다.
        await refreshRecommendations(token);
      } catch {
        // no-op
      }
      // 로그인 상태여도 홈페이지가 먼저 보이도록 바뀌어서, 가입 완료 후에도
      // 대시보드로 바로 꽂지 않고 홈페이지로 보낸다(사용자 요청, 2026-09-02).
      router.push("/");
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
            복잡한 정책 용어 대신, 나에게 필요한 지원과 저축 계획을 한 번에
            확인해요.
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
          {method === "choose" ? (
            <>
              <div className="mb-8">
                <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#2457d6]">
                  SIGN UP
                </div>
                <h2 className="mt-2 text-[22px] font-extrabold tracking-[-.05em]">
                  회원가입 방법을 선택해주세요
                </h2>
                <p className="mt-3 text-[13px] text-slate-500">
                  어떤 방법으로 가입하든, 다음 화면에서 프로필만 입력하면
                  끝나요.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setMethod("email")}
                className="group flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#2457d6] text-[13px] font-extrabold text-white shadow-[0_12px_22px_rgba(36,87,214,.2)] transition hover:-translate-y-0.5 hover:bg-[#1949c1] active:scale-[.98]"
              >
                <Mail size={16} /> 이메일로 가입하기{" "}
                <ArrowRight
                  size={16}
                  className="transition group-hover:translate-x-1"
                />
              </button>
              <div className="mt-7">
                <SocialLoginButtons action="가입" />
              </div>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={() => setMethod("choose")}
                className="mb-5 inline-flex items-center gap-1.5 text-[12px] font-bold text-slate-400 transition hover:text-[#2457d6]"
              >
                <ArrowLeft size={14} /> 다른 방법으로 가입하기
              </button>
              <div className="mb-8">
                <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#2457d6]">
                  PROFILE
                </div>
                <h2 className="mt-2 text-[22px] font-extrabold tracking-[-.05em]">
                  기본 프로필을 입력해 주세요
                </h2>
              </div>
              {/* noValidate: 브라우저 네이티브 검증 툴팁이 첫 빈 칸에서 제출을 가로채면
                  "빠진 항목 전체를 한 번에 보여준다"가 안 되므로 끄고, validate()로 직접 안내한다. */}
              <form onSubmit={handleSubmit} noValidate className="grid gap-5">
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
                      {emailCheckStatus === "checking"
                        ? "확인 중..."
                        : "중복확인"}
                    </button>
                  </div>
                  {emailCheckStatus === "taken" && (
                    <p className="text-[12px] font-bold text-rose-500">
                      이미 가입된 계정입니다.
                    </p>
                  )}
                  {emailCheckStatus === "available" && (
                    <p className="text-[12px] font-bold text-[#159c8d]">
                      사용 가능한 이메일입니다.
                    </p>
                  )}
                </label>
                <PasswordField
                  label="비밀번호"
                  value={password}
                  onChange={setPassword}
                />

                {/* 기본 인적사항 */}
                <div className="border-t border-slate-100 pt-5 text-[11px] font-extrabold uppercase tracking-[.1em] text-slate-400">
                  기본 인적사항
                </div>
                <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
                  나이
                  <input
                    type="number"
                    min={0}
                    max={130}
                    placeholder="29"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                    required
                    className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
                  />
                  {/* 2026-09-02 QA: min/max만 걸어두면 브라우저 네이티브 툴팁 외엔 안내가
                  없어서 왜 제출이 안 되는지 헷갈릴 수 있었다 — 상시 노출 힌트로 보강. */}
                  <span className="text-[11px] font-semibold text-slate-400">
                    0~130세 사이로 입력해주세요.
                  </span>
                </label>

                <div>
                  <div className="mb-2 flex items-center gap-1.5 text-[12px] font-extrabold text-slate-700">
                    혼인 여부
                    <InfoTooltip text="예비신혼부부의 경우, 입주 전일까지 혼인사실을 증명(혼인신고)해야 합니다." />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {MARITAL_STATUS_OPTIONS.map((o) => (
                      <button
                        key={o.value}
                        type="button"
                        className={pillClass(maritalStatus === o.value)}
                        onClick={() => setMaritalStatus(o.value)}
                      >
                        {o.label}
                      </button>
                    ))}
                  </div>
                  {maritalStatus === "married" && (
                    <input
                      type="number"
                      min={0}
                      max={100}
                      placeholder="결혼 몇 년차인가요? (예: 1)"
                      value={marriageYears}
                      onChange={(e) => setMarriageYears(e.target.value)}
                      className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6]"
                    />
                  )}
                </div>

                {isMarried && (
                  <div className="rounded-xl bg-[#f5f8fd] p-4">
                    <p className="mb-3 text-[12px] font-bold text-slate-500">
                      배우자 정보 (선택)
                    </p>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
                        배우자 나이
                        <input
                          type="number"
                          min={0}
                          max={130}
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
                          max={200000}
                          value={spouseIncome}
                          onChange={(e) => setSpouseIncome(e.target.value)}
                          className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6]"
                        />
                      </label>
                    </div>
                    <div className="mt-3 text-[12px] font-extrabold text-slate-700">
                      배우자 직업 구분
                    </div>
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

                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
                    자녀 수
                    <input
                      type="number"
                      min={0}
                      max={20}
                      placeholder="0"
                      value={childrenCount}
                      onChange={(e) => setChildrenCount(e.target.value)}
                      className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
                    />
                  </label>
                  <label className="flex items-center gap-2 self-end pb-1 text-[13px] font-bold text-slate-700">
                    <input
                      type="checkbox"
                      checked={isPregnant}
                      onChange={(e) => setIsPregnant(e.target.checked)}
                      className="h-4 w-4 accent-[#2457d6]"
                    />
                    임신 중이에요
                  </label>
                </div>

                <div className="flex flex-wrap gap-x-6 gap-y-2">
                  <label className="flex items-center gap-2 text-[13px] font-bold text-slate-700">
                    <input
                      type="checkbox"
                      checked={hasDisability}
                      onChange={(e) => setHasDisability(e.target.checked)}
                      className="h-4 w-4 accent-[#2457d6]"
                    />
                    장애가 있어요
                  </label>
                  <label className="flex items-center gap-2 text-[13px] font-bold text-slate-700">
                    <input
                      type="checkbox"
                      checked={isVeteran}
                      onChange={(e) => setIsVeteran(e.target.checked)}
                      className="h-4 w-4 accent-[#2457d6]"
                    />
                    국가보훈대상자예요
                  </label>
                </div>

                <div>
                  <div className="mb-2 text-[12px] font-extrabold text-slate-700">
                    거주 지역
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {REGIONS.map((r) => (
                      <button
                        key={r}
                        type="button"
                        className={pillClass(region === r)}
                        onClick={() => setRegion(r)}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="mb-2 text-[12px] font-extrabold text-slate-700">
                    희망 지역 (선택, 거주 지역과 다를 경우)
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {REGIONS.map((r) => (
                      <button
                        key={r}
                        type="button"
                        className={pillClass(desiredRegion === r)}
                        onClick={() =>
                          setDesiredRegion(desiredRegion === r ? null : r)
                        }
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>

                {/* 소득 및 직업 */}
                <div className="border-t border-slate-100 pt-5 text-[11px] font-extrabold uppercase tracking-[.1em] text-slate-400">
                  소득 및 직업
                </div>
                <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
                  연소득 (만원)
                  <input
                    type="number"
                    min={0}
                    max={200000}
                    placeholder="4000"
                    value={income}
                    onChange={(e) => setIncome(e.target.value)}
                    required
                    className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
                  />
                </label>

                <div>
                  <div className="mb-2 text-[12px] font-extrabold text-slate-700">
                    직업 구분
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {OCCUPATION_OPTIONS.map((o) => (
                      <button
                        key={o.value}
                        type="button"
                        className={pillClass(occupation === o.value)}
                        onClick={() => setOccupation(o.value)}
                      >
                        {o.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="mb-2 text-[12px] font-extrabold text-slate-700">
                    근로 형태 (선택)
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {EMPLOYMENT_TYPE_OPTIONS.map((o) => (
                      <button
                        key={o.value}
                        type="button"
                        className={pillClass(employmentType === o.value)}
                        onClick={() =>
                          setEmploymentType(
                            employmentType === o.value ? "" : o.value,
                          )
                        }
                      >
                        {o.label}
                      </button>
                    ))}
                  </div>
                </div>

                <label className="flex items-center gap-2 text-[13px] font-bold text-slate-700">
                  <input
                    type="checkbox"
                    checked={isSmeEmployee}
                    onChange={(e) => setIsSmeEmployee(e.target.checked)}
                    className="h-4 w-4 accent-[#2457d6]"
                  />
                  중소기업 재직 중이에요
                </label>

                {/* 자산 및 주거 */}
                <div className="border-t border-slate-100 pt-5 text-[11px] font-extrabold uppercase tracking-[.1em] text-slate-400">
                  자산 및 주거
                </div>
                <div>
                  <div className="mb-2 text-[12px] font-extrabold text-slate-700">
                    무주택 여부 (선택)
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {HOUSING_STATUS_OPTIONS.map((o) => (
                      <button
                        key={o.value}
                        type="button"
                        className={pillClass(housingStatus === o.value)}
                        onClick={() =>
                          setHousingStatus(
                            housingStatus === o.value ? "" : o.value,
                          )
                        }
                      >
                        {o.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
                    순자산 (만원, 선택)
                    <input
                      type="number"
                      min={0}
                      max={200000}
                      placeholder="부동산·금융자산 합산"
                      value={netWorth}
                      onChange={(e) => setNetWorth(e.target.value)}
                      className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
                    />
                  </label>
                  <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
                    월 저축 가능 여력 (만원, 선택)
                    <input
                      type="number"
                      min={0}
                      max={200000}
                      value={monthlySavings}
                      onChange={(e) => setMonthlySavings(e.target.value)}
                      className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
                    />
                  </label>
                </div>

                <div className="flex items-start gap-2 rounded-xl bg-[#f5f8fd] p-3.5 text-[11px] leading-5 text-slate-500">
                  <CircleHelp
                    size={15}
                    className="mt-0.5 shrink-0 text-[#2457d6]"
                  />
                  입력한 정보는 정책 매칭·정책금융 시뮬레이터에만 쓰이고, 언제든
                  내 정보 화면에서 다시 수정할 수 있어요.
                </div>

                {fieldErrors.length > 0 && (
                  <div
                    ref={errorSummaryRef}
                    className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-[12px] font-bold text-rose-600"
                  >
                    <p className="mb-1.5">아래 항목을 확인해주세요.</p>
                    <ul className="list-disc space-y-0.5 pl-4 font-semibold">
                      {fieldErrors.map((msg) => (
                        <li key={msg}>{msg}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {error && (
                  <p className="text-[12px] font-bold text-rose-500">{error}</p>
                )}
                <button
                  type="submit"
                  disabled={loading}
                  className="group mt-1 flex h-12 items-center justify-center gap-2 rounded-xl bg-[#2457d6] text-[13px] font-extrabold text-white shadow-[0_12px_22px_rgba(36,87,214,.2)] transition hover:-translate-y-0.5 hover:bg-[#1949c1] disabled:opacity-50"
                >
                  {loading ? "가입 중..." : "회원가입"}{" "}
                  <ArrowRight
                    size={16}
                    className="transition group-hover:translate-x-1"
                  />
                </button>
              </form>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
