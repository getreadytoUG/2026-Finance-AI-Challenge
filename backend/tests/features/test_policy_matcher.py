from app.features.policy_matcher import tool
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.tool import TOOL_SPEC, run
from app.features.policy_matcher.youth_center_client import RawYouthPolicy
from app.tools.base import ToolContext

CTX = ToolContext(user_id=1, db=None)


def _policy(**overrides) -> RawYouthPolicy:
    defaults = dict(
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
    )
    defaults.update(overrides)
    return RawYouthPolicy(**defaults)


def test_tool_spec_has_expected_name_and_schemas():
    assert TOOL_SPEC.name == "policy_matcher"
    assert TOOL_SPEC.entrypoint is run


def test_run_marks_policy_without_conditions_always_eligible(monkeypatch):
    monkeypatch.setattr(tool, "fetch_policies", lambda query=None: [_policy()])
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    assert result.options[0].eligible is True


def test_run_marks_applicant_outside_age_range_ineligible(monkeypatch):
    monkeypatch.setattr(tool, "fetch_policies", lambda query=None: [_policy(min_age=19, max_age=34)])
    result = run(PolicyMatchInput(age=50, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    assert result.options[0].eligible is False


def test_run_requires_marriage_when_policy_restricts_to_married(monkeypatch):
    monkeypatch.setattr(tool, "fetch_policies", lambda query=None: [_policy(marital_status="기혼")])
    single = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    married = run(PolicyMatchInput(age=29, is_married=True, annual_income_krw=40_000_000, region="서울"), CTX)
    assert single.options[0].eligible is False
    assert married.options[0].eligible is True


def test_run_marks_applicant_over_income_ceiling_ineligible(monkeypatch):
    monkeypatch.setattr(tool, "fetch_policies", lambda query=None: [_policy(max_income_krw=30_000_000)])
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    assert result.options[0].eligible is False


def test_run_marks_applicant_below_income_floor_ineligible(monkeypatch):
    monkeypatch.setattr(tool, "fetch_policies", lambda query=None: [_policy(min_income_krw=50_000_000)])
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    assert result.options[0].eligible is False


def test_run_marks_applicant_outside_region_ineligible(monkeypatch):
    monkeypatch.setattr(tool, "fetch_policies", lambda query=None: [_policy(region_code="부산")])
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    assert result.options[0].eligible is False


def test_run_maps_policy_fields_into_output_option(monkeypatch):
    monkeypatch.setattr(
        tool,
        "fetch_policies",
        lambda query=None: [
            _policy(
                policy_name="청년 월세 지원",
                description="월 20만원 지원",
                apply_url="https://example.com/apply",
                application_period="2026-01-01 ~ 2026-12-31",
            )
        ],
    )
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), CTX)
    option = result.options[0]
    assert option.policy_name == "청년 월세 지원"
    assert option.benefit_description == "월 20만원 지원"
    assert option.reference_url == "https://example.com/apply"
    assert option.application_period == "2026-01-01 ~ 2026-12-31"
