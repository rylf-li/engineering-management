"""
组织管理 API 路由
员工 / 部门 / 公司 / 客户 CRUD + 子表管理
"""
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.crud_base import CRUDBase
from app.utils.auth import get_current_user
from app.services.sync_engine import sync_all
from app.models import (
    Employee, EmployeeSalary, EmployeePerformance,
    Department, DepartmentRevenue,
    Company, CompanyBankAccount, CompanyRevenue,
    Customer, CustomerRevenue,
    Project, Contract, Order, Finance,
)
from app.schemas import (
    EmployeeCreate, EmployeeUpdate, EmployeeOut,
    EmployeeSalaryCreate, EmployeeSalaryUpdate, EmployeeSalaryOut,
    EmployeePerfCreate, EmployeePerfOut,
    DepartmentCreate, DepartmentUpdate, DepartmentOut,
    CompanyCreate, CompanyUpdate, CompanyOut,
    BankAccountCreate, BankAccountOut,
    CustomerCreate, CustomerUpdate, CustomerOut,
    PaginatedResponse, APIResponse,
)

# =====================================================================
# 子表查询参数 & 响应模式（未尽处在此定义）
# =====================================================================
class SortOrderUpdate(BaseModel):
    sort_order: int = Field(..., ge=0)


class BatchDeleteIn(BaseModel):
    ids: List[int]


class BatchStatusIn(BaseModel):
    ids: List[int]
    field: str
    value: str


# ---------- 绩效更新（无独立 Update Schema，复用 Create 全量） ----------
class EmployeePerfUpdate(EmployeePerfCreate):
    employee_id: Optional[int] = None
    perf_date: Optional[date] = None
    perf_amount: Optional[Decimal] = None
    orders_unfinished: Optional[int] = None
    orders_finished: Optional[int] = None
    contracts_unfinished: Optional[int] = None
    contracts_finished: Optional[int] = None
    receivable_amount: Optional[Decimal] = None
    request_amount: Optional[Decimal] = None
    collection_amount: Optional[Decimal] = None
    unrequested_amount: Optional[Decimal] = None
    expenditure: Optional[Decimal] = None
    profit: Optional[Decimal] = None


# ---------- 银行账户更新模式 ----------
class BankAccountUpdate(BaseModel):
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    account_type: Optional[str] = None
    bank_account: Optional[str] = None
    bank_name: Optional[str] = None


# ---------- 营收子表输出模式（只读） ----------
class DepartmentRevenueOut(BaseModel):
    id: int
    company_name: Optional[str] = None
    company_id: Optional[int] = None
    department_name: str
    department_id: int
    rev_date: date
    orders_unfinished: int = 0
    orders_finished: int = 0
    contracts_unfinished: int = 0
    contracts_finished: int = 0
    receivable_amount: Decimal = Decimal(0)
    request_amount: Decimal = Decimal(0)
    collection_amount: Decimal = Decimal(0)
    expenditure: Decimal = Decimal(0)
    profit: Decimal = Decimal(0)
    created_at: Optional[Any] = None

    class Config:
        from_attributes = True


class CompanyRevenueOut(BaseModel):
    id: int
    company_name: str
    company_id: int
    department_name: Optional[str] = None
    department_id: Optional[int] = None
    rev_date: date
    orders_unfinished: int = 0
    orders_finished: int = 0
    contracts_unfinished: int = 0
    contracts_finished: int = 0
    receivable_amount: Decimal = Decimal(0)
    request_amount: Decimal = Decimal(0)
    collection_amount: Decimal = Decimal(0)
    unrequested_amount: Decimal = Decimal(0)
    expenditure: Decimal = Decimal(0)
    profit: Decimal = Decimal(0)
    created_at: Optional[Any] = None

    class Config:
        from_attributes = True


class CustomerRevenueOut(BaseModel):
    id: int
    customer_name: str
    customer_id: int
    rev_date: date
    orders_unfinished: int = 0
    orders_finished: int = 0
    contracts_unfinished: int = 0
    contracts_finished: int = 0
    receivable_amount: Decimal = Decimal(0)
    request_amount: Decimal = Decimal(0)
    collection_amount: Decimal = Decimal(0)
    unrequested_amount: Decimal = Decimal(0)
    expenditure: Decimal = Decimal(0)
    profit: Decimal = Decimal(0)
    created_at: Optional[Any] = None

    class Config:
        from_attributes = True


# =====================================================================
# 辅助函数
# =====================================================================
def _paginated_response(items, total, page, page_size, schema=None):
    """构造统一分页响应"""
    if schema and items:
        try:
            items = [schema.model_validate(item).model_dump() for item in items]
        except Exception:
            items = [_orm_to_dict(item) for item in items]
    elif items and hasattr(items[0], '__table__'):
        items = [_orm_to_dict(item) for item in items]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
    }


def _orm_to_dict(obj):
    """将 ORM 对象转为字典"""
    from decimal import Decimal
    d = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, Decimal):
            val = float(val)
        d[col.name] = val
    for key in ['password_hash']:
        d.pop(key, None)
    return d


def _build_filters(
    page: int = 1,
    page_size: int = 20,
    sort_field: Optional[str] = None,
    sort_order: str = "asc",
    search: Optional[str] = None,
    **extra_filters,
) -> Dict[str, Any]:
    """构建分页 + 筛选参数"""
    return {
        "skip": (page - 1) * page_size,
        "limit": page_size,
        "sort_field": sort_field,
        "sort_order": sort_order,
        "filters": {k: v for k, v in extra_filters.items() if v is not None},
        "search": search,
    }


# =====================================================================
# 1. 员工 API
# =====================================================================
employee_router = APIRouter(prefix="/api/employees", tags=["员工管理"])

_employee_crud = CRUDBase[Employee, EmployeeCreate, EmployeeUpdate](Employee)


@employee_router.get("/")
def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    search: Optional[str] = None,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    department_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    all: bool = Query(False, description="返回全部记录（用于下拉选择）"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    if all:
        page = 1
        page_size = 99999
    params = _build_filters(
        page=page, page_size=page_size,
        sort_field=sort_field, sort_order=sort_order,
        search=search, name=name, phone=phone,
        department_id=department_id, is_active=is_active,
    )
    items, total = _employee_crud.get_multi(
        db, **params, search_fields=["name", "phone"]
    )
    return _paginated_response(items, total, page, page_size)


@employee_router.post("/", response_model=EmployeeOut)
def create_employee(
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    import hashlib
    obj_data = data.model_dump()
    password = obj_data.pop("password", "147258")
    obj_data["password_hash"] = hashlib.md5(("pwd_" + password).encode()).hexdigest()
    result = _employee_crud.create_with_dict(db, obj_data=obj_data)
    sync_all(db)
    return result


@employee_router.put("/{item_id}", response_model=EmployeeOut)
def update_employee(
    item_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _employee_crud.update(db, id=item_id, obj_in=data)
    sync_all(db)
    return result


@employee_router.delete("/{item_id}", response_model=EmployeeOut)
def delete_employee(
    item_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _employee_crud.delete(db, id=item_id)
    sync_all(db)
    return result


@employee_router.post("/batch-delete")
def batch_delete_employees(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    count = _employee_crud.batch_delete(db, ids=data.ids)
    sync_all(db)
    return APIResponse(code=200, message=f"成功删除 {count} 条记录")


@employee_router.post("/batch-status")
def batch_update_employee_status(
    data: BatchStatusIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    count = _employee_crud.batch_update_status(
        db, ids=data.ids, status_field=data.field, value=data.value
    )
    sync_all(db)
    return APIResponse(code=200, message=f"成功更新 {count} 条记录")


@employee_router.put("/{item_id}/sort-order", response_model=EmployeeOut)
def update_employee_sort_order(
    item_id: int,
    data: SortOrderUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return _employee_crud.update_sort_order(db, id=item_id, sort_order=data.sort_order)


@employee_router.get("/export/csv")
def export_employees_csv(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    csv_data = _employee_crud.export_csv(db)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"},
    )


@employee_router.post("/import/excel")
def import_employees_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _employee_crud.import_excel(db, file=file)
    return APIResponse(code=200, message=f"导入 {result['imported']} 条", data=result)


# ----- 员工工资子表 -----
_salary_crud = CRUDBase[EmployeeSalary, EmployeeSalaryCreate, EmployeeSalaryUpdate](
    EmployeeSalary
)


@employee_router.get("/{employee_id}/salaries")
def list_employee_salaries(
    employee_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    params = _build_filters(
        page=page, page_size=page_size,
        sort_field=sort_field, sort_order=sort_order,
        search=search, employee_id=employee_id,
    )
    items, total = _salary_crud.get_multi(
        db, **params, search_fields=["salary_month"]
    )
    return _paginated_response(items, total, page, page_size)


@employee_router.post("/{employee_id}/salaries", response_model=EmployeeSalaryOut)
def create_employee_salary(
    employee_id: int,
    data: EmployeeSalaryCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    data.employee_id = employee_id
    result = _salary_crud.create(db, obj_in=data)
    sync_all(db)
    return result


@employee_router.put(
    "/{employee_id}/salaries/{item_id}", response_model=EmployeeSalaryOut
)
def update_employee_salary(
    employee_id: int,
    item_id: int,
    data: EmployeeSalaryUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _salary_crud.update(db, id=item_id, obj_in=data)
    sync_all(db)
    return result


@employee_router.delete("/{employee_id}/salaries/{item_id}")
def delete_employee_salary(
    employee_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _salary_crud.delete(db, id=item_id)
    sync_all(db)
    return result


# ----- 员工绩效子表 -----
_perf_crud = CRUDBase[EmployeePerformance, EmployeePerfCreate, EmployeePerfUpdate](
    EmployeePerformance
)


@employee_router.get("/{employee_id}/performances")
def list_employee_performances(
    employee_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    params = _build_filters(
        page=page, page_size=page_size,
        sort_field=sort_field, sort_order=sort_order,
        search=search, employee_id=employee_id,
    )
    items, total = _perf_crud.get_multi(
        db, **params, search_fields=[]
    )
    return _paginated_response(items, total, page, page_size)


@employee_router.post("/{employee_id}/performances", response_model=EmployeePerfOut)
def create_employee_performance(
    employee_id: int,
    data: EmployeePerfCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    data.employee_id = employee_id
    result = _perf_crud.create(db, obj_in=data)
    sync_all(db)
    return result


@employee_router.put(
    "/{employee_id}/performances/{item_id}", response_model=EmployeePerfOut
)
def update_employee_performance(
    employee_id: int,
    item_id: int,
    data: EmployeePerfUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _perf_crud.update(db, id=item_id, obj_in=data)
    sync_all(db)
    return result


@employee_router.delete("/{employee_id}/performances/{item_id}")
def delete_employee_performance(
    employee_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _perf_crud.delete(db, id=item_id)
    sync_all(db)
    return result


# =====================================================================
# 2. 部门 API
# =====================================================================
department_router = APIRouter(prefix="/api/departments", tags=["部门管理"])

_department_crud = CRUDBase[Department, DepartmentCreate, DepartmentUpdate](Department)


@department_router.get("/")
def list_departments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    search: Optional[str] = None,
    name: Optional[str] = None,
    all: bool = Query(False, description="返回全部记录（用于下拉选择）"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    if all:
        page = 1
        page_size = 99999
    params = _build_filters(
        page=page, page_size=page_size,
        sort_field=sort_field, sort_order=sort_order,
        search=search, name=name,
    )
    items, total = _department_crud.get_multi(
        db, **params, search_fields=["name", "description"]
    )
    return _paginated_response(items, total, page, page_size)


@department_router.post("/", response_model=DepartmentOut)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _department_crud.create(db, obj_in=data)
    sync_all(db)
    return result


@department_router.put("/{item_id}", response_model=DepartmentOut)
def update_department(
    item_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _department_crud.update(db, id=item_id, obj_in=data)
    sync_all(db)
    return result


@department_router.delete("/{item_id}", response_model=DepartmentOut)
def delete_department(
    item_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _department_crud.delete(db, id=item_id)
    sync_all(db)
    return result


@department_router.post("/batch-delete")
def batch_delete_departments(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    count = _department_crud.batch_delete(db, ids=data.ids)
    sync_all(db)
    return APIResponse(code=200, message=f"成功删除 {count} 条记录")


@department_router.post("/batch-status")
def batch_update_department_status(
    data: BatchStatusIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    count = _department_crud.batch_update_status(
        db, ids=data.ids, status_field=data.field, value=data.value
    )
    sync_all(db)
    return APIResponse(code=200, message=f"成功更新 {count} 条记录")


@department_router.put("/{item_id}/sort-order", response_model=DepartmentOut)
def update_department_sort_order(
    item_id: int,
    data: SortOrderUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return _department_crud.update_sort_order(db, id=item_id, sort_order=data.sort_order)


@department_router.get("/export/csv")
def export_departments_csv(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    csv_data = _department_crud.export_csv(db)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=departments.csv"},
    )


@department_router.post("/import/excel")
def import_departments_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _department_crud.import_excel(db, file=file)
    return APIResponse(code=200, message=f"导入 {result['imported']} 条", data=result)


# ----- 部门营收子表（只读，自动生成） -----
@department_router.get("/{department_id}/revenues")
def list_department_revenues(
    department_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    rev_date_from: Optional[date] = None,
    rev_date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    query = db.query(DepartmentRevenue).filter(
        DepartmentRevenue.department_id == department_id
    )
    if rev_date_from:
        query = query.filter(DepartmentRevenue.rev_date >= rev_date_from)
    if rev_date_to:
        query = query.filter(DepartmentRevenue.rev_date <= rev_date_to)

    total = query.count()

    # 排序
    if sort_field and hasattr(DepartmentRevenue, sort_field):
        sort_col = getattr(DepartmentRevenue, sort_field)
        order_fn = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        query = query.order_by(order_fn)
    else:
        query = query.order_by(DepartmentRevenue.rev_date.desc())

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(
        [DepartmentRevenueOut.model_validate(i) for i in items],
        total, page, page_size,
    )


# =====================================================================
# 3. 公司 API
# =====================================================================
company_router = APIRouter(prefix="/api/companies", tags=["公司管理"])

_company_crud = CRUDBase[Company, CompanyCreate, CompanyUpdate](Company)


@company_router.get("/")
def list_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    search: Optional[str] = None,
    name: Optional[str] = None,
    tax_number: Optional[str] = None,
    all: bool = Query(False, description="返回全部记录（用于下拉选择）"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    if all:
        page = 1
        page_size = 99999
    params = _build_filters(
        page=page, page_size=page_size,
        sort_field=sort_field, sort_order=sort_order,
        search=search, name=name, tax_number=tax_number,
    )
    items, total = _company_crud.get_multi(
        db, **params, search_fields=["name", "address", "tax_number"]
    )
    return _paginated_response(items, total, page, page_size)


@company_router.post("/", response_model=CompanyOut)
def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _company_crud.create(db, obj_in=data)
    sync_all(db)
    return result


@company_router.put("/{item_id}", response_model=CompanyOut)
def update_company(
    item_id: int,
    data: CompanyUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _company_crud.update(db, id=item_id, obj_in=data)
    sync_all(db)
    return result


@company_router.delete("/{item_id}", response_model=CompanyOut)
def delete_company(
    item_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _company_crud.delete(db, id=item_id)
    sync_all(db)
    return result


@company_router.post("/batch-delete")
def batch_delete_companies(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    count = _company_crud.batch_delete(db, ids=data.ids)
    sync_all(db)
    return APIResponse(code=200, message=f"成功删除 {count} 条记录")


@company_router.post("/batch-status")
def batch_update_company_status(
    data: BatchStatusIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    count = _company_crud.batch_update_status(
        db, ids=data.ids, status_field=data.field, value=data.value
    )
    sync_all(db)
    return APIResponse(code=200, message=f"成功更新 {count} 条记录")


@company_router.put("/{item_id}/sort-order", response_model=CompanyOut)
def update_company_sort_order(
    item_id: int,
    data: SortOrderUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return _company_crud.update_sort_order(db, id=item_id, sort_order=data.sort_order)


@company_router.get("/export/csv")
def export_companies_csv(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    csv_data = _company_crud.export_csv(db)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=companies.csv"},
    )


@company_router.post("/import/excel")
def import_companies_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _company_crud.import_excel(db, file=file)
    return APIResponse(code=200, message=f"导入 {result['imported']} 条", data=result)


# ----- 公司银行账户子表 -----
_bank_crud = CRUDBase[CompanyBankAccount, BankAccountCreate, BankAccountUpdate](
    CompanyBankAccount
)


@company_router.get("/{company_id}/bank-accounts")
def list_company_bank_accounts(
    company_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    params = _build_filters(
        page=page, page_size=page_size,
        sort_field=sort_field, sort_order=sort_order,
        search=search, company_id=company_id,
    )
    items, total = _bank_crud.get_multi(
        db, **params, search_fields=["bank_name", "bank_account"]
    )
    return _paginated_response(items, total, page, page_size)


@company_router.post("/{company_id}/bank-accounts", response_model=BankAccountOut)
def create_company_bank_account(
    company_id: int,
    data: BankAccountCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    data.company_id = company_id
    result = _bank_crud.create(db, obj_in=data)
    sync_all(db)
    return result


@company_router.put(
    "/{company_id}/bank-accounts/{item_id}", response_model=BankAccountOut
)
def update_company_bank_account(
    company_id: int,
    item_id: int,
    data: BankAccountUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _bank_crud.update(db, id=item_id, obj_in=data)
    sync_all(db)
    return result


@company_router.delete("/{company_id}/bank-accounts/{item_id}")
def delete_company_bank_account(
    company_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _bank_crud.delete(db, id=item_id)
    sync_all(db)
    return result


# ----- 公司营收子表（只读，自动生成） -----
@company_router.get("/{company_id}/revenues")
def list_company_revenues(
    company_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    rev_date_from: Optional[date] = None,
    rev_date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    query = db.query(CompanyRevenue).filter(
        CompanyRevenue.company_id == company_id
    )
    if rev_date_from:
        query = query.filter(CompanyRevenue.rev_date >= rev_date_from)
    if rev_date_to:
        query = query.filter(CompanyRevenue.rev_date <= rev_date_to)

    total = query.count()

    if sort_field and hasattr(CompanyRevenue, sort_field):
        sort_col = getattr(CompanyRevenue, sort_field)
        order_fn = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        query = query.order_by(order_fn)
    else:
        query = query.order_by(CompanyRevenue.rev_date.desc())

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(
        [CompanyRevenueOut.model_validate(i) for i in items],
        total, page, page_size,
    )


# ----- 公司合同子表 -----
@company_router.get("/{company_id}/contracts")
def list_company_contracts(
    company_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """公司合同子表"""
    query = db.query(Contract).filter(Contract.company_id == company_id)
    total = query.count()
    if sort_field and hasattr(Contract, sort_field):
        sort_col = getattr(Contract, sort_field)
        order_fn = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        query = query.order_by(order_fn)
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)


# ----- 公司订单子表 -----
@company_router.get("/{company_id}/orders")
def list_company_orders(
    company_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """公司订单子表"""
    query = db.query(Order).filter(Order.company_id == company_id)
    total = query.count()
    if sort_field and hasattr(Order, sort_field):
        sort_col = getattr(Order, sort_field)
        order_fn = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        query = query.order_by(order_fn)
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)


# ----- 公司财务子表 -----
@company_router.get("/{company_id}/finances")
def list_company_finances(
    company_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """公司财务子表"""
    query = db.query(Finance).filter(Finance.company_id == company_id)
    total = query.count()
    if sort_field and hasattr(Finance, sort_field):
        sort_col = getattr(Finance, sort_field)
        order_fn = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        query = query.order_by(order_fn)
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)


# =====================================================================
# 4. 客户 API
# =====================================================================
customer_router = APIRouter(prefix="/api/customers", tags=["客户管理"])

_customer_crud = CRUDBase[Customer, CustomerCreate, CustomerUpdate](Customer)


@customer_router.get("/")
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    search: Optional[str] = None,
    name: Optional[str] = None,
    contact_person: Optional[str] = None,
    all: bool = Query(False, description="返回全部记录（用于下拉选择）"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    if all:
        page = 1
        page_size = 99999
    params = _build_filters(
        page=page, page_size=page_size,
        sort_field=sort_field, sort_order=sort_order,
        search=search, name=name, contact_person=contact_person,
    )
    items, total = _customer_crud.get_multi(
        db, **params, search_fields=["name", "address", "contact_person"]
    )
    return _paginated_response(items, total, page, page_size)


@customer_router.post("/", response_model=CustomerOut)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _customer_crud.create(db, obj_in=data)
    sync_all(db)
    return result


@customer_router.put("/{item_id}", response_model=CustomerOut)
def update_customer(
    item_id: int,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _customer_crud.update(db, id=item_id, obj_in=data)
    sync_all(db)
    return result


@customer_router.delete("/{item_id}", response_model=CustomerOut)
def delete_customer(
    item_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _customer_crud.delete(db, id=item_id)
    sync_all(db)
    return result


@customer_router.post("/batch-delete")
def batch_delete_customers(
    data: BatchDeleteIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    count = _customer_crud.batch_delete(db, ids=data.ids)
    sync_all(db)
    return APIResponse(code=200, message=f"成功删除 {count} 条记录")


@customer_router.post("/batch-status")
def batch_update_customer_status(
    data: BatchStatusIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    count = _customer_crud.batch_update_status(
        db, ids=data.ids, status_field=data.field, value=data.value
    )
    sync_all(db)
    return APIResponse(code=200, message=f"成功更新 {count} 条记录")


@customer_router.put("/{item_id}/sort-order", response_model=CustomerOut)
def update_customer_sort_order(
    item_id: int,
    data: SortOrderUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return _customer_crud.update_sort_order(db, id=item_id, sort_order=data.sort_order)


@customer_router.get("/export/csv")
def export_customers_csv(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    csv_data = _customer_crud.export_csv(db)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv"},
    )


@customer_router.post("/import/excel")
def import_customers_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = _customer_crud.import_excel(db, file=file)
    return APIResponse(code=200, message=f"导入 {result['imported']} 条", data=result)


# ----- 客户营收子表（只读，自动生成） -----
@customer_router.get("/{customer_id}/revenues")
def list_customer_revenues(
    customer_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    rev_date_from: Optional[date] = None,
    rev_date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    query = db.query(CustomerRevenue).filter(
        CustomerRevenue.customer_id == customer_id
    )
    if rev_date_from:
        query = query.filter(CustomerRevenue.rev_date >= rev_date_from)
    if rev_date_to:
        query = query.filter(CustomerRevenue.rev_date <= rev_date_to)

    total = query.count()

    if sort_field and hasattr(CustomerRevenue, sort_field):
        sort_col = getattr(CustomerRevenue, sort_field)
        order_fn = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        query = query.order_by(order_fn)
    else:
        query = query.order_by(CustomerRevenue.rev_date.desc())

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(
        [CustomerRevenueOut.model_validate(i) for i in items],
        total, page, page_size,
    )


# ----- 客户项目子表（通过合同关联） -----
@customer_router.get("/{customer_id}/projects")
def list_customer_projects(
    customer_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """客户项目子表（通过合同关联）"""
    project_ids = [c[0] for c in db.query(Contract.project_id).filter(
        Contract.customer_id == customer_id,
        Contract.project_id.isnot(None)
    ).all()]
    if not project_ids:
        return _paginated_response([], 0, page, page_size)
    query = db.query(Project).filter(Project.id.in_(project_ids))
    total = query.count()
    if sort_field and hasattr(Project, sort_field):
        sort_col = getattr(Project, sort_field)
        order_fn = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        query = query.order_by(order_fn)
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)


# ----- 客户合同子表 -----
@customer_router.get("/{customer_id}/contracts")
def list_customer_contracts(
    customer_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """客户合同子表"""
    query = db.query(Contract).filter(Contract.customer_id == customer_id)
    total = query.count()
    if sort_field and hasattr(Contract, sort_field):
        sort_col = getattr(Contract, sort_field)
        order_fn = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        query = query.order_by(order_fn)
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)


# ----- 客户订单子表 -----
@customer_router.get("/{customer_id}/orders")
def list_customer_orders(
    customer_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """客户订单子表"""
    query = db.query(Order).filter(Order.customer_id == customer_id)
    total = query.count()
    if sort_field and hasattr(Order, sort_field):
        sort_col = getattr(Order, sort_field)
        order_fn = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        query = query.order_by(order_fn)
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _paginated_response(items, total, page, page_size)