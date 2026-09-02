from datetime import date

from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY, category_tags
from app.features.policy_matcher.matching import (
    has_specific_eligibility_condition,
    is_eligible,
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
    # policy_matcher/tool.py의 금융 카테고리 필터 + recommender.py의 "조건 없음"
    # 더미 데이터 필터를 재사용한다 — 두 시나리오 비교의 목적이 "의미 있는 자격
    # 변화"를 보여주는 것이므로, 아무나 통과하는 더미 레코드나 이미 만료돼 신청
    # 불가능한 정책은 애초에 후보에서 제외한다.
    #
    # recommender.py의 is_likely_template_region_code는 **여기서는 재사용하지
    # 않는다** — 2026-09-02 실측: 서울 거주 유저로 실제 계산해보면 결과가 항상
    # 0건이었는데, 원인이 이 필터였다. "경계선지능청년지원"/"햇살론유스" 같은 실제
    # 전국 단위 금융 정책들이 zipCd를 비워두는 대신 전국 시군구 코드를 전부
    # 나열하는 방식으로 표현돼 있어(16개 시도 이상 커버) 이 임계치에 걸려버렸다 —
    # 추천 배치(recommender.py)에서는 "더미/템플릿 데이터로 추천 알림이 도배되는
    # 것"을 막는 게 우선이라 이 필터가 맞지만, 사용자가 자기 지역을 직접 넣고
    # "그 지역에서 실제로 뭘 받을 수 있는지" 확인하는 이 계산기에서는 정반대로
    # 작동해 진짜 받을 수 있는 정책까지 통째로 사라지는 문제가 됐다.
    candidates = [
        p
        for p in policies
        if FINANCIAL_LARGE_CATEGORY in category_tags(p.large_category)
        and compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)[0] != "만료"
        and has_specific_eligibility_condition(p)
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
