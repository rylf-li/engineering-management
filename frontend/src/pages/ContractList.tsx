import React, { useState, useEffect } from 'react';
import { Tag, Tabs, DatePicker, Input, Select, Form, InputNumber } from 'antd';
import CrudTable, { MiniCrudTable, renderDetail, FilterConfig } from '../components/CrudTable';
import api from '../utils/api';

/** 金额格式化 */
const fmtYuan = (v: number | string | null | undefined) => `¥${(Number(v) || 0).toFixed(2)}`;

/** 日期格式化 */
const fmtDate = (v: string | null | undefined) =>
  v ? new Date(v).toLocaleDateString('zh-CN') : '';

/** 状态颜色映射 */
const statusColors: Record<string, string> = {
  '已完成': 'green', '已批准': 'green', '已收款': 'green',
  '执行中': 'blue', '待请款': 'blue', '待收款': 'blue',
  '未完成': 'orange', '待签订': 'orange', '暂停': 'orange',
  '已驳回': 'red', '已终止': 'red', '已取消': 'red',
};

const statusOptions = [
  { label: '待签订', value: '待签订' },
  { label: '执行中', value: '执行中' },
  { label: '已完成', value: '已完成' },
  { label: '终止', value: '终止' },
];

// ─── 主表列 ────────────────────────────────────────────────────────────────────
const columns: any[] = [
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  { title: '日期', dataIndex: 'contract_date', key: 'contract_date', render: fmtDate },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag> },
  { title: '客户名称', dataIndex: 'customer_name', key: 'customer_name' },
  { title: '应收金额', dataIndex: 'receivable_amount', key: 'receivable_amount', render: fmtYuan },
  { title: '请款金额', dataIndex: 'request_amount', key: 'request_amount', render: fmtYuan },
  { title: '收款金额', dataIndex: 'collection_amount', key: 'collection_amount', render: fmtYuan },
  { title: '利润', dataIndex: 'profit', key: 'profit', render: fmtYuan },
  { title: '负责人', dataIndex: 'owner_name', key: 'owner_name' },
];

// ─── 筛选配置 ────────────────────────────────────────────────────────────────
const filterConfigs: FilterConfig[] = [
  {
    field: 'status',
    label: '状态',
    placeholder: '合同状态',
    options: [
      { label: '待签订', value: '待签订' },
      { label: '执行中', value: '执行中' },
      { label: '已完成', value: '已完成' },
      { label: '终止', value: '终止' },
    ],
  },
];

// ─── 子表列定义 ────────────────────────────────────────────────────────────────
const orderColumns: any[] = [
  { title: '订单编号', dataIndex: 'order_no', key: 'order_no' },
  { title: '日期', dataIndex: 'order_date', key: 'order_date', render: fmtDate },
  { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag> },
  { title: '工程名称', dataIndex: 'project_name', key: 'project_name' },
  { title: '合计金额', dataIndex: 'biz_total_amount', key: 'biz_total_amount', render: fmtYuan },
  { title: '已请款', dataIndex: 'is_requested', key: 'is_requested', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '是' : '否'}</Tag> },
  { title: '已收款', dataIndex: 'is_collected', key: 'is_collected', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '是' : '否'}</Tag> },
];

const financeColumns: any[] = [
  { title: '财务编号', dataIndex: 'finance_no', key: 'finance_no' },
  { title: '日期', dataIndex: 'finance_date', key: 'finance_date', render: fmtDate },
  { title: '款项类别', dataIndex: 'category', key: 'category' },
  { title: '内容描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '收支类别', dataIndex: 'income_expense_type', key: 'income_expense_type', render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag> },
  { title: '金额', dataIndex: 'amount', key: 'amount', render: fmtYuan },
  { title: '已入账', dataIndex: 'status', key: 'status', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '是' : '否'}</Tag> },
];

const requestPaymentColumns: any[] = [
  { title: '批次号', dataIndex: 'batch_no', key: 'batch_no' },
  { title: '请款日期', dataIndex: 'request_date', key: 'request_date', render: fmtDate },
  { title: '请款金额', dataIndex: 'request_amount', key: 'request_amount', render: fmtYuan },
  { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag> },
];

const collectionColumns: any[] = [
  { title: '批次号', dataIndex: 'batch_no', key: 'batch_no' },
  { title: '收款日期', dataIndex: 'collection_date', key: 'collection_date', render: fmtDate },
  { title: '收款金额', dataIndex: 'collection_amount', key: 'collection_amount', render: fmtYuan },
  { title: '实际金额', dataIndex: 'actual_amount', key: 'actual_amount', render: fmtYuan },
  { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag> },
];

// ─── 扩展行渲染 ────────────────────────────────────────────────────────────────
const expandedRowRender = (record: any) => {
  const parentId = record.id;
  return (
    <div style={{ padding: '12px 12px 0 12px', background: '#fafafa' }}>
      <Tabs
        defaultActiveKey="orders"
        size="small"
        items={[
          { key: 'orders', label: '订单明细', children: <MiniCrudTable endpoint={`/contracts/${parentId}/orders`} columns={orderColumns} title="订单明细" /> },
          { key: 'finances', label: '财务支出明细', children: <MiniCrudTable endpoint={`/contracts/${parentId}/finances`} columns={financeColumns} title="财务支出明细" /> },
          { key: 'request-payments', label: '请款管理', children: <MiniCrudTable endpoint={`/contracts/${parentId}/request-payments`} columns={requestPaymentColumns} title="请款管理" /> },
          { key: 'collections', label: '收款管理', children: <MiniCrudTable endpoint={`/contracts/${parentId}/collections`} columns={collectionColumns} title="收款管理" /> },
        ]}
      />
    </div>
  );
};

// ─── 主页面 ────────────────────────────────────────────────────────────────────
const ContractList: React.FC = () => {
  const [customers, setCustomers] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([
      api.get('/customers/', { params: { page_size: 100 } }).then(r => setCustomers(r.items ?? [])).catch(() => {}),
      api.get('/projects/', { params: { page_size: 100 } }).then(r => setProjects(r.items ?? [])).catch(() => {}),
      api.get('/departments/', { params: { page_size: 100 } }).then(r => setDepartments(r.items ?? [])).catch(() => {}),
      api.get('/companies/', { params: { page_size: 100 } }).then(r => setCompanies(r.items ?? [])).catch(() => {}),
      api.get('/employees/', { params: { page_size: 100 } }).then(r => setEmployees(r.items ?? [])).catch(() => {}),
    ]);
  }, []);

  const formFields = (
    <>
      <Form.Item name="contract_no" label="合同编号" rules={[{ required: true, message: '请输入合同编号' }]}>
        <Input placeholder="请输入合同编号" />
      </Form.Item>
      <Form.Item name="contract_date" label="日期">
        <DatePicker style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
        <Input placeholder="请输入名称" />
      </Form.Item>
      <Form.Item name="status" label="状态">
        <Select placeholder="请选择状态">
          {statusOptions.map((s: any) => <Select.Option key={s.value} value={s.value}>{s.label}</Select.Option>)}
        </Select>
      </Form.Item>
      <Form.Item name="service_content" label="服务内容">
        <Input.TextArea rows={3} placeholder="请输入服务内容" />
      </Form.Item>
      <Form.Item name="customer_id" label="客户">
        <Select placeholder="请选择客户" showSearch filterOption={(input, option) => (option?.children as any)?.toString().includes(input)}>
          {customers.map(c => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
        </Select>
      </Form.Item>
      <Form.Item name="project_id" label="项目">
        <Select placeholder="请选择项目" allowClear showSearch filterOption={(input, option) => (option?.children as any)?.toString().includes(input)}>
          {projects.map(p => <Select.Option key={p.id} value={p.id}>{p.name} ({p.project_no})</Select.Option>)}
        </Select>
      </Form.Item>
      <Form.Item name="department_id" label="部门">
        <Select placeholder="请选择部门" showSearch allowClear filterOption={(input, option) => (option?.children as any)?.toString().includes(input)}>
          {departments.map(d => <Select.Option key={d.id} value={d.id}>{d.name}</Select.Option>)}
        </Select>
      </Form.Item>
      <Form.Item name="company_id" label="公司">
        <Select placeholder="请选择公司" showSearch allowClear filterOption={(input, option) => (option?.children as any)?.toString().includes(input)}>
          {companies.map(c => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
        </Select>
      </Form.Item>
      <Form.Item name="owner_name" label="负责人">
        <Select placeholder="请选择负责人" showSearch allowClear filterOption={(input, option) => (option?.children as any)?.toString().includes(input)}>
          {employees.map(e => <Select.Option key={e.id} value={e.name}>{e.name}</Select.Option>)}
        </Select>
      </Form.Item>
      <Form.Item name="sales_name" label="销售人员">
        <Select placeholder="请选择销售人员" showSearch allowClear filterOption={(input, option) => (option?.children as any)?.toString().includes(input)}>
          {employees.map(e => <Select.Option key={e.id} value={e.name}>{e.name}</Select.Option>)}
        </Select>
      </Form.Item>
      <Form.Item name="receivable_amount" label="应收金额(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入应收金额" />
      </Form.Item>
      <Form.Item name="request_amount" label="请款金额(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入请款金额" />
      </Form.Item>
      <Form.Item name="collection_amount" label="收款金额(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入收款金额" />
      </Form.Item>
      <Form.Item name="profit" label="利润(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入利润" />
      </Form.Item>
      <Form.Item name="labor_cost" label="劳务费(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入劳务费" />
      </Form.Item>
      <Form.Item name="cost_amount" label="成本金额(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入成本金额" />
      </Form.Item>
      <Form.Item name="tax_fee" label="税费(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入税费" />
      </Form.Item>
      <Form.Item name="other_fee" label="其他费用(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入其他费用" />
      </Form.Item>
      <Form.Item name="business_fee" label="业务费(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入业务费" />
      </Form.Item>
      <Form.Item name="bonus" label="绩效(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入绩效" />
      </Form.Item>
    </>
  );

  return (
    <CrudTable
      apiEndpoint="/contracts/"
      columns={columns}
      title="合同管理"
      formFields={formFields}
      rowKey="id"
      statusOptions={statusOptions}
      statusField="status"
      searchable importable exportable draggable
      filters={filterConfigs}
      expandedRowRender={expandedRowRender}
      detailRender={(record) => renderDetail(record, columns)}
    />
  );
};

export default ContractList;