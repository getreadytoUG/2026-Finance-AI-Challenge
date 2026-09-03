"use client";

import { DashboardLayout } from "@/components/DashboardLayout";
import PolicyFinanceSimulator from "./PolicyFinanceSimulator";

// 정책금융 시뮬레이터 "목업" 탭. 기존 "저축플랜"(/savings) 탭은 그대로 두고,
// 스크린샷 기준의 3단계 마법사 UI(정책연계 저축계좌상품 / 정책연계 대출)를 별도
// 탭으로 새로 붙인 것 — 수치는 전부 화면 설계용 예시다(백엔드 미연동).
export default function FinanceSimulatorPage() {
  return (
    <DashboardLayout
      eyebrow="POLICY FINANCE · 목업"
      title="정책금융 시뮬레이터"
      action={
        <p className="text-[11px] font-semibold text-slate-400 sm:text-right">
          두 서비스는 서로 독립적으로 동작합니다 · 화면 예시용 표본 수치
        </p>
      }
    >
      <PolicyFinanceSimulator />
    </DashboardLayout>
  );
}
