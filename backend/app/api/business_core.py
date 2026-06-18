"""业务核心 API 路由
项目管理 / 合同管理 / 业务服务
"""
import io
import csv
import json
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, desc as sa_desc, asc as sa_asc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Project, ProjectRevenue,
    Contract,
    BusinessService,
    Order,
    Finance,
    RequestPaymentSummary, RequestPaymentDetail,
    CollectionSummary, CollectionDetail,
)
from app.schemas import (
    PaginationParams, PaginatedResponse, BatchAction, APIResponse,
    ProjectCreate, ProjectUpdate, ProjectOut,
    ContractCreate, ContractUpdate, ContractOut,
    BizServiceCreate, BizServiceUpdate, BizServiceOut,
    OrderCreate, OrderOut,
    FinanceCreate, FinanceOut,
)
from app.utils.auth import get_current_user
from app.utils.crud_base import CRUDBase
from app.services.sync_engine import sync_all


class SortOrderUpdate(BaseModel):
    sort_order: int = Field(..., ge=0)


# ===================================================================
# CRUD 实例
# ===================================================================
project_crud: CRUDBase[Project, ProjectCreate, ProjectUpdate] = CRUDBase(Project)
contract_crud: CRUDBase[Contract, ContractCreate, ContractUpdate] = CRUDBase(Contract)
service_crud: CRUDBase[BusinessService, BizServiceCreate, BizServiceUpdate] = CRUDBase(BusinessService)


# ===================================================================
# 辅助函数 - 合同财务汇总计算
# ===================================================================
def _recalc_contract_finance(db: Session, contract: Contract) -> None:
    """按关联订单 / 财务记录重新计算合同汇总字段"""
    # 订单统计
    orders = db.query(Order).filter(Order.contract_id == contract.id).all()
    contract.orders_unfinished = sum(1 for o in orders if o.status != "已完成")
    contract.orders_finished = sum(1 for o in orders if o.status == "已完成")

    # 财务汇总（从 Finance 表聚合）
    fin_stats = (
        db.query(
            func.coalesce(func.sum(Finance.amount).filter(Finance.income_expense_type == "收入"), 0).label("receivable"),
            func.coalesce(func.sum(Finance.amount).filter(Finance.income_expense_type == "支出"), 0).label("expenditure"),
        )
        .filter(Finance.contract_id == contract.id)
        .first()
    )
    contract.receivable_amount = fin_stats.receivable or Decimal(0)
    contract.collection_amount = fin_stats.receivable or Decimal(0)  # 已收 = 收入合计

    # 请款 / 未请款 (从订单聚合)
    req_stats = (
        db.query(
            func.coalesce(func.sum(Order.biz_total_amount).filter(Order.is_requested == True), 0).label("requested"),
            func.coalesce(func.sum(Order.biz_total_amount).filter(Order.is_requested == False), 0).label("unrequested"),
        )
        .filter(Order.contract_id == contract.id)
        .first()
    )
    contract.request_amount = req_stats.requested or Decimal(0)
    contract.unrequested_amount = req_stats.unrequested or Decimal(0)

    # 利润 = 收入 - 成本 - 劳务 - 税费 - 其他 - 业务费 - 绩效
    contract.profit = (
        (fin_stats.receivable or Decimal(0))
        - contract.cost_amount
        - contract.labor_cost
        - contract.tax_fee
        - contract.other_fee
        - contract.business_fee
        - contract.bonus
    )

    db.commit()
    db.refresh(contract)


# ===================================================================
# 辅助函数 - 构建分页响应
# ===================================================================
def _paginated_response(items: List[Any], total: int, page: int, page_size: int) -> Dict[str, Any]:
    if items and hasattr(items[0], '__table__'):
        items = [_orm_to_dict(item) for item in items]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
    }


def _orm_to_dict(obj):
    from decimal import Decimal
    from datetime import date, datetime
    d = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, Decimal):
            val = float(val)
        elif isinstance(val, (date, datetime)):
            val = val.isoformat()
        d[col.name] = val
    for key in ['password_hash']:
        d.pop(key, None)
    return d


def _parse_pagination(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    search: Optional[str] = Query(None),
) -> Dict[str, Any]:
    return {
        "page": page,
        "page_size": page_size,
        "sort_field": sort_field,
        "sort_order": sort_order,
        "search": search,
    }


# ===================================================================
# 辅助函数 - 自动填充合同关联名称
# ===================================================================
def _fill_contract_names(db: Session, contract: Contract) -> None:
    """根据 customer_id / department_id / company_id 自动填充名称字段"""
    from app.models import Customer, Department, Company
    if contract.customer_id and not contract.customer_name:
        cust = db.query(Customer).filter(Customer.id == contract.customer_id).first()
        if cust:
            contract.customer_name = cust.name
    if contract.department_id and not contract.department_name:
        dept = db.query(Department).filter(Department.id == contract.department_id).first()
        if dept:
            contract.department_name = dept.name
    if contract.company_id and not contract.company_name:
        comp = db.query(Company).filter(Company.id == contract.company_id).first()
        if comp:
            contract.company_name = comp.name
    db.commit()
    db.refresh(contract)


# ===================================================================
# 路由定义 - 项目管理  /api/projects
# ===================================================================
router_projects = APIRouter(prefix="/api/projects", tags=["项目管理"])


@router_projects.get("/", response_model=Dict[str, Any])
def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    all: bool = Query(False, description="返回全部记录（用于下拉选择）"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """项目列表（分页 + 筛选）"""
    if all:
        page = 1
        page_size = 99999
    filters = {}
    if status:
        filters["status"] = status

    items, total = project_crud.get_multi(
        db,
        skip=(page - 1) * page_size,
        limit=page_size,
        sort_field=sort_field,
        sort_order=sort_order,
        filters=filters,
        search=search,
        search_fields=["project_no", "name"],
    )
    return _paginated_response(items, total, page, page_size)


@router_projects.get("/{project_id}", response_model=Dict[str, Any])
def get_project_detail(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """项目详情（含合同 / 订单 / 财务子列表）"""
    project = project_crud.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 合同子列表
    contracts = db.query(Contract).filter(Contract.project_id == project_id).all()

    # 订单子列表 (通过合同关联)
    contract_ids = [c.id for c in contracts]
    orders = (
        db.query(Order).filter(Order.contract_id.in_(contract_ids)).all()
        if contract_ids
        else []
    )

    # 财务子列表 (通过合同关联)
    finances = (
        db.query(Finance).filter(Finance.contract_id.in_(contract_ids)).all()
        if contract_ids
        else []
    )

    return {
        "project": _orm_to_dict(project),
        "contracts": [_orm_to_dict(c) for c in contracts],
        "orders": [_orm_to_dict(o) for o in orders],
        "finances": [_orm_to_dict(f) for f in finances],
    }


@router_projects.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建项目"""
    result = project_crud.create(db, obj_in=data)
    sync_all(db)
    return result


@router_projects.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新项目"""
    result = project_crud.update(db, id=project_id, obj_in=data)
    sync_all(db)
    return result


@router_projects.delete("/{project_id}", response_model=ProjectOut)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除项目"""
    result = project_crud.delete(db, id=project_id)
    sync_all(db)
    return result


@router_projects.post("/batch-delete")
def batch_delete_projects(
    data: BatchAction,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量删除项目"""
    count = project_crud.batch_delete(db, ids=data.ids)
    sync_all(db)
    return {"code": 200, "message": f"成功删除 {count} 条", "data": {"deleted": count}}


@router_projects.post("/batch-status")
def batch_update_project_status(
    data: BatchAction,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量更新项目状态"""
    value = data.value or ""
    count = project_crud.batch_update_status(db, ids=data.ids, status_field="status", value=value)
    sync_all(db)
    return {"code": 200, "message": f"成功更新 {count} 条", "data": {"updated": count}}


@router_projects.put("/{project_id}/sort-order")
def update_project_sort_order(
    project_id: int,
    data: SortOrderUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新项目排序"""
    project = project_crud.update_sort_order(db, id=project_id, sort_order=data.sort_order)
    return {"code": 200, "message": "排序已更新", "data": project}


@router_projects.get("/export/csv")
def export_projects_csv(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """导出项目 CSV"""
    filters = {}
    if status:
        filters["status"] = status
    csv_content = project_crud.export_csv(db, filters=filters)
    return {"code": 200, "data": csv_content}


@router_projects.post("/import/excel")
def import_projects_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """从 Excel 导入项目"""
    result = project_crud.import_excel(db, file=file)
    return {"code": 200, "message": f"导入 {result['imported']} 条", "data": result}


# --- 项目营收子表 (ProjectRevenue, 只读) ---

@router_projects.get("/{project_id}/revenues", response_model=Dict[str, Any])
def list_project_revenues(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """项目营收子表（只读）"""
    project = project_crud.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    query = db.query(ProjectRevenue).filter(ProjectRevenue.project_id == project_id)

    total = query.count()

    if sort_field and hasattr(ProjectRevenue, sort_field):
        col = getattr(ProjectRevenue, sort_field)
        order_fn = sa_desc if sort_order == "desc" else sa_asc
        query = query.order_by(order_fn(col))
    else:
        query = query.order_by(sa_desc(ProjectRevenue.rev_date))

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)


# ===================================================================
# 路由定义 - 合同管理  /api/contracts
# ===================================================================
router_contracts = APIRouter(prefix="/api/contracts", tags=["合同管理"])


@router_contracts.get("/", response_model=Dict[str, Any])
def list_contracts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None),
    all: bool = Query(False, description="返回全部记录（用于下拉选择）"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """合同列表（含计算财务字段：应收、请款、已收、未请款、利润）"""
    if all:
        page = 1
        page_size = 99999
    filters: Dict[str, Any] = {}
    if status:
        filters["status"] = status
    if project_id is not None:
        filters["project_id"] = project_id
    if customer_id is not None:
        filters["customer_id"] = customer_id
    if department_id is not None:
        filters["department_id"] = department_id
    if company_id is not None:
        filters["company_id"] = company_id

    items, total = contract_crud.get_multi(
        db,
        skip=(page - 1) * page_size,
        limit=page_size,
        sort_field=sort_field,
        sort_order=sort_order,
        filters=filters,
        search=search,
        search_fields=["contract_no", "name", "customer_name"],
    )

    # 合同模型已含 computed 财务字段（通过 create/update 时 recalc 写入）
    return _paginated_response(items, total, page, page_size)


@router_contracts.get("/{contract_id}", response_model=Dict[str, Any])
def get_contract_detail(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """合同详情"""
    contract = contract_crud.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    # 触发财务重算
    _recalc_contract_finance(db, contract)

    # 关联数据
    orders = db.query(Order).filter(Order.contract_id == contract_id).all()
    finances = db.query(Finance).filter(Finance.contract_id == contract_id).all()

    return {
        "contract": _orm_to_dict(contract),
        "orders": [_orm_to_dict(o) for o in orders],
        "finances": [_orm_to_dict(f) for f in finances],
    }


@router_contracts.post("/", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
def create_contract(
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建合同（自动填充客户/部门/公司名称）"""
    from app.models import Customer, Department, Company
    # 验证外键引用存在，不存在的设为 None 防止 FK 约束失败
    create_data = data.model_dump()
    if create_data.get("customer_id"):
        if not db.query(Customer).filter(Customer.id == create_data["customer_id"]).first():
            create_data["customer_id"] = None
    if create_data.get("department_id"):
        if not db.query(Department).filter(Department.id == create_data["department_id"]).first():
            create_data["department_id"] = None
    if create_data.get("company_id"):
        if not db.query(Company).filter(Company.id == create_data["company_id"]).first():
            create_data["company_id"] = None
    contract = contract_crud.create_with_dict(db, obj_data=create_data)
    # 自动填充关联名称
    _fill_contract_names(db, contract)
    _recalc_contract_finance(db, contract)
    sync_all(db)
    return contract


@router_contracts.put("/{contract_id}", response_model=ContractOut)
def update_contract(
    contract_id: int,
    data: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新合同（自动填充名称，触发财务字段重算）"""
    from app.models import Customer, Department, Company
    # 验证外键引用存在，不存在的设为 None
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("customer_id"):
        if not db.query(Customer).filter(Customer.id == update_data["customer_id"]).first():
            update_data["customer_id"] = None
    if update_data.get("department_id"):
        if not db.query(Department).filter(Department.id == update_data["department_id"]).first():
            update_data["department_id"] = None
    if update_data.get("company_id"):
        if not db.query(Company).filter(Company.id == update_data["company_id"]).first():
            update_data["company_id"] = None
    contract = contract_crud.update_with_dict(db, id=contract_id, obj_data=update_data)
    _fill_contract_names(db, contract)
    _recalc_contract_finance(db, contract)
    sync_all(db)
    return contract


@router_contracts.delete("/{contract_id}", response_model=ContractOut)
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除合同"""
    result = contract_crud.delete(db, id=contract_id)
    sync_all(db)
    return result


@router_contracts.post("/batch-delete")
def batch_delete_contracts(
    data: BatchAction,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量删除合同"""
    count = contract_crud.batch_delete(db, ids=data.ids)
    sync_all(db)
    return {"code": 200, "message": f"成功删除 {count} 条", "data": {"deleted": count}}


@router_contracts.post("/batch-status")
def batch_update_contract_status(
    data: BatchAction,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量更新合同状态"""
    value = data.value or ""
    count = contract_crud.batch_update_status(db, ids=data.ids, status_field="status", value=value)

    # 重算受影响合同的财务字段
    if count:
        for cid in data.ids:
            contract = contract_crud.get(db, id=cid)
            if contract:
                _recalc_contract_finance(db, contract)
    sync_all(db)

    return {"code": 200, "message": f"成功更新 {count} 条", "data": {"updated": count}}


@router_contracts.put("/{contract_id}/sort-order")
def update_contract_sort_order(
    contract_id: int,
    data: SortOrderUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新合同排序"""
    contract = contract_crud.update_sort_order(db, id=contract_id, sort_order=data.sort_order)
    return {"code": 200, "message": "排序已更新", "data": contract}


@router_contracts.get("/export/csv")
def export_contracts_csv(
    status: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """导出合同 CSV"""
    filters: Dict[str, Any] = {}
    if status:
        filters["status"] = status
    if project_id is not None:
        filters["project_id"] = project_id
    csv_content = contract_crud.export_csv(db, filters=filters)
    return {"code": 200, "data": csv_content}


@router_contracts.post("/import/excel")
def import_contracts_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """从 Excel 导入合同"""
    result = contract_crud.import_excel(db, file=file)

    # 对新导入的合同触发财务重算
    if result["imported"] > 0:
        contracts = db.query(Contract).order_by(sa_desc(Contract.id)).limit(result["imported"]).all()
        for c in contracts:
            _recalc_contract_finance(db, c)
    sync_all(db)

    return {"code": 200, "message": f"导入 {result['imported']} 条", "data": result}


# --- 合同营收统计（手动触发重算） ---

@router_contracts.post("/{contract_id}/recalc-finance")
def recalc_contract_finance(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """手动触发合同财务字段重算"""
    contract = contract_crud.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    _recalc_contract_finance(db, contract)
    return {"code": 200, "message": "财务字段重算完成", "data": contract}


# ===================================================================
# 路由定义 - 业务服务  /api/business-services
# ===================================================================
router_services = APIRouter(prefix="/api/business-services", tags=["业务服务管理"])


@router_services.get("/", response_model=Dict[str, Any])
def list_services(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """业务服务列表（分页 + 筛选）"""
    filters: Dict[str, Any] = {}
    if category:
        filters["category"] = category

    items, total = service_crud.get_multi(
        db,
        skip=(page - 1) * page_size,
        limit=page_size,
        sort_field=sort_field,
        sort_order=sort_order,
        filters=filters,
        search=search,
        search_fields=["item_name", "parameters", "category"],
    )
    return _paginated_response(items, total, page, page_size)


@router_services.get("/{service_id}", response_model=BizServiceOut)
def get_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取单个业务服务"""
    service = service_crud.get(db, id=service_id)
    if not service:
        raise HTTPException(status_code=404, detail="业务服务不存在")
    return service


@router_services.post("/", response_model=BizServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    data: BizServiceCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建业务服务"""
    result = service_crud.create(db, obj_in=data)
    sync_all(db)
    return result


@router_services.put("/{service_id}", response_model=BizServiceOut)
def update_service(
    service_id: int,
    data: BizServiceUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新业务服务"""
    result = service_crud.update(db, id=service_id, obj_in=data)
    sync_all(db)
    return result


@router_services.delete("/{service_id}", response_model=BizServiceOut)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除业务服务"""
    result = service_crud.delete(db, id=service_id)
    sync_all(db)
    return result


@router_services.post("/batch-delete")
def batch_delete_services(
    data: BatchAction,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量删除业务服务"""
    count = service_crud.batch_delete(db, ids=data.ids)
    sync_all(db)
    return {"code": 200, "message": f"成功删除 {count} 条", "data": {"deleted": count}}


@router_services.post("/batch-status")
def batch_update_service_status(
    data: BatchAction,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """批量更新业务服务状态（占位，BusinessService 无 status 字段）"""
    # BusinessService 没有 status 字段，返回提示
    return {"code": 400, "message": "业务服务模块不支持批量状态更新", "data": None}


@router_services.put("/{service_id}/sort-order")
def update_service_sort_order(
    service_id: int,
    data: SortOrderUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新业务服务排序"""
    service = service_crud.update_sort_order(db, id=service_id, sort_order=data.sort_order)
    return {"code": 200, "message": "排序已更新", "data": service}


@router_services.get("/export/csv")
def export_services_csv(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """导出业务服务 CSV"""
    filters: Dict[str, Any] = {}
    if category:
        filters["category"] = category
    csv_content = service_crud.export_csv(db, filters=filters)
    return {"code": 200, "data": csv_content}


@router_services.post("/import/excel")
def import_services_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """从 Excel 导入业务服务"""
    result = service_crud.import_excel(db, file=file)
    return {"code": 200, "message": f"导入 {result['imported']} 条", "data": result}


# ===================================================================
# 追加端点 - 项目拖拽排序 & 子表 & 合同拖拽排序
# ===================================================================

@router_projects.post("/reorder")
def reorder_projects(
    data: BatchAction,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """项目拖拽排序"""
    for i, item_id in enumerate(data.ids):
        db.query(Project).filter(Project.id == item_id).update({"sort_order": i})
    db.commit()
    return {"message": "排序更新成功", "data": {"updated": len(data.ids)}}


@router_projects.get("/{project_id}/contracts", response_model=Dict[str, Any])
def list_project_contracts(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """项目合同子表"""
    project = project_crud.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    query = db.query(Contract).filter(Contract.project_id == project_id)
    total = query.count()
    if sort_field and hasattr(Contract, sort_field):
        col = getattr(Contract, sort_field)
        order_fn = sa_desc if sort_order == "desc" else sa_asc
        query = query.order_by(order_fn(col))
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)


@router_projects.post("/{project_id}/contracts", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
def create_project_contract(
    project_id: int,
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """在项目下创建合同（自动关联项目ID，自动填充名称）"""
    from app.models import Customer, Department, Company
    project = project_crud.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    # 强制设置 project_id 关联到项目
    create_data = data.model_dump()
    create_data["project_id"] = project_id
    # 验证外键引用存在
    if create_data.get("customer_id"):
        if not db.query(Customer).filter(Customer.id == create_data["customer_id"]).first():
            create_data["customer_id"] = None
    if create_data.get("department_id"):
        if not db.query(Department).filter(Department.id == create_data["department_id"]).first():
            create_data["department_id"] = None
    if create_data.get("company_id"):
        if not db.query(Company).filter(Company.id == create_data["company_id"]).first():
            create_data["company_id"] = None
    contract = contract_crud.create_with_dict(db, obj_data=create_data)
    _fill_contract_names(db, contract)
    _recalc_contract_finance(db, contract)
    return contract


@router_projects.get("/{project_id}/orders", response_model=Dict[str, Any])
def list_project_orders(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """项目订单子表（通过合同关联）"""
    project = project_crud.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    contract_ids = [c[0] for c in db.query(Contract.id).filter(Contract.project_id == project_id).all()]
    if not contract_ids:
        return _paginated_response([], 0, page, page_size)
    query = db.query(Order).filter(Order.contract_id.in_(contract_ids))
    total = query.count()
    if sort_field and hasattr(Order, sort_field):
        col = getattr(Order, sort_field)
        order_fn = sa_desc if sort_order == "desc" else sa_asc
        query = query.order_by(order_fn(col))
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)


@router_projects.post("/{project_id}/orders", status_code=status.HTTP_201_CREATED)
def create_project_order(
    project_id: int,
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """在项目下创建新订单（自动关联合同）"""
    from app.models import Customer, Department, Company
    project = project_crud.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    create_data = data.model_dump()
    # 验证外键引用存在
    if create_data.get("customer_id"):
        if not db.query(Customer).filter(Customer.id == create_data["customer_id"]).first():
            create_data["customer_id"] = None
    if create_data.get("department_id"):
        if not db.query(Department).filter(Department.id == create_data["department_id"]).first():
            create_data["department_id"] = None
    if create_data.get("company_id"):
        if not db.query(Company).filter(Company.id == create_data["company_id"]).first():
            create_data["company_id"] = None
    if create_data.get("contract_id"):
        if not db.query(Contract).filter(Contract.id == create_data["contract_id"]).first():
            create_data["contract_id"] = None
    order = Order(**create_data)
    db.add(order)
    db.commit()
    db.refresh(order)
    return _orm_to_dict(order)


@router_projects.get("/{project_id}/finances", response_model=Dict[str, Any])
def list_project_finances(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """项目财务子表（通过合同关联）"""
    project = project_crud.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    contract_ids = [c[0] for c in db.query(Contract.id).filter(Contract.project_id == project_id).all()]
    if not contract_ids:
        return _paginated_response([], 0, page, page_size)
    query = db.query(Finance).filter(Finance.contract_id.in_(contract_ids))
    total = query.count()
    if sort_field and hasattr(Finance, sort_field):
        col = getattr(Finance, sort_field)
        order_fn = sa_desc if sort_order == "desc" else sa_asc
        query = query.order_by(order_fn(col))
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)


@router_projects.post("/{project_id}/finances", status_code=status.HTTP_201_CREATED)
def create_project_finance(
    project_id: int,
    data: FinanceCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """在项目下创建新财务记录"""
    project = project_crud.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    finance = Finance(**data.dict())
    db.add(finance)
    db.commit()
    db.refresh(finance)
    return _orm_to_dict(finance)


# ===================================================================
# 合同拖拽排序
# ===================================================================

@router_contracts.post("/reorder")
def reorder_contracts(
    data: BatchAction,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """合同拖拽排序"""
    for i, item_id in enumerate(data.ids):
        db.query(Contract).filter(Contract.id == item_id).update({"sort_order": i})
    db.commit()
    return {"message": "排序更新成功", "data": {"updated": len(data.ids)}}


# ===================================================================
# 合同子表端点: 订单 / 财务 / 请款 / 收款
# ===================================================================

from typing import Optional
from datetime import date


@router_contracts.get("/{contract_id}/orders", response_model=Dict[str, Any])
def list_contract_orders(
    contract_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """合同关联的订单子表"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    query = db.query(Order).filter(Order.contract_id == contract_id)

    total = query.count()

    if sort_field:
        col = getattr(Order, sort_field, None)
        if col:
            query = query.order_by(sa_desc(col) if sort_order == "desc" else sa_asc(col))

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)


@router_contracts.get("/{contract_id}/finances", response_model=Dict[str, Any])
def list_contract_finances(
    contract_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """合同关联的财务记录子表"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    query = db.query(Finance).filter(Finance.contract_id == contract_id)

    total = query.count()

    if sort_field:
        col = getattr(Finance, sort_field, None)
        if col:
            query = query.order_by(sa_desc(col) if sort_order == "desc" else sa_asc(col))

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)


@router_contracts.get("/{contract_id}/request-payments", response_model=Dict[str, Any])
def list_contract_request_payments(
    contract_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """合同关联的请款汇总子表"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    query = db.query(RequestPaymentSummary).filter(RequestPaymentSummary.contract_id == contract_id)

    total = query.count()

    if sort_field:
        col = getattr(RequestPaymentSummary, sort_field, None)
        if col:
            query = query.order_by(sa_desc(col) if sort_order == "desc" else sa_asc(col))

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)


@router_contracts.get("/{contract_id}/collections", response_model=Dict[str, Any])
def list_contract_collections(
    contract_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """合同关联的收款汇总子表"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    query = db.query(CollectionSummary).filter(CollectionSummary.contract_id == contract_id)

    total = query.count()

    if sort_field:
        col = getattr(CollectionSummary, sort_field, None)
        if col:
            query = query.order_by(sa_desc(col) if sort_order == "desc" else sa_asc(col))

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)