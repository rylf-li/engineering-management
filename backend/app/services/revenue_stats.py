"""
Revenue Statistics Service

Auto-calculates and updates daily revenue statistics for departments,
companies, customers, and projects based on contracts, orders,
request payments, collections, and finance records.

Each function aggregates data from related tables for a given entity
and date, then upserts the corresponding Revenue record.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Department,
    DepartmentRevenue,
    Company,
    CompanyRevenue,
    Customer,
    CustomerRevenue,
    Project,
    ProjectRevenue,
    Contract,
    Order,
    RequestPaymentDetail,
    CollectionDetail,
    Finance,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_TAX_RATE = Decimal("0.06")
FINISHED_STATUS = "已完成"
EXPENSE_TYPE = "支出"


def _get_company_tax_rate(db: Session, company_id: Optional[int]) -> Decimal:
    """Return the tax rate for a company, or the default 6%."""
    if company_id:
        company = db.query(Company).filter(Company.id == company_id).first()
        if company and company.tax_rate is not None:
            return company.tax_rate
    return DEFAULT_TAX_RATE


def _resolve_name(
    db: Session, model, model_id: Optional[int], name_field: str = "name"
) -> Optional[str]:
    """Safely resolve a model instance to its display name."""
    if model_id is None:
        return None
    instance = db.query(model).filter(model.id == model_id).first()
    return getattr(instance, name_field, None) if instance else None


# ---------------------------------------------------------------------------
# Shared aggregation helpers
# ---------------------------------------------------------------------------

def _count_contracts(contracts: list) -> tuple[int, int]:
    """Return (unfinished_count, finished_count) for a list of contracts."""
    unfinished = sum(1 for c in contracts if c.status != FINISHED_STATUS)
    finished = sum(1 for c in contracts if c.status == FINISHED_STATUS)
    return unfinished, finished


def _count_orders(orders: list) -> tuple[int, int]:
    """Return (unfinished_count, finished_count) for a list of orders."""
    unfinished = sum(1 for o in orders if o.status != FINISHED_STATUS)
    finished = sum(1 for o in orders if o.status == FINISHED_STATUS)
    return unfinished, finished


# ---------------------------------------------------------------------------
# 1. Department Revenue
# ---------------------------------------------------------------------------

def calculate_department_revenue(
    db: Session, department_id: int, rev_date: date
) -> DepartmentRevenue:
    """
    Aggregate contracts, orders, and finance for a department on *rev_date*,
    then upsert a :class:`DepartmentRevenue` record.
    """
    dept_name = _resolve_name(db, Department, department_id) or f"Dept#{department_id}"

    # ---- Contracts --------------------------------------------------------
    contracts = (
        db.query(Contract)
        .filter(Contract.department_id == department_id)
        .all()
    )
    contracts_unfinished, contracts_finished = _count_contracts(contracts)

    # First company reference for display (if any)
    first_company_id: Optional[int] = None
    first_company_name: Optional[str] = None
    if contracts:
        first_company_id = contracts[0].company_id
        first_company_name = contracts[0].company_name

    # ---- Orders -----------------------------------------------------------
    orders = (
        db.query(Order)
        .filter(Order.department_id == department_id)
        .all()
    )
    orders_unfinished, orders_finished = _count_orders(orders)

    # ---- Receivable -------------------------------------------------------
    receivable = (
        db.query(func.coalesce(func.sum(Order.biz_total_amount), 0))
        .filter(
            Order.department_id == department_id,
            Order.is_collected == False,
        )
        .scalar()
    ) or Decimal("0")

    # ---- Request amount ---------------------------------------------------
    request_amount = (
        db.query(func.coalesce(func.sum(RequestPaymentDetail.request_amount), 0))
        .join(Order, RequestPaymentDetail.order_id == Order.id)
        .filter(Order.department_id == department_id)
        .scalar()
    ) or Decimal("0")

    # ---- Collection amount ------------------------------------------------
    collection_amount = (
        db.query(func.coalesce(func.sum(CollectionDetail.collection_amount), 0))
        .join(Order, CollectionDetail.order_id == Order.id)
        .filter(Order.department_id == department_id)
        .scalar()
    ) or Decimal("0")

    # ---- Expenditure ------------------------------------------------------
    expenditure = (
        db.query(func.coalesce(func.sum(Finance.amount), 0))
        .filter(
            Finance.department_id == department_id,
            Finance.income_expense_type == EXPENSE_TYPE,
        )
        .scalar()
    ) or Decimal("0")

    # ---- Tax & Profit -----------------------------------------------------
    tax_rate = _get_company_tax_rate(db, first_company_id)
    tax_estimate = collection_amount * tax_rate
    profit = collection_amount - expenditure - tax_estimate

    # ---- Upsert -----------------------------------------------------------
    record = (
        db.query(DepartmentRevenue)
        .filter(
            DepartmentRevenue.department_id == department_id,
            DepartmentRevenue.rev_date == rev_date,
        )
        .first()
    )

    if record:
        record.company_name = first_company_name
        record.company_id = first_company_id
        record.department_name = dept_name
        record.orders_unfinished = orders_unfinished
        record.orders_finished = orders_finished
        record.contracts_unfinished = contracts_unfinished
        record.contracts_finished = contracts_finished
        record.receivable_amount = receivable
        record.request_amount = request_amount
        record.collection_amount = collection_amount
        record.expenditure = expenditure
        record.profit = profit
    else:
        record = DepartmentRevenue(
            company_name=first_company_name,
            company_id=first_company_id,
            department_name=dept_name,
            department_id=department_id,
            rev_date=rev_date,
            orders_unfinished=orders_unfinished,
            orders_finished=orders_finished,
            contracts_unfinished=contracts_unfinished,
            contracts_finished=contracts_finished,
            receivable_amount=receivable,
            request_amount=request_amount,
            collection_amount=collection_amount,
            expenditure=expenditure,
            profit=profit,
        )
        db.add(record)

    db.flush()
    return record


# ---------------------------------------------------------------------------
# 2. Company Revenue (with department breakdown)
# ---------------------------------------------------------------------------

def calculate_company_revenue(
    db: Session, company_id: int, rev_date: date
) -> list[CompanyRevenue]:
    """
    Aggregate contracts, orders, and finance for a company on *rev_date*,
    producing one :class:`CompanyRevenue` record per department.
    The department-less bucket (department_id=NULL) captures cross-dept data.
    """
    company_name = _resolve_name(db, Company, company_id) or f"Company#{company_id}"
    tax_rate = _get_company_tax_rate(db, company_id)

    # Collect all contracts and orders for this company
    all_contracts = (
        db.query(Contract)
        .filter(Contract.company_id == company_id)
        .all()
    )
    all_orders = (
        db.query(Order)
        .filter(Order.company_id == company_id)
        .all()
    )

    # Group by department
    dept_map: dict[Optional[int], dict] = {}
    for c in all_contracts:
        key = c.department_id
        dept_map.setdefault(key, {"contracts": [], "orders": []})["contracts"].append(c)
    for o in all_orders:
        key = o.department_id
        dept_map.setdefault(key, {"contracts": [], "orders": []})["orders"].append(o)

    # Also add an entry for None (global) if there are any contracts/orders
    if all_contracts or all_orders:
        dept_map.setdefault(None, {"contracts": [], "orders": []})

    records: list[CompanyRevenue] = []

    for dept_id, grouped in dept_map.items():
        dept_name = (
            _resolve_name(db, Department, dept_id) if dept_id else None
        )
        dept_contracts = grouped["contracts"]
        dept_orders = grouped["orders"]

        # If the key is None but we have contracts/orders, aggregate everything
        if dept_id is None:
            dept_contracts = all_contracts
            dept_orders = all_orders

        contracts_unfinished, contracts_finished = _count_contracts(dept_contracts)
        orders_unfinished, orders_finished = _count_orders(dept_orders)

        # ---- Receivable ---------------------------------------------------
        receivable_filters = [Order.company_id == company_id, Order.is_collected == False]
        if dept_id is not None:
            receivable_filters.append(Order.department_id == dept_id)
        receivable = (
            db.query(func.coalesce(func.sum(Order.biz_total_amount), 0))
            .filter(*receivable_filters)
            .scalar()
        ) or Decimal("0")

        # ---- Request amount -----------------------------------------------
        req_filters = [Order.company_id == company_id]
        if dept_id is not None:
            req_filters.append(Order.department_id == dept_id)
        request_amount = (
            db.query(func.coalesce(func.sum(RequestPaymentDetail.request_amount), 0))
            .join(Order, RequestPaymentDetail.order_id == Order.id)
            .filter(*req_filters)
            .scalar()
        ) or Decimal("0")

        # ---- Collection amount --------------------------------------------
        coll_filters = [Order.company_id == company_id]
        if dept_id is not None:
            coll_filters.append(Order.department_id == dept_id)
        collection_amount = (
            db.query(func.coalesce(func.sum(CollectionDetail.collection_amount), 0))
            .join(Order, CollectionDetail.order_id == Order.id)
            .filter(*coll_filters)
            .scalar()
        ) or Decimal("0")

        # ---- Expenditure --------------------------------------------------
        exp_filters = [Finance.company_id == company_id, Finance.income_expense_type == EXPENSE_TYPE]
        if dept_id is not None:
            exp_filters.append(Finance.department_id == dept_id)
        expenditure = (
            db.query(func.coalesce(func.sum(Finance.amount), 0))
            .filter(*exp_filters)
            .scalar()
        ) or Decimal("0")

        # ---- Profit -------------------------------------------------------
        tax_estimate = collection_amount * tax_rate
        profit = collection_amount - expenditure - tax_estimate
        unrequested = receivable - request_amount

        # ---- Upsert -------------------------------------------------------
        record = (
            db.query(CompanyRevenue)
            .filter(
                CompanyRevenue.company_id == company_id,
                CompanyRevenue.department_id == dept_id,
                CompanyRevenue.rev_date == rev_date,
            )
            .first()
        )

        data = dict(
            company_name=company_name,
            company_id=company_id,
            department_name=dept_name,
            department_id=dept_id,
            rev_date=rev_date,
            orders_unfinished=orders_unfinished,
            orders_finished=orders_finished,
            contracts_unfinished=contracts_unfinished,
            contracts_finished=contracts_finished,
            receivable_amount=receivable,
            request_amount=request_amount,
            collection_amount=collection_amount,
            unrequested_amount=unrequested,
            expenditure=expenditure,
            profit=profit,
        )

        if record:
            for k, v in data.items():
                setattr(record, k, v)
        else:
            record = CompanyRevenue(**data)
            db.add(record)

        db.flush()
        records.append(record)

    return records


# ---------------------------------------------------------------------------
# 3. Customer Revenue
# ---------------------------------------------------------------------------

def calculate_customer_revenue(
    db: Session, customer_id: int, rev_date: date
) -> CustomerRevenue:
    """
    Aggregate contracts, orders, and finance for a customer on *rev_date*,
    then upsert a :class:`CustomerRevenue` record.
    """
    customer_name = _resolve_name(db, Customer, customer_id) or f"Customer#{customer_id}"

    # ---- Contracts --------------------------------------------------------
    contracts = (
        db.query(Contract)
        .filter(Contract.customer_id == customer_id)
        .all()
    )
    contracts_unfinished, contracts_finished = _count_contracts(contracts)

    # ---- Orders -----------------------------------------------------------
    orders = (
        db.query(Order)
        .filter(Order.customer_id == customer_id)
        .all()
    )
    orders_unfinished, orders_finished = _count_orders(orders)

    # ---- Receivable -------------------------------------------------------
    receivable = (
        db.query(func.coalesce(func.sum(Order.biz_total_amount), 0))
        .filter(
            Order.customer_id == customer_id,
            Order.is_collected == False,
        )
        .scalar()
    ) or Decimal("0")

    # ---- Request amount (via Order join) ----------------------------------
    request_amount = (
        db.query(func.coalesce(func.sum(RequestPaymentDetail.request_amount), 0))
        .join(Order, RequestPaymentDetail.order_id == Order.id)
        .filter(Order.customer_id == customer_id)
        .scalar()
    ) or Decimal("0")

    # ---- Collection amount (via Order join) -------------------------------
    collection_amount = (
        db.query(func.coalesce(func.sum(CollectionDetail.collection_amount), 0))
        .join(Order, CollectionDetail.order_id == Order.id)
        .filter(Order.customer_id == customer_id)
        .scalar()
    ) or Decimal("0")

    # ---- Expenditure (via Contract -> Finance) ----------------------------
    contract_ids = [c.id for c in contracts]
    expenditure = Decimal("0")
    if contract_ids:
        expenditure = (
            db.query(func.coalesce(func.sum(Finance.amount), 0))
            .filter(
                Finance.contract_id.in_(contract_ids),
                Finance.income_expense_type == EXPENSE_TYPE,
            )
            .scalar()
        ) or Decimal("0")

    # ---- Tax & Profit -----------------------------------------------------
    # Derive tax rate from the first contract's company, if available
    tax_rate = DEFAULT_TAX_RATE
    if contracts:
        for c in contracts:
            if c.company_id:
                tax_rate = _get_company_tax_rate(db, c.company_id)
                break

    tax_estimate = collection_amount * tax_rate
    profit = collection_amount - expenditure - tax_estimate
    unrequested = receivable - request_amount

    # ---- Upsert -----------------------------------------------------------
    record = (
        db.query(CustomerRevenue)
        .filter(
            CustomerRevenue.customer_id == customer_id,
            CustomerRevenue.rev_date == rev_date,
        )
        .first()
    )

    data = dict(
        customer_name=customer_name,
        customer_id=customer_id,
        rev_date=rev_date,
        orders_unfinished=orders_unfinished,
        orders_finished=orders_finished,
        contracts_unfinished=contracts_unfinished,
        contracts_finished=contracts_finished,
        receivable_amount=receivable,
        request_amount=request_amount,
        collection_amount=collection_amount,
        unrequested_amount=unrequested,
        expenditure=expenditure,
        profit=profit,
    )

    if record:
        for k, v in data.items():
            setattr(record, k, v)
    else:
        record = CustomerRevenue(**data)
        db.add(record)

    db.flush()
    return record


# ---------------------------------------------------------------------------
# 4. Project Revenue
# ---------------------------------------------------------------------------

def calculate_project_revenue(
    db: Session, project_id: int, rev_date: date
) -> ProjectRevenue:
    """
    Aggregate contracts, orders, and finance for a project on *rev_date*,
    then upsert a :class:`ProjectRevenue` record.
    """
    project_name = _resolve_name(db, Project, project_id) or f"Project#{project_id}"

    # ---- Contracts --------------------------------------------------------
    contracts = (
        db.query(Contract)
        .filter(Contract.project_id == project_id)
        .all()
    )
    contracts_unfinished, contracts_finished = _count_contracts(contracts)
    contract_ids = [c.id for c in contracts]

    # Customer info from first contract
    first_customer_id: Optional[int] = None
    first_customer_name: Optional[str] = None
    if contracts:
        first_customer_id = contracts[0].customer_id
        first_customer_name = contracts[0].customer_name

    # ---- Orders (via contract) --------------------------------------------
    orders = []
    if contract_ids:
        orders = (
            db.query(Order)
            .filter(Order.contract_id.in_(contract_ids))
            .all()
        )
    orders_unfinished, orders_finished = _count_orders(orders)

    # ---- Receivable -------------------------------------------------------
    receivable = Decimal("0")
    if contract_ids:
        receivable = (
            db.query(func.coalesce(func.sum(Order.biz_total_amount), 0))
            .filter(
                Order.contract_id.in_(contract_ids),
                Order.is_collected == False,
            )
            .scalar()
        ) or Decimal("0")

    # ---- Request amount ---------------------------------------------------
    request_amount = Decimal("0")
    if contract_ids:
        request_amount = (
            db.query(func.coalesce(func.sum(RequestPaymentDetail.request_amount), 0))
            .join(Order, RequestPaymentDetail.order_id == Order.id)
            .filter(Order.contract_id.in_(contract_ids))
            .scalar()
        ) or Decimal("0")

    # ---- Collection amount ------------------------------------------------
    collection_amount = Decimal("0")
    if contract_ids:
        collection_amount = (
            db.query(func.coalesce(func.sum(CollectionDetail.collection_amount), 0))
            .join(Order, CollectionDetail.order_id == Order.id)
            .filter(Order.contract_id.in_(contract_ids))
            .scalar()
        ) or Decimal("0")

    # ---- Expenditure ------------------------------------------------------
    expenditure = Decimal("0")
    if contract_ids:
        expenditure = (
            db.query(func.coalesce(func.sum(Finance.amount), 0))
            .filter(
                Finance.contract_id.in_(contract_ids),
                Finance.income_expense_type == EXPENSE_TYPE,
            )
            .scalar()
        ) or Decimal("0")

    # ---- Tax & Profit -----------------------------------------------------
    tax_rate = DEFAULT_TAX_RATE
    if contracts:
        for c in contracts:
            if c.company_id:
                tax_rate = _get_company_tax_rate(db, c.company_id)
                break

    tax_estimate = collection_amount * tax_rate
    profit = collection_amount - expenditure - tax_estimate
    unrequested = receivable - request_amount

    # ---- Upsert -----------------------------------------------------------
    record = (
        db.query(ProjectRevenue)
        .filter(
            ProjectRevenue.project_id == project_id,
            ProjectRevenue.rev_date == rev_date,
        )
        .first()
    )

    data = dict(
        project_id=project_id,
        project_name=project_name,
        customer_name=first_customer_name,
        customer_id=first_customer_id,
        rev_date=rev_date,
        orders_unfinished=orders_unfinished,
        orders_finished=orders_finished,
        contracts_unfinished=contracts_unfinished,
        contracts_finished=contracts_finished,
        receivable_amount=receivable,
        request_amount=request_amount,
        collection_amount=collection_amount,
        unrequested_amount=unrequested,
        expenditure=expenditure,
        profit=profit,
    )

    if record:
        for k, v in data.items():
            setattr(record, k, v)
    else:
        record = ProjectRevenue(**data)
        db.add(record)

    db.flush()
    return record


# ---------------------------------------------------------------------------
# 5. Calculate All Revenues (main scheduler entry-point)
# ---------------------------------------------------------------------------

def calculate_all_revenues(db: Session, rev_date: date) -> dict:
    """
    Run all four revenue calculations for every entity on *rev_date*.
    Returns a summary dict with counts of processed entities.

    This is the main entry-point called by the scheduler.
    """
    results = {
        "departments": 0,
        "companies": 0,
        "customers": 0,
        "projects": 0,
        "date": rev_date.isoformat(),
    }

    # Departments
    dept_ids = [
        row[0]
        for row in db.query(Department.id).all()
    ]
    for dept_id in dept_ids:
        calculate_department_revenue(db, dept_id, rev_date)
        results["departments"] += 1

    # Companies
    company_ids = [
        row[0]
        for row in db.query(Company.id).all()
    ]
    for company_id in company_ids:
        calculate_company_revenue(db, company_id, rev_date)
        results["companies"] += 1

    # Customers
    customer_ids = [
        row[0]
        for row in db.query(Customer.id).all()
    ]
    for customer_id in customer_ids:
        calculate_customer_revenue(db, customer_id, rev_date)
        results["customers"] += 1

    # Projects
    project_ids = [
        row[0]
        for row in db.query(Project.id).all()
    ]
    for project_id in project_ids:
        calculate_project_revenue(db, project_id, rev_date)
        results["projects"] += 1

    db.commit()
    return results


# ---------------------------------------------------------------------------
# 6. Standalone Runner
# ---------------------------------------------------------------------------

def run_daily_stats() -> dict:
    """
    Standalone function that creates a DB session and runs
    :func:`calculate_all_revenues` for today's date.

    Designed for use by cron / schedulers / CLI scripts.
    """
    db = SessionLocal()
    try:
        today = date.today()
        result = calculate_all_revenues(db, today)
        return result
    finally:
        db.close()