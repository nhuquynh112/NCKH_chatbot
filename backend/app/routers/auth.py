from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.config import settings
from app.core.security import create_access_token
from app.schemas.common import APIResponse

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login", response_model=APIResponse[dict])
def login(request: LoginRequest):
    if request.username == settings.ADMIN_USERNAME and request.password == settings.ADMIN_PASSWORD:
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
