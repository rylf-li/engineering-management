import React from 'react';
import { Input, InputNumber, Form, Tag, Tabs } from 'antd';
import CrudTable, { MiniCrudTable, renderDetail } from '../components/CrudTable';

/** 金额格式化 */
const fmtYuan = (v: number | string | null | undefined) => `¥${(Number(v) || 0).toFixed(2)}`;

/** 日期格式化 */
const dateFmt = (v: string | null | undefined) =>
  v ? new Date(v).toLocaleDateString('zh-CN') : '';

/** 状态颜色映射 */
const statusColors: Record<string, string> = {
  '已完成': 'green',
  '已批准': 'green',
  '已收款': 'green',
  '进行中': 'blue',
  '待请款': 'blue',
  '待收款': 'blue',
  '未完成': 'orange',
  '待签订': 'orange',
  '暂停': 'orange',
  '已驳回': 'red',
  '已终止': 'red',
  '已取消': 'red',
};

// ─── 主表列 ──────────────────────────────────────────────────────────────────
const columns: any[] = [
  { title: '公司名称', dataIndex: 'name', key: 'name' },
  {
    title: '税率', dataIndex: 'tax_rate', key: 'tax_rate',
    render: (v: number | string | null | undefined) => v != null ? `${(Number(v) * 100).toFixed(1)}%` : '-',
  },
  { title: '地址', dataIndex: 'address', key: 'address', ellipsis: true },
  { title: '税务号', dataIndex: 'tax_number', key: 'tax_number' },
];

// ─── 子表1：银行账号列 ──────────────────────────────────────────────────────
const bankAccountColumns: any[] = [
  { title: '账户类别', dataIndex: 'account_type', key: 'account_type' },
  { title: '银行账户', dataIndex: 'bank_account', key: 'bank_account' },
  { title: '开户行', dataIndex: 'bank_name', key: 'bank_name' },
];

// ─── 子表2：公司营收统计列 ──────────────────────────────────────────────────
const revenueColumns: any[] = [
  { title: '部门名称', dataIndex: 'department_name', key: 'department_name' },
  {
    title: '日期', dataIndex: 'rev_date', key: 'rev_date',
    render: (v: string) => dateFmt(v),
  },
  { title: '未完成订单', dataIndex: 'orders_unfinished', key: 'orders_unfinished' },
  { title: '已完成订单', dataIndex: 'orders_finished', key: 'orders_finished' },
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

// ─── 子表3：合同列 ──────────────────────────────────────────────────────────
const contractColumns: any[] = [
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  {
    title: '合同日期', dataIndex: 'contract_date', key: 'contract_date',
    render: (v: string) => dateFmt(v),
  },
  { title: '名称', dataIndex: 'name', key: 'name' },
  {
    title: '状态', dataIndex: 'status', key: 'status',
    render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag>,
  },
  { title: '客户名称', dataIndex: 'customer_name', key: 'customer_name' },
  {
    title: '应收金额（¥）', dataIndex: 'receivable_amount', key: 'receivable_amount',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '请款金额（¥）', dataIndex: 'request_amount', key: 'request_amount',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '收款金额（¥）', dataIndex: 'collection_amount', key: 'collection_amount',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '利润（¥）', dataIndex: 'profit', key: 'profit',
    render: (v: number) => fmtYuan(v),
  },
];

// ─── 子表4：订单列 ──────────────────────────────────────────────────────────
const orderColumns: any[] = [
  { title: '订单编号', dataIndex: 'order_no', key: 'order_no' },
  {
    title: '状态', dataIndex: 'status', key: 'status',
    render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag>,
  },
  {
    title: '订单日期', dataIndex: 'order_date', key: 'order_date',
    render: (v: string) => dateFmt(v),
  },
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  { title: '项目名称', dataIndex: 'project_name', key: 'project_name' },
  { title: '客户名称', dataIndex: 'customer_name', key: 'customer_name' },
  { title: '业务类别', dataIndex: 'biz_category', key: 'biz_category' },
  { title: '业务单位', dataIndex: 'biz_unit', key: 'biz_unit' },
  { title: '业务数量', dataIndex: 'biz_quantity', key: 'biz_quantity' },
  {
    title: '业务总额（¥）', dataIndex: 'biz_total_amount', key: 'biz_total_amount',
    render: (v: number) => fmtYuan(v),
  },
  { title: '负责人', dataIndex: 'owner_name', key: 'owner_name' },
  { title: '销售人员', dataIndex: 'sales_name', key: 'sales_name' },
  { title: '部门名称', dataIndex: 'department_name', key: 'department_name' },
];

// ─── 子表5：财务列 ──────────────────────────────────────────────────────────
const financeColumns: any[] = [
  { title: '财务编号', dataIndex: 'finance_no', key: 'finance_no' },
  {
    title: '财务日期', dataIndex: 'finance_date', key: 'finance_date',
    render: (v: string) => dateFmt(v),
  },
  { title: '款项类别', dataIndex: 'category', key: 'category' },
  { title: '内容描述', dataIndex: 'description', key: 'description', ellipsis: true },
  {
    title: '收支类别', dataIndex: 'income_expense_type', key: 'income_expense_type',
    render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag>,
  },
  {
    title: '金额（¥）', dataIndex: 'amount', key: 'amount',
    render: (v: number) => fmtYuan(v),
  },
  { title: '公司名称', dataIndex: 'company_name', key: 'company_name' },
  {
    title: '已入账', dataIndex: 'status', key: 'status',
    render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '是' : '否'}</Tag>,
  },
];

// ─── 表单字段 ────────────────────────────────────────────────────────────────
const formFields: React.ReactNode = (
  <>
    <Form.Item
      name="name"
      label="公司名称"
      rules={[{ required: true, message: '请输入公司名称' }]}
    >
      <Input placeholder="请输入公司名称" />
    </Form.Item>
    <Form.Item name="tax_rate" label="税率">
      <InputNumber style={{ width: '100%' }} suffix="%" placeholder="请输入税率（如 0.13）" />
    </Form.Item>
    <Form.Item name="address" label="地址">
      <Input placeholder="请输入地址" />
    </Form.Item>
    <Form.Item name="tax_number" label="税务号">
      <Input placeholder="请输入税务号" />
    </Form.Item>
  </>
);

// ─── 扩展行渲染 ──────────────────────────────────────────────────────────────
const expandedRowRender = (record: any) => {
  const parentId = record.id;
  return (
    <div style={{ padding: '12px 12px 0 12px', background: '#fafafa' }}>
      <Tabs
        defaultActiveKey="bank_accounts"
        size="small"
        items={[
          {
            key: 'bank_accounts',
            label: '银行账号',
            children: (
              <MiniCrudTable
                endpoint={`/companies/${parentId}/bank-accounts`}
                columns={bankAccountColumns}
                title="银行账号"
                searchable
              />
            ),
          },
          {
            key: 'revenues',
            label: '公司营收统计',
            children: (
              <MiniCrudTable
                endpoint={`/companies/${parentId}/revenues`}
                columns={revenueColumns}
                title="公司营收统计"
                searchable
              />
            ),
          },
          {
            key: 'contracts',
            label: '合同',
            children: (
              <MiniCrudTable
                endpoint={`/companies/${parentId}/contracts`}
                columns={contractColumns}
                title="合同"
                searchable
              />
            ),
          },
          {
            key: 'orders',
            label: '订单',
            children: (
              <MiniCrudTable
                endpoint={`/companies/${parentId}/orders`}
                columns={orderColumns}
                title="订单"
                searchable
              />
            ),
          },
          {
            key: 'finances',
            label: '财务',
            children: (
              <MiniCrudTable
                endpoint={`/companies/${parentId}/finances`}
                columns={financeColumns}
                title="财务"
                searchable
              />
            ),
          },
        ]}
      />
    </div>
  );
};

// ─── 主页面 ──────────────────────────────────────────────────────────────────
const CompanyList: React.FC = () => {
  return (
    <CrudTable
      apiEndpoint="/companies/"
      columns={columns}
      title="公司管理"
      formFields={formFields}
      rowKey="id"
      searchable
      importable
      exportable
      draggable
      expandedRowRender={expandedRowRender}
      detailRender={(record) => renderDetail(record, columns)}
    />
  );
};

export default CompanyList;