import type { OccupationType } from "@/lib/profileOptions";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type SocialProvider = "kakao" | "naver";

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
      if (typeof body.detail === "string") detail = body.detail;
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
      if (typeof body.detail === "string") detail = body.detail;
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
};

export type ProfileInput = {
  age: number;
  is_married: boolean;
  annual_income_krw: number;
  region: string;
  occupation: OccupationType;
  spouse_age?: number | null;
  spouse_annual_income_krw?: number | null;
  spouse_occupation?: OccupationType | null;
};

export type Recommendation = {
  id: number;
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
      if (typeof body.detail === "string") detail = body.detail;
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
};

export type MarriagePolicyItem = {
  policy_key: string;
  policy_name: string;
  benefit_description: string;
  application_period: string;
  reference_url: string;
  is_newlywed_policy: boolean;
};

export type MarriageComparisonOutput = {
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

export type LinkedBenefit = {
  id: number;
  policy_key: string;
  policy_name: string;
  estimated_monthly_benefit_krw: number;
  linked_at: string;
};

export type LinkedBenefitListResponse = {
  items: LinkedBenefit[];
  total_monthly_benefit_krw: number;
};

export async function listSavingsLinkedBenefits(token: string): Promise<LinkedBenefitListResponse> {
  const res = await authedFetch("/savings_planner/linked_benefits", token);
  return res.json();
}

export async function linkSavingsBenefit(
  token: string,
  policyKey: string,
  policyName: string,
  estimatedMonthlyBenefitKrw: number
): Promise<LinkedBenefit> {
  const res = await authedFetch("/savings_planner/linked_benefits", token, {
    method: "POST",
    body: JSON.stringify({
      policy_key: policyKey,
      policy_name: policyName,
      estimated_monthly_benefit_krw: estimatedMonthlyBenefitKrw,
    }),
  });
  return res.json();
}

export async function unlinkSavingsBenefit(token: string, id: number): Promise<void> {
  await authedFetch(`/savings_planner/linked_benefits/${id}`, token, { method: "DELETE" });
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
