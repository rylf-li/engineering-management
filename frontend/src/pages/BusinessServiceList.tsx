import React from 'react';
import { Tag, Form, Input, InputNumber, Select } from 'antd';
import CrudTable, { renderDetail, FilterConfig } from '../components/CrudTable';

const statusColors: Record<string, string> = {
  '检测': 'blue',
  '测绘': 'green',
  '勘察': 'orange',
};

const columns: any[] = [
  {
    title: '业务类别', dataIndex: 'category', key: 'category',
    render: (v: string) => <Tag color={statusColors[v] || 'default'}>{v}</Tag>,
  },
  { title: '业务项目', dataIndex: 'item_name', key: 'item_name' },
  { title: '业务参数', dataIndex: 'parameters', key: 'parameters' },
  {
    title: '业务单价', dataIndex: 'unit_price', key: 'unit_price',
    render: (v: number | string) => `¥${(Number(v) || 0).toFixed(2)}`,
  },
  { title: '业务单位', dataIndex: 'unit', key: 'unit' },
  {
    title: '业务结算费', dataIndex: 'settlement_fee', key: 'settlement_fee',
    render: (v: number | string) => `${(Number(v) || 0).toFixed(1)}%`,
  },
  {
    title: '业务绩效费', dataIndex: 'performance_fee', key: 'performance_fee',
    render: (v: number | string) => `${(Number(v) || 0).toFixed(1)}%`,
  },
];

const filterConfigs: FilterConfig[] = [
  {
    field: 'category',
    label: '业务类别',
    placeholder: '业务类别',
    options: [
      { label: '检测', value: '检测' },
      { label: '测绘', value: '测绘' },
      { label: '勘察', value: '勘察' },
    ],
  },
];

const formFields = (
  <>
    <Form.Item name="category" label="业务类别" rules={[{ required: true, message: '请选择业务类别' }]}>
      <Select placeholder="请选择业务类别">
        <Select.Option value="检测">检测</Select.Option>
        <Select.Option value="测绘">测绘</Select.Option>
        <Select.Option value="勘察">勘察</Select.Option>
      </Select>
    </Form.Item>
    <Form.Item name="item_name" label="业务项目" rules={[{ required: true, message: '请输入业务项目' }]}>
      <Input placeholder="请输入业务项目" />
    </Form.Item>
    <Form.Item name="parameters" label="业务参数">
      <Input placeholder="请输入业务参数" />
    </Form.Item>
    <Form.Item name="unit_price" label="业务单价">
      <InputNumber style={{ width: '100%' }} prefix="¥" />
    </Form.Item>
    <Form.Item name="unit" label="业务单位" rules={[{ required: true, message: '请输入业务单位' }]}>
      <Input placeholder="请输入业务单位" />
    </Form.Item>
    <Form.Item name="settlement_fee" label="业务结算费(%)">
      <InputNumber style={{ width: '100%' }} suffix="%" placeholder="请输入结算费率" />
    </Form.Item>
    <Form.Item name="performance_fee" label="业务绩效费(%)">
      <InputNumber style={{ width: '100%' }} suffix="%" placeholder="请输入绩效费率" />
    </Form.Item>
  </>
);

const BusinessServiceList: React.FC = () => {
  return (
    <CrudTable
      apiEndpoint="/business-services/"
      columns={columns}
      title="业务服务"
      formFields={formFields}
      draggable={false}
      searchable importable exportable
      filters={filterConfigs}
      detailRender={(record) => renderDetail(record, columns)}
    />
  );
};

export default BusinessServiceList;
