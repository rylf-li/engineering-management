"""
报表管理 API
提供日报、季度、年度、项目合同统计报表
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, extract, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Finance, Contract, Order, Project,
    RequestPaymentDetail, CollectionDetail,
    DepartmentRevenue, CompanyRevenue,
    Department, Company,
)

router_reports = APIRouter(prefix="/api/reports", tags=["报表管理"])


def _period_filter(model, date_col, year: int, quarter: Optional[int] = None):
    """生成日期范围筛选条件"""
    if quarter:
        return and_(
            extract("year", date_col) == year,
            extract("quarter", date_col) == quarter,
        )
    return extract("year", date_col) == year


# ==============================
# 日报表
# ==============================

@router_reports.get("/daily/finance/")
async def daily_finance_report(
    report_date: date = Query(default_factory=date.today),
    income_expense_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """当日财务收支详情表"""
    query = db.query(Finance).filter(Finance.finance_date == report_date)
    if income_expense_type:
        query = query.filter(Finance.income_expense_type == income_expense_type)
    records = query.order_by(Finance.id).all()

    income_total = sum(r.amount for r in records if r.income_expense_type == "收入")
    expense_total = sum(r.amount for r in records if r.income_expense_type == "支出")

    return {
        "report_date": str(report_date),
        "records": [
            {
                "id": r.id,
                "finance_no": r.finance_no,
                "category": r.category,
                "description": r.description,
                "income_expense_type": r.income_expense_type,
                "amount": float(r.amount),
                "company_name": r.company_name,
                "status": r.status if r.status else "未入账",
                "invoice_no": r.invoice_no,
            }
            for r in records
        ],
        "summary": {
            "income_total": float(income_total),
            "expense_total": float(expense_total),
            "net": float(income_total - expense_total),
            "record_count": len(records),
        },
    }


@router_reports.get("/daily/company/")
async def daily_company_report(
    report_date: date = Query(default_factory=date.today),
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """当日公司收支统计表"""
    query = db.query(CompanyRevenue).filter(CompanyRevenue.rev_date == report_date)
    if company_id:
        query = query.filter(CompanyRevenue.company_id == company_id)
    records = query.all()

    return {
        "report_date": str(report_date),
        "records": [
            {
                "company_name": r.company_name,
                "department_name": r.department_name,
                "orders_unfinished": r.orders_unfinished,
                "orders_finished": r.orders_finished,
                "contracts_unfinished": r.contracts_unfinished,
                "contracts_finished": r.contracts_finished,
                "receivable_amount": float(r.receivable_amount),
                "request_amount": float(r.request_amount),
                "collection_amount": float(r.collection_amount),
                "unrequested_amount": float(r.unrequested_amount),
                "expenditure": float(r.expenditure),
                "profit": float(r.profit),
            }
            for r in records
        ],
        "summary": _summarize_revenue(records),
    }


@router_reports.get("/daily/department/")
async def daily_department_report(
    report_date: date = Query(default_factory=date.today),
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """当日部门收支统计表"""
    query = db.query(DepartmentRevenue).filter(DepartmentRevenue.rev_date == report_date)
    if department_id:
        query = query.filter(DepartmentRevenue.department_id == department_id)
    records = query.all()

    return {
        "report_date": str(report_date),
        "records": [
            {
                "department_name": r.department_name,
                "company_name": r.company_name,
                "orders_unfinished": r.orders_unfinished,
                "orders_finished": r.orders_finished,
                "contracts_unfinished": r.contracts_unfinished,
                "contracts_finished": r.contracts_finished,
                "receivable_amount": float(r.receivable_amount),
                "request_amount": float(r.request_amount),
                "collection_amount": float(r.collection_amount),
                "expenditure": float(r.expenditure),
                "profit": float(r.profit),
            }
            for r in records
        ],
        "summary": _summarize_revenue(records),
    }


# ==============================
# 季度报表
# ==============================
@router_reports.get("/quarterly/finance/")
async def quarterly_finance_report(
    year: int = Query(default_factory=lambda: date.today().year),
    quarter: int = Query(default=1, ge=1, le=4),
    income_expense_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """当季度财务收支详情表"""
    query = db.query(Finance).filter(
        _period_filter(Finance, Finance.finance_date, year, quarter)
    )
    if income_expense_type:
        query = query.filter(Finance.income_expense_type == income_expense_type)
    records = query.order_by(Finance.finance_date).all()

    income_total = sum(r.amount for r in records if r.income_expense_type == "收入")
    expense_total = sum(r.amount for r in records if r.income_expense_type == "支出")

    return {
        "year": year,
        "quarter": quarter,
        "records": [
            {
                "id": r.id,
                "finance_date": str(r.finance_date),
                "finance_no": r.finance_no,
                "category": r.category,
                "description": r.description,
                "income_expense_type": r.income_expense_type,
                "amount": float(r.amount),
                "company_name": r.company_name,
            }
            for r in records
        ],
        "summary": {
            "income_total": float(income_total),
            "expense_total": float(expense_total),
            "net": float(income_total - expense_total),
            "record_count": len(records),
        },
    }


@router_reports.get("/quarterly/company/")
async def quarterly_company_report(
    year: int = Query(default_factory=lambda: date.today().year),
    quarter: int = Query(default=1, ge=1, le=4),
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """当季度公司收支统计表"""
    query = db.query(CompanyRevenue).filter(
        _period_filter(CompanyRevenue, CompanyRevenue.rev_date, year, quarter)
    )
    if company_id:
        query = query.filter(CompanyRevenue.company_id == company_id)
    records = query.all()

    return {
        "year": year, "quarter": quarter,
        "records": _serialize_revenue_records(records),
        "summary": _summarize_revenue(records),
    }


@router_reports.get("/quarterly/department/")
async def quarterly_department_report(
    year: int = Query(default_factory=lambda: date.today().year),
    quarter: int = Query(default=1, ge=1, le=4),
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """当季度部门收支统计表"""
    query = db.query(DepartmentRevenue).filter(
        _period_filter(DepartmentRevenue, DepartmentRevenue.rev_date, year, quarter)
    )
    if department_id:
        query = query.filter(DepartmentRevenue.department_id == department_id)
    records = query.all()

    return {
        "year": year, "quarter": quarter,
        "records": _serialize_dept_revenue_records(records),
        "summary": _summarize_dept_revenue(records),
    }


# ==============================
# 年度报表
# ==============================
@router_reports.get("/yearly/finance/")
async def yearly_finance_report(
    year: int = Query(default_factory=lambda: date.today().year),
    income_expense_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """当年度财务收支详情表"""
    query = db.query(Finance).filter(
        extract("year", Finance.finance_date) == year
    )
    if income_expense_type:
        query = query.filter(Finance.income_expense_type == income_expense_type)
    records = query.order_by(Finance.finance_date.desc()).all()

    income_total = sum(r.amount for r in records if r.income_expense_type == "收入")
    expense_total = sum(r.amount for r in records if r.income_expense_type == "支出")

    # 按月分组统计
    monthly_stats = {}
    for r in records:
        month = r.finance_date.month
        if month not in monthly_stats:
            monthly_stats[month] = {"income": Decimal(0), "expense": Decimal(0)}
        if r.income_expense_type == "收入":
            monthly_stats[month]["income"] += r.amount
        else:
            monthly_stats[month]["expense"] += r.amount

    return {
        "year": year,
        "records": [
            {
                "id": r.id,
                "finance_date": str(r.finance_date),
                "finance_no": r.finance_no,
                "category": r.category,
                "description": r.description,
                "income_expense_type": r.income_expense_type,
                "amount": float(r.amount),
                "company_name": r.company_name,
            }
            for r in records
        ],
        "monthly_summary": [
            {
                "month": m,
                "income": float(stats["income"]),
                "expense": float(stats["expense"]),
                "net": float(stats["income"] - stats["expense"]),
            }
            for m, stats in sorted(monthly_stats.items())
        ],
        "summary": {
            "income_total": float(income_total),
            "expense_total": float(expense_total),
            "net": float(income_total - expense_total),
            "record_count": len(records),
        },
    }


@router_reports.get("/yearly/company/")
async def yearly_company_report(
    year: int = Query(default_factory=lambda: date.today().year),
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """当年度公司收支统计表"""
    query = db.query(CompanyRevenue).filter(
        extract("year", CompanyRevenue.rev_date) == year
    )
    if company_id:
        query = query.filter(CompanyRevenue.company_id == company_id)
    records = query.all()

    return {
        "year": year,
        "records": _serialize_revenue_records(records),
        "summary": _summarize_revenue(records),
    }


@router_reports.get("/yearly/department/")
async def yearly_department_report(
    year: int = Query(default_factory=lambda: date.today().year),
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """当年度部门收支统计表"""
    query = db.query(DepartmentRevenue).filter(
        extract("year", DepartmentRevenue.rev_date) == year
    )
    if department_id:
        query = query.filter(DepartmentRevenue.department_id == department_id)
    records = query.all()

    return {
        "year": year,
        "records": _serialize_dept_revenue_records(records),
        "summary": _summarize_dept_revenue(records),
    }


# ==============================
# 项目合同报表
# ==============================
@router_reports.get("/project-contract-stats/")
async def project_contract_report(
    year: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """项目合同统计报表"""
    query = db.query(Project)
    if year:
        query = query.filter(extract("year", Project.project_date) == year)
    projects = query.all()

    contract_query = db.query(Contract)
    if year:
        contract_query = contract_query.filter(extract("year", Contract.contract_date) == year)
    contracts = contract_query.all()

    # 项目统计
    project_completed = sum(1 for p in projects if p.status == "已完成")
    project_unfinished = len(projects) - project_completed

    # 合同/订单收款统计
    total_receivable = sum(c.receivable_amount for c in contracts)
    total_collected = sum(c.collection_amount for c in contracts)
    total_requested = sum(c.request_amount for c in contracts)

    contract_completed = sum(1 for c in contracts if c.status == "已完成")
    contract_unfinished = sum(1 for c in contracts if c.status == "执行中")
    contract_pending = sum(1 for c in contracts if c.status == "待签订")

    return {
        "year": year or date.today().year,
        "project_stats": {
            "total": len(projects),
            "completed": project_completed,
            "unfinished": project_unfinished,
            "completion_rate": round(project_completed / len(projects) * 100, 1) if projects else 0,
        },
        "contract_stats": {
            "total": len(contracts),
            "completed": contract_completed,
            "unfinished": contract_unfinished,
            "pending": contract_pending,
        },
        "finance_stats": {
            "receivable_amount": float(total_receivable),
            "requested_amount": float(total_requested),
            "collected_amount": float(total_collected),
            "pending_collection": float(total_receivable - total_collected),
            "unrequested_amount": float(total_receivable - total_requested),
        },
        "project_list": [
            {
                "id": p.id,
                "project_no": p.project_no,
                "name": p.name,
                "status": p.status,
                "date": str(p.project_date),
            }
            for p in projects
        ],
    }


@router_reports.get("/project/{project_id}/detail/")
async def project_detail_report(
    project_id: int,
    db: Session = Depends(get_db),
):
    """单个项目综合报表"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    contracts = db.query(Contract).filter(Contract.project_id == project_id).all()
    contract_ids = [c.id for c in contracts]

    orders = db.query(Order).filter(Order.contract_id.in_(contract_ids)).all() if contract_ids else []
    order_ids = [o.id for o in orders]

    finances = db.query(Finance).filter(Finance.contract_id.in_(contract_ids)).all() if contract_ids else []

    return {
        "project": {
            "id": project.id,
            "project_no": project.project_no,
            "name": project.name,
            "status": project.status,
            "date": str(project.project_date),
        },
        "contract_count": len(contracts),
        "order_count": len(orders),
        "finance_count": len(finances),
        "contracts": [
            {
                "id": c.id,
                "contract_no": c.contract_no,
                "name": c.name,
                "status": c.status,
                "receivable_amount": float(c.receivable_amount),
                "collection_amount": float(c.collection_amount),
            }
            for c in contracts
        ],
        "summary": {
            "receivable_amount": float(sum(c.receivable_amount for c in contracts)),
            "collection_amount": float(sum(c.collection_amount for c in contracts)),
            "expenditure": float(sum(f.amount for f in finances if f.income_expense_type == "支出")),
            "income": float(sum(f.amount for f in finances if f.income_expense_type == "收入")),
        },
    }


# ==============================
# 手动触发每日统计
# ==============================
@router_reports.get("/trigger-daily-stats/")
async def trigger_daily_stats(
    stats_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
):
    """手动触发每日统计数据生成"""
    from app.services.revenue_stats import calculate_all_revenues
    calculate_all_revenues(db, stats_date)
    return {"message": f"✅ {stats_date} 统计数据已生成"}


# ==============================
# 辅助函数
# ==============================
def _serialize_revenue_records(records):
    result = {}
    for r in records:
        key = r.company_name
        if key not in result:
            result[key] = {
                "company_name": r.company_name,
                "orders_unfinished": 0,
                "orders_finished": 0,
                "contracts_unfinished": 0,
                "contracts_finished": 0,
                "receivable_amount": 0,
                "request_amount": 0,
                "collection_amount": 0,
                "unrequested_amount": 0,
                "expenditure": 0,
                "profit": 0,
            }
        item = result[key]
        item["orders_unfinished"] += r.orders_unfinished
        item["orders_finished"] += r.orders_finished
        item["contracts_unfinished"] += r.contracts_unfinished
        item["contracts_finished"] += r.contracts_finished
        item["receivable_amount"] += float(r.receivable_amount)
        item["request_amount"] += float(r.request_amount)
        item["collection_amount"] += float(r.collection_amount)
        item["unrequested_amount"] += float(r.unrequested_amount)
        item["expenditure"] += float(r.expenditure)
        item["profit"] += float(r.profit)
    return list(result.values())


def _serialize_dept_revenue_records(records):
    result = {}
    for r in records:
        key = r.department_name
        if key not in result:
            result[key] = {
                "department_name": r.department_name,
                "company_name": r.company_name,
                "orders_unfinished": 0,
                "orders_finished": 0,
                "contracts_unfinished": 0,
                "contracts_finished": 0,
                "receivable_amount": 0,
                "request_amount": 0,
                "collection_amount": 0,
                "expenditure": 0,
                "profit": 0,
            }
        item = result[key]
        item["orders_unfinished"] += r.orders_unfinished
        item["orders_finished"] += r.orders_finished
        item["contracts_unfinished"] += r.contracts_unfinished
        item["contracts_finished"] += r.contracts_finished
        item["receivable_amount"] += float(r.receivable_amount)
        item["request_amount"] += float(r.request_amount)
        item["collection_amount"] += float(r.collection_amount)
        item["expenditure"] += float(r.expenditure)
        item["profit"] += float(r.profit)
    return list(result.values())


def _summarize_revenue(records):
    return {
        "orders_unfinished": sum(r.orders_unfinished for r in records),
        "orders_finished": sum(r.orders_finished for r in records),
        "contracts_unfinished": sum(r.contracts_unfinished for r in records),
        "contracts_finished": sum(r.contracts_finished for r in records),
        "receivable_amount": float(sum(r.receivable_amount for r in records)),
        "request_amount": float(sum(r.request_amount for r in records)),
        "collection_amount": float(sum(r.collection_amount for r in records)),
        "unrequested_amount": float(sum(r.unrequested_amount for r in records)),
        "expenditure": float(sum(r.expenditure for r in records)),
        "profit": float(sum(r.profit for r in records)),
    }


def _summarize_dept_revenue(records):
    return {
        "orders_unfinished": sum(r.orders_unfinished for r in records),
        "orders_finished": sum(r.orders_finished for r in records),
        "contracts_unfinished": sum(r.contracts_unfinished for r in records),
        "contracts_finished": sum(r.contracts_finished for r in records),
        "receivable_amount": float(sum(r.receivable_amount for r in records)),
        "request_amount": float(sum(r.request_amount for r in records)),
        "collection_amount": float(sum(r.collection_amount for r in records)),
        "expenditure": float(sum(r.expenditure for r in records)),
        "profit": float(sum(r.profit for r in records)),
    }