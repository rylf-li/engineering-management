import React from 'react';
import { Tag, Input, InputNumber, Select, Form } from 'antd';
import CrudTable, { MiniCrudTable, renderDetail, FilterConfig } from '../components/CrudTable';
import SearchableSelect from '../components/SearchableSelect';

/** 金额格式化 */
const fmtYuan = (v: number | string | null | undefined) => `¥${(Number(v) || 0).toFixed(2)}`;

/** 日期格式化 */
const dateFmt = (v: string | null | undefined) =>
  v ? new Date(v).toLocaleDateString('zh-CN') : '';

/** 角色选项 */
const roleOptions = ['管理员', '业务员', '财务', '员工'];

/** 角色颜色映射 */
const roleColors: Record<string, string> = {
  '管理员': 'red',
  '业务员': 'blue',
  '财务': 'purple',
  '员工': 'green',
};

// ─── 主表列 ──────────────────────────────────────────────────────────────────
const columns: any[] = [
  { title: '员工名称', dataIndex: 'name', key: 'name' },
  { title: '手机号码', dataIndex: 'phone', key: 'phone' },
  {
    title: '角色', dataIndex: 'role', key: 'role',
    render: (v: string) => <Tag color={roleColors[v] || 'default'}>{v || '员工'}</Tag>,
  },
  {
    title: '月薪工资', dataIndex: 'monthly_salary', key: 'monthly_salary',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '社保费', dataIndex: 'social_insurance', key: 'social_insurance',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '状态', dataIndex: 'status', key: 'status',
    render: (v: string) => <Tag color={v === '正常' ? 'green' : 'red'}>{v || '正常'}</Tag>,
  },
];

// ─── 工资子表列 ──────────────────────────────────────────────────────────────
const salaryColumns: any[] = [
  { title: '月份', dataIndex: 'salary_month', key: 'salary_month' },
  { title: '月薪工资', dataIndex: 'monthly_salary', key: 'monthly_salary', render: (v: number) => fmtYuan(v) },
  { title: '报销费用', dataIndex: 'reimbursement', key: 'reimbursement', render: (v: number) => fmtYuan(v) },
  { title: '扣款', dataIndex: 'deduction', key: 'deduction', render: (v: number) => fmtYuan(v) },
  { title: '加油费', dataIndex: 'fuel_fee', key: 'fuel_fee', render: (v: number) => fmtYuan(v) },
  { title: '社保费', dataIndex: 'social_insurance', key: 'social_insurance', render: (v: number) => fmtYuan(v) },
  { title: '绩效', dataIndex: 'bonus', key: 'bonus', render: (v: number) => fmtYuan(v) },
  { title: '实发工资', dataIndex: 'actual_salary', key: 'actual_salary', render: (v: number) => fmtYuan(v) },
];

// ─── 绩效子表列 ─────────────────────────────────────────────────────────────
const performanceColumns: any[] = [
  { title: '日期', dataIndex: 'perf_date', key: 'perf_date', render: (v: string) => dateFmt(v) },
  { title: '绩效金额', dataIndex: 'perf_amount', key: 'perf_amount', render: (v: number) => fmtYuan(v) },
  { title: '未完成订单', dataIndex: 'orders_unfinished', key: 'orders_unfinished' },
  { title: '已完成订单', dataIndex: 'orders_finished', key: 'orders_finished' },
  { title: '应收金额', dataIndex: 'receivable_amount', key: 'receivable_amount', render: (v: number) => fmtYuan(v) },
  { title: '请款金额', dataIndex: 'request_amount', key: 'request_amount', render: (v: number) => fmtYuan(v) },
  { title: '收款金额', dataIndex: 'collection_amount', key: 'collection_amount', render: (v: number) => fmtYuan(v) },
  { title: '未请款金额', dataIndex: 'unrequested_amount', key: 'unrequested_amount', render: (v: number) => fmtYuan(v) },
  { title: '支出', dataIndex: 'expenditure', key: 'expenditure', render: (v: number) => fmtYuan(v) },
  { title: '利润', dataIndex: 'profit', key: 'profit', render: (v: number) => fmtYuan(v) },
];

// ─── 筛选配置 ────────────────────────────────────────────────────────────────
const filterConfigs: FilterConfig[] = [
  {
    field: 'role',
    label: '角色',
    placeholder: '角色',
    options: [
      { label: '管理员', value: '管理员' },
      { label: '业务员', value: '业务员' },
      { label: '财务', value: '财务' },
      { label: '员工', value: '员工' },
    ],
  },
  {
    field: 'status',
    label: '状态',
    placeholder: '员工状态',
    options: [
      { label: '正常', value: '正常' },
      { label: '停用', value: '停用' },
    ],
  },
];

// ─── 表单字段 ────────────────────────────────────────────────────────────────
const formFields = (
  <>
    <Form.Item name="name" label="员工名称" rules={[{ required: true, message: '请输入员工名称' }]}>
      <Input placeholder="请输入员工名称" />
    </Form.Item>
    <Form.Item name="phone" label="手机号码">
      <Input placeholder="请输入手机号码" />
    </Form.Item>
    <Form.Item name="monthly_salary" label="月薪工资">
      <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入月薪工资" />
    </Form.Item>
    <Form.Item name="social_insurance" label="社保费">
      <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入社保费" />
    </Form.Item>
    <Form.Item name="role" label="角色" initialValue="员工">
      <Select placeholder="请选择角色">
        {roleOptions.map(r => <Select.Option key={r} value={r}>{r}</Select.Option>)}
      </Select>
    </Form.Item>
    <Form.Item name="status" label="状态" initialValue="正常">
      <Select placeholder="请选择状态">
        <Select.Option value="正常">正常</Select.Option>
        <Select.Option value="停用">停用</Select.Option>
      </Select>
    </Form.Item>
    <Form.Item name="department_id" label="所属部门">
      <SearchableSelect endpoint="/departments/" placeholder="请选择部门（可选）" allowClear allowManual={false} />
    </Form.Item>
  </>
);

// ─── 主页面 ──────────────────────────────────────────────────────────────────
const EmployeeList: React.FC = () => {
  const rowKey = 'id';

  // 扩展行渲染（两个子表）
  const expandedRowRender = (record: any) => {
    const parentId = record[rowKey];
    return (
      <div style={{ padding: 0 }}>
        <MiniCrudTable
          endpoint={`/employees/${parentId}/salaries`}
          columns={salaryColumns}
          title="工资管理"
        />
        <MiniCrudTable
          endpoint={`/employees/${parentId}/performances`}
          columns={performanceColumns}
          title="绩效管理"
        />
      </div>
    );
  };

  return (
    <CrudTable
      apiEndpoint="/employees/"
      title="员工管理"
      columns={columns}
      formFields={formFields}
      rowKey={rowKey}
      searchable
      importable
      exportable
      draggable
      filters={filterConfigs}
      expandedRowRender={expandedRowRender}
      detailRender={(record) => renderDetail(record, columns)}
    />
  );
};

export default EmployeeList;