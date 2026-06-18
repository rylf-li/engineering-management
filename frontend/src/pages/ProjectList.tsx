import React from 'react';
import { Tag, Tabs, Select, DatePicker, Input, Form, InputNumber } from 'antd';
import CrudTable, { MiniCrudTable, renderDetail, FilterConfig } from '../components/CrudTable';
import SearchableSelect from '../components/SearchableSelect';

/** 日期格式化 */
const fmtDate = (v: string | null | undefined) =>
  v ? new Date(v).toLocaleDateString('zh-CN') : '';

/** 金额格式化 */
const fmtYuan = (v: number | string | null | undefined) => `¥${(Number(v) || 0).toFixed(2)}`;

/** 状态颜色映射 */
const statusColors: Record<string, string> = {
  '已完成': 'green',
  '进行中': 'blue',
  '暂停': 'orange',
  '已取消': 'red',
};

// ─── 状态选项（批量操作使用） ──────────────────────────────────────────────────
const statusOptions = [
  { label: '进行中', value: '进行中' },
  { label: '已完成', value: '已完成' },
  { label: '暂停', value: '暂停' },
  { label: '已取消', value: '已取消' },
];

// ─── 主表列 ──────────────────────────────────────────────────────────────────
const columns: any[] = [
  { title: '项目编号', dataIndex: 'project_no', key: 'project_no' },
  {
    title: '日期', dataIndex: 'project_date', key: 'project_date',
    render: (v: string) => fmtDate(v),
  },
  { title: '项目名称', dataIndex: 'name', key: 'name' },
  {
    title: '项目状态', dataIndex: 'status', key: 'status',
    render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag>,
  },
];

// ─── 子表列定义 ──────────────────────────────────────────────────────────────
const contractColumns: any[] = [
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  {
    title: '日期', dataIndex: 'contract_date', key: 'contract_date',
    render: (v: string) => fmtDate(v),
  },
  { title: '名称', dataIndex: 'name', key: 'name' },
  {
    title: '合同金额', dataIndex: 'contract_amount', key: 'contract_amount',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '状态', dataIndex: 'status', key: 'status',
    render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag>,
  },
  {
    title: '应收金额', dataIndex: 'receivable_amount', key: 'receivable_amount',
    render: (v: number) => fmtYuan(v),
  },
];

const orderColumns: any[] = [
  { title: '订单编号', dataIndex: 'order_no', key: 'order_no' },
  {
    title: '日期', dataIndex: 'order_date', key: 'order_date',
    render: (v: string) => fmtDate(v),
  },
  {
    title: '状态', dataIndex: 'status', key: 'status',
    render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag>,
  },
  { title: '工程名称', dataIndex: 'project_name', key: 'project_name' },
  {
    title: '合计金额', dataIndex: 'biz_total_amount', key: 'biz_total_amount',
    render: (v: number) => fmtYuan(v),
  },
];

const financeColumns: any[] = [
  { title: '财务编号', dataIndex: 'finance_no', key: 'finance_no' },
  {
    title: '日期', dataIndex: 'finance_date', key: 'finance_date',
    render: (v: string) => fmtDate(v),
  },
  { title: '款项类别', dataIndex: 'category', key: 'category' },
  {
    title: '内容描述', dataIndex: 'description', key: 'description',
    ellipsis: true,
  },
  {
    title: '收支类别', dataIndex: 'income_expense_type', key: 'income_expense_type',
    render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag>,
  },
  {
    title: '金额', dataIndex: 'amount', key: 'amount',
    render: (v: number) => fmtYuan(v),
  },
];

// ─── 筛选配置 ────────────────────────────────────────────────────────────────
const filterConfigs: FilterConfig[] = [
  {
    field: 'status',
    label: '状态',
    placeholder: '项目状态',
    options: [
      { label: '进行中', value: '进行中' },
      { label: '已完成', value: '已完成' },
      { label: '暂停', value: '暂停' },
      { label: '已取消', value: '已取消' },
    ],
  },
];

// ─── 表单字段 ────────────────────────────────────────────────────────────────
const formFields = (
  <>
    <Form.Item
      name="project_no"
      label="项目编号"
      rules={[{ required: true, message: '请输入项目编号' }]}
    >
      <Input placeholder="请输入项目编号" />
    </Form.Item>
    <Form.Item name="project_date" label="日期">
      <DatePicker style={{ width: '100%' }} />
    </Form.Item>
    <Form.Item
      name="name"
      label="项目名称"
      rules={[{ required: true, message: '请输入项目名称' }]}
    >
      <Input placeholder="请输入项目名称" />
    </Form.Item>
    <Form.Item
      name="status"
      label="项目状态"
      rules={[{ required: true, message: '请选择项目状态' }]}
    >
      <Select placeholder="请选择项目状态">
        {statusOptions.map((opt) => (
          <Select.Option key={opt.value} value={opt.value}>
            {opt.label}
          </Select.Option>
        ))}
      </Select>
    </Form.Item>
  </>
);

// ─── 主页面 ──────────────────────────────────────────────────────────────────
const ProjectList: React.FC = () => {

  // ─── 子表表单字段 ──────────────────────────────────────────────────────────
  const contractFormFields = (
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
      <Form.Item name="contract_amount" label="合同金额(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入合同金额" />
      </Form.Item>
      <Form.Item name="status" label="状态">
        <Select placeholder="请选择状态">
          <Select.Option value="待签订">待签订</Select.Option>
          <Select.Option value="执行中">执行中</Select.Option>
          <Select.Option value="已完成">已完成</Select.Option>
          <Select.Option value="终止">终止</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="customer_id" label="客户">
        <SearchableSelect endpoint="/customers/" placeholder="请选择客户" allowClear allowManual={false} />
      </Form.Item>
      <Form.Item name="department_id" label="部门">
        <SearchableSelect endpoint="/departments/" placeholder="请选择部门" allowClear allowManual={false} />
      </Form.Item>
      <Form.Item name="company_id" label="公司">
        <SearchableSelect endpoint="/companies/" placeholder="请选择公司" allowClear allowManual={false} />
      </Form.Item>
      <Form.Item name="owner_name" label="负责人">
        <SearchableSelect endpoint="/employees/" placeholder="请选择负责人" labelKey="name" valueKey="name" allowClear />
      </Form.Item>
      <Form.Item name="sales_name" label="销售人员">
        <SearchableSelect endpoint="/employees/" placeholder="请选择销售人员" labelKey="name" valueKey="name" allowClear />
      </Form.Item>
      <Form.Item name="receivable_amount" label="应收金额(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入应收金额" />
      </Form.Item>
    </>
  );

  const orderFormFields = (
    <>
      <Form.Item name="order_no" label="订单编号" rules={[{ required: true, message: '请输入订单编号' }]}>
        <Input placeholder="请输入订单编号" />
      </Form.Item>
      <Form.Item name="order_date" label="日期">
        <DatePicker style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item name="status" label="状态">
        <Select placeholder="请选择状态">
          <Select.Option value="未完成">未完成</Select.Option>
          <Select.Option value="已完成">已完成</Select.Option>
          <Select.Option value="已取消">已取消</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="contract_id" label="合同">
        <SearchableSelect endpoint="/contracts/" placeholder="请选择合同" extraLabelKey="contract_no" allowClear allowManual={false} />
      </Form.Item>
      <Form.Item name="customer_id" label="客户">
        <SearchableSelect endpoint="/customers/" placeholder="请选择客户" allowClear allowManual={false} />
      </Form.Item>
      <Form.Item name="biz_category" label="业务类别">
        <Select placeholder="请选择业务类别">
          <Select.Option value="检测">检测</Select.Option>
          <Select.Option value="测绘">测绘</Select.Option>
          <Select.Option value="勘察">勘察</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="biz_unit" label="单位">
        <Input placeholder="请输入单位" />
      </Form.Item>
      <Form.Item name="biz_quantity" label="数量">
        <InputNumber style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item name="biz_unit_price" label="单价(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" />
      </Form.Item>
      <Form.Item name="biz_total_amount" label="合计金额(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" />
      </Form.Item>
      <Form.Item name="owner_name" label="负责人">
        <SearchableSelect endpoint="/employees/" placeholder="请选择负责人" labelKey="name" valueKey="name" allowClear />
      </Form.Item>
      <Form.Item name="department_id" label="部门">
        <SearchableSelect endpoint="/departments/" placeholder="请选择部门" allowClear allowManual={false} />
      </Form.Item>
      <Form.Item name="company_id" label="公司">
        <SearchableSelect endpoint="/companies/" placeholder="请选择公司" allowClear allowManual={false} />
      </Form.Item>
    </>
  );

  // ─── 扩展行渲染（Tabs + MiniCrudTable） ──────────────────────────────────────
  const expandedRowRender = (record: any) => {
    const parentId = record.id;
    return (
      <div style={{ padding: '12px 12px 0 12px', background: '#fafafa' }}>
        <Tabs
          defaultActiveKey="contracts"
          size="small"
          items={[
            {
              key: 'contracts',
              label: '合同明细',
              children: (
                <MiniCrudTable
                  endpoint={`/projects/${parentId}/contracts`}
                  columns={contractColumns}
                  title="合同明细"
                  formFields={contractFormFields}
                  searchable
                />
              ),
            },
            {
              key: 'orders',
              label: '订单明细',
              children: (
                <MiniCrudTable
                  endpoint={`/projects/${parentId}/orders`}
                  columns={orderColumns}
                  title="订单明细"
                  formFields={orderFormFields}
                  searchable
                />
              ),
            },
            {
              key: 'finances',
              label: '财务支出明细',
              children: (
                <MiniCrudTable
                  endpoint={`/projects/${parentId}/finances`}
                  columns={financeColumns}
                  title="财务支出明细"
                  searchable
                />
              ),
            },
          ]}
        />
      </div>
    );
  };

  return (
    <CrudTable
      apiEndpoint="/projects/"
      title="项目管理"
      columns={columns}
      formFields={formFields}
      rowKey="id"
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

export default ProjectList;