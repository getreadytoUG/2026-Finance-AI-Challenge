export type OccupationType = "student" | "employee" | "self_employed" | "unemployed" | "other";

export const OCCUPATION_OPTIONS: { value: OccupationType; label: string }[] = [
  { value: "student", label: "학생" },
  { value: "employee", label: "직장인" },
  { value: "self_employed", label: "자영업자" },
  { value: "unemployed", label: "무직/구직중" },
  { value: "other", label: "기타" },
];

export function occupationLabel(value: OccupationType | null | undefined): string {
  return OCCUPATION_OPTIONS.find((o) => o.value === value)?.label ?? "-";
}

// 백엔드는 연소득을 원 단위(annual_income_krw)로 저장하지만, 입력·표시는 만원 단위가 익숙하므로
// UI 레이어에서만 변환한다.
export function krwToManwon(krw: number): number {
  return Math.round(krw / 10000);
}

export function manwonToKrw(manwon: number): number {
  return Math.round(manwon * 10000);
}

// 백엔드 REGIONS(app/features/policy_matcher/matching.py)와 동일한 17개 시/도 목록.
// 회원가입 시점에는 인증 토큰이 없어 /policy_matcher/regions를 호출할 수 없으므로 고정 목록을 둔다.
export const REGIONS: string[] = [
  "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
  "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
];
