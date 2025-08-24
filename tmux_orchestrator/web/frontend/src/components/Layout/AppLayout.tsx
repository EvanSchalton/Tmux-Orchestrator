import React from 'react'
import { Layout, Menu, theme } from 'antd'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  TeamOutlined,
  DesktopOutlined,
  LineChartOutlined,
} from '@ant-design/icons'

const { Header, Sider, Content } = Layout

const AppLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const {
    token: { colorBgContainer },
  } = theme.useToken()

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/agents',
      icon: <TeamOutlined />,
      label: 'Agents',
    },
    {
      key: '/sessions',
      icon: <DesktopOutlined />,
      label: 'Sessions',
    },
    {
      key: '/metrics',
      icon: <LineChartOutlined />,
      label: 'Metrics',
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark">
        <div style={{
          height: 32,
          margin: 16,
          color: 'white',
          fontSize: 18,
          fontWeight: 'bold',
          textAlign: 'center'
        }}>
          Tmux Orchestrator
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: 0, background: colorBgContainer }} />
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            minHeight: 280,
            background: colorBgContainer,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default AppLayout
