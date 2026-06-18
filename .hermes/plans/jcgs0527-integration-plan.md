# 工程检测管理系统 — jcgs0527 完整整合执行计划

## 现状总结
- ✅ 后端数据模型（11 个主表 + 所有子表）— **95% 已完成**
- ✅ 后端 CRUD API（通用 CRUDBase + 5个路由文件）
- ✅ 后端报表 API（日报/季报/年报/项目合同报表）
- ✅ 前端 13 个页面 + CrudTable 组件 + 路由
- ❌ 状态枚举值需对齐参考项目
- ❌ Dashboard 需重写（指标卡片+业务流面板+进度条）
- ❌ Reports 需重写（切换标签+聚合面板）
- ❌ 前端页面的列字段/子表需与参考项目对齐
- ❌ 种子数据需重写为参考项目风格
- ❌ UI 主题色需改为绿色

## Phase 1: 后端微调（30分钟）
### 1a. 状态枚举值对齐
| 模块 | 当前值 | 参考项目值 |
|------|--------|-----------|
| Contract | 待签订/进行中/已完成 | 待签订/执行中/已完成/终止 |
| Order | 待处理/进行中/已完成 | 未完成/已完成/已取消 |
| Request | 待审批/已批准/已驳回 | 待请款/部分请款/已请款 |
| Collection | 待收款/已收款/部分收款 | 待收款/部分收款/已收款 |
| Finance is_posted | boolean | 未入账/已入账 (string) |
| Employee | is_active boolean | 正常/停用 (string) |
| Customer | 无 status | 正常/停用 (string) |

### 1b. 新增字段
- Employee: status（正常/停用）
- Customer: status（正常/停用）
- Finance: status（未入账/已入账）替换 is_posted boolean
- Employee: 增加 `order_count`, `contract_count`（从订单/合同汇总）

### 1c. 字段名对齐
- Contract: `responsible_person` → `owner_name`, `sales_person` → `sales_name`

## Phase 2: 种子数据重写（30分钟）
参照 jcgs0527 的种子数据结构：
- 2 家公司：江西城工检测有限公司、江西城工测绘勘察有限公司
- 3 个部门：检测部、测绘部、勘察部
- 3 名员工：张工(检测部)、李工(测绘部)、王经理(业务员)
- 3 个客户：华城地产集团、赣江新区城投、星河置业
- 3 个项目：华城云庭三期、赣江新区道路测绘、星河广场岩土勘察
- 3 个合同 + 4 个订单 + 请款/收款/财务记录

## Phase 3: UI 主题重写（2小时）
### 3a. App.tsx 改造
- 侧边栏深绿色（#123b35）
- 品牌标识 "JC" 徽标（#f6c85f 黄色）+ "工程服务管理·检测·测绘·勘察"
- 顶部栏绿色主题
- 活跃导航项左侧黄色指示条（inset 3px 0 #f6c85f）

### 3b. Dashboard 重写
- 4 个指标卡片：项目数量、合同数量、应收金额、实收金额
- 核心业务流面板（含完成率进度条）
- 今日收支快照表格

### 3c. Reports 重写
- 4 个标签切换：日报表、季度报表、年度报表、项目合同报表
- 指标卡片 + 财务收支详情表 + 公司收支统计表 + 部门收支统计表
- 项目合同报表：项目/合同总数 + 应收/已收金额汇总

## Phase 4: 前端页面字段对齐（3小时）
### 4a. 批量更新所有页面列定义
- EmployeeList: 状态→正常/停用，增加工资/绩效子表(Tabs展开)
- DepartmentList: 增加营收统计子表
- CompanyList: 增加银行账号 + 营收统计 + 合同/订单/财务子表(Tabs)
- CustomerList: 增加营收统计 + 项目/合同/订单子表(Tabs)
- ProjectList: 增加营收统计 + 合同/订单/财务子表(Tabs)
- ContractList: 增加订单 + 财务 + 请款明细 + 收款明细子表(Tabs)
- BusinessServiceList: 保持基本 CRUD
- OrderList: 增加请款明细 + 收款明细子表
- RequestPaymentList: 汇总+明细双层(Tabs)
- CollectionList: 汇总+明细双层(Tabs)
- FinanceList: 保持基本 CRUD

### 4b. CrudTable 增强
- expandedRowRender 支持多子表(Tabs)
- 状态枚举值可从 columns 配置中获取
- 金额格式化 ¥ 前缀

## Phase 5: 构建 & 验证（30分钟）
- 前端构建 npm run build
- 后端删除旧 DB + 重新初始化种子数据
- 启动验证所有页面
- API 端点格式一致性检查