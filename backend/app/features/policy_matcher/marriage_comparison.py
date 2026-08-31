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
    PolicyMatchInput,
)
from app.features.policy_matcher.status import compute_policy_status


def build_marriage_scenarios(input: MarriageComparisonInput) -> tuple[PolicyMatchInput, PolicyMatchInput]:
    """미혼/기혼 두 시나리오의 PolicyMatchInput을 만든다.

    나이/지역/본인소득은 두 시나리오가 공유하고, 배우자 소득만 기혼 시나리오에서
    합산된다 — is_eligible()의 가구소득 합산 로직(matching.py 참고)만 재사용할 뿐,
    새 자격 판정 로직은 만들지 않는다.
    """
    unmarried = PolicyMatchInput(
        age=input.age,
        is_married=False,
        annual_income_krw=input.annual_income_krw,
        region=input.region,
        spouse_annual_income_krw=None,
    )
    married = PolicyMatchInput(
        age=input.age,
        is_married=True,
        annual_income_krw=input.annual_income_krw,
        region=input.region,
        spouse_annual_income_krw=input.spouse_annual_income_krw,
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
    # policy_matcher/tool.py의 금융 카테고리 필터 + recommender.py의 "조건 없음"/
    # "템플릿 지역" 더미 데이터 필터를 그대로 재사용한다 — 두 시나리오 비교의
    # 목적이 "의미 있는 자격 변화"를 보여주는 것이므로, 아무나 통과하는 더미
    # 레코드나 이미 만료돼 신청 불가능한 정책은 애초에 후보에서 제외한다.
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
