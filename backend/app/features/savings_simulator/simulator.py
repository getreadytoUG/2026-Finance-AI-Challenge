"""정책연계형 저축/주거 시뮬레이터 — 순수 계산(LLM 미사용).

2026-09-03: "가품(예시 수치)라 실제로 못 쓴다"는 사용자 지적으로 전면 재작업했다.
매칭비율/금리/LTV/소득 상한을 더는 md_files/UPGRADE.md의 예시 구조가 아니라, 실제
정부 고시·공고 수치로 채웠다(출처는 각 섹션 주석 참고, 2026-09 웹 조사 기준).

⚠️ 그래도 두 가지는 여전히 "가정치"로 남는다 — (1) 정책상품/시중상품 비교에 쓰는
예금·대출 이자율 자체는 매일 은행마다 다르므로 업계 통상적인 계산기들도 항상
비교 기준 금리를 하나 가정해서 쓴다(_ASSUMED_* 상수, 아래 참고). (2) 이 앱이
추적하지 않는 조건(가구 중위소득, 생애최초 주택구입 여부, 자녀 수 등)은 반영하지
못했다 — 각 함수 주석에 어떤 조건을 못 넣었는지 명시했다. 정확한 최종 수치는
반드시 서민금융진흥원/주택도시기금 공고로 재확인해야 한다는 문구를 프론트 결과
카드에 유지한다.
"""

from datetime import date
from typing import TypeVar

from app.features.policy_matcher.matching import is_eligible, is_savings_account_policy
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.status import STATUS_ORDER, compute_policy_status
from app.features.savings_simulator.schemas import (
    HousingLoanInput,
    HousingLoanOutput,
    MatchedSavingsPolicy,
    YouthFutureSavingsInput,
    YouthFutureSavingsOutput,
)

T = TypeVar("T")

# 은행/상품마다 다른 실제 예금·대출 금리를 대신하는 비교용 가정 금리 — 모든 금융
# 계산기가 쓰는 방식과 동일하다(정부 고시가 아니라 "비교 기준선"이라는 뜻).
_ASSUMED_SAVINGS_RATE = 0.035
_ASSUMED_JEONSE_MARKET_RATE = 0.043
_ASSUMED_PURCHASE_MARKET_RATE = 0.045
_MARKET_TAX_RATE = 0.154  # 이자소득세


# ---------------------------------------------------------------------------
# 청년미래적금 — 청년도약계좌 후속상품(2026-06-22 출시, 서민금융진흥원)
#
# 청년도약계좌는 2025-12-31부로 신규가입이 종료됐다(조세특례제한법상 비과세 혜택
# 일몰). 2026년부터는 이 청년미래적금이 정부기여금·비과세 혜택을 이어받았다 —
# 출처: 금융위원회 보도자료(2026-06-22, fsc.go.kr), korea.kr 정책뉴스(2026-06),
# 서민금융진흥원(kinfa.or.kr), 하나은행/KB 상품안내(2026-09 재확인).
#
# 못 반영한 조건: "가구 중위소득 150%/200% 이하"(일반형/우대형 둘 다 개인소득
# 조건 외에 가구소득 기준도 있는데, 이 앱 프로필엔 가구 중위소득을 계산할 데이터가
# 없다), "연매출 1억/3억원 이하 소상공인" 트랙(occupation="self_employed"이 꼭
# 이 기준을 만족한다는 보장이 없어 임의로 우대형에 넣지 않았다).
_YFS_TERM_MONTHS = 36
_YFS_MONTHLY_CAP_KRW = 500_000
_YFS_PREFERENTIAL_INCOME_CAP_KRW = 36_000_000  # 우대형: 총급여 3,600만원 이하 + 중소기업 재직
_YFS_GENERAL_INCOME_CAP_KRW = 60_000_000  # 일반형: 총급여 6,000만원 이하
_YFS_MAX_INCOME_KRW = 75_000_000  # 6천만~7,500만원은 기여금 없이 비과세만, 초과 시 가입 불가
_YFS_PREFERENTIAL_MATCH_RATE = 0.12
_YFS_GENERAL_MATCH_RATE = 0.06
_YFS_AGE_MIN, _YFS_AGE_MAX = 19, 34


def _market_only_total(monthly_amount_krw: int, seed_money_krw: int) -> int:
    months = _YFS_TERM_MONTHS
    gross_interest = monthly_amount_krw * (months * (months + 1) / 2) * (_ASSUMED_SAVINGS_RATE / 12)
    net_interest = round(gross_interest * (1 - _MARKET_TAX_RATE))
    return monthly_amount_krw * months + seed_money_krw + net_interest


def simulate_youth_future_savings(
    input: YouthFutureSavingsInput,
    *,
    age: int | None = None,
    is_sme_employee: bool | None = None,
) -> YouthFutureSavingsOutput:
    months = _YFS_TERM_MONTHS

    if age is not None and not (_YFS_AGE_MIN <= age <= _YFS_AGE_MAX):
        total = _market_only_total(input.monthly_amount_krw, input.seed_money_krw)
        return YouthFutureSavingsOutput(
            eligible=False,
            matching_rate=0.0,
            eligibility_note=f"청년미래적금은 만 {_YFS_AGE_MIN}~{_YFS_AGE_MAX}세만 가입할 수 있어요(병역이행 기간은 최대 6년까지 별도 인정).",
            policy_total_krw=total,
            market_total_krw=total,
            benefit_diff_krw=0,
            summary="나이 조건을 벗어나 이 상품에 가입할 수 없어요.",
        )

    if input.annual_income_krw > _YFS_MAX_INCOME_KRW:
        total = _market_only_total(input.monthly_amount_krw, input.seed_money_krw)
        return YouthFutureSavingsOutput(
            eligible=False,
            matching_rate=0.0,
            eligibility_note=f"개인소득이 가입 기준(총급여 {_YFS_MAX_INCOME_KRW // 10_000:,}만원)을 초과해 가입할 수 없어요.",
            policy_total_krw=total,
            market_total_krw=total,
            benefit_diff_krw=0,
            summary="소득 기준 초과로 이 상품에 가입할 수 없어요.",
        )

    matched_base = min(input.monthly_amount_krw, _YFS_MONTHLY_CAP_KRW)

    if input.annual_income_krw > _YFS_GENERAL_INCOME_CAP_KRW:
        matching_rate = 0.0
        note = "개인소득이 6,000만원을 초과해 정부기여금 매칭은 없지만, 이자소득 비과세 혜택은 그대로 적용돼요."
    elif input.annual_income_krw <= _YFS_PREFERENTIAL_INCOME_CAP_KRW and is_sme_employee:
        matching_rate = _YFS_PREFERENTIAL_MATCH_RATE
        note = f"우대형 대상(중소기업 재직 청년)이라 납입액(월 최대 {_YFS_MONTHLY_CAP_KRW // 10_000}만원분)의 {matching_rate * 100:.0f}%를 정부가 더해줘요."
    else:
        matching_rate = _YFS_GENERAL_MATCH_RATE
        note = f"일반형 대상이라 납입액(월 최대 {_YFS_MONTHLY_CAP_KRW // 10_000}만원분)의 {matching_rate * 100:.0f}%를 정부가 더해줘요."

    government_total = round(matched_base * matching_rate * months)
    gross_interest = input.monthly_amount_krw * (months * (months + 1) / 2) * (_ASSUMED_SAVINGS_RATE / 12)
    policy_interest = round(gross_interest)  # 정책상품은 비과세
    market_interest = round(gross_interest * (1 - _MARKET_TAX_RATE))

    principal = input.monthly_amount_krw * months + input.seed_money_krw
    policy_total = principal + government_total + policy_interest
    market_total = principal + market_interest
    diff = policy_total - market_total

    summary = f"정부기여금 및 비과세로 일반 적금 대비 약 {diff:,}원 추가 수익을 기대할 수 있어요."

    return YouthFutureSavingsOutput(
        eligible=True,
        matching_rate=matching_rate,
        eligibility_note=note,
        policy_total_krw=policy_total,
        market_total_krw=market_total,
        benefit_diff_krw=diff,
        summary=summary,
    )


# 2026-09-02 추가: 위 계산은 청년미래적금 하나만 본뜨지만, 이 목록만큼은 실제
# DB(CachedPolicy)에서 지금 입력한 조건으로 진짜 자격되는 저축/자산형성 정책을
# 찾아준다 — matching.is_eligible을 그대로 재사용하므로 장애인/보훈대상자 전용
# 정책 필터링도 자동으로 함께 적용된다. router가 DB에서 CachedPolicy를 조회해
# 넘겨주고, 여기서는 필터링만 한다(이 파일의 "순수 계산" 원칙 유지 — DB I/O는
# router가 담당).
# 2026-09-02 QA에서 발견: 온통청년 원본 데이터에 같은 정책명이 설명만 살짝 다르게
# 중복 등록된 경우가 있어("청년주택드림청약통장" 등), 화면에 같은 이름이 두 번
# 뜨는 문제가 있었다. 사용자에게는 시행 기관/접수처 같은 구분 정보를 보여줄 방법이
# 마땅치 않아, 정책명이 같으면 하나만 남긴다 — candidates가 이미 상태(임박-여유-
# 상시-예정) 순으로 정렬돼 있으므로 먼저 나오는(더 급한/열려있는) 쪽을 남긴다.
def _dedupe_by_policy_name(candidates: list[CachedPolicy]) -> list[CachedPolicy]:
    seen: set[str] = set()
    deduped = []
    for p in candidates:
        if p.policy_name in seen:
            continue
        seen.add(p.policy_name)
        deduped.append(p)
    return deduped


def match_real_savings_policies(
    policies: list[CachedPolicy],
    match_input: PolicyMatchInput,
    today: date,
) -> list[MatchedSavingsPolicy]:
    candidates = [
        p
        for p in policies
        if is_savings_account_policy(p)
        and is_eligible(p, match_input)
        and compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)[0] != "만료"
    ]
    candidates.sort(key=lambda p: STATUS_ORDER[compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)[0]])
    candidates = _dedupe_by_policy_name(candidates)
    return [
        MatchedSavingsPolicy(
            policy_key=p.policy_key,
            policy_name=p.policy_name,
            benefit_description=p.description,
            application_period=p.application_period,
            reference_url=p.apply_url,
        )
        for p in candidates
    ]


# ---------------------------------------------------------------------------
# 청년전용 버팀목 전세자금대출 — 부부합산 연소득 구간별 금리(2026-08-31 기준,
# KB국민은행 대출가이드가 주택도시기금 고시를 그대로 게시 — 2026-09 조회, 3개
# 독립 출처로 교차검증됨).
# 만 19~34세(병역필 시 최대 39세, 이 앱은 나이만 반영), 임차보증금 3억원 이하,
# 전용면적 85㎡ 이하(수도권 기준) 대상. 지방 주택 0.2%p 인하, 기초생활수급자/
# 한부모/다자녀 등 추가 우대금리(최대 -1.7%p)는 이 앱이 추적하지 않는 조건이라
# 반영하지 않았다 — 실제 적용 금리는 이보다 낮을 수 있다.
_JEONSE_INCOME_BRACKETS: list[tuple[int, float]] = [
    (20_000_000, 0.022),
    (40_000_000, 0.025),
    (60_000_000, 0.029),
    (75_000_000, 0.033),
]
_JEONSE_INCOME_CAP_GENERAL_KRW = 50_000_000
_JEONSE_LTV_RATE = 0.80
_JEONSE_LOAN_CAP_KRW = 150_000_000
_JEONSE_AGE_MIN, _JEONSE_AGE_MAX = 19, 34


def _jeonse_rate(income_krw: int) -> float:
    for cap, rate in _JEONSE_INCOME_BRACKETS:
        if income_krw <= cap:
            return rate
    return _JEONSE_INCOME_BRACKETS[-1][1]


# 2026-09-03 사용자 지적("청년전용이랑 신혼부부용이랑 이자 똑같아?"): 처음엔 위
# 청년전용 표를 상품명만 바꿔 기혼 시나리오에도 그대로 재사용했다 — 실제로는
# "신혼가구 전용 버팀목 전세자금대출"이 완전히 별도 상품으로 존재하고, 청년전용
# 보다 대체로 낮은 금리에(동일 소득구간 기준 -0.3%p), 소득뿐 아니라 임차보증금
# 규모로도 한 번 더 갈리는 2차원 표를 쓴다는 걸 재조사로 확인했다(청년전용은
# 소득 단일 기준). 소득상한(7,500만원)도 청년전용(5,000만원)보다 넓다. 나이 제한도
# 없다(신혼부부전용은 "혼인기간 7년 이내"가 진짜 조건인데, 이 앱은 결혼 연차를
# 입력받지 않아 반영하지 못했다 — 이 계산기가 없는 조건으로 잘못 거르는 것보다
# fail-open이 안전하다고 판단했다). 출처: KB국민은행 대출가이드(2026-08-31 기준) +
# 정부24 서비스 상세(www.gov.kr) 교차검증.
_JEONSE_NEWLYWED_INCOME_CAP_KRW = 75_000_000
_JEONSE_NEWLYWED_LOAN_CAP_KRW = 200_000_000  # 정부24: 수도권 3억원/기타지역 2억원 — 지역 미추적이라 보수적으로 낮은 쪽
_JEONSE_NEWLYWED_RATE_TABLE: dict[int, dict[int, float]] = {
    20_000_000: {50_000_000: 0.019, 100_000_000: 0.020, 150_000_000: 0.021, 999_999_999_999: 0.022},
    40_000_000: {50_000_000: 0.022, 100_000_000: 0.023, 150_000_000: 0.024, 999_999_999_999: 0.025},
    60_000_000: {50_000_000: 0.026, 100_000_000: 0.027, 150_000_000: 0.028, 999_999_999_999: 0.029},
    75_000_000: {50_000_000: 0.030, 100_000_000: 0.031, 150_000_000: 0.032, 999_999_999_999: 0.033},
}


def _tier_lookup(table: dict[int, T], value: int) -> T:
    """구간 상한을 키로 하는 표에서 value가 속하는 구간의 값을 찾는다 — value가
    표의 최고 구간을 넘으면(예: 소득이 최상위 구간보다도 높으면) 최고 구간 값으로
    clamp한다(caller가 이미 eligibility 상한으로 income을 clamp해서 넘기므로
    실제로는 항상 표 안에서 찾아진다). 소득 구간 표(dict[int, float])와 소득×보증금
    2단 표(dict[int, dict[int, float]]) 양쪽에 재사용한다."""
    for cap in sorted(table):
        if value <= cap:
            return table[cap]
    return table[max(table)]


def _jeonse_newlywed_rate(income_krw: int, deposit_krw: int) -> float:
    row = _tier_lookup(_JEONSE_NEWLYWED_RATE_TABLE, income_krw)
    return _tier_lookup(row, deposit_krw)


def _simulate_jeonse(input: HousingLoanInput, *, is_married: bool | None, age: int | None) -> HousingLoanOutput:
    income = input.household_annual_income_krw

    if is_married:
        product_name = "신혼부부전용 버팀목 전세자금대출"
        income_cap = _JEONSE_NEWLYWED_INCOME_CAP_KRW
        loan_cap = _JEONSE_NEWLYWED_LOAN_CAP_KRW
        age_ok = True  # 신혼부부전용은 나이 제한이 없다(위 주석 참고)
        eligible = income <= income_cap
        policy_rate = _jeonse_newlywed_rate(min(income, income_cap), input.target_price_krw)
    else:
        product_name = "청년전용 버팀목 전세자금대출"
        income_cap = _JEONSE_INCOME_CAP_GENERAL_KRW
        loan_cap = _JEONSE_LOAN_CAP_KRW
        age_ok = age is None or (_JEONSE_AGE_MIN <= age <= _JEONSE_AGE_MAX)
        eligible = age_ok and income <= income_cap
        policy_rate = _jeonse_rate(min(income, income_cap))

    max_ltv_amount = round(input.target_price_krw * _JEONSE_LTV_RATE)
    price_gap = max(0, input.target_price_krw - input.self_capital_krw)
    loan_amount = min(max_ltv_amount, price_gap, loan_cap)

    monthly_interest = round(loan_amount * policy_rate / 12)
    market_monthly_interest = round(loan_amount * _ASSUMED_JEONSE_MARKET_RATE / 12)
    monthly_saving = market_monthly_interest - monthly_interest

    if not age_ok:
        summary = f"{product_name}은 만 {_JEONSE_AGE_MIN}~{_JEONSE_AGE_MAX}세만 신청할 수 있어요."
    elif not eligible:
        summary = f"부부합산 연소득이 기준({income_cap:,}원)을 초과해 이 상품 대상이 아니에요."
    else:
        summary = (
            f"{product_name} 자격 요건 충족(연 {policy_rate * 100:.1f}%). "
            f"시중 대비 매월 약 {monthly_saving:,}원 이자를 절감할 수 있어요."
        )

    return HousingLoanOutput(
        eligible=eligible,
        product_name=product_name,
        ltv_rate=_JEONSE_LTV_RATE,
        policy_rate=policy_rate,
        market_rate=_ASSUMED_JEONSE_MARKET_RATE,
        loan_amount_krw=loan_amount,
        monthly_interest_krw=monthly_interest,
        market_monthly_interest_krw=market_monthly_interest,
        monthly_saving_krw=monthly_saving if eligible else 0,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# 디딤돌대출(내집마련) — 부부합산 연소득 × 대출기간(년) 매트릭스(2026-08 기준,
# 국토교통부 주택도시기금 myhome.go.kr + KB국민은행 대출가이드 교차검증). LTV 70%,
# 순자산 5억 1,100만원 이하(이 앱은 추적 안 함), 지방 주택 0.2%p 인하는 미반영.
# "생애최초 주택구입자" 우대(소득상한 7,000만원, LTV 80%)는 이 앱에 "생애최초
# 여부" 입력이 없어 반영하지 못했다 — 신혼가구 여부(로그인 유저의 is_married)만
# 구분한다.
_PURCHASE_GENERAL_RATE_TABLE: dict[int, dict[int, float]] = {
    20_000_000: {10: 0.0285, 15: 0.0295, 20: 0.0305, 30: 0.0310},
    40_000_000: {10: 0.0320, 15: 0.0330, 20: 0.0340, 30: 0.0345},
    70_000_000: {10: 0.0355, 15: 0.0365, 20: 0.0375, 30: 0.0380},
}
_PURCHASE_NEWLYWED_RATE_TABLE: dict[int, dict[int, float]] = {
    20_000_000: {10: 0.0255, 15: 0.0265, 20: 0.0275, 30: 0.0280},
    40_000_000: {10: 0.0290, 15: 0.0300, 20: 0.0310, 30: 0.0315},
    70_000_000: {10: 0.0325, 15: 0.0335, 20: 0.0345, 30: 0.0350},
    85_000_000: {10: 0.0360, 15: 0.0370, 20: 0.0380, 30: 0.0385},
}
_PURCHASE_INCOME_CAP_GENERAL_KRW = 60_000_000
_PURCHASE_INCOME_CAP_NEWLYWED_KRW = 85_000_000
_PURCHASE_LTV_RATE = 0.70
_PURCHASE_LOAN_CAP_GENERAL_KRW = 200_000_000
_PURCHASE_LOAN_CAP_NEWLYWED_KRW = 320_000_000


def _purchase_rate(newlywed: bool, income_krw: int, loan_term_years: int) -> float:
    table = _PURCHASE_NEWLYWED_RATE_TABLE if newlywed else _PURCHASE_GENERAL_RATE_TABLE
    for cap in sorted(table):
        if income_krw <= cap:
            return table[cap][loan_term_years]
    return table[max(table)][loan_term_years]


def _simulate_purchase(input: HousingLoanInput, *, is_married: bool | None) -> HousingLoanOutput:
    # 2026-09-03: 혼인신고 계산기의 고정 기준 상품명과 맞춘다(marriage_comparison.
    # compare_housing_loan_scenarios, jeonse 쪽 주석과 동일한 이유).
    newlywed = bool(is_married)
    product_name = "신혼부부전용 디딤돌대출" if newlywed else "내집마련 디딤돌대출"
    income = input.household_annual_income_krw
    income_cap = _PURCHASE_INCOME_CAP_NEWLYWED_KRW if newlywed else _PURCHASE_INCOME_CAP_GENERAL_KRW
    loan_cap = _PURCHASE_LOAN_CAP_NEWLYWED_KRW if newlywed else _PURCHASE_LOAN_CAP_GENERAL_KRW
    eligible = income <= income_cap

    policy_rate = _purchase_rate(newlywed, min(income, income_cap), input.loan_term_years)
    max_ltv_amount = round(input.target_price_krw * _PURCHASE_LTV_RATE)
    price_gap = max(0, input.target_price_krw - input.self_capital_krw)
    loan_amount = min(max_ltv_amount, price_gap, loan_cap)

    monthly_interest = round(loan_amount * policy_rate / 12)
    market_monthly_interest = round(loan_amount * _ASSUMED_PURCHASE_MARKET_RATE / 12)
    monthly_saving = market_monthly_interest - monthly_interest

    if eligible:
        summary = (
            f"{product_name} 자격 요건 충족(연 {policy_rate * 100:.2f}%, {input.loan_term_years}년 만기 기준). "
            f"시중 대비 매월 약 {monthly_saving:,}원 이자를 절감할 수 있어요."
        )
    else:
        summary = f"부부합산 연소득이 기준({income_cap:,}원)을 초과해 이 상품 대상이 아니에요."

    return HousingLoanOutput(
        eligible=eligible,
        product_name=product_name,
        ltv_rate=_PURCHASE_LTV_RATE,
        policy_rate=policy_rate,
        market_rate=_ASSUMED_PURCHASE_MARKET_RATE,
        loan_amount_krw=loan_amount,
        monthly_interest_krw=monthly_interest,
        market_monthly_interest_krw=market_monthly_interest,
        monthly_saving_krw=monthly_saving if eligible else 0,
        summary=summary,
    )


def simulate_housing_loan(
    input: HousingLoanInput,
    *,
    is_married: bool | None = None,
    age: int | None = None,
) -> HousingLoanOutput:
    if input.housing_type == "jeonse":
        return _simulate_jeonse(input, is_married=is_married, age=age)
    return _simulate_purchase(input, is_married=is_married)


# 2026-09-02 추가: 전세/구입 대출이자 지원류는 정책명에 "전세" 또는 "구입/매매"가
# 명확히 들어가는 경우만 골라 housing_type별로 나눈다 — "디딤돌"/"버팀목" 단독
# 키워드는 실측 결과 청년창업농/IP지원 사업처럼 주거와 무관한 이름에도 비유적으로
# 쓰여서 뺐다(예: "청년창업농 디딤돌 사업", "IP 디딤돌 프로그램").
_HOUSING_LOAN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "jeonse": ("전세자금", "전세보증금"),
    "purchase": ("주택구입", "구입자금", "매매자금", "주택자금"),
}


def match_real_housing_policies(
    policies: list[CachedPolicy],
    housing_type: str,
    match_input: PolicyMatchInput,
    today: date,
) -> list[MatchedSavingsPolicy]:
    keywords = _HOUSING_LOAN_KEYWORDS[housing_type]
    candidates = [
        p
        for p in policies
        if any(keyword in p.policy_name for keyword in keywords)
        and is_eligible(p, match_input)
        and compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)[0] != "만료"
    ]
    candidates.sort(key=lambda p: STATUS_ORDER[compute_policy_status(p.apply_start_ymd, p.apply_end_ymd, today)[0]])
    candidates = _dedupe_by_policy_name(candidates)
    return [
        MatchedSavingsPolicy(
            policy_key=p.policy_key,
            policy_name=p.policy_name,
            benefit_description=p.description,
            application_period=p.application_period,
            reference_url=p.apply_url,
        )
        for p in candidates
    ]
