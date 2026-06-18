#!/usr/bin/env python3
"""初始化数据库 - 创建所有表"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import init_db, SessionLocal
from app.models import (
    User, Employee, Department, Company, BusinessService
)


def seed_demo_data():
    """填充演示数据"""
    db = SessionLocal()
    try:
        # 检查是否已有数据
        if db.query(Department).count() > 0:
            print("⚠️  数据库已有数据，跳过演示数据填充")
            return

        # 创建部门
        dept1 = Department(name="检测部", description="工程检测业务")
        dept2 = Department(name="测绘部", description="工程测绘业务")
        dept3 = Department(name="勘察部", description="工程勘察业务")
        dept4 = Department(name="财务部", description="财务管理")
        dept5 = Department(name="行政部", description="行政管理")
        db.add_all([dept1, dept2, dept3, dept4, dept5])
        db.flush()

        # 创建公司
        comp1 = Company(name="XX工程检测有限公司", tax_rate=0.06, address="XX市XX区XX路XX号", tax_number="91440101MA5XXXXXX")
        comp2 = Company(name="XX勘察设计有限公司", tax_rate=0.03, address="XX市XX区XX路XX号", tax_number="91440101MA5YYYYYY")
        db.add_all([comp1, comp2])
        db.flush()

        # 创建业务服务
        services = [
            BusinessService(category="检测", item_name="地基基础检测", unit="项", unit_price=50000),
            BusinessService(category="检测", item_name="主体结构检测", unit="项", unit_price=30000),
            BusinessService(category="检测", item_name="钢结构检测", unit="项", unit_price=40000),
            BusinessService(category="检测", item_name="材料检测", unit="组", unit_price=500),
            BusinessService(category="测绘", item_name="工程测量", unit="项", unit_price=20000),
            BusinessService(category="测绘", item_name="不动产测绘", unit="项", unit_price=35000),
            BusinessService(category="测绘", item_name="遥感测绘", unit="项", unit_price=25000),
            BusinessService(category="勘察", item_name="岩土工程勘察", unit="项", unit_price=80000),
            BusinessService(category="勘察", item_name="水文地质勘察", unit="项", unit_price=60000),
        ]
        db.add_all(services)
        db.flush()

        # 创建管理员用户（使用 hashlib 避免 bcrypt 兼容性问题）
        import hashlib
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        admin = User(username="admin", password_hash=password_hash, role="admin")
        db.add(admin)
        db.flush()

        print("✅ 演示数据填充完成")
        print(f"  - {db.query(Department).count()} 个部门")
        print(f"  - {db.query(Company).count()} 个公司")
        print(f"  - {db.query(BusinessService).count()} 个业务服务")
        print(f"  - 管理员账号: admin / admin123")

    except Exception as e:
        db.rollback()
        print(f"❌ 演示数据填充失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 初始化数据库...")
    init_db()
    print("✅ 数据库表创建完成")
    seed_demo_data()