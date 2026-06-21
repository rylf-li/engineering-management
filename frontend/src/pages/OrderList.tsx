import React, { useState } from 'react';
import { Modal, Form, Input, Select, DatePicker, InputNumber, Tag, Tabs, message } from 'antd';
import { DollarOutlined, BankOutlined } from '@ant-design/icons';
import CrudTable, { MiniCrudTable, renderDetail, FilterConfig } from '../components/CrudTable';
import SearchableSelect from '../components/SearchableSelect';
import api from '../utils/api';

const colors: Record<string, string> = {
  '已完成': 'green', '已批准': 'green', '已收款': 'green',
  '进行中': 'blue', '待审批': 'blue', '待收款': 'blue',
  '待处理': 'orange', '待签订': 'orange', '暂停': 'orange', '部分收款': 'orange',
  '已驳回': 'red', '已终止': 'red', '已取消': 'red',
};

const fmt = (v: number | string) => `¥${(Number(v) || 0).toFixed(2)}`;
const dateFmt = (v: string) => (v ? new Date(v).toLocaleDateString('zh-CN') : '');
const boolTag = (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '是' : '否'}</Tag>;

const columns = [
  { title: '订单编号', dataIndex: 'order_no', key: 'order_no' },
  { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={colors[v] || 'default'}>{v}</Tag> },
  { title: '日期', dataIndex: 'order_date', key: 'order_date', render: dateFmt },
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  { title: '工程名称', dataIndex: 'project_name', key: 'project_name' },
  { title: '客户名称', dataIndex: 'customer_name', key: 'customer_name' },
  { title: '业务类别', dataIndex: 'biz_category', key: 'biz_category' },
  { title: '业务项目', dataIndex: 'biz_item_name', key: 'biz_item_name' },
  { title: '单位', dataIndex: 'biz_unit', key: 'biz_unit' },
  { title: '数量', dataIndex: 'biz_quantity', key: 'biz_quantity' },
  { title: '单价¥', dataIndex: 'biz_unit_price', key: 'biz_unit_price', render: fmt },
  { title: '合计金额¥', dataIndex: 'biz_total_amount', key: 'biz_total_amount', render: fmt },
  { title: '是否已请款', dataIndex: 'is_requested', key: 'is_requested', render: boolTag },
  { title: '是否已收款', dataIndex: 'is_collected', key: 'is_collected', render: boolTag },
  { title: '负责人', dataIndex: 'owner_name', key: 'owner_name' },
  { title: '业务员', dataIndex: 'sales_name', key: 'sales_name' },
  { title: '部门', dataIndex: 'department_name', key: 'department_name' },
];

// ─── 筛选配置 ────────────────────────────────────────────────────────────────
const filterConfigs: FilterConfig[] = [
  {
    field: 'status',
    label: '状态',
    placeholder: '订单状态',
    options: [
      { label: '未完成', value: '未完成' },
      { label: '已完成', value: '已完成' },
      { label: '已取消', value: '已取消' },
    ],
  },
];

// ─── 展开行子表列定义 ──────────────────────────────────────────────────────────
const requestPaymentColumns: any[] = [
  { title: '批次号', dataIndex: 'batch_no', key: 'batch_no' },
  { title: '请款日期', dataIndex: 'request_date', key: 'request_date', render: dateFmt },
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  { title: '工程名称', dataIndex: 'project_name', key: 'project_name' },
  { title: '客户名称', dataIndex: 'customer_name', key: 'customer_name' },
  { title: '请款金额', dataIndex: 'request_amount', key: 'request_amount', render: fmt },
  { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={colors[v] || 'default'}>{v}</Tag> },
];

const collectionColumns: any[] = [
  { title: '批次号', dataIndex: 'batch_no', key: 'batch_no' },
  { title: '收款日期', dataIndex: 'collection_date', key: 'collection_date', render: dateFmt },
  { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
  { title: '工程名称', dataIndex: 'project_name', key: 'project_name' },
  { title: '客户名称', dataIndex: 'customer_name', key: 'customer_name' },
  { title: '收款金额', dataIndex: 'collection_amount', key: 'collection_amount', render: fmt },
  { title: '实收金额', dataIndex: 'actual_amount', key: 'actual_amount', render: fmt },
  { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={colors[v] || 'default'}>{v}</Tag> },
];

const expandedRowRender = (record: any) => {
  const parentId = record.id;
  return (
    <div style={{ padding: '12px 12px 0 12px', background: '#fafafa' }}>
      <Tabs defaultActiveKey="request-payments" size="small" items={[
        { key: 'request-payments', label: '请款管理', children: <MiniCrudTable endpoint={`/orders/${parentId}/request-payments`} columns={requestPaymentColumns} title="请款管理" /> },
        { key: 'collections', label: '收款管理', children: <MiniCrudTable endpoint={`/orders/${parentId}/collections`} columns={collectionColumns} title="收款管理" /> },
      ]} />
    </div>
  );
};

const OrderList: React.FC = () => {
  const [refreshKey, setRefreshKey] = useState(0);
  const [batchModal, setBatchModal] = useState<{ visible: boolean; type: 'request' | 'collect'; selectedRowKeys: React.Key[]; selectedRows: any[] }>({ visible: false, type: 'request', selectedRowKeys: [], selectedRows: [] });
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleBatchOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      if (batchModal.type === 'request') {
        await api.post('/orders/batch-request', {
          order_ids: batchModal.selectedRowKeys,
          batch_no: values.batch_no,
          request_date: values.request_date?.format?.('YYYY-MM-DD') || values.request_date,
          contract_id: values.contract_id,
        });
        message.success('批量请款成功');
      } else {
        await api.post('/orders/batch-collect', {
          order_ids: batchModal.selectedRowKeys,
          batch_no: values.batch_no,
          collection_date: values.collection_date?.format?.('YYYY-MM-DD') || values.collection_date,
          contract_id: values.contract_id,
          collection_amount: values.collection_amount,
          actual_amount: values.actual_amount,
        });
        message.success('批量收款成功');
      }
      setBatchModal((prev) => ({ ...prev, visible: false }));
      form.resetFields();
      setRefreshKey((k) => k + 1);
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(err.message || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  const batchActions = [
    {
      key: 'batch-request', label: '批量请款', type: 'primary' as const, icon: <DollarOutlined />,
      showWhen: (rows: any[]) => rows.every((r) => !r.is_requested),
      handler: (keys: React.Key[], rows: any[]) => setBatchModal({ visible: true, type: 'request', selectedRowKeys: keys, selectedRows: rows }),
    },
    {
      key: 'batch-collect', label: '批量收款', type: 'primary' as const, icon: <BankOutlined />,
      showWhen: (rows: any[]) => rows.every((r) => !r.is_collected),
      handler: (keys: React.Key[], rows: any[]) => setBatchModal({ visible: true, type: 'collect', selectedRowKeys: keys, selectedRows: rows }),
    },
  ];

  const formFields = (
    <>
      <Form.Item name="order_no" label="订单编号" rules={[{ required: true, message: '请输入订单编号' }]}>
        <Input placeholder="请输入订单编号" />
      </Form.Item>
      <Form.Item name="status" label="状态" rules={[{ required: true, message: '请选择状态' }]}>
        <Select placeholder="请选择状态">
          <Select.Option value="未完成">未完成</Select.Option>
          <Select.Option value="已完成">已完成</Select.Option>
          <Select.Option value="已取消">已取消</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="order_date" label="日期">
        <DatePicker style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item name="contract_id" label="合同">
        <SearchableSelect endpoint="/contracts/" placeholder="请选择合同" extraLabelKey="contract_no" allowManual={false} />
      </Form.Item>
      <Form.Item name="customer_id" label="客户">
        <SearchableSelect endpoint="/customers/" placeholder="请选择客户" allowManual={false} />
      </Form.Item>
      <Form.Item name="biz_category" label="业务类别">
        <Select placeholder="请选择业务类别">
          <Select.Option value="检测">检测</Select.Option>
          <Select.Option value="测绘">测绘</Select.Option>
          <Select.Option value="勘察">勘察</Select.Option>
        </Select>
      </Form.Item>
      <Form.Item name="biz_item_name" label="业务项目">
        <SearchableSelect endpoint="/business-services/" placeholder="请选择业务项目" labelKey="item_name" valueKey="item_name" allowClear />
      </Form.Item>
      <Form.Item name="biz_parameters" label="业务参数">
        <Input placeholder="请输入业务参数" />
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
        <InputNumber style={{ width: '100%' }} prefix="¥" disabled />
      </Form.Item>
      <Form.Item name="report_date" label="报告日期">
        <DatePicker style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item name="report_no" label="报告编号">
        <Input placeholder="请输入报告编号" />
      </Form.Item>
      <Form.Item name="report_signoff" label="报告签收">
        <Input placeholder="请输入报告签收" />
      </Form.Item>
      <Form.Item name="report_attachment" label="报告附件">
        <Input placeholder="请输入报告附件路径" />
      </Form.Item>
      <Form.Item name="settlement_fee" label="结算费用(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" />
      </Form.Item>
      <Form.Item name="performance_fee" label="绩效费用(¥)">
        <InputNumber style={{ width: '100%' }} prefix="¥" />
      </Form.Item>
      <Form.Item name="company_id" label="公司">
        <SearchableSelect endpoint="/companies/" placeholder="请选择公司" allowClear allowManual={false} />
      </Form.Item>
      <Form.Item name="owner_name" label="负责人">
        <SearchableSelect endpoint="/employees/" placeholder="请选择负责人" labelKey="name" valueKey="name" allowClear />
      </Form.Item>
      <Form.Item name="sales_name" label="业务员">
        <SearchableSelect endpoint="/employees/" placeholder="请选择业务员" labelKey="name" valueKey="name" allowClear />
      </Form.Item>
      <Form.Item name="department_id" label="部门">
        <SearchableSelect endpoint="/departments/" placeholder="请选择部门" allowClear allowManual={false} />
      </Form.Item>
    </>
  );

  return (
    <>
      <CrudTable
        key={refreshKey}
        apiEndpoint="/orders/"
        columns={columns}
        title="订单管理"
        formFields={formFields}
        rowKey="id"
        statusOptions={[{ label: '未完成', value: '未完成' }, { label: '已完成', value: '已完成' }, { label: '已取消', value: '已取消' }]}
        statusField="status"
        batchActions={batchActions}
        expandedRowRender={expandedRowRender}
        detailRender={(record) => renderDetail(record, columns)}
        searchable importable exportable draggable
        filters={filterConfigs}
      />
      <Modal
        title={batchModal.type === 'request' ? '批量请款' : '批量收款'}
        open={batchModal.visible}
        onOk={handleBatchOk}
        confirmLoading={loading}
        onCancel={() => { setBatchModal((prev) => ({ ...prev, visible: false })); form.resetFields(); }}
        destroyOnHidden
        width={480}
      >
        {batchModal.visible && <Form form={form} layout="vertical">
          {batchModal.type === 'request' ? (
            <>
              <Form.Item name="batch_no" label="批量请款编号" rules={[{ required: true, message: '请输入批量请款编号' }]}>
                <Input placeholder="请输入批量请款编号" />
              </Form.Item>
              <Form.Item name="request_date" label="请款日期" rules={[{ required: true, message: '请选择请款日期' }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="contract_id" label="合同" rules={[{ required: true, message: '请选择合同' }]}>
                <SearchableSelect endpoint="/contracts/" placeholder="请选择合同" extraLabelKey="contract_no" allowManual={false} />
              </Form.Item>
            </>
          ) : (
            <>
              <Form.Item name="batch_no" label="批量收款编号" rules={[{ required: true, message: '请输入批量收款编号' }]}>
                <Input placeholder="请输入批量收款编号" />
              </Form.Item>
              <Form.Item name="collection_date" label="收款日期" rules={[{ required: true, message: '请选择收款日期' }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="contract_id" label="合同" rules={[{ required: true, message: '请选择合同' }]}>
                <SearchableSelect endpoint="/contracts/" placeholder="请选择合同" extraLabelKey="contract_no" allowManual={false} />
              </Form.Item>
              <Form.Item name="collection_amount" label="收款金额(¥)" rules={[{ required: true, message: '请输入收款金额' }]}>
                <InputNumber style={{ width: '100%' }} prefix="¥" />
              </Form.Item>
              <Form.Item name="actual_amount" label="实收金额(¥)" rules={[{ required: true, message: '请输入实收金额' }]}>
                <InputNumber style={{ width: '100%' }} prefix="¥" />
              </Form.Item>
            </>
          )}
        </Form>}
      </Modal>
    </>
  );
};

export default OrderList;
