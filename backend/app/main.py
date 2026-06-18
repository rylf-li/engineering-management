"""FastAPI 主应用"""
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import DATA_DIR, UPLOAD_DIR
from app.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info("🚀 工程检测管理系统启动中...")
    init_db()
    logger.info("✅ 数据库初始化完成")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("👋 应用关闭")


app = FastAPI(
    title="工程检测公司综合管理系统",
    description="检测、测绘、勘察工程类第三方服务公司综合管理平台",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 注册 API 路由（必须在静态文件之前） =====
from app.api.org_management import (
    employee_router,
    department_router,
    company_router,
    customer_router,
)
from app.api.business_core import (
    router_projects,
    router_contracts,
    router_services,
)
from app.api.finance_ops import (
    router_orders,
    router_request_payments,
    router_collections,
    router_finances,
)
from app.api.reports import router_reports
from app.api.auth import router as auth_router
from app.utils.auth import get_current_user

app.include_router(employee_router)
app.include_router(department_router)
app.include_router(company_router)
app.include_router(customer_router)
app.include_router(router_projects)
app.include_router(router_contracts)
app.include_router(router_services)
app.include_router(router_orders)
app.include_router(router_request_payments)
app.include_router(router_collections)
app.include_router(router_finances)
app.include_router(router_reports)
app.include_router(auth_router)

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/api/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return current_user

# ===== 静态文件 + SPA fallback (Middleware 方式) =====
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    # 1. 挂载 /assets 目录 — JS/CSS/字体等静态资源
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # 2. SPA fallback 中间件 — 仅对非 API/非静态路径的 404 返回 index.html
    class SPAFallbackMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            if response.status_code == 404:
                path = request.url.path
                # 跳过 API / 静态资源 / 文档路径
                if not any(path.startswith(p) for p in (
                    "/api/", "/assets/", "/uploads/",
                    "/docs", "/redoc", "/openapi.json",
                )):
                    index_path = FRONTEND_DIST / "index.html"
                    if index_path.exists():
                        return FileResponse(str(index_path))
            return response

    app.add_middleware(SPAFallbackMiddleware)

else:
    @app.get("/")
    async def root():
        return {"name": "工程检测公司综合管理系统 API", "version": "1.0.0", "docs": "/docs"}