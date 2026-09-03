"use client";

// 정책금융 시뮬레이터(목업) 공용 UI 조각들. 이 탭은 백엔드를 호출하지 않고
// 화면 설계용 예시 수치만 보여준다(스크린샷의 "화면 예시용 표본 수치" 문구) —
// 실제 계산이 필요하면 /savings 탭의 YouthFutureSavingsSimulator /
// HousingLoanSimulator가 백엔드(savings_simulator)를 그대로 쓴다.

import { Check } from "lucide-react";

export type WizardStep = { label: string; sub: string };

// 왼쪽 세로 스텝 레일 (1 상품 선택 → 2 정보 입력 → 3 결과 확인)
export function StepRail({ steps, current }: { steps: WizardStep[]; current: number }) {
  return (
    <ol className="grid gap-6">
      {steps.map((step, i) => {
        const active = i === current;
        const done = i < current;
        return (
          <li key={step.label} className="flex gap-3">
            <span
              className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-[11px] font-extrabold ${
                active
                  ? "bg-[#0d1b36] text-white"
                  : done
                    ? "bg-[#0d1b36]/10 text-[#0d1b36]"
                    : "border border-slate-300 text-slate-400"
              }`}
            >
              {done ? <Check size={12} strokeWidth={3} /> : i + 1}
            </span>
            <div>
              <div className={`text-[13px] font-extrabold ${active ? "text-ink" : "text-slate-400"}`}>{step.label}</div>
              <div className="mt-0.5 text-[11px] font-semibold text-slate-400">{step.sub}</div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

// 2지선다 세그먼트 컨트롤 (혼인 여부 / 지역 / 일반형·우대형 등)
export function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={`h-12 rounded-xl border text-[13px] font-extrabold transition ${
            value === o.value
              ? "border-[#0d1b36] bg-white text-[#0d1b36]"
              : "border-slate-200 bg-white text-slate-400 hover:border-slate-300"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// 검정 트랙 슬라이더 + 값 라벨
export function SliderField({
  label,
  valueLabel,
  min,
  max,
  step,
  value,
  onChange,
}: {
  label: string;
  valueLabel: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="mb-2 text-[12px] font-extrabold text-slate-700">{label}</div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[#0d1b36]"
      />
      <div className="mt-1 text-[13px] font-extrabold text-ink">{valueLabel}</div>
    </div>
  );
}

// "자격 예비판정" 행 (충족 / 미충족)
export function PrelimRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between border-t border-slate-100 py-3 text-[12px] first:border-t-0">
      <span className="font-semibold text-slate-600">{label}</span>
      <span className={`font-extrabold ${ok ? "text-[#159c8d]" : "text-rose-500"}`}>{ok ? "충족" : "미충족"}</span>
    </div>
  );
}

// 스텝 본문 프레임: "· N단계" eyebrow + 제목 + 본문 + 하단 이동 버튼 줄
export function WizardFrame({
  eyebrow,
  title,
  children,
  footer,
}: {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <div>
      <div className="text-[11px] font-extrabold uppercase tracking-[.18em] text-slate-400">{eyebrow}</div>
      <h2 className="mt-1.5 text-[20px] font-extrabold tracking-[-.04em] text-ink">{title}</h2>
      <div className="mt-6">{children}</div>
      <div className="mt-8 flex items-center justify-between">{footer}</div>
    </div>
  );
}

export function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="h-11 rounded-xl border border-slate-200 px-5 text-[13px] font-extrabold text-slate-500 transition hover:border-slate-300"
    >
      이전
    </button>
  );
}

export function NextButton({ label, onClick, disabled }: { label: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="h-11 rounded-xl bg-[#0d1b36] px-6 text-[13px] font-extrabold text-white transition hover:bg-[#16264a] disabled:opacity-40"
    >
      {label}
    </button>
  );
}

export function MockDisclaimer({ text }: { text: string }) {
  return <p className="mt-5 text-[11px] font-semibold leading-5 text-slate-400">{text}</p>;
}

// ── 숫자 포맷 ──────────────────────────────────────────────────────────
export function manwon(value: number): string {
  return `${Math.round(value).toLocaleString()}만원`;
}

export function eok(value: number): string {
  // 소수 첫째 자리까지 (3.6억원)
  return `${(Math.round(value * 10) / 10).toLocaleString()}억원`;
}
