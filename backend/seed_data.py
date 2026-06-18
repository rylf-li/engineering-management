"""
种子数据脚本 - 参考 jcgs0527 项目数据模型
"""
import sys, os, hashlib
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, init_db
from app.models import (
    Employee, Department, Company, CompanyBankAccount, Customer,
    BusinessService, Project, Contract, Order,
    RequestPaymentSummary, RequestPaymentDetail,
    CollectionSummary, CollectionDetail,
    Finance, EmployeeSalary, EmployeePerformance,
)
from decimal import Decimal
from datetime import date, datetime

TODAY = date.today()


def seed():
    init_db()
    db = SessionLocal()
    try:
        # ===== 公司 =====
        co_map = {}
        for name, rate, addr, tax in [
            ("江西城工检测有限公司", Decimal("0.06"), "江西省南昌市红谷滩新区检测大道168号", "91360125MA35DETECT"),
            ("江西城工测绘勘察有限公司", Decimal("0.03"), "江西省南昌市青山湖区勘察路88号", "91360111MA35SURVEY"),
        ]:
            c = db.query(Company).filter(Company.name == name).first()
            if not c:
                c = Company(name=name, tax_rate=rate, address=addr, tax_number=tax)
                db.add(c); db.flush()
            co_map[name] = c.id

        COM1, COM2 = co_map["江西城工检测有限公司"], co_map["江西城工测绘勘察有限公司"]

        for cid, cname, acct, bank in [
            (COM1, "江西城工检测有限公司", "6222 8801 0001 2356", "工商银行南昌红谷滩支行"),
            (COM2, "江西城工测绘勘察有限公司", "6222 8802 0002 7788", "建设银行南昌青山湖支行"),
        ]:
            if not db.query(CompanyBankAccount).filter(CompanyBankAccount.company_id == cid).first():
                db.add(CompanyBankAccount(company_id=cid, company_name=cname, account_type="基本户", bank_account=acct, bank_name=bank))

        # ===== 部门 =====
        dept_map = {}
        for name, desc in [
            ("检测部", "主体结构检测、材料见证取样、地基基础检测"),
            ("测绘部", "工程竣工测绘、控制点复核、地形图测绘"),
            ("勘察部", "岩土工程勘察、钻探、报告编制"),
        ]:
            d = db.query(Department).filter(Department.name == name).first()
            if not d:
                d = Department(name=name, description=desc); db.add(d); db.flush()
            dept_map[name] = d.id

        D1, D2, D3 = dept_map["检测部"], dept_map["测绘部"], dept_map["勘察部"]

        # ===== 员工 =====
        emp_map = {}
        for name, phone, did, salary in [
            ("张工", "13800138001", D1, Decimal("8000")),
            ("李工", "13800138002", D2, Decimal("6500")),
            ("王经理", "13800138003", D1, Decimal("8000")),
        ]:
            e = db.query(Employee).filter(Employee.phone == phone).first()
            if not e:
                e = Employee(name=name, phone=phone,
                    password_hash=hashlib.md5(("pwd_"+name).encode()).hexdigest(),
                    monthly_salary=salary, social_insurance=Decimal("1200"),
                    department_id=did, status="正常", is_active=True)
                db.add(e); db.flush()
            emp_map[name] = e.id

        EZ, EL, EW = emp_map["张工"], emp_map["李工"], emp_map["王经理"]

        # 设置角色
        db.query(Employee).filter(Employee.id == EZ).update({"role": "业务员"})
        db.query(Employee).filter(Employee.id == EL).update({"role": "员工"})
        db.query(Employee).filter(Employee.id == EW).update({"role": "管理员"})

        # ===== 客户 =====
        cust_map = {}
        for name, addr, contact in [
            ("华城地产集团", "江西省南昌市西湖区华城路100号", "赵总"),
            ("赣江新区城投", "江西省赣江新区直管区城投大厦", "李部长"),
            ("星河置业有限公司", "江西省九江市濂溪区星河路50号", "钱经理"),
        ]:
            c = db.query(Customer).filter(Customer.name == name).first()
            if not c:
                c = Customer(name=name, address=addr, contact_person=contact, status="正常")
                db.add(c); db.flush()
            cust_map[name] = c.id

        CH, GJ, XH = cust_map["华城地产集团"], cust_map["赣江新区城投"], cust_map["星河置业有限公司"]

        # ===== 项目 =====
        proj_map = {}
        for no, dt, name, st, cid in [
            ("XM-2026-001", TODAY, "华城云庭三期检测项目", "进行中", CH),
            ("XM-2026-002", TODAY, "赣江新区道路测绘项目", "进行中", GJ),
            ("XM-2026-003", date(2026,4,28), "星河广场岩土勘察项目", "已完成", XH),
        ]:
            p = db.query(Project).filter(Project.project_no == no).first()
            if not p:
                p = Project(project_no=no, project_date=dt, name=name, status=st)
                db.add(p); db.flush()
            proj_map[name] = p.id

        PH, PG, PX = proj_map["华城云庭三期检测项目"], proj_map["赣江新区道路测绘项目"], proj_map["星河广场岩土勘察项目"]

        # ===== 业务服务 =====
        biz_map = {}
        for cat, item, param, price, unit, settle, perf in [
            ("检测", "主体结构回弹检测", "构件", Decimal("360"), "组", Decimal("120"), Decimal("35")),
            ("检测", "材料见证取样", "批次", Decimal("220"), "批", Decimal("60"), Decimal("20")),
            ("测绘", "竣工测绘", "面积", Decimal("1.8"), "平方米", Decimal("0.45"), Decimal("0.12")),
            ("勘察", "岩土钻探", "孔深", Decimal("180"), "米", Decimal("70"), Decimal("12")),
        ]:
            b = db.query(BusinessService).filter(BusinessService.category==cat, BusinessService.item_name==item).first()
            if not b:
                b = BusinessService(category=cat, item_name=item, parameters=param, unit_price=price, unit=unit, settlement_fee=settle, performance_fee=perf)
                db.add(b); db.flush()
            biz_map[item] = b.id

        BH, BC, BJ, BZ = biz_map["主体结构回弹检测"], biz_map["材料见证取样"], biz_map["竣工测绘"], biz_map["岩土钻探"]

        # ===== 合同 =====
        def add_contract(cno, cdt, cname, cst, pid, content, cid, cname_str, com_id, com_name, did, dname, oid, oname, sid, sname, other, bizfee):
            c = db.query(Contract).filter(Contract.contract_no == cno).first()
            if not c:
                c = Contract(contract_no=cno, contract_date=cdt, name=cname, status=cst,
                    service_content=content, project_id=pid, customer_id=cid, customer_name=cname_str,
                    company_id=com_id, company_name=com_name, department_id=did, department_name=dname,
                    owner_name=oname, sales_name=sname, other_fee=other, business_fee=bizfee)
                db.add(c); db.flush()
            return c.id

        C1 = add_contract("HT-2026-0501", TODAY, "华城云庭三期主体检测合同", "执行中",
            PH, "主体结构检测、材料见证取样", CH, "华城地产集团", COM1, "江西城工检测有限公司", D1, "检测部",
            EZ, "张工", EW, "王经理", Decimal("0"), Decimal("1200"))
        C2 = add_contract("HT-2026-0502", TODAY, "赣江新区道路测绘合同", "执行中",
            PG, "道路竣工测绘、控制点复核", GJ, "赣江新区城投", COM2, "江西城工测绘勘察有限公司", D2, "测绘部",
            EL, "李工", EW, "王经理", Decimal("0"), Decimal("800"))
        C3 = add_contract("HT-2026-0428", date(2026,4,28), "星河广场岩土勘察合同", "已完成",
            PX, "详勘、钻探、报告编制", XH, "星河置业有限公司", COM2, "江西城工测绘勘察有限公司", D3, "勘察部",
            EZ, "张工", EW, "王经理", Decimal("500"), Decimal("1000"))

        # ===== 订单 =====
        def add_order(ono, ost, odate, cid, cno, pname, cuid, cuname, bid, bcat, bpar, bunit, qty, uprice, total, settle, perfee, repdate, repno, signoff, attach, oid, oname, sid, sname, did, dname, comid, comname):
            o = db.query(Order).filter(Order.order_no == ono).first()
            if not o:
                o = Order(order_no=ono, status=ost, order_date=odate,
                    contract_id=cid, contract_no=cno, project_name=pname,
                    customer_id=cuid, customer_name=cuname,
                    biz_category=bcat, biz_parameters=bpar, biz_unit=bunit,
                    biz_quantity=qty, biz_unit_price=uprice, biz_total_amount=total,
                    settlement_fee=settle, performance_fee=perfee,
                    report_date=repdate if repdate else None, report_no=repno,
                    report_signoff=signoff, report_attachment=attach,
                    owner_name=oname, sales_name=sname,
                    department_id=did, department_name=dname,
                    company_id=comid, company_name=comname)
                db.add(o); db.flush()
            return o.id

        O1 = add_order("DD-2026-0501", "未完成", TODAY, C1, "HT-2026-0501",
            "华城云庭三期 1#楼主体检测", CH, "华城地产集团", BH, "检测", "构件", "组",
            Decimal("18"), Decimal("360"), Decimal("6480"), Decimal("2160"), Decimal("630"),
            None, "", "未签收", "", EZ, "张工", EW, "王经理", D1, "检测部", COM1, "江西城工检测有限公司")
        O2 = add_order("DD-2026-0502", "未完成", TODAY, C1, "HT-2026-0501",
            "华城云庭三期材料见证取样", CH, "华城地产集团", BC, "检测", "批次", "批",
            Decimal("24"), Decimal("220"), Decimal("5280"), Decimal("1440"), Decimal("480"),
            None, "", "未签收", "", EZ, "张工", EW, "王经理", D1, "检测部", COM1, "江西城工检测有限公司")
        O3 = add_order("DD-2026-0503", "未完成", TODAY, C2, "HT-2026-0502",
            "赣江新区道路竣工测绘", GJ, "赣江新区城投", BJ, "测绘", "面积", "平方米",
            Decimal("18600"), Decimal("1.8"), Decimal("33480"), Decimal("8370"), Decimal("2232"),
            None, "", "未签收", "", EL, "李工", EW, "王经理", D2, "测绘部", COM2, "江西城工测绘勘察有限公司")
        O4 = add_order("DD-2026-0428", "已完成", date(2026,4,28), C3, "HT-2026-0428",
            "星河广场岩土钻探", XH, "星河置业有限公司", BZ, "勘察", "孔深", "米",
            Decimal("320"), Decimal("180"), Decimal("57600"), Decimal("22400"), Decimal("3840"),
            date(2026,5,20), "BG-KC-2026-0428", "已签收", "勘察报告.pdf",
            EZ, "张工", EW, "王经理", D3, "勘察部", COM2, "江西城工测绘勘察有限公司")

        # ===== 请款 =====
        def add_request(no, onos, rdate, cid, cno, pname, cuid, cuname, amt, st):
            s = db.query(RequestPaymentSummary).filter(RequestPaymentSummary.batch_no == no).first()
            if s: return s.id
            s = RequestPaymentSummary(batch_no=no, order_ids=onos, request_date=rdate,
                contract_id=cid, contract_no=cno, project_name=pname,
                customer_name=cuname, customer_id=cuid, request_amount=amt, status=st)
            db.add(s); db.flush()
            for ono in onos.split(","):
                o = db.query(Order).filter(Order.order_no == ono.strip()).first()
                if o:
                    db.add(RequestPaymentDetail(summary_id=s.id, order_id=o.id, order_no=ono.strip(),
                        request_date=rdate, contract_id=cid, contract_no=cno,
                        project_name=pname, customer_name=cuname, customer_id=cuid,
                        request_amount=o.biz_total_amount, status=st))
                    o.is_requested = True
            return s.id

        add_request("QK0001", "DD-2026-0428", date(2026,5,20), C3, "HT-2026-0428",
            "星河广场岩土钻探", XH, "星河置业有限公司", Decimal("57600"), "已请款")
        add_request("QK0002", "DD-2026-0501,DD-2026-0502", TODAY, C1, "HT-2026-0501",
            "多个工程", CH, "华城地产集团", Decimal("11760"), "已请款")

        # ===== 收款 =====
        def add_collection(no, onos, rdate, cid, cno, pname, cuid, cuname, amt, actual, st):
            s = db.query(CollectionSummary).filter(CollectionSummary.batch_no == no).first()
            if s: return s.id
            s = CollectionSummary(batch_no=no, order_ids=onos, collection_date=rdate,
                contract_id=cid, contract_no=cno, project_name=pname,
                customer_name=cuname, customer_id=cuid,
                collection_amount=amt, actual_amount=actual, status=st)
            db.add(s); db.flush()
            for ono in onos.split(","):
                o = db.query(Order).filter(Order.order_no == ono.strip()).first()
                if o:
                    db.add(CollectionDetail(summary_id=s.id, order_id=o.id, order_no=ono.strip(),
                        collection_date=rdate, contract_id=cid, contract_no=cno,
                        project_name=pname, customer_name=cuname, customer_id=cuid,
                        collection_amount=o.biz_total_amount, actual_amount=actual, status=st))
                    o.is_collected = True
            return s.id

        add_collection("SK0001", "DD-2026-0428", date(2026,5,22), C3, "HT-2026-0428",
            "星河广场岩土钻探", XH, "星河置业有限公司", Decimal("57600"), Decimal("57600"), "已收款")

        # ===== 财务 =====
        def add_finance(fno, fdate, cid, cno, cat, desc, ietype, amt, comid, comname, bank, st, inv, attach):
            f = db.query(Finance).filter(Finance.finance_no == fno).first()
            if f: return
            c = db.query(Contract).filter(Contract.id == cid).first()
            db.add(Finance(finance_no=fno, finance_date=fdate,
                contract_id=cid, contract_no=cno, category=cat, description=desc,
                income_expense_type=ietype, amount=amt,
                company_name=comname, company_bank_account=bank,
                status=st, is_posted=(st=="已入账"), invoice_no=inv, attachment=attach,
                department_id=c.department_id if c else None,
                department_name=c.department_name if c else None,
                company_id=comid))

        add_finance("CW-SK0001-DD-2026-0428", date(2026,5,22), C3, "HT-2026-0428",
            "勘察费", "星河广场岩土勘察收款", "收入", Decimal("57600"),
            COM2, "江西城工测绘勘察有限公司", "6222 8802 0002 7788", "已入账", "FP-2026-0501", "")
        add_finance("CW-ZC-2026-0501", TODAY, C1, "HT-2026-0501",
            "劳务费", "华城云庭检测外协劳务", "支出", Decimal("1800"),
            COM1, "江西城工检测有限公司", "6222 8801 0001 2356", "未入账", "", "")
        add_finance("CW-ZC-2026-0502", TODAY, C2, "HT-2026-0502",
            "差旅费", "赣江新区测绘交通差旅", "支出", Decimal("620"),
            COM2, "江西城工测绘勘察有限公司", "6222 8802 0002 7788", "已入账", "", "")
        add_finance("CW-ZC-2026-0428", date(2026,5,10), C3, "HT-2026-0428",
            "材料费", "星河广场勘察耗材", "支出", Decimal("4200"),
            COM2, "江西城工测绘勘察有限公司", "6222 8802 0002 7788", "已入账", "", "")

        db.commit()
        print("✅ 种子数据写入成功！")
        print(f"  部门:{db.query(Department).count()} 公司:{db.query(Company).count()} 员工:{db.query(Employee).count()} 客户:{db.query(Customer).count()}")
        print(f"  项目:{db.query(Project).count()} 合同:{db.query(Contract).count()} 订单:{db.query(Order).count()} 业务:{db.query(BusinessService).count()}")
        print(f"  请款:{db.query(RequestPaymentSummary).count()} 收款:{db.query(CollectionSummary).count()} 财务:{db.query(Finance).count()}")

    except Exception as e:
        db.rollback()
        print(f"❌ 种子数据写入失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()