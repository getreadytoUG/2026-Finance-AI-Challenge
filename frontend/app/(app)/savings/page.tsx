"use client";

import { useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import YouthFutureSavingsSimulator from "@/components/YouthFutureSavingsSimulator";
import HousingLoanSimulator from "@/components/HousingLoanSimulator";

const SUB_TABS = [
  { key: "leap", label: "정책 연계 저축 시뮬레이터" },
  { key: "housing", label: "정책 연계 주거 시뮬레이터" },
] as const;

type SubTabKey = (typeof SUB_TABS)[number]["key"];

// 2026-09-01 UPGRADE.md 반영: "저축플랜"이 목표금액 계산기에서 정책연계형
// 저축/주거 시뮬레이터로 탈바꿈했다 — 구독료/카드소비 리포트는 문서에 언급이
// 없어서 복원하지 않는다(오늘 삭제된 채로 유지).
export default function SavingsPage() {
  const [activeTab, setActiveTab] = useState<SubTabKey>("leap");

  return (
    <DashboardLayout eyebrow="POLICY-LINKED SIMULATOR" title="저축플랜">
      <div className="mb-6 inline-flex gap-1.5 rounded-xl bg-[#eef3f9] p-1">
        {SUB_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-lg px-4 py-2.5 text-[12px] font-extrabold transition ${
              activeTab === tab.key ? "bg-white text-[#2457d6] shadow-sm" : "text-slate-500"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "leap" ? <YouthFutureSavingsSimulator /> : <HousingLoanSimulator />}
    </DashboardLayout>
  );
}
