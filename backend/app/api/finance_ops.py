"""
财务运营 API 路由
Order / RequestPayment / Collection / Finance 模块
扁平响应风格（同 org_management.py）
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Contract,
    Order,
    RequestPaymentSummary,
    RequestPaymentDetail,
    CollectionSummary,
    CollectionDetail,
    Finance,
)
from app.schemas import (
    BatchAction,
    OrderCreate,
    OrderOut,
    OrderUpdate,
    RequestSummaryCreate,
    RequestSummaryOut,
    RequestDetailOut,
    CollectionSummaryCreate,
    CollectionSummaryOut,
    CollectionDetailOut,
    FinanceCreate,
    FinanceOut,
    FinanceUpdate,
    PaginatedResponse,
)
from app.services.sync_engine import sync_all
from app.utils.crud_base import CRUDBase
from app.utils.auth import get_current_user

# ---- 独立路由器 ----
router_orders = APIRouter(prefix="/api/orders", tags=["订单管理"])
router_request_payments = APIRouter(prefix="/api/request-payments", tags=["请款管理"])
router_collections = APIRouter(prefix="/api/collections", tags=["收款管理"])
router_finances = APIRouter(prefix="/api/finances", tags=["财务管理"])


# ---- CRUD 实例 ----
order_crud = CRUDBase(Order)
request_summary_crud = CRUDBase(RequestPaymentSummary)
collection_summary_crud = CRUDBase(CollectionSummary)
finance_crud = CRUDBase(Finance)


# ---- 批量操作请求模型 ----
class BatchRequestInput(BaseModel):
    order_ids: List[int]
    batch_no: str
    request_date: date
    contract_id: int


class BatchCollectInput(BaseModel):
    order_ids: List[int]
    batch_no: str
    collection_date: date
    contract_id: int
    actual_amount: Decimal = Decimal(0)
    collection_amount: Decimal = Decimal(0)
    status: str = "待收款"


# ==================== 辅助函数 ====================

def _orm_to_dict(obj):
    """将 ORM 对象转为字典"""
    d = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, Decimal):
            val = float(val)
        d[col.name] = val
    for key in ['password_hash']:
        d.pop(key, None)
    return d


def _recalc_contract_financials(db: Session, contract_id: int):
    """重新计算合同的财务汇总字段"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        return

    orders = db.query(Order).filter(Order.contract_id == contract_id).all()

    # 订单统计
    contract.orders_unfinished = sum(1 for o in orders if o.status != "已完成")
    contract.orders_finished = sum(1 for o in orders if o.status == "已完成")

    # 应收金额 = 所有未收款的订单合计金额之和
    contract.receivable_amount = sum(
        (o.biz_total_amount or Decimal(0)) for o in orders if not o.is_collected
    )

    # 请款金额 = 所有关联请款明细之和
    request_total = (
        db.query(func.coalesce(func.sum(RequestPaymentDetail.request_amount), 0))
        .join(RequestPaymentSummary, RequestPaymentDetail.summary_id == RequestPaymentSummary.id)
        .filter(RequestPaymentSummary.contract_id == contract_id)
        .scalar()
    )
    contract.request_amount = request_total or Decimal(0)

    # 收款金额 = 所有关联收款明细之和
    collection_total = (
        db.query(func.coalesce(func.sum(CollectionDetail.actual_amount), 0))
        .join(CollectionSummary, CollectionDetail.summary_id == CollectionSummary.id)
        .filter(CollectionSummary.contract_id == contract_id)
        .scalar()
    )
    contract.collection_amount = collection_total or Decimal(0)

    # 未请款金额 = 应收 - 请款
    contract.unrequested_amount = max(
        Decimal(0), (contract.receivable_amount or Decimal(0)) - (contract.request_amount or Decimal(0))
    )

    db.commit()
    db.refresh(contract)


def _orm_to_dict(obj) -> dict:
    """Convert SQLAlchemy ORM object to a serializable dict."""
    if obj is None:
        return None
    d = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, Decimal):
            d[col.name] = float(val)
        elif isinstance(val, datetime):
            d[col.name] = val.isoformat()
        elif isinstance(val, date):
            d[col.name] = val.isoformat()
        else:
            d[col.name] = val
    return d


def _build_paginated_response(items: List, total: int, page: int, page_size: int) -> PaginatedResponse:
    serialized_items = []
    for item in items:
        if hasattr(item, '__table__'):
            serialized_items.append(_orm_to_dict(item))
        else:
            serialized_items.append(item)
    return PaginatedResponse(
        items=serialized_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# ============================================================
# 1. 订单管理 /api/orders
# ============================================================
@router_orders.get("/")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = "asc",
    search: Optional[str] = None,
    status: Optional[str] = None,
    contract_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    is_requested: Optional[bool] = None,
    is_collected: Optional[bool] = None,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取订单列表（分页、搜索、筛选）"""
    filters = {}
    if status:
        filters["status"] = status
    if contract_id is not None:
        filters["contract_id"] = contract_id
    if customer_id is not None:
        filters["customer_id"] = customer_id
    if is_requested is not None:
        filters["is_requested"] = is_requested
    if is_collected is not None:
        filters["is_collected"] = is_collected

    skip = (page - 1) * page_size
    items, total = order_crud.get_multi(
        db,
        skip=skip,
        limit=page_size,
        sort_field=sort_field,
        sort_order=sort_order,
        filters=filters,
        search=search,
        search_fields=["order_no", "project_name", "customer_name", "contract_no"],
    )
    return _build_paginated_response(items, total, page, page_size)


@router_orders.post("/")
async def create_order(
    obj_in: OrderCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """创建订单，自动更新合同的财务汇总字段"""
    order = order_crud.create(db, obj_in=obj_in)
    # 自动更新合同的财务汇总
    if order.contract_id:
        _recalc_contract_financials(db, order.contract_id)
    sync_all(db)
    return _orm_to_dict(order)


@router_orders.get("/{order_id}")
async def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取单个订单"""
    order = order_crud.get(db, id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return _orm_to_dict(order)


@router_orders.put("/{order_id}")
async def update_order(
    order_id: int,
    obj_in: OrderUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """更新订单，自动更新合同的财务汇总字段"""
    order = order_crud.update(db, id=order_id, obj_in=obj_in)
    if order.contract_id:
        _recalc_contract_financials(db, order.contract_id)
    sync_all(db)
    return _orm_to_dict(order)


@router_orders.delete("/{order_id}")
async def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """删除订单"""
    order = order_crud.get(db, id=order_id)
    contract_id = order.contract_id if order else None
    order_crud.delete(db, id=order_id)
    if contract_id:
        _recalc_contract_financials(db, contract_id)
    sync_all(db)
    return {"message": "删除成功"}


@router_orders.post("/batch")
async def batch_orders(
    action: BatchAction,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """订单批量操作（删除/修改状态）"""
    if action.action == "delete":
        count = order_crud.batch_delete(db, ids=action.ids)
        return {"deleted": count}
    elif action.action == "status":
        count = order_crud.batch_update_status(
            db, ids=action.ids, status_field="status", value=action.value or ""
        )
        return {"updated": count}
    raise HTTPException(status_code=400, detail=f"不支持的操作: {action.action}")


@router_orders.post("/batch-delete")
async def batch_delete_orders(
    data: BatchAction,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """批量删除订单"""
    count = order_crud.batch_delete(db, ids=data.ids)
    return {"deleted": count}


@router_orders.post("/batch-status")
async def batch_status_orders(
    ids: List[int],
    value: str,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """批量修改订单状态"""
    count = order_crud.batch_update_status(
        db, ids=ids, status_field="status", value=value
    )
    return {"updated": count}


@router_orders.post("/export")
async def export_orders(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """导出订单 CSV"""
    csv_data = order_crud.export_csv(db)
    return {"csv": csv_data}


@router_orders.post("/import")
async def import_orders(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """从 Excel 导入订单"""
    result = order_crud.import_excel(db, file=file)
    return result


@router_orders.post("/batch-request")
async def batch_request_orders(
    data: BatchRequestInput,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """批量请款：创建请款汇总和明细"""
    # 创建请款汇总
    orders = db.query(Order).filter(Order.id.in_(data.order_ids)).all()
    if not orders:
        raise HTTPException(status_code=400, detail="未找到有效订单")
    contract = db.query(Contract).filter(Contract.id == data.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    summary = RequestPaymentSummary(
        batch_no=data.batch_no,
        request_date=data.request_date,
        contract_id=data.contract_id,
        contract_no=contract.contract_no,
        project_name=getattr(contract, "project_name", None),
        customer_name=contract.customer_name,
        customer_id=contract.customer_id,
        request_amount=sum(o.biz_total_amount or Decimal(0) for o in orders),
        status="待请款",
    )
    db.add(summary)
    db.flush()

    # 为每个订单创建请款明细
    for order in orders:
        detail = RequestPaymentDetail(
            summary_id=summary.id,
            order_id=order.id,
            order_no=order.order_no,
            request_date=data.request_date,
            contract_id=data.contract_id,
            contract_no=contract.contract_no,
            project_name=order.project_name or contract.project_name,
            customer_name=order.customer_name or contract.customer_name,
            customer_id=order.customer_id or contract.customer_id,
            request_amount=order.biz_total_amount or Decimal(0),
            status="待请款",
        )
        db.add(detail)
        order.is_requested = True

    db.commit()
    db.refresh(summary)
    _recalc_contract_financials(db, data.contract_id)
    sync_all(db)
    return _orm_to_dict(summary)


@router_orders.post("/batch-collect")
async def batch_collect_orders(
    data: BatchCollectInput,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """批量收款：创建收款汇总和明细"""
    orders = db.query(Order).filter(Order.id.in_(data.order_ids)).all()
    if not orders:
        raise HTTPException(status_code=400, detail="未找到有效订单")
    contract = db.query(Contract).filter(Contract.id == data.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    # 创建收款汇总
    summary = CollectionSummary(
        batch_no=data.batch_no,
        collection_date=data.collection_date,
        contract_id=data.contract_id,
        contract_no=contract.contract_no,
        project_name=getattr(contract, "project_name", None),
        customer_name=contract.customer_name,
        customer_id=contract.customer_id,
        collection_amount=data.collection_amount,
        actual_amount=data.actual_amount,
        status=data.status,
    )
    db.add(summary)
    db.flush()

    # 为每个订单创建收款明细
    for order in orders:
        detail = CollectionDetail(
            summary_id=summary.id,
            order_id=order.id,
            order_no=order.order_no,
            collection_date=data.collection_date,
            contract_id=data.contract_id,
            contract_no=contract.contract_no,
            project_name=order.project_name or contract.project_name,
            customer_name=order.customer_name or contract.customer_name,
            customer_id=order.customer_id or contract.customer_id,
            collection_amount=order.biz_total_amount or Decimal(0),
            actual_amount=data.actual_amount / len(orders) if orders else Decimal(0),
            status=data.status,
        )
        db.add(detail)
        order.is_collected = True

    db.commit()
    db.refresh(summary)
    _recalc_contract_financials(db, data.contract_id)
    sync_all(db)
    return _orm_to_dict(summary)


# ---- 订单关联子路由：请款/收款 ----


@router_orders.get("/{order_id}/request-payments")
async def list_order_request_payments(
    order_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """查看指定订单的所有请款明细"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    details = (
        db.query(RequestPaymentDetail)
        .filter(RequestPaymentDetail.order_id == order_id)
        .order_by(RequestPaymentDetail.id.desc())
        .all()
    )
    return [_orm_to_dict(d) for d in details]


@router_orders.get("/{order_id}/collections")
async def list_order_collections(
    order_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """查看指定订单的所有收款明细"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    details = (
        db.query(CollectionDetail)
        .filter(CollectionDetail.order_id == order_id)
        .order_by(CollectionDetail.id.desc())
        .all()
    )
    return [_orm_to_dict(d) for d in details]


# ============================================================
# 2. 请款管理 /api/request-payments
# ============================================================
@router_request_payments.get("/")
async def list_request_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = "asc",
    search: Optional[str] = None,
    status: Optional[str] = None,
    contract_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取请款汇总列表"""
    filters = {}
    if status:
        filters["status"] = status
    if contract_id is not None:
        filters["contract_id"] = contract_id
    if customer_id is not None:
        filters["customer_id"] = customer_id

    skip = (page - 1) * page_size
    items, total = request_summary_crud.get_multi(
        db,
        skip=skip,
        limit=page_size,
        sort_field=sort_field,
        sort_order=sort_order,
        filters=filters,
        search=search,
        search_fields=["batch_no", "contract_no", "project_name", "customer_name"],
    )
    return _build_paginated_response(items, total, page, page_size)


@router_request_payments.post("/")
async def create_request_payment(
    obj_in: RequestSummaryCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """创建请款汇总，自动标记相关订单为已请款"""
    # 创建汇总
    summary = request_summary_crud.create(db, obj_in=obj_in)

    # 创建明细：如果传入了 detail_order_ids
    if obj_in.detail_order_ids:
        orders = db.query(Order).filter(Order.id.in_(obj_in.detail_order_ids)).all()
        for order in orders:
            detail = RequestPaymentDetail(
                summary_id=summary.id,
                order_id=order.id,
                order_no=order.order_no,
                request_date=obj_in.request_date,
                contract_id=summary.contract_id,
                contract_no=summary.contract_no,
                project_name=order.project_name or summary.project_name,
                customer_name=order.customer_name or summary.customer_name,
                customer_id=order.customer_id or summary.customer_id,
                request_amount=order.biz_total_amount or Decimal(0),
                status=summary.status,
            )
            db.add(detail)
            # 标记订单为已请款
            order.is_requested = True
        db.commit()

    # 更新合同财务汇总
    if summary.contract_id:
        _recalc_contract_financials(db, summary.contract_id)
    sync_all(db)

    db.refresh(summary)
    return _orm_to_dict(summary)


@router_request_payments.get("/{summary_id}")
async def get_request_payment(
    summary_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取单个请款汇总"""
    summary = request_summary_crud.get(db, id=summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="请款记录不存在")
    return _orm_to_dict(summary)


@router_request_payments.put("/{summary_id}")
async def update_request_payment(
    summary_id: int,
    obj_in: RequestSummaryCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """更新请款汇总"""
    summary = request_summary_crud.update(db, id=summary_id, obj_in=obj_in)
    if summary.contract_id:
        _recalc_contract_financials(db, summary.contract_id)
    sync_all(db)
    return _orm_to_dict(summary)


@router_request_payments.delete("/{summary_id}")
async def delete_request_payment(
    summary_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """删除请款汇总"""
    summary = request_summary_crud.get(db, id=summary_id)
    contract_id = summary.contract_id if summary else None
    request_summary_crud.delete(db, id=summary_id)
    if contract_id:
        _recalc_contract_financials(db, contract_id)
    sync_all(db)
    return {"message": "删除成功"}


@router_request_payments.post("/batch-delete")
async def batch_delete_request_payments(
    data: BatchAction,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """批量删除请款汇总"""
    from app.models import RequestPaymentSummary
    count = db.query(RequestPaymentSummary).filter(RequestPaymentSummary.id.in_(data.ids)).delete()
    db.commit()
    sync_all(db)
    return {"deleted": count}


@router_request_payments.post("/batch-status")
async def batch_status_request_payments(
    ids: List[int],
    value: str,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """批量修改请款状态"""
    from app.models import RequestPaymentSummary
    count = db.query(RequestPaymentSummary).filter(RequestPaymentSummary.id.in_(ids)).update(
        {"status": value}, synchronize_session=False
    )
    db.commit()
    sync_all(db)
    return {"updated": count}


@router_request_payments.get("/{summary_id}/details")
async def get_request_payment_details(
    summary_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取请款明细（嵌套）"""
    details = (
        db.query(RequestPaymentDetail)
        .filter(RequestPaymentDetail.summary_id == summary_id)
        .all()
    )
    return [_orm_to_dict(d) for d in details]


# ============================================================
# 3. 收款管理 /api/collections
# ============================================================
@router_collections.get("/")
async def list_collections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = "asc",
    search: Optional[str] = None,
    status: Optional[str] = None,
    contract_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取收款汇总列表"""
    filters = {}
    if status:
        filters["status"] = status
    if contract_id is not None:
        filters["contract_id"] = contract_id
    if customer_id is not None:
        filters["customer_id"] = customer_id

    skip = (page - 1) * page_size
    items, total = collection_summary_crud.get_multi(
        db,
        skip=skip,
        limit=page_size,
        sort_field=sort_field,
        sort_order=sort_order,
        filters=filters,
        search=search,
        search_fields=["batch_no", "contract_no", "project_name", "customer_name"],
    )
    return _build_paginated_response(items, total, page, page_size)


@router_collections.post("/")
async def create_collection(
    obj_in: CollectionSummaryCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """创建收款汇总，自动标记相关订单为已收款"""
    # 创建汇总
    summary = collection_summary_crud.create(db, obj_in=obj_in)

    # 创建明细
    if obj_in.detail_order_ids:
        orders = db.query(Order).filter(Order.id.in_(obj_in.detail_order_ids)).all()
        for order in orders:
            detail = CollectionDetail(
                summary_id=summary.id,
                order_id=order.id,
                order_no=order.order_no,
                collection_date=obj_in.collection_date,
                contract_id=summary.contract_id,
                contract_no=summary.contract_no,
                project_name=order.project_name or summary.project_name,
                customer_name=order.customer_name or summary.customer_name,
                customer_id=order.customer_id or summary.customer_id,
                collection_amount=order.biz_total_amount or Decimal(0),
                actual_amount=summary.actual_amount,
                status=summary.status,
            )
            db.add(detail)
            # 标记订单为已收款
            order.is_collected = True
        db.commit()

    # 更新合同财务汇总
    if summary.contract_id:
        _recalc_contract_financials(db, summary.contract_id)
    sync_all(db)

    db.refresh(summary)
    return _orm_to_dict(summary)


@router_collections.get("/{summary_id}")
async def get_collection(
    summary_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取单个收款汇总"""
    summary = collection_summary_crud.get(db, id=summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="收款记录不存在")
    return _orm_to_dict(summary)


@router_collections.put("/{summary_id}")
async def update_collection(
    summary_id: int,
    obj_in: CollectionSummaryCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """更新收款汇总"""
    summary = collection_summary_crud.update(db, id=summary_id, obj_in=obj_in)
    if summary.contract_id:
        _recalc_contract_financials(db, summary.contract_id)
    sync_all(db)
    return _orm_to_dict(summary)


@router_collections.delete("/{summary_id}")
async def delete_collection(
    summary_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """删除收款汇总"""
    summary = collection_summary_crud.get(db, id=summary_id)
    contract_id = summary.contract_id if summary else None
    collection_summary_crud.delete(db, id=summary_id)
    if contract_id:
        _recalc_contract_financials(db, contract_id)
    sync_all(db)
    return {"message": "删除成功"}


@router_collections.post("/batch-delete")
async def batch_delete_collections(
    data: BatchAction,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """批量删除收款汇总"""
    count = collection_summary_crud.batch_delete(db, ids=data.ids)
    sync_all(db)
    return {"deleted": count}


@router_collections.get("/{summary_id}/details")
async def get_collection_details(
    summary_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取收款明细（嵌套）"""
    details = (
        db.query(CollectionDetail)
        .filter(CollectionDetail.summary_id == summary_id)
        .all()
    )
    return [_orm_to_dict(d) for d in details]


# ============================================================
# 4. 财务管理 /api/finances
# ============================================================
@router_finances.get("/")
async def list_finances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = None,
    sort_order: str = "asc",
    search: Optional[str] = None,
    income_expense_type: Optional[str] = Query(None, pattern="^(收入|支出)$"),
    category: Optional[str] = None,
    contract_id: Optional[int] = None,
    status: Optional[str] = Query(None, description="入账状态(未入账/已入账)"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取财务列表（支持收支类别筛选）"""
    filters: Dict[str, Any] = {}
    if income_expense_type:
        filters["income_expense_type"] = income_expense_type
    if category:
        filters["category"] = category
    if contract_id is not None:
        filters["contract_id"] = contract_id
    if status is not None:
        filters["status"] = status

    skip = (page - 1) * page_size
    items, total = finance_crud.get_multi(
        db,
        skip=skip,
        limit=page_size,
        sort_field=sort_field,
        sort_order=sort_order,
        filters=filters,
        search=search,
        search_fields=["finance_no", "description", "contract_no", "company_name", "invoice_no"],
    )
    return _build_paginated_response(items, total, page, page_size)


@router_finances.post("/")
async def create_finance(
    obj_in: FinanceCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """创建财务记录"""
    finance = finance_crud.create(db, obj_in=obj_in)
    sync_all(db)
    return _orm_to_dict(finance)


@router_finances.get("/{finance_id}")
async def get_finance(
    finance_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取单个财务记录"""
    finance = finance_crud.get(db, id=finance_id)
    if not finance:
        raise HTTPException(status_code=404, detail="财务记录不存在")
    return _orm_to_dict(finance)


@router_finances.put("/{finance_id}")
async def update_finance(
    finance_id: int,
    obj_in: FinanceUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """更新财务记录"""
    finance = finance_crud.update(db, id=finance_id, obj_in=obj_in)
    sync_all(db)
    return _orm_to_dict(finance)


@router_finances.delete("/{finance_id}")
async def delete_finance(
    finance_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """删除财务记录"""
    finance_crud.delete(db, id=finance_id)
    sync_all(db)
    return {"message": "删除成功"}


@router_finances.post("/batch")
async def batch_finances(
    action: BatchAction,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """财务批量操作（删除/修改状态）"""
    if action.action == "delete":
        count = finance_crud.batch_delete(db, ids=action.ids)
        sync_all(db)
        return {"deleted": count}
    elif action.action == "status":
        count = finance_crud.batch_update_status(
            db, ids=action.ids, status_field=action.value or "status", value=action.value or ""
        )
        sync_all(db)
        return {"updated": count}
    raise HTTPException(status_code=400, detail=f"不支持的操作: {action.action}")


@router_finances.post("/batch-delete")
async def batch_delete_finances(
    data: BatchAction,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """批量删除财务记录"""
    count = finance_crud.batch_delete(db, ids=data.ids)
    sync_all(db)
    return {"deleted": count}


@router_finances.post("/batch-status")
async def batch_status_finances(
    ids: List[int],
    value: str,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """批量修改财务状态"""
    count = finance_crud.batch_update_status(
        db, ids=ids, status_field="status", value=value
    )
    sync_all(db)
    return {"updated": count}


@router_finances.post("/batch-post")
async def batch_post_finances(
    ids: List[int],
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """批量标记财务记录为已入账 (status="已入账")"""
    count = (
        db.query(Finance)
        .filter(Finance.id.in_(ids))
        .update({"status": "已入账"}, synchronize_session=False)
    )
    db.commit()
    sync_all(db)
    return {"updated": count}


# ============================================================
# 追加端点 - 拖拽排序
# ============================================================

@router_orders.post("/reorder")
async def reorder_orders(
    data: BatchAction,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """订单拖拽排序"""
    for i, item_id in enumerate(data.ids):
        db.query(Order).filter(Order.id == item_id).update({"sort_order": i})
    db.commit()
    return {"message": "排序更新成功", "data": {"updated": len(data.ids)}}


@router_request_payments.post("/reorder")
async def reorder_request_payments(
    data: BatchAction,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """请款拖拽排序"""
    for i, item_id in enumerate(data.ids):
        db.query(RequestPaymentSummary).filter(RequestPaymentSummary.id == item_id).update({"sort_order": i})
    db.commit()
    return {"message": "排序更新成功", "data": {"updated": len(data.ids)}}


@router_collections.post("/reorder")
async def reorder_collections(
    data: BatchAction,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """收款拖拽排序"""
    for i, item_id in enumerate(data.ids):
        db.query(CollectionSummary).filter(CollectionSummary.id == item_id).update({"sort_order": i})
    db.commit()
    return {"message": "排序更新成功", "data": {"updated": len(data.ids)}}


@router_finances.get("/{finance_id}/contract", response_model=Dict[str, Any])
async def get_finance_contract(
    finance_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取财务记录关联的合同（返回分页格式）"""
    finance = finance_crud.get(db, id=finance_id)
    if not finance:
        raise HTTPException(status_code=404, detail="财务记录不存在")
    if not finance.contract_id:
        return _build_paginated_response([], 0, page, page_size)
    from app.models import Contract
    contract = db.query(Contract).filter(Contract.id == finance.contract_id).first()
    items = [contract] if contract else []
    return _build_paginated_response(items, 1 if contract else 0, page, page_size)


@router_finances.get("/{finance_id}/orders", response_model=Dict[str, Any])
async def list_finance_orders(
    finance_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_field: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """获取财务记录关联合同的订单列表"""
    finance = finance_crud.get(db, id=finance_id)
    if not finance:
        raise HTTPException(status_code=404, detail="财务记录不存在")
    if not finance.contract_id:
        return _build_paginated_response([], 0, page, page_size)
    from app.models import Order
    query = db.query(Order).filter(Order.contract_id == finance.contract_id)
    total = query.count()
    if sort_field and hasattr(Order, sort_field):
        col = getattr(Order, sort_field)
        order_fn = sa_desc if sort_order == "desc" else sa_asc
        query = query.order_by(order_fn(col))
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return _build_paginated_response(items, total, page, page_size)


@router_finances.post("/reorder")
async def reorder_finances(
    data: BatchAction,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """财务拖拽排序"""
    for i, item_id in enumerate(data.ids):
        db.query(Finance).filter(Finance.id == item_id).update({"sort_order": i})
    db.commit()
    return {"message": "排序更新成功", "data": {"updated": len(data.ids)}}