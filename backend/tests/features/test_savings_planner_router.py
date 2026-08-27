def _signup_login(client, email="savings-user@example.com"):
    client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": "secret123",
            "age": 29,
            "is_married": False,
            "annual_income_krw": 40_000_000,
            "region": "서울",
            "occupation": "employee",
        },
    )
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return login.json()["access_token"]


def test_list_linked_benefits_requires_auth(client):
    response = client.get("/savings_planner/linked_benefits")
    assert response.status_code == 401


def test_link_benefit_requires_auth(client):
    response = client.post(
        "/savings_planner/linked_benefits",
        json={"policy_key": "P1", "policy_name": "정책", "estimated_monthly_benefit_krw": 200_000},
    )
    assert response.status_code == 401


def test_list_linked_benefits_starts_empty(client):
    token = _signup_login(client)
    response = client.get("/savings_planner/linked_benefits", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total_monthly_benefit_krw"] == 0


def test_link_benefit_creates_and_lists_it(client):
    token = _signup_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/savings_planner/linked_benefits",
        json={"policy_key": "P1", "policy_name": "청년 월세 지원", "estimated_monthly_benefit_krw": 200_000},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["policy_key"] == "P1"
    assert body["policy_name"] == "청년 월세 지원"
    assert body["estimated_monthly_benefit_krw"] == 200_000
    assert "id" in body

    listed = client.get("/savings_planner/linked_benefits", headers=headers).json()
    assert listed["total_monthly_benefit_krw"] == 200_000
    assert len(listed["items"]) == 1


def test_link_benefit_upserts_on_duplicate_policy_key(client):
    token = _signup_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        "/savings_planner/linked_benefits",
        json={"policy_key": "P1", "policy_name": "정책", "estimated_monthly_benefit_krw": 200_000},
        headers=headers,
    ).json()
    second = client.post(
        "/savings_planner/linked_benefits",
        json={"policy_key": "P1", "policy_name": "정책(갱신)", "estimated_monthly_benefit_krw": 300_000},
        headers=headers,
    ).json()

    assert first["id"] == second["id"]
    assert second["estimated_monthly_benefit_krw"] == 300_000

    listed = client.get("/savings_planner/linked_benefits", headers=headers).json()
    assert len(listed["items"]) == 1
    assert listed["total_monthly_benefit_krw"] == 300_000


def test_unlink_benefit_removes_it(client):
    token = _signup_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/savings_planner/linked_benefits",
        json={"policy_key": "P1", "policy_name": "정책", "estimated_monthly_benefit_krw": 200_000},
        headers=headers,
    ).json()

    response = client.delete(f"/savings_planner/linked_benefits/{created['id']}", headers=headers)
    assert response.status_code == 204

    listed = client.get("/savings_planner/linked_benefits", headers=headers).json()
    assert listed["items"] == []


def test_unlink_benefit_requires_auth(client):
    response = client.delete("/savings_planner/linked_benefits/1")
    assert response.status_code == 401


def test_unlink_benefit_404_for_unknown_id(client):
    token = _signup_login(client)
    response = client.delete(
        "/savings_planner/linked_benefits/999999", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_unlink_benefit_404_for_other_users_benefit(client):
    owner_token = _signup_login(client, email="owner@example.com")
    other_token = _signup_login(client, email="other@example.com")
    created = client.post(
        "/savings_planner/linked_benefits",
        json={"policy_key": "P1", "policy_name": "정책", "estimated_monthly_benefit_krw": 200_000},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()

    response = client.delete(
        f"/savings_planner/linked_benefits/{created['id']}", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert response.status_code == 404

    # 소유자 쪽에는 여전히 남아 있어야 한다.
    listed = client.get(
        "/savings_planner/linked_benefits", headers={"Authorization": f"Bearer {owner_token}"}
    ).json()
    assert len(listed["items"]) == 1
