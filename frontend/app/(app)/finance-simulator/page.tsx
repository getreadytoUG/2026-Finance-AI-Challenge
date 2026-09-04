"use client";

import { DashboardLayout } from "@/components/DashboardLayout";
import PolicyFinanceSimulator from "./PolicyFinanceSimulator";

// 정책금융 시뮬레이터 탭 — 3단계 마법사 UI(정책연계 저축계좌상품 / 정책연계 대출).
// 2026-09-03 재작업: 원래는 화면 설계용 목업(백엔드 미연동)이었는데, 사이드바에
// 있던 "저축플랜"(/savings)의 실제 계산 로직을 이쪽으로 흡수하고 그 탭은
// 삭제했다(둘이 사실상 같은 기능이었다는 사용자 지적).
export default function FinanceSimulatorPage() {
  return (
    <DashboardLayout
      eyebrow="POLICY FINANCE"
      title="정책금융 시뮬레이터"
      action={
        <p className="text-[11px] font-semibold text-slate-400 sm:text-right">
          두 서비스는 서로 독립적으로 동작합니다 · 실제 정부 고시 수치 기준
        </p>
      }
    >
      <PolicyFinanceSimulator />
    </DashboardLayout>
  );
}
