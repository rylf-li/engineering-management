"""认证工具 - JWT 登录 + 用户依赖注入"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee

# JWT 配置
SECRET_KEY = "jcgs0527-engineering-mgmt-secret-key-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 小时

security = HTTPBearer(auto_error=False)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """验证密码（使用 MD5 匹配现有种子数据）"""
    import hashlib
    return password_hash == hashlib.md5(("pwd_" + plain_password).encode()).hexdigest()


def authenticate_employee(db: Session, phone: str, password: str) -> Optional[Employee]:
    """通过手机号和密码验证员工"""
    emp = db.query(Employee).filter(Employee.phone == phone).first()
    if not emp:
        return None
    if not verify_password(password, emp.password_hash):
        return None
    return emp


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """JWT 认证依赖 - 从 token 中解析当前用户"""
    if credentials is None:
        # 未登录时返回访客身份（前端登录页可访问）
        return {"id": 0, "role": "guest", "name": "未登录"}

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        emp_id: int = payload.get("id")
        if emp_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证令牌已过期或无效",
        )

    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if emp is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    return {
        "id": emp.id,
        "name": emp.name,
        "phone": emp.phone,
        "role": emp.role or "员工",
    }
