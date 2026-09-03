"use client";

// 정책금융 시뮬레이터 (목업) — 위쪽에 두 서비스 카드를 나란히 두고, 아래에
// 선택된 서비스의 3단계 마법사(상품 선택 → 정보 입력 → 결과 확인)를 보여준다.
// 두 시뮬레이터는 서로 독립이고, 백엔드를 호출하지 않는 화면 설계용 예시다.
// 실제 계산이 붙은 버전은 사이드바 "저축플랜"(/savings) 탭에 그대로 있다.

import { useState } from "react";
import { Landmark, PiggyBank } from "lucide-react";
import SavingsWizard from "./SavingsWizard";
import LoanWizard from "./LoanWizard";

type ServiceKey = "savings" | "loan";

const SERVICES = [
  {
    key: "savings" as const,
    kicker: "저축 시뮬레이터",
    title: "얼마를 모을 수 있을까",
    desc: "청년미래적금, 청년도약계좌 등 정책 저축상품의 만기 수령액을 확인합니다.",
    icon: PiggyBank,
    accent: "border-[#2f7a3f] bg-[#eef7ee]",
    accentIcon: "text-[#2f7a3f]",
  },
  {
    key: "loan" as const,
    kicker: "대출 시뮬레이터",
    title: "얼마까지 빌릴 수 있을까",
    desc: "청년주택드림 디딤돌대출 등 정책 주택담보대출의 한도와 상환액을 확인합니다.",
    icon: Landmark,
    accent: "border-[#b5623a] bg-[#fdf1ea]",
    accentIcon: "text-[#b5623a]",
  },
];

export default function PolicyFinanceSimulator() {
  const [active, setActive] = useState<ServiceKey>("savings");
  // 각 마법사는 마운트 해제 시 상태가 초기화되도록 key로 강제 리마운트한다 —
  // 서비스를 전환하면 1단계부터 다시 시작하는 게 자연스럽다.
  return (
    <div>
      <div className="grid gap-4 lg:grid-cols-2">
        {SERVICES.map((s) => {
          const on = s.key === active;
          const Icon = s.icon;
          return (
            <button
              key={s.key}
              type="button"
              onClick={() => setActive(s.key)}
              className={`rounded-[22px] border p-6 text-left transition ${
                on ? s.accent : "border-slate-200 bg-white hover:border-slate-300"
              }`}
            >
              <div className={`flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-[.16em] ${on ? s.accentIcon : "text-slate-400"}`}>
                <Icon size={13} /> {s.kicker}
              </div>
              <div className="mt-2 text-[22px] font-extrabold tracking-[-.04em] text-ink">{s.title}</div>
              <p className="mt-2 text-[12px] leading-5 text-slate-500">{s.desc}</p>
            </button>
          );
        })}
      </div>

      <div className="mt-8 rounded-[22px] border border-slate-200 bg-white p-6 sm:p-8">
        {active === "savings" ? <SavingsWizard key="savings" /> : <LoanWizard key="loan" />}
      </div>
    </div>
  );
}
