from datetime import datetime, timezone

from app.auth.models import User
from app.features.policy_chat import analysis
from app.features.policy_chat.analysis import PolicyAnalysisResult
from app.features.policy_matcher.models import CachedPolicy
from app.llm.base import LLMResponse, ToolCallRequest


def _user(**overrides) -> User:
    defaults = dict(
        id=1,
        email="a@example.com",
        hashed_password="x",
        age=29,
        is_married=False,
        annual_income_krw=40_000_000,
        region="서울",
    )
    defaults.update(overrides)
    return User(**defaults)


def _policy(**overrides) -> CachedPolicy:
    defaults = dict(
        policy_key="P1",
        policy_name="청년 월세 지원",
        description="월 20만원 지원",
        apply_url="https://example.com",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=19,
        max_age=34,
        min_income_krw=None,
        max_income_krw=26_000_000,
        marital_status="",
        region_code="",
        large_category="주거",
        mid_category="",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return CachedPolicy(**defaults)


class _FakeProvider:
    def __init__(self, response: LLMResponse):
        self._response = response
        self.calls: list[tuple] = []

    def chat(self, messages, tools):
        self.calls.append((messages, tools))
        return self._response


def test_policy_text_omits_raw_marital_status_code():
    # 2026-09-02 QA에서 발견: marital_status는 "0055003" 같은 원본 API 코드값이지
    # 사람이 읽을 문자열이 아닌데, 프롬프트에 그대로 들어가면 LLM이 그 코드를 그대로
    # 사용자에게 되읽어줬다 — 아예 프롬프트에서 빼야 한다.
    policy = _policy(marital_status="0055003")
    text = analysis._policy_text(policy)
    assert "0055003" not in text
    assert "혼인 조건 코드" not in text


def test_policy_text_includes_required_documents_and_application_method_when_present():
    # 2026-09-04 사용자 지적("K패스 필요서류 모른다는데 실제로 없어서 그런거야,
    # 아니면 못찾아오는거야?") 조사 중 발견 — sbmsnDcmntCn/plcyAplyMthdCn은 실제
    # API 필드인데 캐시에 안 담고 있어서, 값이 있는 정책도 챗봇이 "모른다"고
    # 답할 수밖에 없었다. 값이 있으면 프롬프트에 포함돼야 한다.
    policy = _policy(required_documents="주민등록등본, 소득금액증명원", application_method="온라인 신청")
    text = analysis._policy_text(policy)
    assert "주민등록등본, 소득금액증명원" in text
    assert "온라인 신청" in text


def test_policy_text_omits_required_documents_and_application_method_when_absent():
    # K패스처럼 실제로 해당 정보가 없는 정책은 있는 척 지어내지 않고 아예 프롬프트에서
    # 빠져야(LLM이 "모른다"고 정직하게 답하도록) 한다.
    policy = _policy(required_documents="", application_method="")
    text = analysis._policy_text(policy)
    assert "제출 서류" not in text
    assert "신청 방법" not in text


def test_generate_policy_report_calls_llm_once_via_tool_call(monkeypatch):
    fake = _FakeProvider(
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCallRequest(
                    name="policy_analysis_result",
                    arguments={
                        "fit": "적합",
                        "concerns": None,
                        "benefit_summary": "월 20만원 지원",
                        "application_notes": "재직 증명서를 준비하세요.",
                        "required_documents": ["재직증명서", "주민등록등본"],
                        "estimated_monthly_benefit_krw": 200_000,
                    },
                )
            ],
        )
    )
    monkeypatch.setattr(analysis, "get_provider", lambda: fake)

    result = analysis.generate_policy_report(_user(), _policy())

    assert result == PolicyAnalysisResult(
        fit="적합",
        concerns=None,
        benefit_summary="월 20만원 지원",
        application_notes="재직 증명서를 준비하세요.",
        required_documents=["재직증명서", "주민등록등본"],
        estimated_monthly_benefit_krw=200_000,
    )
    assert len(fake.calls) == 1
    messages, tools = fake.calls[0]
    assert tools[0].name == "policy_analysis_result"
    assert messages[0].role == "system"
    assert "청년 월세 지원" in messages[1].content
    assert "29세" in messages[1].content


def test_generate_policy_report_defaults_required_documents_to_empty_list_when_omitted(monkeypatch):
    fake = _FakeProvider(
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCallRequest(
                    name="policy_analysis_result",
                    arguments={
                        "fit": "적합",
                        "benefit_summary": "월 20만원 지원",
                        "application_notes": "특별한 유의사항 없음",
                    },
                )
            ],
        )
    )
    monkeypatch.setattr(analysis, "get_provider", lambda: fake)

    result = analysis.generate_policy_report(_user(), _policy())

    assert result.required_documents == []


def test_generate_policy_report_defaults_estimated_monthly_benefit_to_none_when_omitted(monkeypatch):
    fake = _FakeProvider(
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCallRequest(
                    name="policy_analysis_result",
                    arguments={
                        "fit": "적합",
                        "benefit_summary": "우선 입주 자격 부여",
                        "application_notes": "특별한 유의사항 없음",
                    },
                )
            ],
        )
    )
    monkeypatch.setattr(analysis, "get_provider", lambda: fake)

    result = analysis.generate_policy_report(_user(), _policy())

    assert result.estimated_monthly_benefit_krw is None


def test_generate_policy_report_falls_back_when_no_tool_call(monkeypatch):
    fake = _FakeProvider(LLMResponse(content="그냥 텍스트로만 답했어요", tool_calls=[]))
    monkeypatch.setattr(analysis, "get_provider", lambda: fake)

    result = analysis.generate_policy_report(_user(), _policy())

    assert result.fit == "부적합"
    assert result.concerns


def test_generate_policy_report_falls_back_when_tool_call_has_invalid_fit_value(monkeypatch):
    # fit은 "적합"/"부적합" Literal이라 모델이 다른 값(예: "조건부 적합")을 내면
    # 검증에 실패해야 한다 — 프론트에서 원 색깔을 이분법으로만 표시하기 위함.
    fake = _FakeProvider(
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCallRequest(
                    name="policy_analysis_result",
                    arguments={
                        "fit": "조건부 적합",
                        "benefit_summary": "월 20만원 지원",
                        "application_notes": "",
                    },
                )
            ],
        )
    )
    monkeypatch.setattr(analysis, "get_provider", lambda: fake)

    result = analysis.generate_policy_report(_user(), _policy())

    assert result.fit == "부적합"
    assert result.concerns
