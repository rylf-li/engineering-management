import React, { useState, useEffect, useCallback } from 'react';
import { Card, Table, DatePicker, Select, Button, Space, Tag, Spin, Row, Col, Statistic, Tabs } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import api from '../utils/api';

const colors: Record<string, string> = {
  '收入': '#147f64', '支出': '#c2413a',
  '已入账': '#147f64', '未入账': '#b45309',
};

const fmt = (v: number) => `¥${(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`;
const dateFmt = (v: string) => (v ? new Date(v).toLocaleDateString('zh-CN') : '');

const $ = (res: any) => res?.items ?? res?.results ?? res?.data?.items ?? [];

const financeColumns = [
  { title: '日期', dataIndex: 'finance_date', key: 'fd', render: dateFmt },
  { title: '款项类别', dataIndex: 'category', key: 'cat' },
  { title: '内容描述', dataIndex: 'description', key: 'desc', ellipsis: true },
  { title: '收支', dataIndex: 'income_expense_type', key: 'iet', render: (v: string) => (
    <span style={{ color: colors[v] || 'inherit' }}>{v}</span>
  )},
  { title: '金额¥', dataIndex: 'amount', key: 'amt', render: fmt },
  { title: '公司', dataIndex: 'company_name', key: 'cn' },
  { title: '入账', dataIndex: 'status', key: 'st', render: (v: string) => (
    <Tag color={v === '已入账' ? 'green' : 'orange'}>{v || '未入账'}</Tag>
  )},
];

const statColumns = (nameKey: string) => [
  { title: '名称', dataIndex: nameKey, key: nameKey },
  { title: '订单(未/已完成)', key: 'orders', render: (_: any, r: any) => `${r.orders_unfinished ?? 0}/${r.orders_finished ?? 0}` },
  { title: '合同(未/已完成)', key: 'contracts', render: (_: any, r: any) => `${r.contracts_unfinished ?? 0}/${r.contracts_finished ?? 0}` },
  { title: '应收款¥', dataIndex: 'receivable_amount', key: 'ra', render: fmt },
  { title: '请款¥', dataIndex: 'request_amount', key: 'rqa', render: fmt },
  { title: '收款¥', dataIndex: 'collection_amount', key: 'ca', render: fmt },
  { title: '支出¥', dataIndex: 'expenditure', key: 'exp', render: fmt },
  { title: '利润¥', dataIndex: 'profit', key: 'pf', render: fmt },
];

const Reports: React.FC = () => {
  const [activeKey, setActiveKey] = useState('daily');
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<any>({
    daily: { finances: [], companies: [], departments: [] },
    quarterly: { finances: [], companies: [], departments: [] },
    yearly: { finances: [], companies: [], departments: [] },
    projectContract: null,
  });

  // Date/period state
  const [dailyDate, setDailyDate] = useState<any>(null);
  const [quarterYear, setQuarterYear] = useState<number>(new Date().getFullYear());
  const [quarter, setQuarter] = useState<number>(Math.ceil((new Date().getMonth() + 1) / 3));
  const [yearlyYear, setYearlyYear] = useState<number>(new Date().getFullYear());

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      if (activeKey === 'daily') {
        const d = dailyDate ? dailyDate.format('YYYY-MM-DD') : new Date().toISOString().split('T')[0];
        const [finRes, compRes, deptRes] = await Promise.all([
          api.get('/reports/daily/finance/', { params: { report_date: d } }).catch(() => ({ records: [] })),
          api.get('/reports/daily/company/', { params: { report_date: d } }).catch(() => ({ records: [] })),
          api.get('/reports/daily/department/', { params: { report_date: d } }).catch(() => ({ records: [] })),
        ]);
        setReports(prev => ({ ...prev, daily: {
          finances: Array.isArray(finRes.records) ? finRes.records : $(finRes),
          companies: Array.isArray(compRes.records) ? compRes.records : $(compRes),
          departments: Array.isArray(deptRes.records) ? deptRes.records : $(deptRes),
          period: d,
        }}));
      } else if (activeKey === 'quarterly') {
        const startM = (quarter - 1) * 3 + 1;
        const endM = startM + 2;
        const start = `${quarterYear}-${String(startM).padStart(2,'0')}-01`;
        const end = `${quarterYear}-${String(endM).padStart(2,'0')}-${new Date(quarterYear, endM, 0).getDate()}`;
        const [finRes, compRes, deptRes] = await Promise.all([
          api.get('/reports/quarterly/finance/', { params: { year: quarterYear, quarter } }).catch(() => ({ records: [] })),
          api.get('/reports/quarterly/company/', { params: { year: quarterYear, quarter } }).catch(() => ({ records: [] })),
          api.get('/reports/quarterly/department/', { params: { year: quarterYear, quarter } }).catch(() => ({ records: [] })),
        ]);
        setReports(prev => ({ ...prev, quarterly: {
          finances: Array.isArray(finRes.records) ? finRes.records : $(finRes),
          companies: Array.isArray(compRes.records) ? compRes.records : $(compRes),
          departments: Array.isArray(deptRes.records) ? deptRes.records : $(deptRes),
          period: `${start} 至 ${end}`,
        }}));
      } else if (activeKey === 'yearly') {
        const start = `${yearlyYear}-01-01`;
        const end = `${yearlyYear}-12-31`;
        const [finRes, compRes, deptRes] = await Promise.all([
          api.get('/reports/yearly/finance/', { params: { year: yearlyYear } }).catch(() => ({ records: [] })),
          api.get('/reports/yearly/company/', { params: { year: yearlyYear } }).catch(() => ({ records: [] })),
          api.get('/reports/yearly/department/', { params: { year: yearlyYear } }).catch(() => ({ records: [] })),
        ]);
        setReports(prev => ({ ...prev, yearly: {
          finances: Array.isArray(finRes.records) ? finRes.records : $(finRes),
          companies: Array.isArray(compRes.records) ? compRes.records : $(compRes),
          departments: Array.isArray(deptRes.records) ? deptRes.records : $(deptRes),
          period: `${yearlyYear}年度`,
        }}));
      } else if (activeKey === 'projectContract') {
        const res = await api.get('/reports/project-contract-stats/').catch(() => null);
        setReports(prev => ({ ...prev, projectContract: res }));
      }
    } catch (e) {
      console.error('Report fetch failed:', e);
    }
    setLoading(false);
  }, [activeKey, dailyDate, quarterYear, quarter, yearlyYear]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const renderReportContent = (data: any, title: string) => {
    if (!data) return <Spin />;
    const finances = data.finances || [];
    const companies = data.companies || [];
    const departments = data.departments || [];
    const income = finances.filter((f: any) => f.income_expense_type === '收入').reduce((s: number, f: any) => s + (f.amount || 0), 0);
    const expense = finances.filter((f: any) => f.income_expense_type === '支出').reduce((s: number, f: any) => s + (f.amount || 0), 0);

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Card size="small"><Statistic title="报表区间" value={data.period || title} valueStyle={{ fontSize: 14 }} /></Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small" style={{ borderLeft: '3px solid #147f64' }}>
              <Statistic title="收入合计" value={income} formatter={(v) => fmt(Number(v))} valueStyle={{ color: '#147f64' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small" style={{ borderLeft: '3px solid #c2413a' }}>
              <Statistic title="支出合计" value={expense} formatter={(v) => fmt(Number(v))} valueStyle={{ color: '#c2413a' }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small" style={{ borderLeft: '3px solid #256b85' }}>
              <Statistic title="净额" value={income - expense} formatter={(v) => fmt(Number(v))} valueStyle={{ fontWeight: 700 }} />
            </Card>
          </Col>
        </Row>
        <Card size="small" title={`${title}财务收支详情表`}>
          <Table dataSource={finances} columns={financeColumns} rowKey="id" size="small" pagination={false} />
        </Card>
        <Card size="small" title={`${title}公司收支统计表`}>
          <Table dataSource={companies} columns={statColumns('company_name')} rowKey={(r, i) => i?.toString() || r.id} size="small" pagination={false} />
        </Card>
        <Card size="small" title={`${title}部门收支统计表`}>
          <Table dataSource={departments} columns={statColumns('department_name')} rowKey={(r, i) => i?.toString() || r.id} size="small" pagination={false} />
        </Card>
      </div>
    );
  };

  const renderProjectContract = () => {
    const d = reports.projectContract;
    if (!d) return <Spin />;
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Card size="small"><Statistic title="项目数量" value={d?.project_stats?.total || 0} suffix={`${d?.project_stats?.completed || 0} 已完成`} /></Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small"><Statistic title="合同数量" value={d?.contract_stats?.total || 0} /></Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small"><Statistic title="应收款金额" value={d?.finance_stats?.receivable_amount || 0} formatter={(v) => fmt(Number(v))} /></Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small"><Statistic title="已收款金额" value={d?.finance_stats?.collected_amount || 0} formatter={(v) => fmt(Number(v))} /></Card>
          </Col>
        </Row>
        {d?.project_list?.length > 0 && (
          <Card size="small" title="项目列表">
            <Table dataSource={d.project_list} rowKey="id" size="small" pagination={false} />
          </Card>
        )}
      </div>
    );
  };

  const tabItems = [
    {
      key: 'daily',
      label: '日报表',
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <DatePicker value={dailyDate} onChange={setDailyDate} />
            <Button type="primary" icon={<SearchOutlined />} onClick={fetchData}>查询</Button>
          </Space>
          {renderReportContent(reports.daily, '日报')}
        </div>
      ),
    },
    {
      key: 'quarterly',
      label: '季度报表',
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Select value={quarterYear} onChange={setQuarterYear} style={{ width: 100 }}>
              {[2024, 2025, 2026, 2027].map(y => <Select.Option key={y} value={y}>{y}</Select.Option>)}
            </Select>
            <Select value={quarter} onChange={setQuarter} style={{ width: 100 }}>
              {[1, 2, 3, 4].map(q => <Select.Option key={q} value={q}>第{q}季度</Select.Option>)}
            </Select>
            <Button type="primary" icon={<SearchOutlined />} onClick={fetchData}>查询</Button>
          </Space>
          {renderReportContent(reports.quarterly, '季度报表')}
        </div>
      ),
    },
    {
      key: 'yearly',
      label: '年度报表',
      children: (
        <div>
          <Space style={{ marginBottom: 16 }}>
            <Select value={yearlyYear} onChange={setYearlyYear} style={{ width: 100 }}>
              {[2024, 2025, 2026, 2027].map(y => <Select.Option key={y} value={y}>{y}</Select.Option>)}
            </Select>
            <Button type="primary" icon={<SearchOutlined />} onClick={fetchData}>查询</Button>
          </Space>
          {renderReportContent(reports.yearly, '年度报表')}
        </div>
      ),
    },
    {
      key: 'projectContract',
      label: '项目合同报表',
      children: renderProjectContract(),
    },
  ];

  return (
    <div>
      <Card style={{ borderRadius: 8 }}>
        <Tabs activeKey={activeKey} onChange={setActiveKey} items={tabItems} />
      </Card>
    </div>
  );
};

export default Reports;