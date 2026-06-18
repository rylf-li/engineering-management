import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Table, Spin, Progress, Typography } from 'antd';
import api from '../utils/api';

const { Text } = Typography;

const fmt = (v: number) => `¥${(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`;
const dateFmt = (v: string) => (v ? new Date(v).toLocaleDateString('zh-CN') : '');

const $ = (res: any) => res?.items ?? res?.results ?? res?.data?.items ?? [];

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState({
    projects: { count: 0, done: 0, open: 0 } as any,
    contracts: { count: 0, done: 0, open: 0, pending: 0 } as any,
    orders: { count: 0, done: 0, open: 0 } as any,
    receivable: 0, unrequested: 0, receipt: 0, profit: 0,
    todayFinances: [] as any[],
    employees: { total: 0, admins: 0, business: 0, finance: 0, staff: 0 },
    departments: { total: 0 },
    customers: { total: 0 },
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [projRes, contrRes, orderRes, empRes, deptRes, custRes] = await Promise.all([
          api.get('/projects/').catch(() => ({ data: { items: [] } })),
          api.get('/contracts/').catch(() => ({ data: { items: [] } })),
          api.get('/orders/').catch(() => ({ data: { items: [] } })),
          api.get('/employees/', { params: { page: 1 } }).catch(() => ({ items: [] })),
          api.get('/departments/', { params: { page: 1 } }).catch(() => ({ items: [] })),
          api.get('/customers/', { params: { page: 1 } }).catch(() => ({ items: [] })),
        ]);
        const projects = $(projRes);
        const contracts = $(contrRes);
        const orders = $(orderRes);
        const employees = $(empRes);
        const departments = $(deptRes);
        const customers = $(custRes);

        const todayStr = new Date().toISOString().split('T')[0];
        let todayFinances: any[] = [];
        try {
          const finRes = await api.get('/finances/', { params: { page: 1, page_size: 100, sort_field: 'finance_date', sort_order: 'desc' } });
          todayFinances = ($(finRes)).filter((f: any) => (f.finance_date ? f.finance_date.substring(0, 10) : '') === todayStr);
        } catch { }

        const pCount = projects.length;
        const pDone = projects.filter((p: any) => p.status === '已完成').length;
        const pOpen = pCount - pDone;

        const cCount = contracts.length;
        const cDone = contracts.filter((c: any) => c.status === '已完成').length;
        const cPending = contracts.filter((c: any) => c.status === '待签订').length;
        const cOpen = cCount - cDone;

        const oCount = orders.length;
        const oDone = orders.filter((o: any) => o.status === '已完成').length;
        const oOpen = oCount - oDone;

        const receivable = contracts.reduce((s: number, c: any) => s + (c.receivable_amount || 0), 0);
        const receipt = contracts.reduce((s: number, c: any) => s + (c.collection_amount || 0), 0);
        const unrequested = contracts.reduce((s: number, c: any) => s + (c.unrequested_amount || 0), 0);
        const profit = contracts.reduce((s: number, c: any) => s + (c.profit || 0), 0);

        const admins = employees.filter((e: any) => e.role === '管理员').length;
        const business = employees.filter((e: any) => e.role === '业务员').length;
        const finance = employees.filter((e: any) => e.role === '财务').length;
        const staff = employees.filter((e: any) => e.role === '员工' || !e.role).length;

        setData({
          projects: { count: pCount, done: pDone, open: pOpen },
          contracts: { count: cCount, done: cDone, open: cOpen, pending: cPending },
          orders: { count: oCount, done: oDone, open: oOpen },
          receivable, unrequested, receipt, profit,
          todayFinances,
          employees: { total: employees.length, admins, business, finance, staff },
          departments: { total: departments.length },
          customers: { total: customers.length },
        });
      } catch (e) {
        console.error('Dashboard fetch failed:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;
  }

  const metrics = [
    { label: '项目数量', value: data.projects.count, hint: `${data.projects.done} 已完成 / ${data.projects.open} 未完成` },
    { label: '合同数量', value: data.contracts.count, hint: `${data.contracts.done} 已完成 / ${data.contracts.open} 未完成` },
    { label: '应收金额', value: fmt(data.receivable), hint: `未请款 ${fmt(data.unrequested)}` },
    { label: '实收金额', value: fmt(data.receipt), hint: `利润 ${fmt(data.profit)}` },
  ];

  const orgMetrics = [
    { label: '员工总数', value: data.employees.total, hint: `管理员 ${data.employees.admins} / 业务员 ${data.employees.business} / 财务 ${data.employees.finance} / 员工 ${data.employees.staff}` },
    { label: '部门数量', value: data.departments.total, hint: '' },
    { label: '客户数量', value: data.customers.total, hint: '' },
  ];

  const financeColumns = [
    { title: '日期', dataIndex: 'finance_date', key: 'fd', render: dateFmt },
    { title: '款项类别', dataIndex: 'category', key: 'cat' },
    { title: '收支', dataIndex: 'income_expense_type', key: 'iet', render: (v: string) => <span style={{ color: v === '收入' ? '#147f64' : '#c2413a' }}>{v}</span> },
    { title: '金额', dataIndex: 'amount', key: 'amt', render: (v: number) => fmt(v) },
    { title: '公司', dataIndex: 'company_name', key: 'cn' },
    { title: '入账', dataIndex: 'status', key: 'st', render: (v: string) => v === '已入账' ? '✓' : '○' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <Row gutter={[16, 16]}>
        {metrics.map((m, i) => (
          <Col xs={24} sm={12} lg={6} key={i}>
            <Card hoverable style={{ borderRadius: 8, borderLeft: `4px solid ${['#147f64', '#0d5f4b', '#b45309', '#256b85'][i]}` }}>
              <Statistic title={<span style={{ fontSize: 13, color: '#66736f' }}>{m.label}</span>} value={m.value} valueStyle={{ fontSize: 24, fontWeight: 700, color: '#17201d' }} />
              <div style={{ fontSize: 12, color: '#66736f', marginTop: 4 }}>{m.hint}</div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        {orgMetrics.map((m, i) => (
          <Col xs={24} sm={8} key={i}>
            <Card hoverable style={{ borderRadius: 8, borderLeft: `4px solid ${['#722ed1', '#13c2c2', '#eb2f96'][i]}` }}>
              <Statistic title={<span style={{ fontSize: 13, color: '#66736f' }}>{m.label}</span>} value={m.value} valueStyle={{ fontSize: 24, fontWeight: 700, color: '#17201d' }} />
              {m.hint && <div style={{ fontSize: 12, color: '#66736f', marginTop: 4 }}>{m.hint}</div>}
            </Card>
          </Col>
        ))}
      </Row>

      <Card title={<span style={{ fontSize: 15, fontWeight: 600 }}>核心业务流</span>} style={{ borderRadius: 8 }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          项目管理 → 合同管理 → 订单管理 → 请款管理 → 收款管理 → 财务管理 → 合同与项目统计回写
        </Text>
        <Row gutter={[24, 16]}>
          <Col xs={24} md={8}>
            <div style={{ marginBottom: 4 }}><Text style={{ fontSize: 13 }}>订单完成率</Text></div>
            <Progress percent={data.orders.count > 0 ? Math.round(data.orders.done / data.orders.count * 100) : 0} strokeColor="#147f64" format={() => `${data.orders.done}/${data.orders.count}`} />
          </Col>
          <Col xs={24} md={8}>
            <div style={{ marginBottom: 4 }}><Text style={{ fontSize: 13 }}>合同完成率</Text></div>
            <Progress percent={data.contracts.count > 0 ? Math.round(data.contracts.done / data.contracts.count * 100) : 0} strokeColor="#0d5f4b" format={() => `${data.contracts.done}/${data.contracts.count}`} />
          </Col>
          <Col xs={24} md={8}>
            <div style={{ marginBottom: 4 }}><Text style={{ fontSize: 13 }}>项目完成率</Text></div>
            <Progress percent={data.projects.count > 0 ? Math.round(data.projects.done / data.projects.count * 100) : 0} strokeColor="#256b85" format={() => `${data.projects.done}/${data.projects.count}`} />
          </Col>
        </Row>
      </Card>

      <Card title={<span style={{ fontSize: 15, fontWeight: 600 }}>今日收支快照</span>} style={{ borderRadius: 8 }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>{new Date().toLocaleDateString('zh-CN')} 自动汇总财务明细</Text>
        <Table dataSource={data.todayFinances} columns={financeColumns} rowKey="id" size="small" pagination={false} locale={{ emptyText: '今日暂无收支记录' }} />
      </Card>
    </div>
  );
};

export default Dashboard;