import type { EmploymentType, HousingStatusType, MaritalStatusType, OccupationType } from "@/lib/profileOptions";

// 2026-09-01 UPGRADE.md 반영: 확장 프로필 필드. 전부 선택 입력 — 안 채워도 로그인/
// 매칭에 영향 없음(백엔드도 전부 nullable).
export type ExtendedProfileFields = {
  marital_status?: MaritalStatusType | null;
  marriage_years?: number | null;
  children_count?: number | null;
  is_pregnant?: boolean | null;
  desired_region?: string | null;
  employment_type?: EmploymentType | null;
  is_sme_employee?: boolean | null;
  housing_status?: HousingStatusType | null;
  net_worth_krw?: number | null;
  monthly_savings_capacity_krw?: number | null;
  // 2026-09-02 추가: 장애인/국가보훈대상자 전용 정책이 있어 수집(매칭 로직 미반영).
  has_disability?: boolean | null;
  is_veteran?: boolean | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type SocialProvider = "kakao";

// 백엔드가 프로바이더 인증 페이지로 302 리다이렉트해준다. SPA 라우팅이 아니라
// 브라우저 전체 이동이어야 하므로 window.location.href에 그대로 넣어 쓴다.
export function socialLoginUrl(provider: SocialProvider): string {
  return `${API_BASE}/auth/${provider}/login`;
}

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    throw new Error("Login failed");
  }
  const data = await res.json();
  return data.access_token as string;
}

export async function checkEmailAvailable(email: string): Promise<boolean> {
  const res = await fetch(`${API_BASE}/auth/check-email?email=${encodeURIComponent(email)}`);
  if (!res.ok) {
    throw new Error("이메일 확인에 실패했습니다.");
  }
  const data = await res.json();
  return data.available as boolean;
}

export type SignupInput = ProfileInput & {
  email: string;
  password: string;
};

// FastAPI 검증 실패(422)는 detail이 문자열이 아니라 {loc, msg, type} 객체 배열로
// 온다 — 그동안은 `typeof body.detail === "string"`만 체크해서 이 경우를 못 읽고
// 항상 fallback 문구로만 떨어졌다(2026-09-02 QA: 연소득에 비현실적으로 큰 값을
// 넣었을 때 "Failed to fetch"만 뜨고 원인을 알 수 없던 문제의 일부). 배열이면
// 각 에러의 msg를 모아 한 줄로 합쳐서 좀 더 구체적인 안내를 보여준다.
function extractErrorDetail(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const messages = detail
        .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : null))
        .filter((m): m is string => Boolean(m));
      if (messages.length > 0) return `입력값을 확인해주세요: ${messages.join(", ")}`;
    }
  }
  return fallback;
}

export async function signup(payload: SignupInput): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = "회원가입에 실패했습니다.";
    try {
      const body = await res.json();
      detail = extractErrorDetail(body, detail);
    } catch {
      // response body wasn't JSON — keep the generic message
    }
    throw new Error(detail);
  }
}

export async function callTool<TOutput>(
  token: string,
  name: string,
  input: Record<string, unknown>
): Promise<TOutput> {
  const res = await fetch(`${API_BASE}/tools/${name}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(input),
  });
  if (res.status === 401) {
    handleUnauthorized();
  }
  if (!res.ok) {
    let detail = "요청이 실패했습니다.";
    try {
      const body = await res.json();
      detail = extractErrorDetail(body, detail);
    } catch {
      // response body wasn't JSON — keep the generic message
    }
    throw new Error(detail);
  }
  return (await res.json()) as TOutput;
}

export type UserProfile = {
  id: number;
  email: string;
  provider: string;
  // 표시용 이름 (소셜 닉네임). 이메일 가입은 null → 이메일 아이디로 폴백.
  name: string | null;
  // 나이/소득/지역/직업이 모두 채워졌는지(관리자는 항상 true). 소셜 로그인 유저는
  // 이 값이 false인 채로 생성되므로 프론트가 온보딩 페이지로 보낸다.
  profile_complete: boolean;
  age: number | null;
  is_married: boolean | null;
  annual_income_krw: number | null;
  region: string | null;
  occupation: OccupationType | null;
  spouse_age: number | null;
  spouse_annual_income_krw: number | null;
  spouse_occupation: OccupationType | null;
  is_admin: boolean;
} & ExtendedProfileFields;

export type ProfileInput = {
  age: number;
  is_married: boolean;
  annual_income_krw: number;
  region: string;
  occupation: OccupationType;
  spouse_age?: number | null;
  spouse_annual_income_krw?: number | null;
  spouse_occupation?: OccupationType | null;
} & ExtendedProfileFields;

export type Recommendation = {
  id: number;
  // 2026-09-02 QA 후속: 링크가 없는 추천 항목도 정책별 챗봇으로는 물어볼 수 있게
  // 하려고 추가(PolicyChatDrawer/PolicyQaTarget이 필요로 함).
  policy_key: string;
  policy_name: string;
  benefit_description: string;
  application_period: string;
  reference_url: string;
  matched_at: string;
  is_read: boolean;
  apply_start_ymd: string | null;
  apply_end_ymd: string | null;
  status: string;
  status_emoji: string;
};

type RecommendationListResponse = {
  recommendations: Recommendation[];
  unread_count: number;
};

export function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (typeof payload.exp !== "number") return false;
    return Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}

function handleUnauthorized() {
  localStorage.removeItem("token");
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

async function authedFetch(path: string, token: string, options: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  if (res.status === 401) {
    handleUnauthorized();
  }
  if (!res.ok) {
    let detail = "요청이 실패했습니다.";
    try {
      const body = await res.json();
      detail = extractErrorDetail(body, detail);
    } catch {
      // response body wasn't JSON — keep the generic message
    }
    throw new Error(detail);
  }
  return res;
}

export async function getMe(token: string): Promise<UserProfile> {
  const res = await authedFetch("/auth/me", token);
  return res.json();
}

export async function updateProfile(token: string, profile: ProfileInput): Promise<UserProfile> {
  const res = await authedFetch("/auth/profile", token, {
    method: "PUT",
    body: JSON.stringify(profile),
  });
  return res.json();
}

export async function deleteAccount(token: string, password?: string): Promise<void> {
  await authedFetch("/auth/me", token, {
    method: "DELETE",
    body: JSON.stringify({ password: password ?? null }),
  });
}

export async function getRecommendations(token: string): Promise<RecommendationListResponse> {
  const res = await authedFetch("/policy_matcher/recommendations", token);
  return res.json();
}

export async function refreshRecommendations(token: string): Promise<{ created: number }> {
  const res = await authedFetch("/policy_matcher/recommendations/refresh", token, { method: "POST" });
  return res.json();
}

export async function markRecommendationRead(token: string, id: number): Promise<void> {
  await authedFetch(`/policy_matcher/recommendations/${id}/read`, token, { method: "PATCH" });
}

export type PolicyBrowseItem = {
  policy_key: string;
  policy_name: string;
  benefit_description: string;
  application_period: string;
  reference_url: string;
  large_category: string;
  status: string;
  status_emoji: string;
  apply_start_ymd: string | null;
  apply_end_ymd: string | null;
};

export type PolicyBrowseResponse = {
  items: PolicyBrowseItem[];
  total: number;
  page: number;
  page_size: number;
};

export async function browsePolicies(
  token: string,
  params: { category?: string; region?: string; page?: number; pageSize?: number; includeClosed?: boolean }
): Promise<PolicyBrowseResponse> {
  const search = new URLSearchParams();
  if (params.category) search.set("category", params.category);
  if (params.region) search.set("region", params.region);
  if (params.page) search.set("page", String(params.page));
  if (params.pageSize) search.set("page_size", String(params.pageSize));
  if (params.includeClosed) search.set("include_closed", "true");
  const qs = search.toString();
  const res = await authedFetch(`/policy_matcher/browse${qs ? `?${qs}` : ""}`, token);
  return res.json();
}

export type PolicyCategory = { name: string; count: number };

export async function getPolicyCategories(
  token: string,
  params: { region?: string; includeClosed?: boolean } = {}
): Promise<{ categories: PolicyCategory[] }> {
  const search = new URLSearchParams();
  if (params.region) search.set("region", params.region);
  if (params.includeClosed) search.set("include_closed", "true");
  const qs = search.toString();
  const res = await authedFetch(`/policy_matcher/categories${qs ? `?${qs}` : ""}`, token);
  return res.json();
}

export async function getRegions(token: string): Promise<{ regions: string[] }> {
  const res = await authedFetch("/policy_matcher/regions", token);
  return res.json();
}

export type MarriageComparisonInput = {
  age: number;
  region: string;
  annual_income_krw: number;
  spouse_age?: number | null;
  spouse_annual_income_krw?: number | null;
  // 2026-09-03 추가("혼인신고 계산기 타겟팅" 재작업): 버팀목/디딤돌 실제 대출조건
  // 비교에 쓰인다. 안 보내면 백엔드 기본값(2.5억/5천만원)이 적용된다.
  target_price_krw?: number;
  self_capital_krw?: number;
};

export type MarriagePolicyItem = {
  policy_key: string;
  policy_name: string;
  benefit_description: string;
  application_period: string;
  reference_url: string;
  is_newlywed_policy: boolean;
  // married_only/unmarried_only 버킷에 왜 그 정책이 속했는지(혼인상태 조건 자체 /
  // 가구소득 합산) 설명하는 한 줄. both 버킷은 변화가 없으므로 null.
  change_reason: string | null;
};

export type HousingLoanScenario = {
  eligible: boolean;
  product_name: string;
  policy_rate: number;
  ltv_rate: number;
  loan_amount_krw: number;
  monthly_interest_krw: number;
  summary: string;
};

// 2026-09-03 추가("혼인신고 계산기도 특정 정책 타겟팅해야 함", 사용자 요청): 정책
// DB 전체 스캔 대신, 실제로 미혼용/기혼용 상품이 따로 있는 걸로 확인된 고정 기준
// 2개(버팀목 전세자금대출/디딤돌대출)를 항상 먼저 비교해서 보여준다.
export type HousingLoanMarriageComparison = {
  housing_type: "jeonse" | "purchase";
  unmarried: HousingLoanScenario;
  married: HousingLoanScenario;
};

export type MarriageComparisonOutput = {
  housing_loan_comparisons: HousingLoanMarriageComparison[];
  married_only: MarriagePolicyItem[];
  unmarried_only: MarriagePolicyItem[];
  both: MarriagePolicyItem[];
};

export async function compareMarriageScenarios(
  token: string,
  input: MarriageComparisonInput
): Promise<MarriageComparisonOutput> {
  const res = await authedFetch("/policy_matcher/marriage_comparison", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
  return res.json();
}

export type PolicyRankingInput = MarriageComparisonInput & {
  policy_keys: string[];
  context_label: string;
};

export type RankedPolicyItem = { policy_key: string; reason: string };

export type PolicyRankingOutput = { ranked: RankedPolicyItem[] };

export async function rankMarriagePolicies(
  token: string,
  input: PolicyRankingInput
): Promise<PolicyRankingOutput> {
  const res = await authedFetch("/policy_matcher/marriage_comparison/rank", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
  return res.json();
}

export type PolicyChatOption = {
  policy_name: string;
  benefit_description: string;
  application_period: string;
  reference_url: string;
  is_newlywed_policy: boolean;
  status: string;
  status_emoji: string;
};

export type PolicyChatMessage = { role: "user" | "assistant"; content: string };

export async function sendPolicyChatMessage(
  token: string,
  messages: PolicyChatMessage[]
): Promise<{ reply: string; policies: PolicyChatOption[] }> {
  const res = await authedFetch("/policy_chat/message", token, {
    method: "POST",
    body: JSON.stringify({ messages }),
  });
  return res.json();
}

export type PolicyStatus = "임박" | "여유" | "상시" | "예정" | "만료";

export type AiSearchFilters = {
  age?: number | null;
  is_married?: boolean | null;
  annual_income_krw?: number | null;
  spouse_annual_income_krw?: number | null;
  region?: string | null;
  category?: string | null;
  keyword?: string | null;
  status?: PolicyStatus | null;
  // 2026-09-03 추가: "직업 구분" 필터(회원가입/내 정보 수정의 occupation과 동일한
  // 5분류). age/region처럼 프로필 값으로 자동 채워지고, 필터바에서 바꿀 수 있다.
  occupation?: OccupationType | null;
  // 2026-09-02 추가: "장애인 대상만"/"보훈대상자 대상만" 좁혀보기 필터. 다른
  // 필드와 달리 프로필 값으로 자동 채우지 않는다(useAiPolicySearch.ts 참고) —
  // "나에게 맞는 조건"이 아니라 "이 대상군 정책만 보고 싶다"는 명시적 선택이라
  // 비장애인/비보훈대상자도 켤 수 있어야 한다.
  disability_target?: boolean | null;
  veteran_target?: boolean | null;
};

export type AiSearchMessageResult = {
  reply: string;
  filters: AiSearchFilters;
  items: PolicyBrowseItem[];
  total: number;
  page: number;
  page_size: number;
};

export type AiSearchResults = {
  items: PolicyBrowseItem[];
  total: number;
  page: number;
  page_size: number;
};

export async function sendAiSearchMessage(
  token: string,
  messages: PolicyChatMessage[],
  filters: AiSearchFilters | null,
  includeClosed: boolean,
  pageSize: number
): Promise<AiSearchMessageResult> {
  const res = await authedFetch("/policy_chat/ai_search/message", token, {
    method: "POST",
    body: JSON.stringify({ messages, filters, include_closed: includeClosed, page_size: pageSize }),
  });
  return res.json();
}

export async function fetchAiSearchResults(
  token: string,
  filters: AiSearchFilters,
  includeClosed: boolean,
  page: number,
  pageSize: number
): Promise<AiSearchResults> {
  const search = new URLSearchParams();
  if (filters.age != null) search.set("age", String(filters.age));
  if (filters.is_married != null) search.set("is_married", String(filters.is_married));
  if (filters.annual_income_krw != null) search.set("annual_income_krw", String(filters.annual_income_krw));
  if (filters.spouse_annual_income_krw != null) {
    search.set("spouse_annual_income_krw", String(filters.spouse_annual_income_krw));
  }
  if (filters.region) search.set("region", filters.region);
  if (filters.category) search.set("category", filters.category);
  if (filters.keyword) search.set("keyword", filters.keyword);
  if (filters.status) search.set("status", filters.status);
  if (filters.occupation) search.set("occupation", filters.occupation);
  if (filters.disability_target) search.set("disability_target", "true");
  if (filters.veteran_target) search.set("veteran_target", "true");
  if (includeClosed) search.set("include_closed", "true");
  search.set("page", String(page));
  search.set("page_size", String(pageSize));
  const res = await authedFetch(`/policy_chat/ai_search/results?${search.toString()}`, token);
  return res.json();
}

export type PolicyAnalysisResult = {
  fit: "적합" | "부적합";
  concerns: string | null;
  benefit_summary: string;
  application_notes: string;
  required_documents: string[];
  estimated_monthly_benefit_krw: number | null;
};

export async function analyzePolicy(token: string, policyKey: string): Promise<PolicyAnalysisResult> {
  const res = await authedFetch("/policy_chat/ai_search/analyze", token, {
    method: "POST",
    body: JSON.stringify({ policy_key: policyKey }),
  });
  return res.json();
}

export type PolicyQaMessage = { role: "user" | "assistant"; content: string };

// 정책별 챗봇: 사용자가 지금 보고 있는 정책 하나에 대해서만 자유롭게 질문한다
// (sendAiSearchMessage와 달리 필터를 바꾸지 않고, 정책 문서를 프롬프트로 넣은
// 순수 Q&A).
export async function sendPolicyQaMessage(
  token: string,
  policyKey: string,
  messages: PolicyQaMessage[]
): Promise<{ reply: string }> {
  const res = await authedFetch("/policy_chat/policy_qa/message", token, {
    method: "POST",
    body: JSON.stringify({ policy_key: policyKey, messages }),
  });
  return res.json();
}

// 2026-09-01 UPGRADE.md 반영, 2026-09-03 전면 재작업: 저축플랜 → 정책연계형
// 시뮬레이터. 청년도약계좌는 2025-12-31 신규가입이 종료돼 후속 상품인
// 청년미래적금 기준으로 다시 만들었고, 매칭비율/금리/LTV도 예시가 아니라 실제
// 정부 고시 수치로 교체했다(백엔드 savings_simulator/simulator.py 상단 주석 참고
// — 다만 비교용 시중 금리 자체는 은행마다 달라 여전히 가정치다).
export type YouthFutureSavingsInput = {
  monthly_amount_krw: number;
  annual_income_krw: number;
  seed_money_krw?: number;
};

// 2026-09-02 추가: 위 계산과 별개로, 이 목록은 DB에 실제로 있는 저축/자산형성
// 정책 중 지금 로그인한 유저가 진짜 자격되는 것만 골라 보여준다(백엔드
// savings_simulator/simulator.py의 match_real_savings_policies 참고).
export type MatchedSavingsPolicy = {
  policy_key: string;
  policy_name: string;
  benefit_description: string;
  application_period: string;
  reference_url: string;
};

export type YouthFutureSavingsOutput = {
  eligible: boolean;
  matching_rate: number;
  eligibility_note: string;
  policy_total_krw: number;
  market_total_krw: number;
  benefit_diff_krw: number;
  summary: string;
  matched_policies: MatchedSavingsPolicy[];
};

export async function simulateYouthFutureSavings(
  token: string,
  input: YouthFutureSavingsInput
): Promise<YouthFutureSavingsOutput> {
  const res = await authedFetch("/savings_simulator/youth_future_savings", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
  return res.json();
}

export type HousingLoanInput = {
  housing_type: "jeonse" | "purchase";
  target_price_krw: number;
  self_capital_krw: number;
  household_annual_income_krw: number;
  // 2026-09-03 추가: 디딤돌대출은 대출기간(10/15/20/30년)마다 금리가 다르다.
  loan_term_years?: 10 | 15 | 20 | 30;
};

export type HousingLoanOutput = {
  eligible: boolean;
  product_name: string;
  ltv_rate: number;
  policy_rate: number;
  market_rate: number;
  loan_amount_krw: number;
  monthly_interest_krw: number;
  market_monthly_interest_krw: number;
  monthly_saving_krw: number;
  summary: string;
  matched_policies: MatchedSavingsPolicy[];
};

export async function simulateHousingLoan(token: string, input: HousingLoanInput): Promise<HousingLoanOutput> {
  const res = await authedFetch("/savings_simulator/housing_loan", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
  return res.json();
}

export type AdminOverview = {
  total_users: number;
  married_users: number;
  total_policies: number;
  last_cache_refreshed_at: string | null;
  policies_missing_link: number;
  policies_expired: number;
  nationwide_template_policies: number;
  total_recommendations: number;
  unread_recommendations: number;
};

export type AdminUserItem = {
  id: number;
  email: string;
  age: number | null;
  is_married: boolean | null;
  annual_income_krw: number | null;
  region: string | null;
  occupation: OccupationType | null;
  created_at: string | null;
};

export type AdminUserListResponse = {
  users: AdminUserItem[];
  total: number;
};

export type AdminSignupTrendPoint = { date: string; count: number };

export type AdminSignupTrendResponse = {
  points: AdminSignupTrendPoint[];
  unknown_signup_date_count: number;
};

export type AdminCategoryStat = { name: string; count: number };
export type AdminStatusStat = { status: string; count: number };

export type AdminPolicyStatsResponse = {
  total: number;
  by_category: AdminCategoryStat[];
  by_status: AdminStatusStat[];
  missing_link_count: number;
  nationwide_template_count: number;
  last_refreshed_at: string | null;
};

export type AdminPolicyItem = {
  policy_key: string;
  policy_name: string;
  description: string;
  large_category: string;
  status: string;
  application_period: string;
  region_code: string;
  apply_url: string;
  refreshed_at: string;
};

export type AdminPolicyListResponse = {
  items: AdminPolicyItem[];
  total: number;
  page: number;
  page_size: number;
};

export async function getAdminOverview(token: string): Promise<AdminOverview> {
  const res = await authedFetch("/admin/overview", token);
  return res.json();
}

export async function getAdminUsers(token: string): Promise<AdminUserListResponse> {
  const res = await authedFetch("/admin/users", token);
  return res.json();
}

export async function getAdminSignupTrend(token: string, days = 14): Promise<AdminSignupTrendResponse> {
  const res = await authedFetch(`/admin/users/signup-trend?days=${days}`, token);
  return res.json();
}

export async function getAdminPolicyStats(token: string): Promise<AdminPolicyStatsResponse> {
  const res = await authedFetch("/admin/policies/stats", token);
  return res.json();
}

export async function getAdminPolicyList(
  token: string,
  params: { keyword?: string; category?: string; status?: string; page?: number; pageSize?: number } = {}
): Promise<AdminPolicyListResponse> {
  const search = new URLSearchParams();
  if (params.keyword) search.set("keyword", params.keyword);
  if (params.category) search.set("category", params.category);
  if (params.status) search.set("status", params.status);
  search.set("page", String(params.page ?? 1));
  search.set("page_size", String(params.pageSize ?? 20));
  const res = await authedFetch(`/admin/policies/list?${search.toString()}`, token);
  return res.json();
}

export async function refreshAdminPolicyCache(token: string): Promise<{ upserted: number }> {
  const res = await authedFetch("/admin/policies/refresh", token, { method: "POST" });
  return res.json();
}

// 2026-09-03 추가: 온통청년 원본 코드값 점검 화면. 별도 테이블 없이 cached_policies를
// 매 요청마다 그대로 집계해서 내려주므로("항상 최신화" 요구사항), 배치가 갱신할
// 때마다 자동으로 최신 값이 된다 — 프론트는 그냥 이 응답을 그대로 보여주면 된다.
export type AdminMaritalStatusCode = { value: string; count: number; label: string | null };
export type AdminRegionPrefix = { prefix: string; count: number; mapped_region_names: string[] };
export type AdminCategoryTagCount = { value: string; count: number; is_known: boolean };
export type AdminMidCategoryValue = { value: string; count: number };

export type AdminCodeValuesResponse = {
  generated_at: string;
  cache_last_refreshed_at: string | null;
  total_policies: number;
  marital_status_codes: AdminMaritalStatusCode[];
  nationwide_region_count: number;
  region_prefixes: AdminRegionPrefix[];
  large_category_tags: AdminCategoryTagCount[];
  mid_categories: AdminMidCategoryValue[];
};

export async function getAdminCodeValues(token: string): Promise<AdminCodeValuesResponse> {
  const res = await authedFetch("/admin/policies/code-values", token);
  return res.json();
}
