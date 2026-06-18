"""
SQLite 性能优化迁移脚本
========================
为现有数据库添加复合索引、启用 WAL 模式、优化 PRAGMA 参数，
无需重建数据库，可重复执行（幂等）。

适用场景：现有数据库已包含数据，需要提升查询性能
执行方式：python -m app.migrations.optimize_sqlite
"""

import os
import sys
from pathlib import Path

# 确保能找到 backend 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text
from app.database import engine, SessionLocal, Base


# =============================================================================
# SQLite PRAGMA 优化
# =============================================================================
PRAGMAS = [
    # WAL 模式：读写不互斥，读时不阻塞写，写时不阻塞读
    ("journal_mode", "WAL"),
    # 同步级别 NORMAL：WAL 模式下安全性足够，性能远优于 FULL
    ("synchronous", "NORMAL"),
    # 缓存大小：设为 64MB（-64000 pages * 1024 bytes）
    ("cache_size", -64000),
    # 临时文件存内存
    ("temp_store", "MEMORY"),
    # 内存映射 I/O：减少系统调用  (128MB)
    ("mmap_size", 134217728),
    # 每页字节数：默认 4096，可改 8192 减少 IO
    # ("page_size", 8192),  # 需要在创建数据库时设置，已有数据库不可改
    # 外键约束
    ("foreign_keys", "ON"),
]


def set_pragmas():
    """设置 SQLite PRAGMA 参数（每次连接时应用）"""
    with engine.connect() as conn:
        for name, value in PRAGMAS:
            conn.execute(text(f"PRAGMA {name} = {value}"))
        conn.commit()
    print("[✓] PRAGMA 参数已设置")


# =============================================================================
# 复合索引定义
# =============================================================================
# 格式： (表名, 索引名, [列名列表], 是否唯一)
# 设计原则：最左前缀匹配，高频筛选放左边
INDEXES = [
    # ==================== 订单 orders ====================
    # 按部门+状态：部门营收统计最频繁的查询
    ("orders", "idx_orders_dept_status", ["department_id", "status"]),
    # 按公司+状态：公司营收统计
    ("orders", "idx_orders_company_status", ["company_id", "status"]),
    # 按合同+状态：合同详情页展示关联订单
    ("orders", "idx_orders_contract_status", ["contract_id", "status"]),
    # 按客户+状态：客户营收页
    ("orders", "idx_orders_customer_status", ["customer_id", "status"]),
    # 按日期+状态：日期范围+状态筛选查询
    ("orders", "idx_orders_date_status", ["order_date", "status"]),
    # 按部门+未收款：应收款汇总 key 查询
    ("orders", "idx_orders_dept_uncollected", ["department_id", "is_collected"]),
    # 按公司+未收款：公司应收款汇总
    ("orders", "idx_orders_company_uncollected", ["company_id", "is_collected"]),
    # 按部门+日期：部门营收统计按时间聚合
    ("orders", "idx_orders_dept_date", ["department_id", "order_date"]),
    # 按公司+日期：公司营收统计按时间聚合
    ("orders", "idx_orders_company_date", ["company_id", "order_date"]),

    # ==================== 合同 contracts ====================
    ("contracts", "idx_contracts_dept_status", ["department_id", "status"]),
    ("contracts", "idx_contracts_company_status", ["company_id", "status"]),
    ("contracts", "idx_contracts_customer_status", ["customer_id", "status"]),
    ("contracts", "idx_contracts_project_status", ["project_id", "status"]),
    ("contracts", "idx_contracts_date_status", ["contract_date", "status"]),

    # ==================== 财务 finances ====================
    ("finances", "idx_finances_date_type", ["finance_date", "income_expense_type"]),
    ("finances", "idx_finances_contract_type", ["contract_id", "income_expense_type"]),
    ("finances", "idx_finances_dept_date", ["department_id", "finance_date"]),
    ("finances", "idx_finances_company_date", ["company_id", "finance_date"]),
    ("finances", "idx_finances_dept_type", ["department_id", "income_expense_type"]),
    ("finances", "idx_finances_company_type", ["company_id", "income_expense_type"]),

    # ==================== 请款明细 request_payment_details ====================
    ("request_payment_details", "idx_rpd_contract", ["contract_id"]),
    ("request_payment_details", "idx_rpd_order", ["order_id"]),
    ("request_payment_details", "idx_rpd_contract_status", ["contract_id", "status"]),

    # ==================== 收款明细 collection_details ====================
    ("collection_details", "idx_cd_contract", ["contract_id"]),
    ("collection_details", "idx_cd_order", ["order_id"]),
    ("collection_details", "idx_cd_contract_status", ["contract_id", "status"]),

    # ==================== 营收统计（已有单索引，加复合索引） ====================
    # 公司营收：按公司+日期查询日报
    ("company_revenues", "idx_comp_rev_comp_date", ["company_id", "rev_date"]),
    # 部门营收：已有 idx_dept_rev_dept + idx_dept_rev_date，加复合实现部门+日期快速定位
    ("department_revenues", "idx_dept_rev_dept_date", ["department_id", "rev_date"]),
    # 客户营收：按客户+日期
    ("customer_revenues", "idx_cust_rev_cust_date", ["customer_id", "rev_date"]),
    # 项目营收：按项目+日期
    ("project_revenues", "idx_proj_rev_proj_date", ["project_id", "rev_date"]),

    # ==================== 员工绩效 employee_performances ====================
    ("employee_performances", "idx_perf_emp_date", ["employee_id", "perf_date"]),

    # ==================== 员工工资 employee_salaries ====================
    ("employee_salaries", "idx_sal_emp_month", ["employee_id", "salary_month"]),
]


def get_existing_indexes():
    """获取数据库中已存在的所有索引名"""
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        ))
        return {row[0] for row in result}


def add_indexes():
    """添加复合索引（跳过多余索引）"""
    existing = get_existing_indexes()
    created = 0
    skipped = 0

    for table, index_name, columns in INDEXES:
        if index_name in existing:
            skipped += 1
            continue

        col_list = ", ".join(columns)
        sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({col_list})"

        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()

        created += 1
        print(f"  [+] {index_name} ON {table} ({col_list})")

    return created, skipped


# =============================================================================
# 分析数据库（更新查询计划统计信息）
# =============================================================================
def analyze_db():
    """运行 ANALYZE 更新 SQLite 查询计划统计信息"""
    with engine.connect() as conn:
        conn.execute(text("ANALYZE"))
        conn.commit()
    print("[✓] ANALYZE 完成，查询计划已优化")


# =============================================================================
# 主入口
# =============================================================================
def main():
    print("=" * 60)
    print("  SQLite 性能优化")
    print("=" * 60)

    # 步骤 1：PRAGMA 优化
    print("\n[1/3] 设置 PRAGMA 参数...")
    set_pragmas()

    # 步骤 2：添加复合索引
    print("\n[2/3] 添加复合索引...")
    created, skipped = add_indexes()
    print(f"  新增: {created} 个索引, 跳过(已存在): {skipped} 个")

    # 步骤 3：分析数据库
    print("\n[3/3] 分析数据库统计信息...")
    analyze_db()

    # 汇总
    total = len(INDEXES)
    print(f"\n{'=' * 60}")
    print(f"  优化完成！总计 {total} 个索引目标")
    print(f"  新增: {created}, 已有: {skipped}")
    print(f"  WAL模式: ✓ 开启")
    print(f"  缓存大小: 64MB")
    print(f"  同步模式: NORMAL")
    print(f"{'=' * 60}")

    # 打印现有索引清单供验证
    print("\n当前数据库所有索引：")
    existing = get_existing_indexes()
    for idx in sorted(existing):
        print(f"  - {idx}")


if __name__ == "__main__":
    main()