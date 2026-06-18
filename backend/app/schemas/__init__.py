"""
Pydantic 数据模式 - 请求/响应验证
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Any, Dict

from pydantic import BaseModel, Field, field_validator


# ====================== 通用 ======================
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_field: Optional[str] = None
    sort_order: Optional[str] = Field(default="asc", pattern="^(asc|desc)$")


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class BatchAction(BaseModel):
    ids: List[int]
    action: Optional[str] = None  # delete, status 等
    value: Optional[str] = None  # 状态值等


class APIResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None


# ====================== 1. 员工 ======================
class EmployeeBase(BaseModel):
    name: str = Field(..., max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    monthly_salary: Optional[Decimal] = Decimal(0)
    social_insurance: Optional[Decimal] = Decimal(0)
    role: Optional[str] = Field(default="员工", max_length=20)
    department_id: Optional[int] = None
    is_active: Optional[bool] = True


class EmployeeCreate(EmployeeBase):
    password: str = Field(default="147258", min_length=6)
    phone: str = Field(..., max_length=20)


class EmployeeUpdate(EmployeeBase):
    name: Optional[str] = None
    password: Optional[str] = None


class EmployeeOut(EmployeeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


class EmployeeSalaryBase(BaseModel):
    employee_id: int
    salary_month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    monthly_salary: Optional[Decimal] = Decimal(0)
    reimbursement: Optional[Decimal] = Decimal(0)
    deduction: Optional[Decimal] = Decimal(0)
    fuel_fee: Optional[Decimal] = Decimal(0)
    social_insurance: Optional[Decimal] = Decimal(0)
    bonus: Optional[Decimal] = Decimal(0)
    actual_salary: Optional[Decimal] = Decimal(0)


class EmployeeSalaryCreate(EmployeeSalaryBase):
    employee_id: Optional[int] = None


class EmployeeSalaryUpdate(EmployeeSalaryBase):
    employee_id: Optional[int] = None
    salary_month: Optional[str] = None


class EmployeeSalaryOut(EmployeeSalaryBase):
    id: int
    created_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


class EmployeePerfBase(BaseModel):
    employee_id: int
    perf_date: date
    perf_amount: Optional[Decimal] = Decimal(0)
    orders_unfinished: Optional[int] = 0
    orders_finished: Optional[int] = 0
    contracts_unfinished: Optional[int] = 0
    contracts_finished: Optional[int] = 0
    receivable_amount: Optional[Decimal] = Decimal(0)
    request_amount: Optional[Decimal] = Decimal(0)
    collection_amount: Optional[Decimal] = Decimal(0)
    unrequested_amount: Optional[Decimal] = Decimal(0)
    expenditure: Optional[Decimal] = Decimal(0)
    profit: Optional[Decimal] = Decimal(0)


class EmployeePerfCreate(EmployeePerfBase):
    employee_id: Optional[int] = None


class EmployeePerfOut(EmployeePerfBase):
    id: int
    created_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


# ====================== 2. 部门 ======================
class DepartmentBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(DepartmentBase):
    pass


class DepartmentOut(DepartmentBase):
    id: int
    created_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


# ====================== 3. 公司 ======================
class CompanyBase(BaseModel):
    name: str = Field(..., max_length=200)
    tax_rate: Optional[Decimal] = Decimal("0.06")
    address: Optional[str] = None
    tax_number: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(CompanyBase):
    pass


class CompanyOut(CompanyBase):
    id: int
    created_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


class BankAccountBase(BaseModel):
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    account_type: str = Field(..., max_length=50)
    bank_account: str = Field(..., max_length=100)
    bank_name: Optional[str] = None


class BankAccountCreate(BankAccountBase):
    pass


class BankAccountOut(BankAccountBase):
    id: int
    sort_order: int = 0

    class Config:
        from_attributes = True


# ====================== 4. 客户 ======================
class CustomerBase(BaseModel):
    name: str = Field(..., max_length=200)
    address: Optional[str] = None
    contact_person: Optional[str] = None
    status: str = Field(default="正常", max_length=20)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(CustomerBase):
    pass


class CustomerOut(CustomerBase):
    id: int
    created_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


# ====================== 5. 项目 ======================
class ProjectBase(BaseModel):
    project_no: str = Field(..., max_length=100)
    project_date: date
    name: str = Field(..., max_length=200)
    status: str = Field(default="进行中", max_length=20)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    project_no: Optional[str] = None
    project_date: Optional[date] = None
    name: Optional[str] = None
    status: Optional[str] = None


class ProjectOut(ProjectBase):
    id: int
    created_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


# ====================== 6. 合同 ======================
class ContractBase(BaseModel):
    contract_no: str = Field(..., max_length=100)
    contract_date: date
    name: str = Field(..., max_length=200)
    status: str = Field(default="待签订", max_length=20)
    service_content: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[int] = None
    project_id: Optional[int] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    labor_cost: Optional[Decimal] = Decimal(0)
    cost_amount: Optional[Decimal] = Decimal(0)
    tax_fee: Optional[Decimal] = Decimal(0)
    other_fee: Optional[Decimal] = Decimal(0)
    business_fee: Optional[Decimal] = Decimal(0)
    bonus: Optional[Decimal] = Decimal(0)
    owner_name: Optional[str] = None
    sales_name: Optional[str] = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(ContractBase):
    contract_no: Optional[str] = None
    name: Optional[str] = None


class ContractOut(ContractBase):
    id: int
    orders_unfinished: int = 0
    orders_finished: int = 0
    receivable_amount: Decimal = Decimal(0)
    request_amount: Decimal = Decimal(0)
    collection_amount: Decimal = Decimal(0)
    unrequested_amount: Decimal = Decimal(0)
    profit: Decimal = Decimal(0)
    created_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


# ====================== 7. 业务 ======================
class BizServiceBase(BaseModel):
    category: str = Field(..., max_length=100)
    item_name: str = Field(..., max_length=200)
    parameters: Optional[str] = None
    unit_price: Optional[Decimal] = Decimal(0)
    unit: str = Field(..., max_length=50)
    settlement_fee: Optional[Decimal] = Decimal(0)
    performance_fee: Optional[Decimal] = Decimal(0)


class BizServiceCreate(BizServiceBase):
    pass


class BizServiceUpdate(BizServiceBase):
    pass


class BizServiceOut(BizServiceBase):
    id: int
    sort_order: int = 0

    class Config:
        from_attributes = True


# ====================== 8. 订单 ======================
class OrderBase(BaseModel):
    order_no: str = Field(..., max_length=100)
    status: str = Field(default="未完成", max_length=20)
    order_date: date
    contract_id: Optional[int] = None
    contract_no: Optional[str] = None
    project_name: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[int] = None
    biz_category: Optional[str] = None
    biz_parameters: Optional[str] = None
    biz_unit: Optional[str] = None
    biz_quantity: Optional[Decimal] = Decimal(0)
    biz_unit_price: Optional[Decimal] = Decimal(0)
    biz_total_amount: Optional[Decimal] = Decimal(0)
    report_date: Optional[date] = None
    report_no: Optional[str] = None
    report_signoff: Optional[str] = None
    report_attachment: Optional[str] = None
    settlement_fee: Optional[Decimal] = Decimal(0)
    performance_fee: Optional[Decimal] = Decimal(0)
    owner_name: Optional[str] = None
    sales_name: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None


class OrderCreate(OrderBase):
    pass


class OrderUpdate(OrderBase):
    order_no: Optional[str] = None


class OrderOut(OrderBase):
    id: int
    is_requested: bool = False
    is_collected: bool = False
    created_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


# ====================== 9. 请款 ======================
class RequestSummaryBase(BaseModel):
    batch_no: str = Field(..., max_length=100)
    order_ids: Optional[str] = None
    request_date: date
    contract_id: Optional[int] = None
    contract_no: Optional[str] = None
    project_name: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[int] = None
    request_amount: Optional[Decimal] = Decimal(0)
    status: str = Field(default="待请款", max_length=20)


class RequestSummaryCreate(RequestSummaryBase):
    detail_order_ids: Optional[List[int]] = None


class RequestSummaryOut(RequestSummaryBase):
    id: int
    created_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


class RequestDetailBase(BaseModel):
    summary_id: int
    order_id: Optional[int] = None
    order_no: Optional[str] = None
    request_date: date
    contract_id: Optional[int] = None
    contract_no: Optional[str] = None
    project_name: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[int] = None
    request_amount: Optional[Decimal] = Decimal(0)
    status: str = Field(default="待请款", max_length=20)


class RequestDetailOut(RequestDetailBase):
    id: int

    class Config:
        from_attributes = True


# ====================== 10. 收款 ======================
class CollectionSummaryBase(BaseModel):
    batch_no: str = Field(..., max_length=100)
    order_ids: Optional[str] = None
    collection_date: date
    contract_id: Optional[int] = None
    contract_no: Optional[str] = None
    project_name: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[int] = None
    collection_amount: Optional[Decimal] = Decimal(0)
    actual_amount: Optional[Decimal] = Decimal(0)
    status: str = Field(default="待收款", max_length=20)


class CollectionSummaryCreate(CollectionSummaryBase):
    detail_order_ids: Optional[List[int]] = None


class CollectionSummaryOut(CollectionSummaryBase):
    id: int
    created_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


class CollectionDetailBase(BaseModel):
    summary_id: int
    order_id: Optional[int] = None
    order_no: Optional[str] = None
    collection_date: date
    contract_id: Optional[int] = None
    contract_no: Optional[str] = None
    project_name: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[int] = None
    collection_amount: Optional[Decimal] = Decimal(0)
    actual_amount: Optional[Decimal] = Decimal(0)
    status: str = Field(default="待收款", max_length=20)


class CollectionDetailOut(CollectionDetailBase):
    id: int

    class Config:
        from_attributes = True


# ====================== 11. 财务 ======================
class FinanceBase(BaseModel):
    finance_no: str = Field(..., max_length=100)
    finance_date: date
    contract_id: Optional[int] = None
    contract_no: Optional[str] = None
    category: str = Field(..., max_length=100)
    description: Optional[str] = None
    income_expense_type: str = Field(..., pattern="^(收入|支出)$")
    amount: Optional[Decimal] = Decimal(0)
    company_name: Optional[str] = None
    company_bank_account: Optional[str] = None
    status: str = Field(default="未入账", max_length=20)
    invoice_no: Optional[str] = None
    attachment: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    company_id: Optional[int] = None


class FinanceCreate(FinanceBase):
    pass


class FinanceUpdate(FinanceBase):
    finance_no: Optional[str] = None


class FinanceOut(FinanceBase):
    id: int
    created_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


# ====================== 报表 ======================
class ReportQuery(BaseModel):
    report_type: str  # daily / quarterly / yearly / project / contract
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    year: Optional[int] = None
    quarter: Optional[int] = Field(None, ge=1, le=4)
    company_id: Optional[int] = None
    department_id: Optional[int] = None
    project_id: Optional[int] = None


class RevenueReportItem(BaseModel):
    label: str
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


class FinanceReportItem(BaseModel):
    finance_date: date
    category: str
    description: Optional[str]
    income_expense_type: str
    amount: Decimal
    company_name: Optional[str]
    status: str


class ProjectContractReport(BaseModel):
    project_count: int = 0
    project_completed: int = 0
    project_unfinished: int = 0
    contract_count: int = 0
    contract_completed: int = 0
    contract_unfinished: int = 0
    contract_pending: int = 0
    receivable_amount: Decimal = Decimal(0)
    pending_collection: Decimal = Decimal(0)
    collected_amount: Decimal = Decimal(0)