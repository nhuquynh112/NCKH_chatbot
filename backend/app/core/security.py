import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"iat": issued_at, "exp": expire, "type": "admin"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def _admin_username_from_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username != settings.ADMIN_USERNAME or payload.get("type") != "admin":
            raise HTTPException(status_code=403, detail="Not an admin")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_admin_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    return _admin_username_from_token(credentials.credentials)


def has_valid_admin_credentials(
    credentials: HTTPAuthorizationCredentials | None,
) -> bool:
    if credentials is None:
        return False
    try:
        _admin_username_from_token(credentials.credentials)
        return True
    except HTTPException:
        return False
