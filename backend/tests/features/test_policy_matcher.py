import itertools
from datetime import datetime, timezone

from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.tool import TOOL_SPEC, run
from app.tools.base import ToolContext

_key_seq = itertools.count(1)


def _seed_policy(db_session, **overrides) -> CachedPolicy:
    defaults = dict(
        policy_key=f"P{next(_key_seq)}",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category=FINANCIAL_LARGE_CATEGORY,
        mid_category="취약계층 및 금융지원",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    row = CachedPolicy(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


def _ctx(db_session) -> ToolContext:
    return ToolContext(user_id=1, db=db_session)


def test_tool_spec_has_expected_name_and_schemas():
    assert TOOL_SPEC.name == "policy_matcher"
    assert TOOL_SPEC.entrypoint is run


def test_run_includes_eligible_financial_policy_without_conditions(db_session):
    _seed_policy(db_session)
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert len(result.options) == 1
    assert result.options[0].policy_name == "테스트 정책"


def test_run_excludes_applicant_outside_age_range(db_session):
    _seed_policy(db_session, min_age=19, max_age=34)
    result = run(PolicyMatchInput(age=50, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert result.options == []


_15_PROVINCE_CODES = ",".join(
    f"{p}110" for p in ("11", "26", "27", "28", "29", "30", "31", "36", "41", "51", "43", "44", "52", "46", "47")
)  # 17개 시도 중 15개 — matching.is_likely_template_region_code 임계치


def test_run_excludes_policy_with_template_region_code(db_session):
    # 2026-09-03 사용자 지적: 서울로 프로필을 해놨는데 의성/서산 같은 지자체 전용
    # 정책이 나왔다 — zipCd에 거의 모든 시/도가 나열된(템플릿/기본값) 레코드가
    # region_matches()엔 "서울도 포함"으로 보였기 때문. "내 맞춤 정책 보기"도
    # recommender.py와 동일하게 이런 레코드를 걸러야 한다.
    _seed_policy(db_session, region_code=_15_PROVINCE_CODES)
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert result.options == []


def test_run_excludes_student_only_policy_for_non_student_occupation(db_session):
    # 2026-09-03 사용자 지적: "40대인데 국가근로장학금이 뜬다" — 실제로 이 정책이
    # 나이/소득 조건 없이 schoolCd(대학 재학)만으로 재학생을 가리고 있었다.
    _seed_policy(db_session, policy_name="국가근로장학금", school_code="0049005")
    result = run(
        PolicyMatchInput(age=45, is_married=False, annual_income_krw=40_000_000, region="서울", occupation="employee"),
        _ctx(db_session),
    )
    assert result.options == []

    result = run(
        PolicyMatchInput(age=22, is_married=False, annual_income_krw=0, region="서울", occupation="student"),
        _ctx(db_session),
    )
    assert [o.policy_name for o in result.options] == ["국가근로장학금"]


def test_run_narrows_by_district_when_region_includes_gu(db_session):
    # 2026-09-03 PLAN.md #2 — "서울 강남구"처럼 구/군까지 지정하면 5자리
    # 법정동코드로 정밀 매칭한다(matching.district_codes 참고).
    _seed_policy(db_session, policy_name="강남구 청년 지원", region_code="11680")
    _seed_policy(db_session, policy_name="종로구 청년 지원", region_code="11110")

    result = run(
        PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울 강남구"),
        _ctx(db_session),
    )
    assert [o.policy_name for o in result.options] == ["강남구 청년 지원"]


def test_run_excludes_sme_only_policy_for_non_sme_employee(db_session):
    # 2026-09-03 사용자 지적: "중소기업 다닌다고 해도 관련 없는 정책 뜬다".
    _seed_policy(db_session, policy_name="중소기업 청년 지원", sbiz_code="0014001")
    result = run(
        PolicyMatchInput(
            age=29, is_married=False, annual_income_krw=40_000_000, region="서울", is_sme_employee=False
        ),
        _ctx(db_session),
    )
    assert result.options == []

    result = run(
        PolicyMatchInput(
            age=29, is_married=False, annual_income_krw=40_000_000, region="서울", is_sme_employee=True
        ),
        _ctx(db_session),
    )
    assert [o.policy_name for o in result.options] == ["중소기업 청년 지원"]


def test_run_includes_wide_region_policy_when_institution_is_central_government(db_session):
    # 2026-09-03 사용자 지적: "햇살론유스가 왜 안 나오지?" — 서민금융진흥원(중앙부처)이
    # 운영하는 진짜 전국 상품인데도 zipCd가 17개 시도를 다 나열한 형태라 위 필터에
    # 잘못 걸려 빠지고 있었다. 제공기관그룹코드가 중앙부처(0054001)로 확인되면
    # 걸러지지 않아야 한다(matching.py 주석 참고).
    _seed_policy(db_session, policy_name="햇살론유스", region_code=_15_PROVINCE_CODES, institution_group_code="0054001")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert [o.policy_name for o in result.options] == ["햇살론유스"]


def test_run_requires_marriage_when_policy_restricts_to_married(db_session):
    # "0055001" = 온통청년 공식 mrgSttsCd 기혼 코드(matching.MARITAL_STATUS_LABELS).
    _seed_policy(db_session, marital_status="0055001")
    single = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    married = run(PolicyMatchInput(age=29, is_married=True, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert single.options == []
    assert len(married.options) == 1


def test_run_excludes_applicant_over_income_ceiling(db_session):
    _seed_policy(db_session, max_income_krw=30_000_000)
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert result.options == []


def test_run_excludes_applicant_below_income_floor(db_session):
    _seed_policy(db_session, min_income_krw=50_000_000)
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert result.options == []


def test_run_excludes_applicant_outside_region(db_session):
    _seed_policy(db_session, region_code="부산")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert result.options == []


def test_run_includes_applicant_inside_region(db_session):
    _seed_policy(db_session, region_code="11110,11140,26110")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert len(result.options) == 1


def test_run_excludes_region_restricted_policy_when_input_region_empty(db_session):
    _seed_policy(db_session, region_code="부산")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region=""), _ctx(db_session))
    assert result.options == []


def test_run_excludes_ineligible_policies_entirely(db_session):
    _seed_policy(db_session, policy_name="부적격 정책", min_age=50)
    _seed_policy(db_session, policy_name="적격 정책")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    names = [o.policy_name for o in result.options]
    assert names == ["적격 정책"]


def test_run_includes_non_financial_policy_when_eligible(db_session):
    # 2026-09-03 사용자 요청: "내 맞춤 정책 보기"가 예전엔 "금융･복지･문화"
    # 대분류로만 좁혔었는데(그러다 보니 실제 조건으로는 0건이 나오는 경우가 잦았다),
    # 이제 전 분야를 다 보여준다 — "정책 전체 보기"와 동일한 범위.
    _seed_policy(db_session, policy_name="일자리 정책", large_category="일자리")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert [o.policy_name for o in result.options] == ["일자리 정책"]


def test_run_sorts_newlywed_policies_first_when_married(db_session):
    _seed_policy(db_session, policy_name="일반 청년 대출")
    _seed_policy(db_session, policy_name="신혼부부 전세자금 대출")
    _seed_policy(db_session, policy_name="또 다른 일반 정책")
    result = run(PolicyMatchInput(age=29, is_married=True, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    names = [o.policy_name for o in result.options]
    assert names == ["신혼부부 전세자금 대출", "일반 청년 대출", "또 다른 일반 정책"]


def test_run_does_not_reorder_when_not_married(db_session):
    _seed_policy(db_session, policy_name="일반 청년 대출")
    _seed_policy(db_session, policy_name="신혼부부 전세자금 대출")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    names = [o.policy_name for o in result.options]
    assert names == ["일반 청년 대출", "신혼부부 전세자금 대출"]


def test_run_marks_is_newlywed_policy_flag_on_options(db_session):
    _seed_policy(db_session, policy_name="신혼부부 전세자금 대출")
    _seed_policy(db_session, policy_name="일반 청년 대출")
    result = run(PolicyMatchInput(age=29, is_married=True, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    flags = {o.policy_name: o.is_newlywed_policy for o in result.options}
    assert flags["신혼부부 전세자금 대출"] is True
    assert flags["일반 청년 대출"] is False


def test_run_uses_combined_household_income_when_spouse_income_given(db_session):
    _seed_policy(db_session, max_income_krw=50_000_000)
    result = run(
        PolicyMatchInput(
            age=29,
            is_married=True,
            annual_income_krw=40_000_000,
            region="서울",
            spouse_annual_income_krw=20_000_000,
        ),
        _ctx(db_session),
    )
    assert result.options == []


def test_run_computes_real_status_instead_of_hardcoding_available(db_session):
    # 2026-09-02 QA에서 발견: 대시보드가 이 output을 그대로 써서 "신청 가능"을
    # 하드코딩했었다 — 실제로 만료된 정책도 status가 정확히 "만료"로 나와야 한다.
    _seed_policy(db_session, policy_name="이미 마감된 정책", apply_start_ymd="20200101", apply_end_ymd="20200201")
    _seed_policy(db_session, policy_name="상시 모집 정책")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    statuses = {o.policy_name: (o.status, o.status_emoji) for o in result.options}
    assert statuses["이미 마감된 정책"] == ("만료", "🔴")
    assert statuses["상시 모집 정책"] == ("상시", "🟢")


def test_run_sorts_expired_policies_after_open_ones(db_session):
    _seed_policy(db_session, policy_name="이미 마감된 정책", apply_start_ymd="20200101", apply_end_ymd="20200201")
    _seed_policy(db_session, policy_name="상시 모집 정책")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    names = [o.policy_name for o in result.options]
    assert names == ["상시 모집 정책", "이미 마감된 정책"]


def test_run_maps_policy_fields_into_output_option(db_session):
    _seed_policy(
        db_session,
        policy_name="청년 월세 지원",
        description="월 20만원 지원",
        apply_url="https://example.com/apply",
        application_period="2026-01-01 ~ 2026-12-31",
    )
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    option = result.options[0]
    assert option.policy_name == "청년 월세 지원"
    assert option.benefit_description == "월 20만원 지원"
    assert option.reference_url == "https://example.com/apply"
    assert option.application_period == "2026-01-01 ~ 2026-12-31"
