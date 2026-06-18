import React, { useState, useEffect, useCallback } from 'react';
import { Card, Row, Col, Statistic, Tag, Form, Input, Select, DatePicker, InputNumber, Tabs } from 'antd';
import { DollarOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import CrudTable, { MiniCrudTable, renderDetail, FilterConfig } from '../components/CrudTable';
import SearchableSelect from '../components/SearchableSelect';
import api from '../utils/api';

const colors: Record<string, string> = {
  '已完成': 'green', '已批准': 'green', '已收款': 'green', '收入': 'green',
  '执行中': 'blue', '待请款': 'blue', '待收款': 'blue',
  '未完成': 'orange', '待签订': 'orange', '暂停': 'orange', '部分收款': 'orange',
  '已驳回': 'red', '已终止': 'red', '已取消': 'red', '支出': 'red',
};

const fmt = (v: number | string) => `¥${(Number(v) || 0).toFixed(2)}`;
const dateFmt = (v: string) => (v ? new Date(v).toLocaleDateString('zh-CN') : '');
const boolTag = (v: string) => {
  const isPosted = v === '已入账';
  return <Tag color={isPosted ? 'green' : 'orange'}>{isPosted ? '✓ 已入账' : '○ 未入账'}</Tag>;
};

const columns = [
  { title: '财务编号', dataIndex: 'finance_no', key: 'finance_no' },
  { title: '日期', dataIndex: 'finance_date', key: 'finance_date', render: dateFmt },
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  { title: '款项类别', dataIndex: 'category', key: 'category' },
  { title: '内容描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '收支类别', dataIndex: 'income_expense_type', key: 'income_expense_type', render: (v: string) => <Tag color={colors[v] || 'default'}>{v}</Tag> },
  { title: '收支金额¥', dataIndex: 'amount', key: 'amount', render: fmt },
  { title: '公司名称', dataIndex: 'company_name', key: 'company_name' },
  { title: '银行账号', dataIndex: 'company_bank_account', key: 'company_bank_account' },
  { title: '入账状态', dataIndex: 'status', key: 'status', render: boolTag },
  { title: '发票号', dataIndex: 'invoice_no', key: 'invoice_no' },
];

// ─── 子表列定义 ──────────────────────────────────────────────────────────────
const contractColumns = [
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  { title: '日期', dataIndex: 'contract_date', key: 'contract_date', render: dateFmt },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={colors[v] || 'default'}>{v}</Tag> },
  { title: '应收金额', dataIndex: 'receivable_amount', key: 'receivable_amount', render: fmt },
  { title: '收款金额', dataIndex: 'collection_amount', key: 'collection_amount', render: fmt },
];

const orderColumns = [
  { title: '订单编号', dataIndex: 'order_no', key: 'order_no' },
  { title: '日期', dataIndex: 'order_date', key: 'order_date', render: dateFmt },
  { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={colors[v] || 'default'}>{v}</Tag> },
  { title: '工程名称', dataIndex: 'project_name', key: 'project_name' },
  { title: '合计金额', dataIndex: 'biz_total_amount', key: 'biz_total_amount', render: fmt },
];

// ─── 筛选配置 ────────────────────────────────────────────────────────────────
const filterConfigs: FilterConfig[] = [
  {
    field: 'income_expense_type',
    label: '收支类别',
    placeholder: '收支类别',
    options: [
      { label: '收入', value: '收入' },
      { label: '支出', value: '支出' },
    ],
  },
  {
    field: 'status',
    label: '入账状态',
    placeholder: '入账状态',
    options: [
      { label: '已入账', value: '已入账' },
      { label: '未入账', value: '未入账' },
    ],
  },
];

const FinanceList: React.FC = () => {
  const [summary, setSummary] = useState({ income: 0, expense: 0 });
  const [refreshKey, setRefreshKey] = useState(0);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await api.get('/finances/', { params: { page_size: 10000 } });
      const items = res.items ?? res.results ?? [];
      const income = items.filter((r: any) => r.income_expense_type === '收入').reduce((s: number, r: any) => s + (r.amount || 0), 0);
      const expense = items.filter((r: any) => r.income_expense_type === '支出').reduce((s: number, r: any) => s + (r.amount || 0), 0);
      setSummary({ income, expense });
    } catch { /* silently fail */ }
  }, []);

  useEffect(() => { fetchSummary(); }, [fetchSummary, refreshKey]);

  // ─── 扩展行渲染（子表） ──────────────────────────────────────────────────
  const expandedRowRender = (record: any) => {
    const parentId = record.id;
    return (
      <div style={{ padding: '12px 12px 0 12px', background: '#fafafa' }}>
        <Tabs defaultActiveKey="contract" size="small" items={[
          {
            key: 'contract',
            label: '关联合同',
            children: <MiniCrudTable endpoint={`/finances/${parentId}/contract`} columns={contractColumns} title="关联合同" searchable={false} />,
          },
          {
            key: 'orders',
            label: '关联订单',
            children: <MiniCrudTable endpoint={`/finances/${parentId}/orders`} columns={orderColumns} title="关联订单" />,
          },
        ]} />
      </div>
    );
  };

  const formFields = (
    <>
      <Form.Item name="finance_no" label="财务编号" rules={[{ required: true, message: '请输入财务编号' }]}>
        <Input placeholder="请输入财务编号" />
      </Form.Item>
      <Form.Item name="finance_date" label="日期">
        <DatePicker style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item name="contract_id" label="合同">
        <SearchableSelect endpoint="/contracts/" placeholder="请选择合同" extraLabelKey="contract_no" allowClear allowManual={false} />
      </Form.Item>
      <Form.Item name="category" label="款项类别">
        <Select placeholder="请选择款项类别">
          <Select.Option value="检测费">检测费</Select.Option>
          <Select.Option value="测绘费">测绘费</Select.Option>
          <Select.Option value="勘察费">勘察费</Select.Option>
          <Select.Option value="办公费">办公费</Select.Option>
          <Select.Option value="人工费">人工费</Select.Option>
          <Select.Option value="设备费">设备费</Select.Option>
          <Select.Option value="其他">其他</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="description" label="内容描述">
        <Input placeholder="请输入内容描述" />
      </Form.Item>
      <Form.Item name="income_expense_type" label="收支类别" rules={[{ required: true, message: '请选择收支类别' }]}>
        <Select placeholder="请选择收支类别">
          <Select.Option value="收入">收入</Select.Option>
          <Select.Option value="支出">支出</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="amount" label="收支金额(¥)" rules={[{ required: true, message: '请输入收支金额' }]}>
        <InputNumber style={{ width: '100%' }} prefix="¥" />
      </Form.Item>
      <Form.Item name="company_id" label="公司">
        <SearchableSelect endpoint="/companies/" placeholder="请选择公司" allowClear allowManual={false} />
      </Form.Item>
      <Form.Item name="company_bank_account" label="银行账号">
        <Input placeholder="请输入银行账号" />
      </Form.Item>
      <Form.Item name="status" label="入账状态">
        <Select placeholder="请选择">
          <Select.Option value="已入账">已入账</Select.Option>
          <Select.Option value="未入账">未入账</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="invoice_no" label="发票号">
        <Input placeholder="请输入发票号" />
      </Form.Item>
      <Form.Item name="department_id" label="部门">
        <SearchableSelect endpoint="/departments/" placeholder="请选择部门" allowClear allowManual={false} />
      </Form.Item>
    </>
  );

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="总收入" value={summary.income} precision={2} prefix={<DollarOutlined />} suffix={<ArrowUpOutlined />} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="总支出" value={summary.expense} precision={2} prefix={<DollarOutlined />} suffix={<ArrowDownOutlined />} valueStyle={{ color: '#ff4d4f' }} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="净额" value={summary.income - summary.expense} precision={2} prefix={<DollarOutlined />} valueStyle={{ color: summary.income >= summary.expense ? '#52c41a' : '#ff4d4f' }} />
          </Card>
        </Col>
      </Row>
      <CrudTable
        key={refreshKey}
        apiEndpoint="/finances/"
        columns={columns}
        title="财务管理"
        formFields={formFields}
        rowKey="id"
        draggable={false}
        searchable importable exportable
        filters={filterConfigs}
        expandedRowRender={expandedRowRender}
        detailRender={(record) => renderDetail(record, columns)}
        onDataChange={() => setRefreshKey(k => k + 1)}
      />
    </div>
  );
};

export default FinanceList;
