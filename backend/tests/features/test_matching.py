from app.features.policy_matcher.matching import (
    age_matches,
    has_specific_eligibility_condition,
    income_matches,
    is_disability_targeted_policy,
    is_eligible,
    is_likely_template_region_code,
    is_newlywed_policy,
    is_student_only_policy,
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


def test_is_likely_template_region_code_is_false_when_institution_is_central_government():
    # 2026-09-03: 온통청년 공식 코드정의서의 pvsnInstGroupCd(제공기관그룹코드)로
    # 교차검증한 결과 — 지자체(0054002)가 15개 이상 시도를 커버하면 데이터 실수일
    # 확률이 높지만, 중앙부처(0054001)가 그러는 건 "햇살론유스"처럼 정상적인 전국
    # 상품이다. 중앙부처로 확인되면 이 필터를 적용하지 않는다.
    central = _policy(region_code=_15_PROVINCE_CODES, institution_group_code="0054001")
    assert is_likely_template_region_code(central) is False


def test_is_likely_template_region_code_still_true_for_unknown_institution_group():
    # institution_group_code가 빈 값(기존 캐시 마이그레이션 직후 등)이면 안전한
    # 쪽(지자체로 간주)으로 기존 동작을 유지한다.
    unknown = _policy(region_code=_15_PROVINCE_CODES, institution_group_code="")
    assert is_likely_template_region_code(unknown) is True


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


def test_is_student_only_policy_true_for_enrollment_codes():
    # 2026-09-03 사용자 지적: "국가근로장학금"이 schoolCd="0049005"(대학 재학)인데
    # 나이/소득 조건이 둘 다 없어서(min_age/max_age/min_income/max_income 전부
    # None) 40대에게도 그냥 노출되고 있었다.
    assert is_student_only_policy(_policy(school_code="0049005")) is True  # 대학 재학
    assert is_student_only_policy(_policy(school_code="0049002")) is True  # 고교 재학
    assert is_student_only_policy(_policy(school_code="0049003,0049006")) is True  # 고졸/대졸 예정


def test_is_student_only_policy_false_for_graduation_codes_or_unrestricted():
    # 이미 졸업했다는 학력(대졸/석박사)만으로는 "지금 재학 중"이 아니므로 걸러내지
    # 않는다 — 대졸 직장인도 그 학력을 갖고 있을 수 있어서 오탐 위험이 있다.
    assert is_student_only_policy(_policy(school_code="0049007")) is False  # 대학 졸업
    assert is_student_only_policy(_policy(school_code="0049008")) is False  # 석·박사
    assert is_student_only_policy(_policy(school_code="0049010")) is False  # 제한없음
    assert is_student_only_policy(_policy(school_code="")) is False


def test_is_student_only_policy_false_when_unrestricted_code_is_mixed_in():
    # 재학 코드와 "제한없음"이 같이 찍혀 있으면(데이터 모순) 안전한 쪽(통과)으로.
    assert is_student_only_policy(_policy(school_code="0049005,0049010")) is False


def test_student_only_policy_is_ineligible_for_explicit_non_student_occupation():
    policy = _policy(school_code="0049005")  # 대학 재학 전용
    assert is_eligible(policy, _input(occupation="employee")) is False
    assert is_eligible(policy, _input(occupation="student")) is True
    # occupation 미입력(None)인 기존 유저는 fail-open으로 계속 노출한다.
    assert is_eligible(policy, _input()) is True


def test_job_code_rules_match_occupation():
    employee_only = _policy(job_code="0013001")
    assert is_eligible(employee_only, _input(occupation="self_employed")) is False
    assert is_eligible(employee_only, _input(occupation="employee")) is True
    assert is_eligible(employee_only, _input()) is True  # occupation 미입력은 fail-open

    self_employed_only = _policy(job_code="0013006")  # (예비)창업자
    assert is_eligible(self_employed_only, _input(occupation="employee")) is False
    assert is_eligible(self_employed_only, _input(occupation="self_employed")) is True

    unemployed_only = _policy(job_code="0013003")
    assert is_eligible(unemployed_only, _input(occupation="employee")) is False
    assert is_eligible(unemployed_only, _input(occupation="unemployed")) is True


def test_job_code_unrestricted_and_unmapped_categories_pass_through():
    # "제한없음"이면 당연히 통과.
    assert is_eligible(_policy(job_code="0013010"), _input(occupation="employee")) is True
    # 프리랜서/일용근로자 같은, occupation에 대응 값이 없는 코드는 규칙 자체가 없어
    # 그냥 통과한다(오탐 위험이 있어 일부러 규칙을 안 만들었다 — matching.py 주석 참고).
    assert is_eligible(_policy(job_code="0013004"), _input(occupation="employee")) is True


def test_sme_only_policy_requires_is_sme_employee():
    policy = _policy(sbiz_code="0014001")
    assert is_eligible(policy, _input(is_sme_employee=False)) is False
    assert is_eligible(policy, _input(is_sme_employee=True)) is True
    assert is_eligible(policy, _input()) is True  # 미입력은 fail-open


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


# 2026-09-03 추가: PLAN.md #2 — "서울 강남구"처럼 구/군까지 지정하면 5자리
# 법정동코드로 정밀 매칭한다(district_codes.py 참고). "서울"만 주면 기존처럼
# 시/도 단위로만 본다(하위 호환).
def test_region_matches_with_district_narrows_to_5_digit_code():
    seoul_all_gu = "11110,11140,11170,11200,11215,11230,11260,11290,11305,11320,11350,11380,11410,11440,11470,11500,11530,11545,11560,11590,11620,11650,11680,11710,11740"
    assert region_matches(seoul_all_gu, "서울 강남구") is True
    # 강남구 코드(11680)가 아예 없는, 몇 개 구만 콕 집은 정책이면 강남구 사용자에겐 안 걸려야 한다.
    assert region_matches("11110,11140", "서울 강남구") is False  # 종로구·중구만 대상
    assert region_matches("11680", "서울 서초구") is False  # 강남구만 대상인데 서초구로 조회


def test_region_matches_district_falls_back_to_province_when_district_unmapped():
    # 광주/전남은 구/군 표 자체가 없다(district_codes.py 상단 주석 참고) — 시/도
    # 단위로 완화해서 계속 거른다(필터링을 통째로 포기하지 않음).
    assert region_matches("29110", "광주 동구") is True
    # 오타/모르는 구 이름도 마찬가지로 시/도 단위까지는 유지된다.
    assert region_matches("11110", "서울 없는구") is True
    assert region_matches("26110", "서울 없는구") is False


def test_region_matches_district_works_with_province_alias():
    # "서울특별시 강남구"처럼 정식 명칭 별칭 + 구/군 조합도 canonical로 정규화돼 동작한다.
    assert region_matches("11680", "서울특별시 강남구") is True
    assert region_matches("11110", "서울특별시 강남구") is False


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
