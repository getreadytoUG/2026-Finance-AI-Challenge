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

// 2026-09-01 UPGRADE.md 반영: 확장 프로필 필드 옵션들.
// 2026-09-02: 미혼/예비부부/신혼부부 3분류 → 미혼/기혼 2분류로 축소. "예비신혼부부"는
// 별도 옵션 대신 혼인 여부 옆 툴팁으로 안내한다(입주 전 혼인신고 필요).
export type MaritalStatusType = "single" | "married";

export const MARITAL_STATUS_OPTIONS: { value: MaritalStatusType; label: string }[] = [
  { value: "single", label: "미혼" },
  { value: "married", label: "기혼" },
];

// 미혼/기혼 축소 이전의 구버전 값(engaged/newlywed)이 응답에 섞여 들어와도
// 화면이 깨지지 않게 매핑한다. 백엔드도 UserOut에서 같은 정규화를 한다.
export function normalizeMaritalStatus(value: string | null | undefined): MaritalStatusType | null {
  if (value === "single" || value === "engaged") return "single";
  if (value === "married" || value === "newlywed") return "married";
  return null;
}

export function maritalStatusLabel(value: string | null | undefined): string {
  const normalized = normalizeMaritalStatus(value);
  return MARITAL_STATUS_OPTIONS.find((o) => o.value === normalized)?.label ?? "-";
}

export type EmploymentType = "regular" | "gig_freelance" | "business_owner";

export const EMPLOYMENT_TYPE_OPTIONS: { value: EmploymentType; label: string }[] = [
  { value: "regular", label: "정규직" },
  { value: "gig_freelance", label: "특고·프리랜서" },
  { value: "business_owner", label: "사업자" },
];

export function employmentTypeLabel(value: EmploymentType | null | undefined): string {
  return EMPLOYMENT_TYPE_OPTIONS.find((o) => o.value === value)?.label ?? "-";
}

export type HousingStatusType = "homeless_head" | "homeless_member" | "homeowner";

export const HOUSING_STATUS_OPTIONS: { value: HousingStatusType; label: string }[] = [
  { value: "homeless_head", label: "무주택 세대주" },
  { value: "homeless_member", label: "무주택 세대원" },
  { value: "homeowner", label: "유주택" },
];

export function housingStatusLabel(value: HousingStatusType | null | undefined): string {
  return HOUSING_STATUS_OPTIONS.find((o) => o.value === value)?.label ?? "-";
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

// 백엔드 PolicyCategoryTag(app/features/policy_matcher/categories.py)와 동일한 8개
// 대분류 태그 목록. AI 정책 검색의 클릭형 필터(AiSearchFilterBar)가 쓴다 — 백엔드
// 목록이 바뀌면 이것도 같이 갱신해야 한다.
export const POLICY_CATEGORY_OPTIONS: string[] = [
  "일자리", "금융･복지･문화", "복지문화", "주거", "교육", "참여･기반", "교육･직업훈련", "참여권리",
];
