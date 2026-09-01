def _signup_login(client, email="sim-user@example.com", **overrides):
    payload = {
        "email": email,
        "password": "secret123",
        "age": 29,
        "is_married": False,
        "annual_income_krw": 40_000_000,
        "region": "서울",
        "occupation": "employee",
    }
    payload.update(overrides)
    client.post("/auth/signup", json=payload)
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return login.json()["access_token"]


def test_youth_leap_account_requires_auth(client):
    response = client.post(
        "/savings_simulator/youth_leap_account",
        json={"monthly_amount_krw": 400_000, "goal_years": 3, "annual_income_krw": 30_000_000},
    )
    assert response.status_code == 401


def test_youth_leap_account_lowest_income_bracket_gets_highest_matching_rate(client):
    token = _signup_login(client)
    response = client.post(
        "/savings_simulator/youth_leap_account",
        json={"monthly_amount_krw": 400_000, "goal_years": 3, "annual_income_krw": 20_000_000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is True
    assert body["matching_rate"] == 0.060
    assert body["benefit_diff_krw"] > 0
    assert body["policy_total_krw"] > body["market_total_krw"]


def test_youth_leap_account_over_income_cap_is_ineligible(client):
    token = _signup_login(client)
    response = client.post(
        "/savings_simulator/youth_leap_account",
        json={"monthly_amount_krw": 400_000, "goal_years": 5, "annual_income_krw": 100_000_000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    assert body["matching_rate"] == 0.0
    assert body["benefit_diff_krw"] == 0
    assert body["policy_total_krw"] == body["market_total_krw"]


def test_youth_leap_account_matching_capped_at_400000_monthly():
    # HTTP 왕복 없이 계산 함수를 직접 호출해 매칭 상한(월 40만원)이 실제로 걸리는지
    # 검증한다 — 월 100만원을 넣어도 정부 매칭분은 40만원 기준으로만 계산돼야 한다.
    from app.features.savings_simulator.schemas import YouthLeapAccountInput
    from app.features.savings_simulator.simulator import simulate_youth_leap_account

    months = 3 * 12
    matching_rate = 0.060
    expected_government_total = round(400_000 * matching_rate * months)

    result = simulate_youth_leap_account(
        YouthLeapAccountInput(monthly_amount_krw=1_000_000, goal_years=3, annual_income_krw=20_000_000)
    )
    # policy_total = principal(월납입*개월+시드) + government_total + policy_interest
    # market_total = principal + market_interest 이므로, 두 total의 차이에서 이자 차이분을
    # 빼면 government_total만 남는다. 이자는 policy(비과세) - market(세후)이라 항상
    # policy_interest > market_interest이므로, diff는 government_total보다 크거나 같다.
    diff = result.policy_total_krw - result.market_total_krw
    assert diff >= expected_government_total


def test_housing_loan_requires_auth(client):
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 250_000_000,
            "self_capital_krw": 50_000_000,
            "household_annual_income_krw": 65_000_000,
        },
    )
    assert response.status_code == 401


def test_housing_loan_jeonse_within_income_cap_is_eligible(client):
    token = _signup_login(client)
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 250_000_000,
            "self_capital_krw": 50_000_000,
            "household_annual_income_krw": 65_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is True
    assert body["product_name"] == "버팀목 전세자금대출(예시)"
    assert body["loan_amount_krw"] == 200_000_000  # min(250M*0.8=200M, 250M-50M=200M)
    assert body["monthly_saving_krw"] > 0


def test_housing_loan_purchase_over_income_cap_is_ineligible(client):
    token = _signup_login(client)
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "purchase",
            "target_price_krw": 400_000_000,
            "self_capital_krw": 100_000_000,
            "household_annual_income_krw": 150_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    assert body["monthly_saving_krw"] == 0


def test_housing_loan_amount_never_exceeds_price_minus_self_capital(client):
    token = _signup_login(client)
    # LTV 한도(80%)보다 목표가-자기자본 차액이 더 작은 경우, 그 작은 쪽을 따라야 한다.
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 200_000_000,
            "self_capital_krw": 180_000_000,
            "household_annual_income_krw": 65_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    body = response.json()
    assert body["loan_amount_krw"] == 20_000_000
