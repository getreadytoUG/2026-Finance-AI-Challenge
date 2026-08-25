import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

# 프로세스가 새로 뜰 때마다(=새 배포/재시작) 값이 바뀐다. 발급되는 토큰마다 이 값을
# 같이 심어두고 검증 시 지금 떠 있는 프로세스의 값과 비교한다 — 재배포 전에
# 발급됐던 토큰은 새 프로세스에서 전부 무효 처리되어, 데모 계정을 포함해 로그인해
# 있던 모두가 강제 로그아웃된다(재로그인은 그대로 가능). SQLite가 재배포 때
# 초기화되는지 여부와 무관하게 항상 동작하도록 별도 메커니즘으로 둔다.
BOOT_ID = uuid.uuid4().hex


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_minutes: int = 60 * 24) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "exp": expire, "boot": BOOT_ID}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    if payload.get("boot") != BOOT_ID:
        raise JWTError("Token was issued before the current server boot")
    return payload["sub"]
