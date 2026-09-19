from fastapi import APIRouter, HTTPException, status
from hmac import compare_digest

from pydantic import BaseModel, ConfigDict, Field
from app.config import settings
from app.core.security import create_access_token
from app.schemas.common import APIResponse

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=255)

    model_config = ConfigDict(extra="forbid")

@router.post("/login", response_model=APIResponse[dict])
def login(request: LoginRequest):
    username_ok = compare_digest(request.username, settings.ADMIN_USERNAME)
    password_ok = compare_digest(request.password, settings.ADMIN_PASSWORD)
    if username_ok and password_ok:
        token = create_access_token(data={"sub": request.username})
        return APIResponse(
            success=True,
            message="Đăng nhập thành công",
            data={"access_token": token, "token_type": "bearer"}
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sai tài khoản hoặc mật khẩu",
    )
