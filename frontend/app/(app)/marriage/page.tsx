"use client";

import { DashboardLayout } from "@/components/DashboardLayout";
import MarriageComparisonTab from "./MarriageComparisonTab";

// 2026-09-01 UPGRADE.md "정책 매칭 폐쇄" 반영 후 사용자 재지시: "혼인신고 계산기"는
// "정책 매칭"이라는 상위 탭 아래 서브탭이 아니라, 사이드바에서 독립된 탭으로
// 운영한다(AppShell.tsx NAV_ITEMS 참고). 컴포넌트 자체(MarriageComparisonTab)는
// 예전 policy/ 폴더에 있던 걸 그대로 옮겨왔다 — 로직 변경 없음.
export default function MarriagePage() {
  return (
    <DashboardLayout eyebrow="MARRIAGE CALCULATOR" title="혼인신고 계산기">
      <MarriageComparisonTab />
    </DashboardLayout>
  );
}
