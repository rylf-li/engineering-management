import React from 'react';
import { Tag, Tabs, Input, Select, Form } from 'antd';
import CrudTable, { MiniCrudTable, renderDetail, FilterConfig } from '../components/CrudTable';

/** 金额格式化 */
const fmtYuan = (v: number | string | null | undefined) => `¥${(Number(v) || 0).toFixed(2)}`;

/** 日期格式化 */
const fmtDate = (v: string | null | undefined) =>
  v ? new Date(v).toLocaleDateString('zh-CN') : '';

/** 状态颜色映射 */
const statusColors: Record<string, string> = {
  '已完成': 'green',
  '已批准': 'green',
  '已收款': 'green',
  '进行中': 'blue',
  '待审批': 'blue',
  '待收款': 'blue',
  '待处理': 'orange',
  '待签订': 'orange',
  '暂停': 'orange',
  '已驳回': 'red',
  '已终止': 'red',
  '已取消': 'red',
};

// ─── 主表列 ──────────────────────────────────────────────────────────────────
const columns = [
  { title: '客户名称', dataIndex: 'name', key: 'name' },
  { title: '客户地址', dataIndex: 'address', key: 'address', ellipsis: true },
  { title: '联系人', dataIndex: 'contact_person', key: 'contact_person' },
];

// ─── 筛选配置 ────────────────────────────────────────────────────────────────
const filterConfigs: FilterConfig[] = [
  {
    field: 'status',
    label: '状态',
    placeholder: '客户状态',
    options: [
      { label: '正常', value: '正常' },
      { label: '停用', value: '停用' },
    ],
  },
];

// ─── 状态选项（批量操作使用）──────────────────────────────────────────────────
const statusOptions = [
  { label: '正常', value: '正常' },
  { label: '停用', value: '停用' },
];

// ─── 表单字段 ────────────────────────────────────────────────────────────────
const formFields = (
  <>
    <Form.Item name="name" label="客户名称" rules={[{ required: true, message: '请输入客户名称' }]}>
      <Input placeholder="请输入客户名称" />
    </Form.Item>
    <Form.Item name="address" label="客户地址">
      <Input placeholder="请输入客户地址" />
    </Form.Item>
    <Form.Item name="contact_person" label="联系人">
      <Input placeholder="请输入联系人" />
    </Form.Item>
    <Form.Item name="status" label="状态" initialValue="正常">
      <Select placeholder="请选择状态">
        <Select.Option value="正常">正常</Select.Option>
        <Select.Option value="停用">停用</Select.Option>
      </Select>
    </Form.Item>
  </>
);

// ─── 子表：客户营收统计 ──────────────────────────────────────────────────────
const revenueColumns = [
  {
    title: '日期', dataIndex: 'rev_date', key: 'rev_date',
    render: (v: string) => fmtDate(v),
  },
  { title: '未完成订单', dataIndex: 'orders_unfinished', key: 'orders_unfinished' },
  { title: '已完成订单', dataIndex: 'orders_finished', key: 'orders_finished' },
  { title: '未完成合同', dataIndex: 'contracts_unfinished', key: 'contracts_unfinished' },
  { title: '已完成合同', dataIndex: 'contracts_finished', key: 'contracts_finished' },
  {
    title: '应收金额', dataIndex: 'receivable_amount', key: 'receivable_amount',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '请款金额', dataIndex: 'request_amount', key: 'request_amount',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '收款金额', dataIndex: 'collection_amount', key: 'collection_amount',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '未请款金额', dataIndex: 'unrequested_amount', key: 'unrequested_amount',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '支出', dataIndex: 'expenditure', key: 'expenditure',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '利润', dataIndex: 'profit', key: 'profit',
    render: (v: number) => fmtYuan(v),
  },
];

// ─── 子表：项目明细 ──────────────────────────────────────────────────────────
const projectColumns: any[] = [
  { title: '项目编号', dataIndex: 'project_no', key: 'project_no' },
  {
    title: '项目日期', dataIndex: 'project_date', key: 'project_date',
    render: (v: string) => fmtDate(v),
  },
  { title: '项目名称', dataIndex: 'name', key: 'name' },
  {
    title: '状态', dataIndex: 'status', key: 'status',
    render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag>,
  },
  {
    title: '应收金额', dataIndex: 'receivable_amount', key: 'receivable_amount',
    render: (v: number) => fmtYuan(v),
  },
];

// ─── 子表：合同明细 ──────────────────────────────────────────────────────────
const contractColumns: any[] = [
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  {
    title: '合同日期', dataIndex: 'contract_date', key: 'contract_date',
    render: (v: string) => fmtDate(v),
  },
  { title: '合同名称', dataIndex: 'name', key: 'name' },
  {
    title: '状态', dataIndex: 'status', key: 'status',
    render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag>,
  },
  { title: '客户名称', dataIndex: 'customer_name', key: 'customer_name' },
  {
    title: '应收金额', dataIndex: 'receivable_amount', key: 'receivable_amount',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '请款金额', dataIndex: 'request_amount', key: 'request_amount',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '收款金额', dataIndex: 'collection_amount', key: 'collection_amount',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '利润', dataIndex: 'profit', key: 'profit',
    render: (v: number) => fmtYuan(v),
  },
];

// ─── 子表：订单明细 ──────────────────────────────────────────────────────────
const orderColumns: any[] = [
  { title: '订单编号', dataIndex: 'order_no', key: 'order_no' },
  {
    title: '状态', dataIndex: 'status', key: 'status',
    render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag>,
  },
  {
    title: '订单日期', dataIndex: 'order_date', key: 'order_date',
    render: (v: string) => fmtDate(v),
  },
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  { title: '项目名称', dataIndex: 'project_name', key: 'project_name' },
  { title: '客户名称', dataIndex: 'customer_name', key: 'customer_name' },
  { title: '业务类别', dataIndex: 'biz_category', key: 'biz_category' },
  { title: '业务单位', dataIndex: 'biz_unit', key: 'biz_unit' },
  { title: '业务数量', dataIndex: 'biz_quantity', key: 'biz_quantity' },
  {
    title: '业务合计金额', dataIndex: 'biz_total_amount', key: 'biz_total_amount',
    render: (v: number) => fmtYuan(v),
  },
  { title: '负责人', dataIndex: 'owner_name', key: 'owner_name' },
  { title: '销售人员', dataIndex: 'sales_name', key: 'sales_name' },
];

// ─── 扩展行渲染 ──────────────────────────────────────────────────────────────
const expandedRowRender = (record: any) => {
  const parentId = record.id;
  return (
    <div style={{ padding: '12px 12px 0 12px', background: '#fafafa' }}>
      <Tabs
        defaultActiveKey="revenues"
        size="small"
        items={[
          {
            key: 'revenues',
            label: '客户营收统计',
            children: (
              <MiniCrudTable
                endpoint={`/customers/${parentId}/revenues`}
                columns={revenueColumns}
                title="客户营收统计"
              />
            ),
          },
          {
            key: 'projects',
            label: '项目明细',
            children: (
              <MiniCrudTable
                endpoint={`/customers/${parentId}/projects`}
                columns={projectColumns}
                title="项目明细"
              />
            ),
          },
          {
            key: 'contracts',
            label: '合同明细',
            children: (
              <MiniCrudTable
                endpoint={`/customers/${parentId}/contracts`}
                columns={contractColumns}
                title="合同明细"
              />
            ),
          },
          {
            key: 'orders',
            label: '订单明细',
            children: (
              <MiniCrudTable
                endpoint={`/customers/${parentId}/orders`}
                columns={orderColumns}
                title="订单明细"
              />
            ),
          },
        ]}
      />
    </div>
  );
};

// ─── 主页面 ──────────────────────────────────────────────────────────────────
const CustomerList: React.FC = () => {
  return (
    <CrudTable
      apiEndpoint="/customers/"
      columns={columns}
      title="客户管理"
      formFields={formFields}
      statusOptions={statusOptions}
      statusField="status"
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

export default CustomerList;