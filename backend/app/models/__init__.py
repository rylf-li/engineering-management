"""
数据库模型 - 工程检测公司综合管理系统
包含所有核心表、子表及关联关系
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Numeric, Date, DateTime, Text,
    ForeignKey, Boolean, Float, Enum as SAEnum, UniqueConstraint,
    Index, JSON
)
from sqlalchemy.orm import relationship, backref

from app.database import Base


# ============================
# Mixin：通用字段
# ============================
class TimestampMixin:
    """创建/更新时间戳"""
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class SortableMixin:
    """可拖拽排序"""
    sort_order = Column(Integer, default=0, comment="排序号")


# ============================
# 1. 员工管理
# ============================
class Employee(Base, TimestampMixin, SortableMixin):
    __tablename__ = "employees"
    __table_args__ = (Index("idx_employee_phone", "phone"),)

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    name = Column(String(100), nullable=False, comment="员工名称")
    phone = Column(String(20), unique=True, nullable=False, comment="手机号码")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    monthly_salary = Column(Numeric(12, 2), default=0, comment="月薪工资")
    social_insurance = Column(Numeric(12, 2), default=0, comment="社保费")
    role = Column(String(20), default="员工", comment="角色(管理员/业务员/财务/员工)")
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="所属部门")
    status = Column(String(20), default="正常", comment="状态(正常/停用)")
    is_active = Column(Boolean, default=True, comment="是否在职")

    department = relationship("Department", back_populates="employees")
    salaries = relationship("EmployeeSalary", back_populates="employee", cascade="all, delete-orphan")
    performances = relationship("EmployeePerformance", back_populates="employee", cascade="all, delete-orphan")


class EmployeeSalary(Base, TimestampMixin, SortableMixin):
    __tablename__ = "employee_salaries"
    __table_args__ = (
        UniqueConstraint("employee_id", "salary_month", name="uq_emp_salary_month"),
        Index("idx_salary_employee", "employee_id"),
        Index("idx_sal_emp_month", "employee_id", "salary_month"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, comment="员工ID")
    salary_month = Column(String(7), nullable=False, comment="日期月份 (YYYY-MM)")
    monthly_salary = Column(Numeric(12, 2), default=0, comment="月薪工资")
    reimbursement = Column(Numeric(12, 2), default=0, comment="报销费用")
    deduction = Column(Numeric(12, 2), default=0, comment="扣款")
    fuel_fee = Column(Numeric(12, 2), default=0, comment="加油费")
    social_insurance = Column(Numeric(12, 2), default=0, comment="社保费")
    bonus = Column(Numeric(12, 2), default=0, comment="绩效")
    actual_salary = Column(Numeric(12, 2), default=0, comment="实发工资")

    employee = relationship("Employee", back_populates="salaries")


class EmployeePerformance(Base, TimestampMixin, SortableMixin):
    __tablename__ = "employee_performances"
    __table_args__ = (
        Index("idx_perf_employee", "employee_id"),
        Index("idx_perf_emp_date", "employee_id", "perf_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, comment="员工ID")
    perf_date = Column(Date, nullable=False, comment="日期")
    perf_amount = Column(Numeric(12, 2), default=0, comment="绩效金额")
    orders_unfinished = Column(Integer, default=0, comment="订单数(未完成)")
    orders_finished = Column(Integer, default=0, comment="订单数(已完成)")
    contracts_unfinished = Column(Integer, default=0, comment="合同数(未完成)")
    contracts_finished = Column(Integer, default=0, comment="合同数(已完成)")
    receivable_amount = Column(Numeric(12, 2), default=0, comment="应收金额")
    request_amount = Column(Numeric(12, 2), default=0, comment="请款金额")
    collection_amount = Column(Numeric(12, 2), default=0, comment="收款金额")
    unrequested_amount = Column(Numeric(12, 2), default=0, comment="未请款金额")
    expenditure = Column(Numeric(12, 2), default=0, comment="支出")
    profit = Column(Numeric(12, 2), default=0, comment="利润")

    employee = relationship("Employee", back_populates="performances")


# ============================
# 2. 部门管理
# ============================
class Department(Base, TimestampMixin, SortableMixin):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    name = Column(String(100), nullable=False, unique=True, comment="部门名称")
    description = Column(Text, nullable=True, comment="描述")

    employees = relationship("Employee", back_populates="department")
    revenues = relationship("DepartmentRevenue", back_populates="department", cascade="all, delete-orphan")


class DepartmentRevenue(Base, TimestampMixin):
    __tablename__ = "department_revenues"
    __table_args__ = (
        UniqueConstraint("department_id", "rev_date", name="uq_dept_rev_date"),
        Index("idx_dept_rev_dept", "department_id"),
        Index("idx_dept_rev_date", "rev_date"),
        Index("idx_dept_rev_dept_date", "department_id", "rev_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    company_name = Column(String(200), nullable=True, comment="公司名称")
    company_id = Column(Integer, nullable=True, comment="公司ID")
    department_name = Column(String(100), nullable=False, comment="部门名称")
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, comment="部门ID")
    rev_date = Column(Date, nullable=False, comment="日期")
    orders_unfinished = Column(Integer, default=0, comment="订单数(未完成)")
    orders_finished = Column(Integer, default=0, comment="订单数(已完成)")
    contracts_unfinished = Column(Integer, default=0, comment="合同数(未完成)")
    contracts_finished = Column(Integer, default=0, comment="合同数(已完成)")
    receivable_amount = Column(Numeric(12, 2), default=0, comment="应收金额")
    request_amount = Column(Numeric(12, 2), default=0, comment="请款金额")
    collection_amount = Column(Numeric(12, 2), default=0, comment="收款金额")
    expenditure = Column(Numeric(12, 2), default=0, comment="支出")
    profit = Column(Numeric(12, 2), default=0, comment="利润")

    department = relationship("Department", back_populates="revenues")


# ============================
# 3. 公司管理
# ============================
class Company(Base, TimestampMixin, SortableMixin):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    name = Column(String(200), nullable=False, unique=True, comment="公司名称")
    tax_rate = Column(Numeric(5, 4), default=0.06, comment="税率")
    address = Column(String(500), nullable=True, comment="地址")
    tax_number = Column(String(50), nullable=True, comment="税务号")

    bank_accounts = relationship("CompanyBankAccount", back_populates="company", cascade="all, delete-orphan")
    revenues = relationship("CompanyRevenue", back_populates="company", cascade="all, delete-orphan")


class CompanyBankAccount(Base, TimestampMixin, SortableMixin):
    __tablename__ = "company_bank_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, comment="公司ID")
    company_name = Column(String(200), nullable=True, comment="公司名称")
    account_type = Column(String(50), nullable=False, comment="账户类别(对公/对私)")
    bank_account = Column(String(100), nullable=False, comment="银行账户")
    bank_name = Column(String(200), nullable=True, comment="开户行")

    company = relationship("Company", back_populates="bank_accounts")


class CompanyRevenue(Base, TimestampMixin):
    __tablename__ = "company_revenues"
    __table_args__ = (
        UniqueConstraint("company_id", "department_id", "rev_date", name="uq_comp_dept_rev_date"),
        Index("idx_comp_rev_comp", "company_id"),
        Index("idx_comp_rev_date", "rev_date"),
        Index("idx_comp_rev_comp_date", "company_id", "rev_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    company_name = Column(String(200), nullable=False, comment="公司名称")
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, comment="公司ID")
    department_name = Column(String(100), nullable=True, comment="部门名称")
    department_id = Column(Integer, nullable=True, comment="部门ID")
    rev_date = Column(Date, nullable=False, comment="日期")
    orders_unfinished = Column(Integer, default=0, comment="订单数(未完成)")
    orders_finished = Column(Integer, default=0, comment="订单数(已完成)")
    contracts_unfinished = Column(Integer, default=0, comment="合同数(未完成)")
    contracts_finished = Column(Integer, default=0, comment="合同数(已完成)")
    receivable_amount = Column(Numeric(12, 2), default=0, comment="应收金额")
    request_amount = Column(Numeric(12, 2), default=0, comment="请款金额")
    collection_amount = Column(Numeric(12, 2), default=0, comment="收款金额")
    unrequested_amount = Column(Numeric(12, 2), default=0, comment="未请款金额")
    expenditure = Column(Numeric(12, 2), default=0, comment="支出")
    profit = Column(Numeric(12, 2), default=0, comment="利润")

    company = relationship("Company", back_populates="revenues")


# ============================
# 4. 客户管理
# ============================
class Customer(Base, TimestampMixin, SortableMixin):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    name = Column(String(200), nullable=False, comment="客户名称")
    address = Column(String(500), nullable=True, comment="客户地址")
    contact_person = Column(String(100), nullable=True, comment="联系人")
    status = Column(String(20), default="正常", comment="状态(正常/停用)")

    revenues = relationship("CustomerRevenue", back_populates="customer", cascade="all, delete-orphan")


class CustomerRevenue(Base, TimestampMixin):
    __tablename__ = "customer_revenues"
    __table_args__ = (
        UniqueConstraint("customer_id", "rev_date", name="uq_cust_rev_date"),
        Index("idx_cust_rev_cust", "customer_id"),
        Index("idx_cust_rev_cust_date", "customer_id", "rev_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    customer_name = Column(String(200), nullable=False, comment="客户名称")
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, comment="客户ID")
    rev_date = Column(Date, nullable=False, comment="日期")
    orders_unfinished = Column(Integer, default=0, comment="订单数(未完成)")
    orders_finished = Column(Integer, default=0, comment="订单数(已完成)")
    contracts_unfinished = Column(Integer, default=0, comment="合同数(未完成)")
    contracts_finished = Column(Integer, default=0, comment="合同数(已完成)")
    receivable_amount = Column(Numeric(12, 2), default=0, comment="应收金额")
    request_amount = Column(Numeric(12, 2), default=0, comment="请款金额")
    collection_amount = Column(Numeric(12, 2), default=0, comment="收款金额")
    unrequested_amount = Column(Numeric(12, 2), default=0, comment="未请款金额")
    expenditure = Column(Numeric(12, 2), default=0, comment="支出")
    profit = Column(Numeric(12, 2), default=0, comment="利润")

    customer = relationship("Customer", back_populates="revenues")


# ============================
# 5. 项目管理
# ============================
class Project(Base, TimestampMixin, SortableMixin):
    __tablename__ = "projects"
    __table_args__ = (Index("idx_project_status", "status"),)

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    project_no = Column(String(100), unique=True, nullable=False, comment="项目编号")
    project_date = Column(Date, nullable=False, comment="日期")
    name = Column(String(200), nullable=False, comment="项目名称")
    status = Column(String(20), default="进行中", comment="项目状态(进行中/已完成/暂停)")

    revenues = relationship("ProjectRevenue", back_populates="project", cascade="all, delete-orphan")
    contracts = relationship("Contract", back_populates="project")


class ProjectRevenue(Base, TimestampMixin):
    __tablename__ = "project_revenues"
    __table_args__ = (
        UniqueConstraint("project_id", "rev_date", name="uq_proj_rev_date"),
        Index("idx_proj_rev_proj", "project_id"),
        Index("idx_proj_rev_proj_date", "project_id", "rev_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, comment="项目ID")
    project_name = Column(String(200), nullable=True, comment="项目名称")
    customer_name = Column(String(200), nullable=True, comment="客户名称")
    customer_id = Column(Integer, nullable=True, comment="客户ID")
    rev_date = Column(Date, nullable=False, comment="日期")
    orders_unfinished = Column(Integer, default=0, comment="订单数(未完成)")
    orders_finished = Column(Integer, default=0, comment="订单数(已完成)")
    contracts_unfinished = Column(Integer, default=0, comment="合同数(未完成)")
    contracts_finished = Column(Integer, default=0, comment="合同数(已完成)")
    receivable_amount = Column(Numeric(12, 2), default=0, comment="应收金额")
    request_amount = Column(Numeric(12, 2), default=0, comment="请款金额")
    collection_amount = Column(Numeric(12, 2), default=0, comment="收款金额")
    unrequested_amount = Column(Numeric(12, 2), default=0, comment="未请款金额")
    expenditure = Column(Numeric(12, 2), default=0, comment="支出")
    profit = Column(Numeric(12, 2), default=0, comment="利润")

    project = relationship("Project", back_populates="revenues")


# ============================
# 6. 合同管理
# ============================
class Contract(Base, TimestampMixin, SortableMixin):
    __tablename__ = "contracts"
    __table_args__ = (
        Index("idx_contract_status", "status"),
        Index("idx_contract_customer", "customer_id"),
        Index("idx_contracts_dept_status", "department_id", "status"),
        Index("idx_contracts_company_status", "company_id", "status"),
        Index("idx_contracts_customer_status", "customer_id", "status"),
        Index("idx_contracts_project_status", "project_id", "status"),
        Index("idx_contracts_date_status", "contract_date", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    contract_no = Column(String(100), unique=True, nullable=False, comment="合同编号")
    contract_date = Column(Date, nullable=False, comment="日期")
    name = Column(String(200), nullable=False, comment="合同名称")
    status = Column(String(20), default="待签订", comment="合同状态(待签订/执行中/已完成/终止)")
    service_content = Column(Text, nullable=True, comment="服务内容")

    # 客户信息
    customer_name = Column(String(200), nullable=True, comment="客户名称")
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, comment="客户ID")

    # 项目和部门关联
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, comment="项目ID")
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="部门ID")
    department_name = Column(String(100), nullable=True, comment="部门名称")
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, comment="公司ID")
    company_name = Column(String(200), nullable=True, comment="公司名称")

    # 订单统计
    orders_unfinished = Column(Integer, default=0, comment="订单数(未完成)")
    orders_finished = Column(Integer, default=0, comment="订单数(已完成)")

    # 财务汇总
    receivable_amount = Column(Numeric(12, 2), default=0, comment="应收金额")
    request_amount = Column(Numeric(12, 2), default=0, comment="请款金额")
    collection_amount = Column(Numeric(12, 2), default=0, comment="收款金额")
    unrequested_amount = Column(Numeric(12, 2), default=0, comment="未请款金额")

    # 成本与费用
    contract_amount = Column(Numeric(12, 2), default=0, comment="合同金额")
    labor_cost = Column(Numeric(12, 2), default=0, comment="劳务费")
    cost_amount = Column(Numeric(12, 2), default=0, comment="成本金额")
    tax_fee = Column(Numeric(12, 2), default=0, comment="税费")
    other_fee = Column(Numeric(12, 2), default=0, comment="其他")
    business_fee = Column(Numeric(12, 2), default=0, comment="业务费")
    bonus = Column(Numeric(12, 2), default=0, comment="绩效")
    profit = Column(Numeric(12, 2), default=0, comment="利润")

    # 人员
    owner_name = Column(String(100), nullable=True, comment="负责人")
    sales_name = Column(String(100), nullable=True, comment="业务员")

    project = relationship("Project", back_populates="contracts")
    customer = relationship("Customer")
    department = relationship("Department")
    company = relationship("Company")
    orders = relationship("Order", back_populates="contract")
    finance_records = relationship("Finance", back_populates="contract")


# ============================
# 7. 业务管理（服务与计费规则）
# ============================
class BusinessService(Base, TimestampMixin, SortableMixin):
    __tablename__ = "business_services"
    __table_args__ = (UniqueConstraint("category", "item_name", name="uq_biz_cat_item"),)

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    category = Column(String(100), nullable=False, comment="业务类别(检测/测绘/勘察)")
    item_name = Column(String(200), nullable=False, comment="业务项目")
    parameters = Column(String(500), nullable=True, comment="业务参数")
    unit_price = Column(Numeric(12, 2), default=0, comment="业务单价")
    unit = Column(String(50), nullable=True, comment="业务单位")
    settlement_fee = Column(Numeric(12, 2), default=0, comment="业务结算费")
    performance_fee = Column(Numeric(12, 2), default=0, comment="业务绩效费")


# ============================
# 8. 订单管理
# ============================
class Order(Base, TimestampMixin, SortableMixin):
    __tablename__ = "orders"
    __table_args__ = (
        Index("idx_order_status", "status"),
        Index("idx_order_contract", "contract_id"),
        Index("idx_order_customer", "customer_id"),
        Index("idx_orders_dept_status", "department_id", "status"),
        Index("idx_orders_company_status", "company_id", "status"),
        Index("idx_orders_contract_status", "contract_id", "status"),
        Index("idx_orders_customer_status", "customer_id", "status"),
        Index("idx_orders_date_status", "order_date", "status"),
        Index("idx_orders_dept_uncollected", "department_id", "is_collected"),
        Index("idx_orders_company_uncollected", "company_id", "is_collected"),
        Index("idx_orders_dept_date", "department_id", "order_date"),
        Index("idx_orders_company_date", "company_id", "order_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    order_no = Column(String(100), unique=True, nullable=False, comment="订单编号")
    status = Column(String(20), default="未完成", comment="订单状态(未完成/已完成/已取消)")
    order_date = Column(Date, nullable=False, comment="日期")

    # 合同关联
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True, comment="合同ID")
    contract_no = Column(String(100), nullable=True, comment="合同编号")

    # 工程与客户
    project_name = Column(String(200), nullable=True, comment="工程名称")
    customer_name = Column(String(200), nullable=True, comment="客户名称")
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, comment="客户ID")

    # 业务参数
    biz_category = Column(String(100), nullable=True, comment="业务类别")
    biz_parameters = Column(String(500), nullable=True, comment="业务参数")
    biz_unit = Column(String(50), nullable=True, comment="业务单位")
    biz_quantity = Column(Numeric(12, 2), default=0, comment="业务数量")
    biz_unit_price = Column(Numeric(12, 2), default=0, comment="业务单价")
    biz_total_amount = Column(Numeric(12, 2), default=0, comment="合计金额")

    # 报告
    report_date = Column(Date, nullable=True, comment="报告日期")
    report_no = Column(String(100), nullable=True, comment="报告编号")
    report_signoff = Column(String(50), nullable=True, comment="报告签收")
    report_attachment = Column(String(500), nullable=True, comment="报告附件")

    # 请款/收款标记
    is_requested = Column(Boolean, default=False, comment="是否已请款")
    is_collected = Column(Boolean, default=False, comment="是否已收款")

    # 结算与绩效
    settlement_fee = Column(Numeric(12, 2), default=0, comment="业务结算费")
    performance_fee = Column(Numeric(12, 2), default=0, comment="业务绩效费")

    # 人员与部门
    owner_name = Column(String(100), nullable=True, comment="负责人")
    sales_name = Column(String(100), nullable=True, comment="业务员")
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="部门ID")
    department_name = Column(String(100), nullable=True, comment="部门名称")
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, comment="公司ID")
    company_name = Column(String(200), nullable=True, comment="公司名称")

    contract = relationship("Contract", back_populates="orders")
    customer = relationship("Customer")
    department = relationship("Department")
    company = relationship("Company")
    request_details = relationship("RequestPaymentDetail", back_populates="order")
    collection_details = relationship("CollectionDetail", back_populates="order")


# ============================
# 9. 请款管理
# ============================
class RequestPaymentSummary(Base, TimestampMixin, SortableMixin):
    __tablename__ = "request_payment_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    batch_no = Column(String(100), unique=True, nullable=False, comment="批量请款编号")
    order_ids = Column(Text, nullable=True, comment="订单编号(多个,逗号分隔)")
    request_date = Column(Date, nullable=False, comment="日期")
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True, comment="合同ID")
    contract_no = Column(String(100), nullable=True, comment="合同编号")
    project_name = Column(String(200), nullable=True, comment="工程名称")
    customer_name = Column(String(200), nullable=True, comment="客户名称")
    customer_id = Column(Integer, nullable=True, comment="客户ID")
    request_amount = Column(Numeric(12, 2), default=0, comment="请款金额")
    status = Column(String(20), default="待请款", comment="请款状态(待请款/部分请款/已请款)")

    details = relationship("RequestPaymentDetail", back_populates="summary", cascade="all, delete-orphan")


class RequestPaymentDetail(Base, TimestampMixin):
    __tablename__ = "request_payment_details"
    __table_args__ = (
        Index("idx_rpd_summary", "summary_id"),
        Index("idx_rpd_contract", "contract_id"),
        Index("idx_rpd_order", "order_id"),
        Index("idx_rpd_contract_status", "contract_id", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    summary_id = Column(Integer, ForeignKey("request_payment_summaries.id", ondelete="CASCADE"), nullable=False, comment="请款ID")
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, comment="订单ID")
    order_no = Column(String(100), nullable=True, comment="订单编号(单个)")
    request_date = Column(Date, nullable=False, comment="日期")
    contract_id = Column(Integer, nullable=True, comment="合同ID")
    contract_no = Column(String(100), nullable=True, comment="合同编号")
    project_name = Column(String(200), nullable=True, comment="工程名称")
    customer_name = Column(String(200), nullable=True, comment="客户名称")
    customer_id = Column(Integer, nullable=True, comment="客户ID")
    request_amount = Column(Numeric(12, 2), default=0, comment="请款金额")
    status = Column(String(20), default="待请款", comment="请款状态(待请款/部分请款/已请款)")

    summary = relationship("RequestPaymentSummary", back_populates="details")
    order = relationship("Order", back_populates="request_details")


# ============================
# 10. 收款管理
# ============================
class CollectionSummary(Base, TimestampMixin, SortableMixin):
    __tablename__ = "collection_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    batch_no = Column(String(100), unique=True, nullable=False, comment="批量收款编号")
    order_ids = Column(Text, nullable=True, comment="订单编号(多个,逗号分隔)")
    collection_date = Column(Date, nullable=False, comment="日期")
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True, comment="合同ID")
    contract_no = Column(String(100), nullable=True, comment="合同编号")
    project_name = Column(String(200), nullable=True, comment="工程名称")
    customer_name = Column(String(200), nullable=True, comment="客户名称")
    customer_id = Column(Integer, nullable=True, comment="客户ID")
    collection_amount = Column(Numeric(12, 2), default=0, comment="收款金额")
    actual_amount = Column(Numeric(12, 2), default=0, comment="实收金额")
    status = Column(String(20), default="待收款", comment="收款状态(待收款/已收款/部分收款)")

    details = relationship("CollectionDetail", back_populates="summary", cascade="all, delete-orphan")


class CollectionDetail(Base, TimestampMixin):
    __tablename__ = "collection_details"
    __table_args__ = (
        Index("idx_cd_summary", "summary_id"),
        Index("idx_cd_contract", "contract_id"),
        Index("idx_cd_order", "order_id"),
        Index("idx_cd_contract_status", "contract_id", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    summary_id = Column(Integer, ForeignKey("collection_summaries.id", ondelete="CASCADE"), nullable=False, comment="收款ID")
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, comment="订单ID")
    order_no = Column(String(100), nullable=True, comment="订单编号(单个)")
    collection_date = Column(Date, nullable=False, comment="日期")
    contract_id = Column(Integer, nullable=True, comment="合同ID")
    contract_no = Column(String(100), nullable=True, comment="合同编号")
    project_name = Column(String(200), nullable=True, comment="工程名称")
    customer_name = Column(String(200), nullable=True, comment="客户名称")
    customer_id = Column(Integer, nullable=True, comment="客户ID")
    collection_amount = Column(Numeric(12, 2), default=0, comment="收款金额")
    actual_amount = Column(Numeric(12, 2), default=0, comment="实收金额")
    status = Column(String(20), default="待收款", comment="收款状态")

    summary = relationship("CollectionSummary", back_populates="details")
    order = relationship("Order", back_populates="collection_details")


# ============================
# 11. 财务管理
# ============================
class Finance(Base, TimestampMixin, SortableMixin):
    __tablename__ = "finances"
    __table_args__ = (
        Index("idx_finance_date", "finance_date"),
        Index("idx_finance_contract", "contract_id"),
        Index("idx_finance_type", "income_expense_type"),
        Index("idx_finances_date_type", "finance_date", "income_expense_type"),
        Index("idx_finances_contract_type", "contract_id", "income_expense_type"),
        Index("idx_finances_dept_date", "department_id", "finance_date"),
        Index("idx_finances_company_date", "company_id", "finance_date"),
        Index("idx_finances_dept_type", "department_id", "income_expense_type"),
        Index("idx_finances_company_type", "company_id", "income_expense_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    finance_no = Column(String(100), unique=True, nullable=False, comment="财务编号")
    finance_date = Column(Date, nullable=False, comment="日期")
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True, comment="合同ID")
    contract_no = Column(String(100), nullable=True, comment="合同编号")
    category = Column(String(100), nullable=False, comment="款项类别")
    description = Column(Text, nullable=True, comment="内容描述")
    income_expense_type = Column(String(10), nullable=False, comment="收支类别(收入/支出)")
    amount = Column(Numeric(12, 2), default=0, comment="收支金额")
    company_name = Column(String(200), nullable=True, comment="公司名称")
    company_bank_account = Column(String(100), nullable=True, comment="公司银行账号")
    status = Column(String(20), default="未入账", comment="入账状态(未入账/已入账)")
    is_posted = Column(Boolean, default=False, comment="是否入账")
    invoice_no = Column(String(100), nullable=True, comment="发票号")
    attachment = Column(String(500), nullable=True, comment="附件")

    contract = relationship("Contract", back_populates="finance_records")

    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, comment="部门ID")
    department_name = Column(String(100), nullable=True, comment="部门名称")
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, comment="公司ID")


# ============================
# 用户 / 登录
# ============================
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    username = Column(String(100), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    role = Column(String(20), default="user", comment="角色(admin/user)")
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, comment="关联员工ID")
    is_active = Column(Boolean, default=True, comment="是否启用")

    employee = relationship("Employee")