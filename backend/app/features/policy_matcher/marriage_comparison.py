from datetime import date

from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY, category_tags
from app.features.policy_matcher.matching import (
    has_specific_eligibility_condition,
    is_eligible,
    is_likely_template_region_code,
    is_newlywed_policy,
)
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import (
    MarriageComparisonInput,
    MarriageComparisonOutput,
    MarriagePolicyItem,
    OccupationType,
    PolicyMatchInput,
)
from app.features.policy_matcher.status import compute_policy_status


def build_marriage_scenarios(
    input: MarriageComparisonInput,
    *,
    has_disability: bool | None = None,
    is_veteran: bool | None = None,
    occupation: OccupationType | None = None,
    is_sme_employee: bool | None = None,
) -> tuple[PolicyMatchInput, PolicyMatchInput]:
    """미혼/기혼 두 시나리오의 PolicyMatchInput을 만든다.

    나이/지역/본인소득은 두 시나리오가 공유하고, 배우자 소득만 기혼 시나리오에서
    합산된다 — is_eligible()의 가구소득 합산 로직(matching.py 참고)만 재사용할 뿐,
    새 자격 판정 로직은 만들지 않는다.

    2026-09-03 사용자 발견: 이 계산기는 폼에서 나이/소득/지역만 입력받다 보니
    has_disability/is_veteran/occupation/is_sme_employee가 항상 None으로
    넘어갔다 — TargetingRule은 None을 "아직 모름"으로 fail-open 처리하므로
    (matching.py 주석 참고), 장애인 전용 정책("경계성지능청년" 등)이 일반
    직장인 부부에게도 계속 노출됐다. 이 필드들은 폼에 없으니 저장된 프로필
    값을 호출자(router.py)가 넘겨준다 — age/income/region처럼 그 자리에서
    바꿔보는 값이 아니라 고정 속성이라 폼에 넣을 이유가 없다.
    """
    unmarried = PolicyMatchInput(
        age=input.age,
        is_married=False,
        annual_income_krw=input.annual_income_krw,
        region=input.region,
        spouse_annual_income_krw=None,
        has_disability=has_disability,
        is_veteran=is_veteran,
        occupation=occupation,
        is_sme_employee=is_sme_employee,
    )
    married = PolicyMatchInput(
        age=input.age,
        is_married=True,
        annual_income_krw=input.annual_income_krw,
        region=input.region,
        spouse_annual_income_krw=input.spouse_annual_income_krw,
        has_disability=has_disability,
        is_veteran=is_veteran,
        occupation=occupation,
        is_sme_employee=is_sme_employee,
    )
    return unmarried, married


def _to_item(policy: CachedPolicy) -> MarriagePolicyItem:
    return MarriagePolicyItem(
        policy_key=policy.policy_key,
        policy_name=policy.policy_name,
        benefit_description=policy.description,
        application_period=policy.application_period,
        reference_url=policy.apply_url,
        is_newlywed_policy=is_newlywed_policy(policy),
    )


def compare_marriage_scenarios(
    policies: list[CachedPolicy],
    unmarried_input: PolicyMatchInput,
    married_input: PolicyMatchInput,
    today: date,
) -> MarriageComparisonOutput:
    # policy_matcher/tool.py의 금융 카테고리 필터 + recommender.py의 "조건 없음"
    # 더미 데이터 필터를 재사용한다 — 두 시나리오 비교의 목적이 "의미 있는 자격
    # 변화"를 보여주는 것이므로, 아무나 통과하는 더미 레코드나 이미 만료돼 신청
    # 불가능한 정책은 애초에 후보에서 제외한다.
    #
    # is_likely_template_region_code: 2026-09-02엔 여기 재사용하면 "햇살론유스"
    # 같은 진짜 전국 단위 금융 정책까지 걸려서 결과가 항상 0건이 되는 문제가 있어
    # 일부러 뺐었다. 2026-09-03에 이 함수 자체를 고쳤다 — 제공기관그룹코드
    # (institution_group_code)로 중앙부처 상품은 애초에 걸지 않도록 구분했으므로
    # (matching.py 주석 참고), 이제 다시 재사용해도 안전하다 — 서산시/의성군처럼
    # 지자체가 지역코드를 잘못 전체로 찍은 진짜 데이터 결함만 걸러진다.
    candidates = [
        p
        for p in policies
        if FINANCIAL_LARGE_CATEGORY in category_tags(p.large_category)
        and compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)[0] != "만료"
        and has_specific_eligibility_condition(p)
        and not is_likely_template_region_code(p)
    ]

    unmarried_eligible = {p.policy_key: p for p in candidates if is_eligible(p, unmarried_input)}
    married_eligible = {p.policy_key: p for p in candidates if is_eligible(p, married_input)}

    married_only_keys = married_eligible.keys() - unmarried_eligible.keys()
    unmarried_only_keys = unmarried_eligible.keys() - married_eligible.keys()
    both_keys = married_eligible.keys() & unmarried_eligible.keys()

    def _items(keys, source: dict[str, CachedPolicy]) -> list[MarriagePolicyItem]:
        return sorted((_to_item(source[k]) for k in keys), key=lambda item: item.policy_name)

    return MarriageComparisonOutput(
        married_only=_items(married_only_keys, married_eligible),
        unmarried_only=_items(unmarried_only_keys, unmarried_eligible),
        both=_items(both_keys, married_eligible),
    )
