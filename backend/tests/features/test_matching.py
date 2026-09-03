from app.features.policy_matcher.matching import (
    age_matches,
    has_specific_eligibility_condition,
    income_matches,
    is_disability_targeted_policy,
    is_eligible,
    is_likely_template_region_code,
    is_newlywed_policy,
    is_veteran_targeted_policy,
    region_matches,
)
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.youth_center_client import RawYouthPolicy


def _policy(**overrides) -> RawYouthPolicy:
    defaults = dict(
        policy_id="",
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


def _input(**overrides) -> PolicyMatchInput:
    defaults = dict(age=29, is_married=False, annual_income_krw=40_000_000, region="서울")
    defaults.update(overrides)
    return PolicyMatchInput(**defaults)


def test_policy_without_conditions_is_always_eligible():
    assert is_eligible(_policy(), _input()) is True


def test_applicant_outside_age_range_is_ineligible():
    assert is_eligible(_policy(min_age=19, max_age=34), _input(age=50)) is False


def test_marriage_requirement_is_enforced_both_ways():
    # "0055001"/"0055002"는 온통청년 공식 코드정의서(API코드정보.xlsx)의 실제
    # mrgSttsCd 값이다 — 예전엔 "기혼"/"미혼" 문자열과 비교해서 실제 데이터에는
    # 한 번도 안 걸리는 죽은 코드였다(matching.py MARITAL_STATUS_LABELS 참고).
    married_only = _policy(marital_status="0055001")
    assert is_eligible(married_only, _input(is_married=False)) is False
    assert is_eligible(married_only, _input(is_married=True)) is True

    unmarried_only = _policy(marital_status="0055002")
    assert is_eligible(unmarried_only, _input(is_married=True)) is False
    assert is_eligible(unmarried_only, _input(is_married=False)) is True


def test_marital_status_unrestricted_code_and_unknown_values_pass_through():
    # "0055003"(제한없음, 실측상 97%가 이 값)은 물론, 아직 공식 코드표에 없는
    # 값이나 빈 문자열도 fail-open으로 통과시킨다.
    for value in ("0055003", "", "9999999"):
        policy = _policy(marital_status=value)
        assert is_eligible(policy, _input(is_married=False)) is True
        assert is_eligible(policy, _input(is_married=True)) is True


def test_income_ceiling_is_enforced():
    assert is_eligible(_policy(max_income_krw=30_000_000), _input(annual_income_krw=40_000_000)) is False


def test_income_floor_is_enforced():
    assert is_eligible(_policy(min_income_krw=50_000_000), _input(annual_income_krw=40_000_000)) is False


def test_region_restricted_policy_is_ineligible_outside_region():
    assert is_eligible(_policy(region_code="부산"), _input(region="서울")) is False


def test_region_restricted_policy_is_ineligible_when_input_region_empty():
    assert is_eligible(_policy(region_code="부산"), _input(region="")) is False


def test_income_ceiling_uses_combined_household_income_when_spouse_income_given():
    policy = _policy(max_income_krw=50_000_000)
    # 본인 소득만으로는 통과하지만, 배우자 소득을 합치면 상한을 넘는다.
    assert is_eligible(policy, _input(annual_income_krw=40_000_000)) is True
    assert (
        is_eligible(
            policy, _input(annual_income_krw=40_000_000, spouse_annual_income_krw=20_000_000)
        )
        is False
    )


def test_income_floor_uses_combined_household_income_when_spouse_income_given():
    policy = _policy(min_income_krw=50_000_000)
    # 본인 소득만으로는 하한 미달이지만, 배우자 소득을 합치면 통과한다.
    assert is_eligible(policy, _input(annual_income_krw=40_000_000)) is False
    assert (
        is_eligible(
            policy, _input(annual_income_krw=40_000_000, spouse_annual_income_krw=20_000_000)
        )
        is True
    )


def test_has_specific_eligibility_condition_is_false_when_all_four_fields_are_none():
    assert has_specific_eligibility_condition(_policy()) is False


def test_has_specific_eligibility_condition_is_true_when_any_one_field_is_set():
    assert has_specific_eligibility_condition(_policy(min_age=19)) is True
    assert has_specific_eligibility_condition(_policy(max_age=39)) is True
    assert has_specific_eligibility_condition(_policy(min_income_krw=1)) is True
    assert has_specific_eligibility_condition(_policy(max_income_krw=1)) is True


_15_PROVINCE_CODES = ",".join(
    f"{p}110" for p in ("11", "26", "27", "28", "29", "30", "31", "36", "41", "51", "43", "44", "52", "46", "47")
)  # 17개 시도 중 15개


def test_is_likely_template_region_code_is_false_for_empty_region_code():
    assert is_likely_template_region_code(_policy(region_code="")) is False


def test_is_likely_template_region_code_is_false_for_a_single_region():
    assert is_likely_template_region_code(_policy(region_code="11110,11140")) is False


def test_is_likely_template_region_code_is_true_when_15_or_more_provinces_are_covered():
    assert is_likely_template_region_code(_policy(region_code=_15_PROVINCE_CODES)) is True


def test_is_newlywed_policy_matches_keyword_in_name_or_description():
    assert is_newlywed_policy(_policy(policy_name="신혼부부 전세자금 대출이자 지원")) is True
    assert is_newlywed_policy(_policy(description="예비·신혼부부 대상 건강검진 지원")) is True
    assert is_newlywed_policy(_policy(policy_name="청년 전세자금 대출")) is False


def test_is_newlywed_policy_matches_청년부부_and_예비부부_without_신혼():
    assert is_newlywed_policy(_policy(policy_name="청년부부 결혼축하금 지원사업")) is True
    assert is_newlywed_policy(_policy(policy_name="예비부부 건강검진 사업")) is True


def test_is_newlywed_policy_does_not_match_unrelated_결혼_policies():
    # "결혼"만 들어간 정책은 신혼부부와 무관한 경우가 많아(미혼남녀 만남 지원,
    # 결혼이민여성 취업지원 등) 키워드에서 제외했다.
    assert is_newlywed_policy(_policy(policy_name="미혼남녀 만남 지원 프로그램")) is False
    assert is_newlywed_policy(_policy(policy_name="결혼이민여성 취업지원")) is False


def test_is_disability_targeted_policy_matches_keyword_in_policy_name():
    assert is_disability_targeted_policy(_policy(policy_name="장애인 취업 지원 사업")) is True
    assert is_disability_targeted_policy(_policy(policy_name="경계성 지능 청년 자립 지원")) is True
    assert is_disability_targeted_policy(_policy(policy_name="경계선지능청년지원")) is True  # 띄어쓰기 없는 실제 사례
    assert is_disability_targeted_policy(_policy(policy_name="청년 취업 지원 사업")) is False


def test_is_disability_targeted_policy_ignores_description_and_general_eligible_titles():
    # description에만 등장(정책명엔 없음)하는 경우는 걸러내지 않는다 — 실측 결과
    # "저소득 서민, 청년, 신혼부부, 장애인, 국가유공자 등"처럼 여러 대상을 나열하는
    # 설명문에 걸려, 장애인 전용이 아닌 정책(예: 통합공공임대주택)까지 잘못
    # 걸러내는 오탐이 있었기 때문이다.
    assert is_disability_targeted_policy(_policy(policy_name="청년 임대주택 공급", description="장애인 등 주거취약계층 지원")) is False
    # "일반"이 정책명에 함께 있으면 장애인 전용이 아니라 일반인도 받을 수 있다는
    # 뜻이라 제외한다.
    assert is_disability_targeted_policy(_policy(policy_name="평생교육이용권[일반·장애인] 지원")) is False


def test_is_veteran_targeted_policy_matches_keyword_in_policy_name():
    assert is_veteran_targeted_policy(_policy(policy_name="국가유공자 자녀 학자금 지원")) is True
    assert is_veteran_targeted_policy(_policy(policy_name="제대군인 직업능력 개발훈련")) is True
    assert is_veteran_targeted_policy(_policy(policy_name="청년 취업 지원 사업")) is False


def test_is_veteran_targeted_policy_ignores_description_only_mentions():
    assert is_veteran_targeted_policy(_policy(policy_name="청년 임대주택 공급", description="국가유공자 등 주거취약계층 지원")) is False


def test_disability_targeted_policy_is_ineligible_for_explicit_non_disabled_input():
    policy = _policy(policy_name="장애인 취업 지원 사업")
    assert is_eligible(policy, _input(has_disability=False)) is False
    assert is_eligible(policy, _input(has_disability=True)) is True
    # 아직 입력 안 한(None) 기존 유저는 fail-open으로 계속 노출한다.
    assert is_eligible(policy, _input()) is True


def test_veteran_targeted_policy_is_ineligible_for_explicit_non_veteran_input():
    policy = _policy(policy_name="국가유공자 자녀 학자금 지원")
    assert is_eligible(policy, _input(is_veteran=False)) is False
    assert is_eligible(policy, _input(is_veteran=True)) is True
    assert is_eligible(policy, _input()) is True


def test_region_matches_seoul_uses_11_prefix():
    assert region_matches("11110,11140", "서울") is True
    assert region_matches("26110", "서울") is False


def test_region_matches_gwangju_and_jeonnam_accept_both_old_and_new_merged_code():
    # 2026-08-26 실측: 광주광역시+전라남도가 "전남광주통합특별시"로 통합되며 새
    # zipCd 접두사 "12"가 부여됐다 — 옛 코드(광주=29, 전남=46)로 남아있는 레코드와
    # 새 코드(12)로 넘어간 레코드 양쪽 다 "광주"/"전남" 검색에 걸려야 한다.
    assert region_matches("29110", "광주") is True  # 옛 광주 코드
    assert region_matches("12110", "광주") is True  # 새 통합 코드
    assert region_matches("46110", "전남") is True  # 옛 전남 코드
    assert region_matches("12110", "전남") is True  # 새 통합 코드
    # 다른 지역과는 여전히 안 섞인다.
    assert region_matches("12110", "서울") is False


def test_region_matches_unmapped_input_fails_open():
    # 매핑에 없는 자유 텍스트는 필터링하지 않고 통과시킨다(기존 동작 유지).
    assert region_matches("11110", "강남구") is True


# age_matches/income_matches는 is_eligible과 policy_chat/tool._matches가 공유하는
# 헬퍼다(2026-09-03 중복 제거) — None을 넘기면 "그 조건은 안 본다"는 뜻으로
# 무조건 통과시키는 게 핵심 계약이라 여기서 직접 검증한다.
def test_age_matches_passes_when_age_is_none():
    assert age_matches(_policy(min_age=19, max_age=34), None) is True


def test_age_matches_enforces_bounds_when_age_given():
    policy = _policy(min_age=19, max_age=34)
    assert age_matches(policy, 10) is False
    assert age_matches(policy, 25) is True
    assert age_matches(policy, 40) is False


def test_income_matches_passes_when_income_is_none():
    assert income_matches(_policy(max_income_krw=1), None) is True


def test_income_matches_combines_spouse_income_when_given():
    policy = _policy(max_income_krw=50_000_000)
    assert income_matches(policy, 40_000_000) is True
    assert income_matches(policy, 40_000_000, 20_000_000) is False
