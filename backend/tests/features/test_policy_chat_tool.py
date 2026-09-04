import itertools
from datetime import datetime, timezone

from app.features.policy_chat import tool
from app.features.policy_chat.schemas import PolicyChatSearchInput
from app.features.policy_chat.tool import TOOL_SPEC, run
from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY
from app.features.policy_matcher.models import CachedPolicy
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


def test_tool_spec_has_expected_name():
    assert TOOL_SPEC.name == "policy_chat_search"
    assert TOOL_SPEC.entrypoint is run


def test_run_returns_all_financial_policies_when_no_conditions_given(db_session):
    _seed_policy(db_session)
    _seed_policy(db_session, policy_name="다른 정책")
    result = run(PolicyChatSearchInput(), _ctx(db_session))
    assert len(result.options) == 2


def test_run_excludes_non_financial_policy(db_session):
    _seed_policy(db_session, large_category="일자리")
    result = run(PolicyChatSearchInput(), _ctx(db_session))
    assert result.options == []


def test_run_filters_by_age_only_when_given(db_session):
    _seed_policy(db_session, min_age=19, max_age=34)
    assert len(run(PolicyChatSearchInput(age=50), _ctx(db_session)).options) == 0
    assert len(run(PolicyChatSearchInput(age=25), _ctx(db_session)).options) == 1
    assert len(run(PolicyChatSearchInput(), _ctx(db_session)).options) == 1  # 나이 안 주면 그냥 통과


def test_run_uses_combined_household_income_when_given(db_session):
    _seed_policy(db_session, max_income_krw=50_000_000)
    matched = run(
        PolicyChatSearchInput(annual_income_krw=40_000_000, spouse_annual_income_krw=20_000_000), _ctx(db_session)
    )
    assert matched.options == []
    matched = run(PolicyChatSearchInput(annual_income_krw=40_000_000), _ctx(db_session))
    assert len(matched.options) == 1


_15_PROVINCE_CODES = ",".join(
    f"{p}110" for p in ("11", "26", "27", "28", "29", "30", "31", "36", "41", "51", "43", "44", "52", "46", "47")
)  # 17개 시도 중 15개 — matching.is_likely_template_region_code 임계치


def test_run_excludes_policy_with_template_region_code(db_session):
    # 2026-09-03 사용자 지적: "정책 전체 보기"(AI 정책 검색)에서 서울로 필터링해도
    # 의성/서산 같은 지자체 전용 정책이 나왔다 — zipCd에 거의 모든 시/도가 나열된
    # 레코드가 region_matches()엔 "서울도 포함"으로 보였기 때문. _matches()가
    # 이런 레코드를 걸러야 한다(ai_search.py의 search_policies도 _matches를
    # 그대로 쓰므로 같이 고쳐진다).
    _seed_policy(db_session, region_code=_15_PROVINCE_CODES)
    result = run(PolicyChatSearchInput(region="서울"), _ctx(db_session))
    assert result.options == []


def test_run_filters_by_marital_status_only_when_given(db_session):
    # "0055001"은 온통청년 공식 mrgSttsCd 기혼 코드다(matching.MARITAL_STATUS_LABELS,
    # 2026-09-03 수정 전에는 _matches가 "기혼" 문자열과 비교하는 별도 복붙 로직이라
    # 이 필터가 실제로는 한 번도 안 걸렸다).
    _seed_policy(db_session, marital_status="0055001")
    assert run(PolicyChatSearchInput(is_married=False), _ctx(db_session)).options == []
    assert len(run(PolicyChatSearchInput(is_married=True), _ctx(db_session)).options) == 1
    assert len(run(PolicyChatSearchInput(), _ctx(db_session)).options) == 1  # 혼인여부 안 주면 통과


def test_run_filters_by_region_only_when_given(db_session):
    _seed_policy(db_session, region_code="26110")
    assert run(PolicyChatSearchInput(region="서울"), _ctx(db_session)).options == []
    assert len(run(PolicyChatSearchInput(region="부산"), _ctx(db_session)).options) == 1
    assert len(run(PolicyChatSearchInput(), _ctx(db_session)).options) == 1


def test_run_filters_by_keyword(db_session):
    _seed_policy(db_session, policy_name="전세자금 대출")
    _seed_policy(db_session, policy_name="창업 지원금")
    result = run(PolicyChatSearchInput(keyword="전세"), _ctx(db_session))
    assert len(result.options) == 1
    assert result.options[0].policy_name == "전세자금 대출"


def test_run_filters_by_keyword_with_suffix_variation(db_session):
    # 2026-09-03 사용자 발견: 실제 정책명은 "청소년 한부모 복지급여 지원"처럼
    # "한부모"까지만 쓰는데 사용자는 "한부모가정"이라고 검색해서 0건이었다.
    _seed_policy(db_session, policy_name="청소년 한부모 복지급여 지원")
    _seed_policy(db_session, policy_name="창업 지원금")
    result = run(PolicyChatSearchInput(keyword="한부모가정"), _ctx(db_session))
    assert len(result.options) == 1
    assert result.options[0].policy_name == "청소년 한부모 복지급여 지원"


def test_run_keyword_suffix_trim_does_not_shrink_below_two_chars(db_session):
    # 접미어를 1글자까지 줄이면 "여성청년"처럼 "여" 한 글자만 겹치는 무관한 정책까지
    # 걸릴 수 있다 — 최소 2글자("여자")까지만 시도하고 그 밑으로는 안 줄여야 한다.
    _seed_policy(db_session, policy_name="여성청년 지원")
    result = run(PolicyChatSearchInput(keyword="여자들"), _ctx(db_session))
    assert result.options == []


def test_run_sorts_newlywed_policies_first_when_married(db_session):
    _seed_policy(db_session, policy_name="일반 대출")
    _seed_policy(db_session, policy_name="신혼부부 전세자금 대출")
    result = run(PolicyChatSearchInput(is_married=True), _ctx(db_session))
    names = [o.policy_name for o in result.options]
    assert names == ["신혼부부 전세자금 대출", "일반 대출"]


def test_run_excludes_expired_policy(db_session):
    _seed_policy(db_session, policy_name="마감된 정책", apply_start_ymd="20200101", apply_end_ymd="20200201")
    result = run(PolicyChatSearchInput(), _ctx(db_session))
    assert result.options == []


def test_run_includes_status_and_emoji_on_options(db_session):
    _seed_policy(db_session)
    result = run(PolicyChatSearchInput(), _ctx(db_session))
    assert result.options[0].status == "상시"
    assert result.options[0].status_emoji == "🟢"


def test_run_filters_by_disability_filter_only_and_exclude(db_session):
    # 2026-09-05 3단계로 확장(사용자 요청: "전체/해당 없음/해당 있음으로 다 걸게
    # 해줘") — None(생략)=전체, "only"=그 대상군만, "exclude"=그 대상군 제외.
    _seed_policy(db_session, policy_name="장애인 취업 지원 사업")
    _seed_policy(db_session, policy_name="일반 청년 취업 지원")
    assert len(run(PolicyChatSearchInput(disability_filter="only"), _ctx(db_session)).options) == 1
    assert len(run(PolicyChatSearchInput(disability_filter="exclude"), _ctx(db_session)).options) == 1
    assert len(run(PolicyChatSearchInput(), _ctx(db_session)).options) == 2  # 안 주면 전체 다 나온다


def test_run_filters_by_veteran_filter_only_and_exclude(db_session):
    _seed_policy(db_session, policy_name="제대군인 직업능력 개발훈련")
    _seed_policy(db_session, policy_name="일반 청년 취업 지원")
    assert len(run(PolicyChatSearchInput(veteran_filter="only"), _ctx(db_session)).options) == 1
    assert len(run(PolicyChatSearchInput(veteran_filter="exclude"), _ctx(db_session)).options) == 1


def test_run_filters_job_targeted_policy_by_occupation_only_when_given(db_session):
    # 2026-09-04 추가(사용자 지적: "정책달력 맞춤검색결과랑 한눈에보기 신청가능
    # 정책 개수가 왜 달라?") — matching.is_eligible()의 TARGETING_RULES와 똑같이
    # 재학생/재직자/자영업자/미취업자 전용 정책은 occupation이 안 맞으면 걸러져야
    # 한다. 그동안 이 스키마엔 occupation 필드 자체가 없어서 한 번도 안 걸렸다.
    _seed_policy(db_session, policy_name="대학생 전용 장학금", school_code="0049005")
    _seed_policy(db_session, policy_name="재직자 전용 지원", job_code="0013001")
    _seed_policy(db_session, policy_name="자영업자 전용 지원", job_code="0013002")
    _seed_policy(db_session, policy_name="미취업자 전용 지원", job_code="0013003")
    _seed_policy(db_session, policy_name="일반 청년 지원")

    result = run(PolicyChatSearchInput(occupation="employee"), _ctx(db_session))
    assert [o.policy_name for o in result.options] == ["재직자 전용 지원", "일반 청년 지원"]

    # occupation을 안 주면(대화 초반이라 아직 안 밝혀졌으면) 예전처럼 전부 통과한다
    assert len(run(PolicyChatSearchInput(), _ctx(db_session)).options) == 5


def test_run_filters_sme_only_policy_by_is_sme_employee_only_when_given(db_session):
    _seed_policy(db_session, policy_name="중소기업 재직자 전용 지원", sbiz_code="0014001")
    _seed_policy(db_session, policy_name="일반 청년 지원")

    assert len(run(PolicyChatSearchInput(is_sme_employee=False), _ctx(db_session)).options) == 1
    assert len(run(PolicyChatSearchInput(is_sme_employee=True), _ctx(db_session)).options) == 2
    assert len(run(PolicyChatSearchInput(), _ctx(db_session)).options) == 2  # 안 주면 전체 통과


def test_run_caps_results_at_max(db_session):
    for i in range(20):
        _seed_policy(db_session, policy_name=f"정책{i}")
    result = run(PolicyChatSearchInput(), _ctx(db_session))
    assert len(result.options) == tool.MAX_RESULTS
