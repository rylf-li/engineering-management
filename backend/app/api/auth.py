"""认证 API 路由 - 登录 / 登出 / 当前用户"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.auth import create_access_token, authenticate_employee, get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])


class LoginRequest(BaseModel):
    phone: str = Field(..., max_length=20)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """手机号 + 密码登录"""
    emp = authenticate_employee(db, phone=data.phone, password=data.password)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
        )

    access_token = create_access_token(data={
        "id": emp.id,
        "phone": emp.phone,
        "role": emp.role or "员工",
    })

    return LoginResponse(
        access_token=access_token,
        user={
            "id": emp.id,
            "name": emp.name,
            "phone": emp.phone,
            "role": emp.role or "员工",
        },
    )


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user
