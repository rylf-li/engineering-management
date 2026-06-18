import React from 'react';
import { Tag, Input, Form } from 'antd';
import CrudTable, { MiniCrudTable, renderDetail } from '../components/CrudTable';

/** 金额格式化 */
const fmtYuan = (v: number | string | null | undefined) => `¥${(Number(v) || 0).toFixed(2)}`;

/** 日期格式化 */
const fmtDate = (v: string | null | undefined) =>
  v ? new Date(v).toLocaleDateString('zh-CN') : '';

// ─── 主表列 ──────────────────────────────────────────────────────────────────
const columns = [
  { title: '部门名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
];

// ─── 子表：部门营收统计 ──────────────────────────────────────────────────────
const revenueColumns = [
  { title: '公司名称', dataIndex: 'company_name', key: 'company_name' },
  {
    title: '日期', dataIndex: 'rev_date', key: 'rev_date',
    render: (v: string) => fmtDate(v),
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
    title: '支出', dataIndex: 'expenditure', key: 'expenditure',
    render: (v: number) => fmtYuan(v),
  },
  {
    title: '利润', dataIndex: 'profit', key: 'profit',
    render: (v: number) => fmtYuan(v),
  },
];

// ─── 表单字段 ────────────────────────────────────────────────────────────────
const formFields = (
  <>
    <Form.Item name="name" label="部门名称" rules={[{ required: true, message: '请输入部门名称' }]}>
      <Input placeholder="请输入部门名称" />
    </Form.Item>
    <Form.Item name="description" label="描述">
      <Input.TextArea rows={3} placeholder="请输入描述" />
    </Form.Item>
  </>
);

// ─── 扩展行渲染 ──────────────────────────────────────────────────────────────
const expandedRowRender = (record: any) => {
  const parentId = record.id;
  return (
    <div style={{ padding: '12px 12px 0 12px', background: '#fafafa' }}>
      <MiniCrudTable
        endpoint={`/departments/${parentId}/revenues`}
        columns={revenueColumns}
        title="部门营收统计"
        searchable
      />
    </div>
  );
};

const DepartmentList: React.FC = () => {
  return (
    <CrudTable
      apiEndpoint="/departments/"
      columns={columns}
      title="部门管理"
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

export default DepartmentList;