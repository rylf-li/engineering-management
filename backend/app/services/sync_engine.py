"""
同步引擎 - syncDerivedData 后端实现

按 app.js 的 syncDerivedData 逻辑，在每次 create/update/delete 后自动同步：
1. 合同统计回写（订单数、应收/请款/收款/劳务费/绩效/利润）
2. 营收统计（调用现有 revenue_stats.py）
3. 员工绩效自动计算
4. 工资自动生成（含绩效联动）
5. 请款/收款汇总状态自动流转
6. 订单/合同状态自动流转
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Contract,
    Order,
    RequestPaymentSummary,
    RequestPaymentDetail,
    CollectionSummary,
    CollectionDetail,
    Finance,
    Employee,
    EmployeePerformance,
    EmployeeSalary,
    Company,
    Department,
    Customer,
    Project,
    CompanyBankAccount,
)
from app.services.revenue_stats import calculate_all_revenues

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FINISHED = "已完成"
CANCELLED = "已取消"
TERMINATED = "终止"
EXPENSE = "支出"
DEFAULT_TAX_RATE = Decimal("0.06")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sum(rows: list, field: str) -> Decimal:
    """Sum a numeric field across a list of ORM objects."""
    total = Decimal("0")
    for r in rows:
        val = getattr(r, field, None)
        if val is not None:
            total += Decimal(str(val))
    return total


def _round2(val) -> Decimal:
    """Round to 2 decimal places."""
    return Decimal(str(val)).quantize(Decimal("0.01"))


def _get_company_tax_rate(db: Session, company_id: Optional[int]) -> Decimal:
    if company_id:
        company = db.query(Company).filter(Company.id == company_id).first()
        if company and company.tax_rate is not None:
            return company.tax_rate
    return DEFAULT_TAX_RATE


def _current_month() -> str:
    """Return current month string like '2026-06'."""
    return date.today().strftime("%Y-%m")


# ===================================================================
# 1. 合同统计回写 (syncContractStats)
# ===================================================================

def sync_contract_stats(db: Session):
    """
    遍历所有合同，重新计算：
    - orders_unfinished / orders_finished
    - receivable_amount / request_amount / collection_amount / unrequested_amount
    - labor_cost / cost_amount / tax_fee / bonus / profit
    - 自动流转状态：全部收款 → 已完成
    """
    contracts = db.query(Contract).all()
    for contract in contracts:
        orders = db.query(Order).filter(Order.contract_id == contract.id).all()
        request_details = (
            db.query(RequestPaymentDetail)
            .filter(RequestPaymentDetail.contract_id == contract.id)
            .all()
        )
        collection_details = (
            db.query(CollectionDetail)
            .filter(CollectionDetail.contract_id == contract.id)
            .all()
        )
        finances = (
            db.query(Finance)
            .filter(Finance.contract_id == contract.id)
            .all()
        )

        # 订单统计
        contract.orders_unfinished = sum(
            1 for o in orders if o.status != FINISHED
        )
        contract.orders_finished = sum(
            1 for o in orders if o.status == FINISHED
        )

        # 应收 = 所有订单合计
        receivable = _sum(orders, "biz_total_amount")
        # 请款 = 请款明细合计
        request_amount = _sum(request_details, "request_amount")
        # 收款 = 收款明细实收合计
        collection_amount = _sum(collection_details, "actual_amount")
        # 劳务费 = 订单结算费合计
        labor_cost = _sum(orders, "settlement_fee")
        # 绩效 = 订单绩效费合计
        bonus = _sum(orders, "performance_fee")
        # 支出 = 财务支出合计
        expense = _sum(
            [f for f in finances if f.income_expense_type == EXPENSE], "amount"
        )

        # 税费 = 应收 * 公司税率
        tax_rate = _get_company_tax_rate(db, contract.company_id)
        tax_fee = _round2(receivable * tax_rate)

        contract.receivable_amount = _round2(receivable)
        contract.request_amount = _round2(request_amount)
        contract.collection_amount = _round2(collection_amount)
        contract.unrequested_amount = _round2(
            max(receivable - request_amount, Decimal("0"))
        )
        contract.labor_cost = _round2(labor_cost)
        contract.cost_amount = _round2(expense)
        contract.tax_fee = tax_fee
        contract.bonus = _round2(bonus)

        # 利润 = 收款 - 劳务费 - 支出 - 税费 - 其他 - 业务费 - 绩效
        other_fee = contract.other_fee or Decimal("0")
        business_fee = contract.business_fee or Decimal("0")
        contract.profit = _round2(
            collection_amount - labor_cost - expense - tax_fee
            - other_fee - business_fee - bonus
        )

        # 状态自动流转：全部收款 → 已完成
        if (
            orders
            and contract.collection_amount >= contract.receivable_amount
            and contract.status != TERMINATED
        ):
            contract.status = FINISHED

    db.commit()


# ===================================================================
# 2. 营收统计 (syncRevenueStats) — 调用现有模块
# ===================================================================

def sync_revenue_stats(db: Session):
    """调用现有 revenue_stats.py 的 calculate_all_revenues。"""
    today = date.today()
    calculate_all_revenues(db, today)


# ===================================================================
# 3. 员工绩效自动计算 (syncPerformanceStats)
# ===================================================================

def sync_performance_stats(db: Session):
    """
    遍历所有员工，按日期聚合：
    - 关联订单的应收/请款/收款
    - 关联合同的未完成/已完成数
    - 关联财务支出
    - 绩效金额 = 订单绩效费合计
    """
    today = date.today()

    # 收集所有有数据的日期
    dates = set()
    dates.add(today)
    for row in db.query(Order.order_date).distinct():
        if row[0]:
            dates.add(row[0])
    for row in db.query(Contract.contract_date).distinct():
        if row[0]:
            dates.add(row[0])

    employees = db.query(Employee).all()
    for emp in employees:
        emp_name = emp.name or ""
        for d in sorted(dates):
            # 员工关联的订单（负责人或业务员，按名称匹配）
            related_orders = (
                db.query(Order)
                .filter(
                    Order.order_date == d,
                    (Order.owner_name == emp_name) | (Order.sales_name == emp_name),
                )
                .all()
            )
            # 员工关联的合同
            related_contracts = (
                db.query(Contract)
                .filter(
                    Contract.contract_date == d,
                    (Contract.owner_name == emp_name) | (Contract.sales_name == emp_name),
                )
                .all()
            )
            # 员工所有订单ID
            all_order_ids = [
                row[0]
                for row in db.query(Order.id)
                .filter(
                    (Order.owner_name == emp_name) | (Order.sales_name == emp_name)
                )
                .all()
            ]

            if not all_order_ids:
                continue

            # 请款明细
            request_rows = (
                db.query(RequestPaymentDetail)
                .filter(
                    RequestPaymentDetail.request_date == d,
                    RequestPaymentDetail.order_id.in_(all_order_ids),
                )
                .all()
            )
            # 收款明细
            collection_rows = (
                db.query(CollectionDetail)
                .filter(
                    CollectionDetail.collection_date == d,
                    CollectionDetail.order_id.in_(all_order_ids),
                )
                .all()
            )
            # 关联合同编号
            contract_nos = [
                c.contract_no
                for c in db.query(Contract)
                .filter(
                    (Contract.owner_name == emp_name) | (Contract.sales_name == emp_name)
                )
                .all()
            ]
            # 财务支出
            expense_rows = (
                db.query(Finance)
                .filter(
                    Finance.finance_date == d,
                    Finance.income_expense_type == EXPENSE,
                    Finance.contract_no.in_(contract_nos) if contract_nos else False,
                )
                .all()
            ) if contract_nos else []

            receivable = _sum(related_orders, "biz_total_amount")
            request_amt = _sum(request_rows, "request_amount")
            collection_amt = _sum(collection_rows, "actual_amount")
            expense = _sum(expense_rows, "amount")
            perf_amount = _sum(related_orders, "performance_fee")

            if (
                not related_orders
                and not related_contracts
                and not request_rows
                and not collection_rows
                and not expense_rows
            ):
                continue

            # Upsert
            record = (
                db.query(EmployeePerformance)
                .filter(
                    EmployeePerformance.employee_id == emp.id,
                    EmployeePerformance.perf_date == d,
                )
                .first()
            )

            data = dict(
                employee_id=emp.id,
                perf_date=d,
                perf_amount=_round2(perf_amount),
                orders_unfinished=sum(
                    1 for o in related_orders if o.status != FINISHED
                ),
                orders_finished=sum(
                    1 for o in related_orders if o.status == FINISHED
                ),
                contracts_unfinished=sum(
                    1 for c in related_contracts if c.status != FINISHED
                ),
                contracts_finished=sum(
                    1 for c in related_contracts if c.status == FINISHED
                ),
                receivable_amount=_round2(receivable),
                request_amount=_round2(request_amt),
                collection_amount=_round2(collection_amt),
                unrequested_amount=_round2(
                    max(receivable - request_amt, Decimal("0"))
                ),
                expenditure=_round2(expense),
                profit=_round2(collection_amt - expense - perf_amount),
            )

            if record:
                for k, v in data.items():
                    setattr(record, k, v)
            else:
                record = EmployeePerformance(**data)
                db.add(record)

    db.commit()


# ===================================================================
# 4. 工资自动生成 (syncSalaryStats)
# ===================================================================

def sync_salary_stats(db: Session):
    """
    遍历所有员工，为当前月自动生成/更新工资：
    - 绩效 = 当月绩效金额合计
    - 实发 = 月薪 + 报销 + 加油费 + 绩效 - 扣款 - 社保
    - 如果当月无工资记录则自动创建
    """
    month = _current_month()
    employees = db.query(Employee).all()

    for emp in employees:
        # 当月绩效合计（SQLite 用 strftime）
        month_perf = (
            db.query(func.coalesce(func.sum(EmployeePerformance.perf_amount), 0))
            .filter(
                EmployeePerformance.employee_id == emp.id,
                func.strftime("%Y-%m", EmployeePerformance.perf_date) == month,
            )
            .scalar()
        ) or Decimal("0")

        # 查找当月工资
        salary = (
            db.query(EmployeeSalary)
            .filter(
                EmployeeSalary.employee_id == emp.id,
                EmployeeSalary.salary_month == month,
            )
            .first()
        )

        if not salary:
            salary = EmployeeSalary(
                employee_id=emp.id,
                salary_month=month,
                monthly_salary=emp.monthly_salary or Decimal("0"),
                reimbursement=Decimal("0"),
                deduction=Decimal("0"),
                fuel_fee=Decimal("0"),
                social_insurance=emp.social_insurance or Decimal("0"),
                bonus=_round2(month_perf),
                actual_salary=Decimal("0"),
            )
            db.add(salary)

        # 更新绩效
        salary.bonus = _round2(month_perf)
        # 计算实发
        monthly = salary.monthly_salary or Decimal("0")
        reimbursement = salary.reimbursement or Decimal("0")
        deduction = salary.deduction or Decimal("0")
        fuel = salary.fuel_fee or Decimal("0")
        social = salary.social_insurance or Decimal("0")
        bonus = salary.bonus or Decimal("0")

        salary.actual_salary = _round2(
            monthly + reimbursement + fuel + bonus - deduction - social
        )

    db.commit()


# ===================================================================
# 5. 请款/收款汇总状态自动流转 (syncRequestAndReceiptSummaries)
# ===================================================================

def sync_request_receipt_summaries(db: Session):
    """
    遍历请款汇总和收款汇总，根据明细状态自动更新汇总状态：
    - 请款汇总：全部明细"已请款" → "已请款"，否则 "部分请款"
    - 收款汇总：全部明细"已收款" → "已收款"，否则 "部分收款"
    """
    # 请款汇总
    summaries = db.query(RequestPaymentSummary).all()
    for summary in summaries:
        details = (
            db.query(RequestPaymentDetail)
            .filter(RequestPaymentDetail.summary_id == summary.id)
            .all()
        )
        if not details:
            continue
        all_done = all(d.status == "已请款" for d in details)
        summary.status = "已请款" if all_done else "部分请款"

    # 收款汇总
    coll_summaries = db.query(CollectionSummary).all()
    for summary in coll_summaries:
        details = (
            db.query(CollectionDetail)
            .filter(CollectionDetail.summary_id == summary.id)
            .all()
        )
        if not details:
            continue
        all_done = all(d.status == "已收款" for d in details)
        summary.status = "已收款" if all_done else "部分收款"

    db.commit()


# ===================================================================
# 6. 订单状态自动流转 (syncOrderStatus)
# ===================================================================

def sync_order_status(db: Session):
    """
    遍历所有订单：
    - 如果全部收款且未取消 → 已完成
    - 更新 is_requested / is_collected 标记
    """
    orders = db.query(Order).all()
    for order in orders:
        if order.status == CANCELLED:
            continue

        # 计算请款/收款金额
        request_total = (
            db.query(func.coalesce(func.sum(RequestPaymentDetail.request_amount), 0))
            .filter(RequestPaymentDetail.order_id == order.id)
            .scalar()
        ) or Decimal("0")

        collection_total = (
            db.query(func.coalesce(func.sum(CollectionDetail.actual_amount), 0))
            .filter(CollectionDetail.order_id == order.id)
            .scalar()
        ) or Decimal("0")

        total = order.biz_total_amount or Decimal("0")

        order.is_requested = request_total >= total and total > 0
        order.is_collected = collection_total >= total and total > 0

        if order.is_collected and order.status != FINISHED:
            order.status = FINISHED

    db.commit()


# ===================================================================
# 7. 主入口 (syncAll)
# ===================================================================

def sync_all(db: Session):
    """
    完整同步引擎入口，按顺序执行所有同步步骤。
    匹配 app.js 的 syncDerivedData() 调用顺序。
    """
    sync_order_status(db)
    sync_request_receipt_summaries(db)
    sync_contract_stats(db)
    sync_revenue_stats(db)
    sync_performance_stats(db)
    sync_salary_stats(db)


# ===================================================================
# 8. Standalone Runner
# ===================================================================

def run_sync_all() -> dict:
    """
    独立运行函数，创建 DB session 并执行完整同步。
    适用于定时任务 / CLI 调用。
    """
    db = SessionLocal()
    try:
        sync_all(db)
        return {"status": "ok", "message": "同步完成"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
