import React from 'react';
import { Tag, Form, Input, Select, DatePicker, InputNumber } from 'antd';
import CrudTable, { MiniCrudTable, renderDetail, FilterConfig } from '../components/CrudTable';

const colors: Record<string, string> = {
  '已收款': 'green', '已请款': 'green',
  '执行中': 'blue', '待请款': 'blue', '待收款': 'blue',
  '未完成': 'orange', '待签订': 'orange', '暂停': 'orange', '部分收款': 'orange', '部分请款': 'orange',
  '已驳回': 'red', '已终止': 'red', '已取消': 'red',
};

const fmt = (v: number | string) => `¥${(Number(v) || 0).toFixed(2)}`;
const dateFmt = (v: string) => (v ? new Date(v).toLocaleDateString('zh-CN') : '');
const statusTag = (v: string) => <Tag color={colors[v] || 'default'}>{v}</Tag>;

const columns = [
  { title: '批量收款编号', dataIndex: 'batch_no', key: 'batch_no' },
  { title: '日期', dataIndex: 'collection_date', key: 'collection_date', render: dateFmt },
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  { title: '工程名称', dataIndex: 'project_name', key: 'project_name' },
  { title: '客户名称', dataIndex: 'customer_name', key: 'customer_name' },
  { title: '收款金额¥', dataIndex: 'collection_amount', key: 'collection_amount', render: fmt },
  { title: '实收金额¥', dataIndex: 'actual_amount', key: 'actual_amount', render: fmt },
  { title: '状态', dataIndex: 'status', key: 'status', render: statusTag },
];

// 收款明细子表列
const detailColumns = [
  { title: '订单编号', dataIndex: 'order_no', key: 'order_no' },
  { title: '日期', dataIndex: 'collection_date', key: 'collection_date', render: dateFmt },
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  { title: '工程名称', dataIndex: 'project_name', key: 'project_name' },
  { title: '客户名称', dataIndex: 'customer_name', key: 'customer_name' },
  { title: '收款金额¥', dataIndex: 'collection_amount', key: 'collection_amount', render: fmt },
  { title: '实收金额¥', dataIndex: 'actual_amount', key: 'actual_amount', render: fmt },
  { title: '状态', dataIndex: 'status', key: 'status', render: statusTag },
];

// ─── 筛选配置 ────────────────────────────────────────────────────────────────
const filterConfigs: FilterConfig[] = [
  {
    field: 'status',
    label: '状态',
    placeholder: '收款状态',
    options: [
      { label: '待收款', value: '待收款' },
      { label: '部分收款', value: '部分收款' },
      { label: '已收款', value: '已收款' },
    ],
  },
];

// ─── 表单字段 ────────────────────────────────────────────────────────────────
const formFields = (
  <>
    <Form.Item name="batch_no" label="批量收款编号" rules={[{ required: true, message: '请输入批量收款编号' }]}>
      <Input placeholder="请输入批量收款编号" />
    </Form.Item>
    <Form.Item name="collection_date" label="日期" rules={[{ required: true, message: '请选择日期' }]}>
      <DatePicker style={{ width: '100%' }} placeholder="请选择日期" />
    </Form.Item>
    <Form.Item name="contract_no" label="合同编号">
      <Input placeholder="请输入合同编号" />
    </Form.Item>
    <Form.Item name="project_name" label="工程名称">
      <Input placeholder="请输入工程名称" />
    </Form.Item>
    <Form.Item name="customer_name" label="客户名称">
      <Input placeholder="请输入客户名称" />
    </Form.Item>
    <Form.Item name="collection_amount" label="收款金额">
      <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入收款金额" />
    </Form.Item>
    <Form.Item name="actual_amount" label="实收金额">
      <InputNumber style={{ width: '100%' }} prefix="¥" placeholder="请输入实收金额" />
    </Form.Item>
    <Form.Item name="status" label="状态" initialValue="待收款">
      <Select placeholder="请选择状态">
        <Select.Option value="待收款">待收款</Select.Option>
        <Select.Option value="已收款">已收款</Select.Option>
        <Select.Option value="部分收款">部分收款</Select.Option>
      </Select>
    </Form.Item>
  </>
);

// ─── 扩展行渲染 ──────────────────────────────────────────────────────────────
const expandedRowRender = (record: any) => {
  const parentId = record.id;
  return (
    <div style={{ padding: '12px 12px 0 12px', background: '#fafafa' }}>
      <MiniCrudTable
        endpoint={`/collections/${parentId}/details`}
        columns={detailColumns}
        title="收款明细"
      />
    </div>
  );
};

const CollectionList: React.FC = () => {
  return (
    <CrudTable
      apiEndpoint="/collections/"
      columns={columns}
      title="收款管理"
      formFields={formFields}
      rowKey="id"
      statusOptions={[
        { label: '待收款', value: '待收款' },
        { label: '已收款', value: '已收款' },
        { label: '部分收款', value: '部分收款' },
      ]}
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

export default CollectionList;