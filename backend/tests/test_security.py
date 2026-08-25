import pytest
from jose import JWTError

from app.core import security


def test_decode_access_token_returns_subject_for_current_boot():
    token = security.create_access_token(subject="42")
    assert security.decode_access_token(token) == "42"


def test_decode_access_token_rejects_token_issued_before_a_restart(monkeypatch):
    # BOOT_ID는 프로세스가 새로 뜰 때마다 바뀐다 — 재배포/재시작을 흉내 내려면
    # 토큰 발급 이후에 BOOT_ID를 바꿔서 검증한다.
    token = security.create_access_token(subject="42")
    monkeypatch.setattr(security, "BOOT_ID", "a-different-boot-id")
    with pytest.raises(JWTError):
        security.decode_access_token(token)
