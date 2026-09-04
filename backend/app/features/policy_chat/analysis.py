from typing import Literal

from pydantic import BaseModel, ValidationError

from app.auth.models import User
from app.features.policy_matcher.categories import category_tags
from app.features.policy_matcher.matching import OCCUPATION_LABELS, REGIONS, region_names_for_prefix
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.status import compute_policy_status, today_kst
from app.llm.base import Message
from app.llm.factory import get_provider
from app.tools.base import ToolSpec


class PolicyAnalysisResult(BaseModel):
    # 자유 텍스트로 두면 "조건부 적합"처럼 애매한 값이 섞여 프론트에서 원 색깔로
    # 표시하기 어려워진다 — 좋다/나쁘다 둘 중 하나로만 강제한다(2026-08-26 요청).
    fit: Literal["적합", "부적합"]
    # 적합할 때는 이유를 안 적어도 된다 — 부적합일 때만 우려 지점을 채운다.
    concerns: str | None = None
    benefit_summary: str
    application_notes: str
    # 신청 전에 미리 챙겨야 할 서류/조건 체크리스트 — application_notes(문장형
    # 유의사항)와 별도로 목록 형태로 둬야 프론트에서 리스트로 렌더링할 수 있다.
    required_documents: list[str] = []
    # 저축플랜 탭에 반영할 수 있도록 benefit_summary(자유 텍스트)와 별도로
    # 숫자 필드를 둔다 — 매달 반복 지급되는 금전 혜택이 명확할 때만 채우고,
    # 일회성 지원금/대출/비금전 혜택이면 반드시 None으로 둔다(2026-08-27 요청).
    estimated_monthly_benefit_krw: int | None = None


def _profile_text(user: User) -> str:
    lines = []
    if user.age is not None:
        lines.append(f"나이: {user.age}세")
    if user.is_married is not None:
        lines.append(f"기혼 여부: {'기혼' if user.is_married else '미혼'}")
    if user.annual_income_krw is not None:
        lines.append(f"연소득: {user.annual_income_krw:,}원")
    if user.is_married and user.spouse_annual_income_krw is not None:
        lines.append(f"배우자 연소득: {user.spouse_annual_income_krw:,}원")
    if user.region is not None:
        lines.append(f"거주 지역: {user.region}")
    # 2026-09-05 감사(사용자 요청: "다른 부분들도 제대로 들어가고 있는지 확인해봐")
    # 중 발견 — occupation/is_sme_employee/has_disability/is_veteran은 matching.py의
    # TARGETING_RULES가 정책 목록을 거르는 데 실제로 쓰는데, 개별 정책의 AI 분석
    # 리포트/정책별 챗봇(_profile_text를 같이 씀)엔 이 정보가 아예 안 들어가고
    # 있었다 — 재직자 전용 정책을 학생이 봐도 "적합"으로 오판할 수 있는 정보 공백.
    if user.occupation is not None:
        lines.append(f"직업: {OCCUPATION_LABELS.get(user.occupation, user.occupation)}")
    if user.is_sme_employee is not None:
        lines.append(f"중소기업 재직 여부: {'재직' if user.is_sme_employee else '비재직'}")
    if user.has_disability is not None:
        lines.append(f"장애인 여부: {'해당' if user.has_disability else '해당 없음'}")
    if user.is_veteran is not None:
        lines.append(f"국가보훈대상자 여부: {'해당' if user.is_veteran else '해당 없음'}")
    return "\n".join(lines) if lines else "(등록된 정보 없음)"


# 2026-09-05 발견(사용자 지적: "지역 매핑이 안 되고 있나? AI 분석 리포트가 자꾸
# 지역으로 부적합이라고 나와, K패스도") — K패스처럼 진짜 전국 상품인 정책도
# region_code엔 법정동코드 187개가 콤마로 나열돼 있다(youth_center_client.py가
# 원본 API를 그대로 캐시하기 때문). 이걸 프롬프트에 그대로 덤프하면(예전 코드)
# LLM이 이 숫자 뭉치를 해석 못 하고, 시스템 프롬프트의 "애매하면 보수적으로
# 부적합"을 그대로 따라 지역 때문에 부적합 처리해버렸다 — marital_status 원본
# 코드값을 프롬프트에서 뺀 것과 같은 종류의 버그다. 사람이 읽을 수 있는 지역명
# 목록(또는 대부분 전국이면 "전국")으로 요약해서 넣는다.
_NATIONWIDE_SUMMARY_THRESHOLD = 15  # matching._NATIONWIDE_TEMPLATE_PROVINCE_THRESHOLD와 동일 기준


def _region_summary(policy: CachedPolicy) -> str | None:
    if not policy.region_code:
        return None
    prefixes = {code.strip()[:2] for code in policy.region_code.split(",") if code.strip()}
    matched_names: set[str] = set()
    for prefix in prefixes:
        matched_names.update(region_names_for_prefix(prefix))
    if not matched_names:
        return None
    if len(matched_names) >= _NATIONWIDE_SUMMARY_THRESHOLD:
        return "전국 (지역 제한 없음)"
    return ", ".join(name for name in REGIONS if name in matched_names)


def _policy_text(policy: CachedPolicy) -> str:
    status, emoji = compute_policy_status(policy.apply_start_ymd, policy.apply_end_ymd, today_kst())
    lines = [
        f"정책명: {policy.policy_name}",
        f"분야: {', '.join(category_tags(policy.large_category)) or '기타'}",
        f"설명: {policy.description}",
        f"신청 기간: {policy.application_period} (현재 상태: {emoji} {status})",
    ]
    if policy.min_age is not None or policy.max_age is not None:
        min_age = f"{policy.min_age}세" if policy.min_age is not None else "제한 없음"
        max_age = f"{policy.max_age}세" if policy.max_age is not None else "제한 없음"
        lines.append(f"연령 조건: {min_age} ~ {max_age}")
    if policy.min_income_krw is not None or policy.max_income_krw is not None:
        min_income = f"{policy.min_income_krw:,}원" if policy.min_income_krw is not None else "제한 없음"
        max_income = f"{policy.max_income_krw:,}원" if policy.max_income_krw is not None else "제한 없음"
        lines.append(f"소득 조건: {min_income} ~ {max_income}")
    # 2026-09-02 QA에서 발견: marital_status는 온통청년 API의 원본 mrgSttsCd 코드값
    # ("0055003" 등)이지 "기혼"/"미혼" 같은 사람이 읽을 문자열이 아니다(matching.py의
    # 혼인상태 필터 주석 참고 — 공통코드 표를 못 구해 못 옮겼고, 실측상 97%가 이
    # 코드 하나로 쏠려있어 사실상 "제한없음" sentinel이나 다름없다). 이걸 프롬프트에
    # 그대로 넣으면 LLM이 의미를 모른 채 "혼인 조건 코드: 0055003"이라고 그대로
    # 사용자에게 되읽어주는 게 실제로 확인됐다 — 의미 있는 값으로 바꿀 수 없으니
    # 아예 프롬프트에서 뺀다(안 넣는 게 이상한 코드를 노출하는 것보다 낫다).
    region_summary = _region_summary(policy)
    if region_summary:
        lines.append(f"지역 조건: {region_summary}")
    # 2026-09-04 추가: 사용자가 "K패스 필요서류가 뭐야?"라고 물었을 때 챗봇이
    # "모른다"고 답한 원인을 조사하다가 발견 — sbmsnDcmntCn(제출서류)/
    # plcyAplyMthdCn(신청방법)은 온통청년 API에 실제로 존재하는 필드인데(라이브
    # 조회 기준 각각 34%/55% 정책에 값이 채워져 있음) 이 필드 자체를 캐시하지
    # 않고 있었다 — 그래서 실제 서류 정보가 있는 정책도 "모른다"고 답할 수밖에
    # 없었다(K패스 자체는 우연히 진짜로 서류가 없는 경우였다). 값이 있을 때만
    # 넣는다 — 없으면 이전처럼 LLM이 "정책 정보에 없다"고 정직하게 답한다.
    if policy.required_documents:
        lines.append(f"제출 서류: {policy.required_documents}")
    if policy.application_method:
        lines.append(f"신청 방법: {policy.application_method}")
    return "\n".join(lines)


_SYSTEM_PROMPT = (
    "당신은 청년/신혼부부를 위한 정책 분석 도우미입니다. 아래 사용자 프로필과 정책 정보를 "
    "바탕으로 이 사용자에게 이 정책이 적합한지 분석해 반드시 policy_analysis_result 도구를 "
    "호출해 결과를 반환하세요.\n\n"
    "- fit: 프로필 조건(나이/소득/혼인/지역/직업/중소기업 재직/장애인 및 국가보훈대상자 해당 여부)과 "
    "정책 조건을 대조해 '적합' 또는 '부적합' 중 하나로만 판단하세요. 프로필에 없는(안 밝혀진) 조건은 "
    "대조하지 말고 무시하세요 — 없는 정보로 부적합 판단을 내리지 마세요. 애매하면 보수적으로 "
    "'부적합'으로 판단하세요.\n"
    "- concerns: fit이 '적합'이면 비워두세요. fit이 '부적합'이면 어떤 조건이 왜 우려되는지 한두 "
    "문장으로만 적으세요 — 적합한 이유는 설명하지 마세요.\n"
    "- benefit_summary: 이 정책이 제공하는 예상 혜택을 간결하게 요약하세요.\n"
    "- application_notes: 신청 시 유의사항을 간결하게 적으세요(구비 서류 목록은 여기 말고 "
    "required_documents에 담으세요).\n"
    "- required_documents: 신청 전에 미리 준비해야 할 서류나 증빙(예: 재직증명서, 주민등록등본, "
    "소득금액증명원 등)을 항목별로 나열하세요. 정책 정보에 구체적인 서류가 안 나와 있으면 "
    "일반적으로 요구되는 서류를 상식선에서 제시하되, 정책과 무관한 내용은 지어내지 마세요. "
    "필요한 서류가 전혀 없다고 판단되면 빈 리스트로 두세요.\n"
    "- estimated_monthly_benefit_krw: 정책 설명에 매달 반복적으로 지급되는 금전 혜택 금액이 "
    "명확히 나와 있을 때만(예: '월 20만원 지원') 그 숫자(원)를 채우세요. 일회성 지원금, 대출, "
    "우선 입주 자격처럼 매달 반복되는 금전이 아니거나 구체적 금액이 없으면 반드시 null로 "
    "두세요 — 추측해서 숫자를 만들어내지 마세요.\n\n"
    "정책 데이터에 없는 내용은 추측해서 지어내지 마세요."
)

# 실제 실행 로직은 없다 — provider.chat(tools=[...])의 함수 호출 스키마 계약으로만
# 쓰이고, 결과는 generate_policy_report()가 tool_call 인자를 직접 파싱해서 쓴다.
# ALL_TOOL_SPECS에는 등록하지 않는다(policy_chat.ai_search.FILTER_DELTA_SPEC과 동일한 이유).
ANALYSIS_RESULT_SPEC = ToolSpec(
    name="policy_analysis_result",
    description="사용자 프로필과 정책 조건을 대조한 개인화 분석 결과를 구조화된 형태로 반환합니다.",
    input_schema=PolicyAnalysisResult,
    output_schema=PolicyAnalysisResult,
    entrypoint=lambda input, ctx: input,
)

_FALLBACK_RESULT = PolicyAnalysisResult(
    fit="부적합",
    concerns="분석 결과를 생성하지 못했습니다. 잠시 후 다시 시도해주세요.",
    benefit_summary="",
    application_notes="",
    required_documents=[],
)


def generate_policy_report(user: User, policy: CachedPolicy) -> PolicyAnalysisResult:
    provider = get_provider()
    user_msg = f"[사용자 프로필]\n{_profile_text(user)}\n\n[정책 정보]\n{_policy_text(policy)}"
    response = provider.chat(
        [Message(role="system", content=_SYSTEM_PROMPT), Message(role="user", content=user_msg)],
        tools=[ANALYSIS_RESULT_SPEC],
    )
    if not response.tool_calls:
        return _FALLBACK_RESULT
    try:
        return PolicyAnalysisResult(**response.tool_calls[0].arguments)
    except (TypeError, ValidationError):
        return _FALLBACK_RESULT
