"""API 路由"""
from app.api.org_management import (
    employee_router as router_employees,
    department_router as router_departments,
    company_router as router_companies,
    customer_router as router_customers,
)
from app.api.business_core import (
    router_projects,
    router_contracts,
    router_services,
)
from app.api.finance_ops import (
    router_orders as router_orders,
    router_request_payments as router_request_payments,
    router_collections as router_collections,
    router_finances as router_finances,
)
from app.api.reports import router_reports

__all__ = [
    "router_employees",
    "router_departments",
    "router_companies",
    "router_customers",
    "router_projects",
    "router_contracts",
    "router_services",
    "router_orders",
    "router_request_payments",
    "router_collections",
    "router_finances",
    "router_reports",
]