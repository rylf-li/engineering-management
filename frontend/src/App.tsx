import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom';
import { Layout, Menu, Spin, Typography, Button, Dropdown } from 'antd';
import {
  DashboardOutlined, TeamOutlined, ApartmentOutlined,
  ProjectOutlined, FileTextOutlined, ToolOutlined,
  ShoppingCartOutlined, DollarOutlined, BankOutlined,
  PieChartOutlined, UserOutlined, BarChartOutlined,
  LogoutOutlined, UserSwitchOutlined,
} from '@ant-design/icons';
import { AuthProvider, useAuth } from './services/auth';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const EmployeeList = React.lazy(() => import('./pages/EmployeeList'));
const DepartmentList = React.lazy(() => import('./pages/DepartmentList'));
const CompanyList = React.lazy(() => import('./pages/CompanyList'));
const CustomerList = React.lazy(() => import('./pages/CustomerList'));
const ProjectList = React.lazy(() => import('./pages/ProjectList'));
const ContractList = React.lazy(() => import('./pages/ContractList'));
const BusinessServiceList = React.lazy(() => import('./pages/BusinessServiceList'));
const OrderList = React.lazy(() => import('./pages/OrderList'));
const RequestPaymentList = React.lazy(() => import('./pages/RequestPaymentList'));
const CollectionList = React.lazy(() => import('./pages/CollectionList'));
const FinanceList = React.lazy(() => import('./pages/FinanceList'));
const Reports = React.lazy(() => import('./pages/Reports'));
const LoginPage = React.lazy(() => import('./pages/LoginPage'));

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/employees', icon: <TeamOutlined />, label: '员工管理' },
  { key: '/departments', icon: <ApartmentOutlined />, label: '部门管理' },
  { key: '/companies', icon: <BankOutlined />, label: '公司管理' },
  { key: '/customers', icon: <UserOutlined />, label: '客户管理' },
  { key: '/projects', icon: <ProjectOutlined />, label: '项目管理' },
  { key: '/contracts', icon: <FileTextOutlined />, label: '合同管理' },
  { key: '/business-services', icon: <ToolOutlined />, label: '业务服务' },
  { key: '/orders', icon: <ShoppingCartOutlined />, label: '订单管理' },
  { key: '/request-payments', icon: <DollarOutlined />, label: '请款管理' },
  { key: '/collections', icon: <BankOutlined />, label: '收款管理' },
  { key: '/finances', icon: <PieChartOutlined />, label: '财务管理' },
  { key: '/reports', icon: <BarChartOutlined />, label: '报表中心' },
];

const roleColors: Record<string, string> = {
  '管理员': 'red',
  '业务员': 'blue',
  '财务': 'purple',
  '员工': 'green',
};

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const userMenuItems = [
    {
      key: 'role',
      label: `角色: ${user?.role || '员工'}`,
      disabled: true,
    },
    { type: 'divider' as const },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        width={220}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          background: '#123b35',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '18px 14px',
            borderBottom: '1px solid rgba(255,255,255,0.14)',
            minHeight: 58,
          }}
        >
          <div
            style={{
              display: 'grid',
              placeItems: 'center',
              width: 42,
              height: 42,
              borderRadius: 6,
              background: '#f6c85f',
              color: '#153730',
              fontWeight: 800,
              fontSize: 16,
              flexShrink: 0,
            }}
          >
            JC
          </div>
          <div>
            <div style={{ color: '#fff', fontSize: 15, fontWeight: 600, lineHeight: 1.3 }}>
              工程服务管理
            </div>
            <div style={{ color: 'rgba(255,255,255,0.68)', fontSize: 11, marginTop: 2 }}>
              检测 · 测绘 · 勘察
            </div>
          </div>
        </div>

        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            background: '#123b35',
            borderInlineEnd: 'none',
            color: 'rgba(255,255,255,0.84)',
          }}
        />
      </Sider>

      <Layout style={{ marginLeft: 220 }}>
        <Header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
            position: 'sticky',
            top: 0,
            zIndex: 100,
            height: 56,
          }}
        >
          <Text strong style={{ fontSize: 16, color: '#17201d' }}>
            工程检测公司综合管理系统
          </Text>

          <Dropdown
            menu={{
              items: userMenuItems,
              onClick: ({ key }) => {
                if (key === 'logout') {
                  logout();
                  navigate('/login');
                }
              },
            }}
            placement="bottomRight"
          >
            <Button
              type="text"
              icon={<UserSwitchOutlined />}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <span style={{ color: roleColors[user?.role || '员工'] || 'green', fontWeight: 600 }}>
                {user?.name || '未登录'}
              </span>
            </Button>
          </Dropdown>
        </Header>
        <Content style={{ margin: 24, minHeight: 280 }}>
          <Suspense fallback={<div style={{ textAlign: 'center', padding: 100 }}><Spin size="large" /></div>}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/employees" element={<EmployeeList />} />
              <Route path="/departments" element={<DepartmentList />} />
              <Route path="/companies" element={<CompanyList />} />
              <Route path="/customers" element={<CustomerList />} />
              <Route path="/projects" element={<ProjectList />} />
              <Route path="/contracts" element={<ContractList />} />
              <Route path="/business-services" element={<BusinessServiceList />} />
              <Route path="/orders" element={<OrderList />} />
              <Route path="/request-payments" element={<RequestPaymentList />} />
              <Route path="/collections" element={<CollectionList />} />
              <Route path="/finances" element={<FinanceList />} />
              <Route path="/reports" element={<Reports />} />
            </Routes>
          </Suspense>
        </Content>
      </Layout>
    </Layout>
  );
};

const App: React.FC = () => (
  <BrowserRouter>
    <AuthProvider>
      <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}><Spin size="large" /></div>}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/*" element={<AppLayout />} />
        </Routes>
      </Suspense>
    </AuthProvider>
  </BrowserRouter>
);

export default App;
