/** Author: Dev2 | Date: 2026-07-16 | Purpose: Shared navigation shell with role-aware menu. */
import {
  AppstoreOutlined,
  BarChartOutlined,
  BellOutlined,
  FileTextOutlined,
  HomeOutlined,
  LaptopOutlined,
  LogoutOutlined,
  MedicineBoxOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MonitorOutlined,
  SettingOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import { Button, Layout, Menu, Tooltip } from 'antd'
import { useMemo, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import type { Role } from '../types/auth'

const { Header, Sider, Content } = Layout

type MenuDefinition = {
  key: string
  label: string
  icon: React.ReactNode
  roles: Role[]
}

const staffRoles: Role[] = ['Admin', 'IT-Head', 'Engineer', 'Executive']
const technicalRoles: Role[] = ['Admin', 'IT-Head', 'Engineer']

const menuDefinitions: MenuDefinition[] = [
  { key: '/', label: 'Главная', icon: <HomeOutlined />, roles: staffRoles },
  { key: '/tickets', label: 'Заявки', icon: <AppstoreOutlined />, roles: ['Admin', 'IT-Head', 'Engineer', 'User'] },
  { key: '/inventory', label: 'Инвентаризация', icon: <LaptopOutlined />, roles: technicalRoles },
  { key: '/maintenance', label: 'Обслуживание', icon: <ToolOutlined />, roles: technicalRoles },
  { key: '/orders', label: 'Документы ОРД', icon: <FileTextOutlined />, roles: staffRoles },
  { key: '/monitoring', label: 'Мониторинг', icon: <MonitorOutlined />, roles: technicalRoles },
  { key: '/reports', label: 'Отчёты', icon: <BarChartOutlined />, roles: ['Admin', 'IT-Head', 'Executive'] },
  { key: '/admin', label: 'Настройки', icon: <SettingOutlined />, roles: ['Admin'] },
]

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const user = useAuthStore((state) => state.user)!
  const logout = useAuthStore((state) => state.logout)
  const location = useLocation()
  const navigate = useNavigate()

  const menuItems = useMemo(
    () => menuDefinitions.filter((item) => item.roles.includes(user.role)).map(({ roles: _roles, ...item }) => item),
    [user.role],
  )

  const activeDefinition = menuDefinitions.find((item) => item.key === location.pathname)

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <Layout className="app-shell">
      <Sider className="app-sider" width={256} collapsedWidth={76} collapsed={collapsed} trigger={null}>
        <div className="brand-block">
          <div className="brand-mark"><MedicineBoxOutlined /></div>
          {!collapsed && <div><strong>IT Management</strong><span>Медицинская организация</span></div>}
        </div>
        {!collapsed && <div className="nav-label">Рабочее пространство</div>}
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }: { key: string }) => navigate(key)}
          className="main-menu"
        />
        <div className="sider-profile">
          <div className="profile-avatar">{user.initials}</div>
          {!collapsed && <div className="profile-copy"><strong>{user.fullName}</strong><span>{user.position}</span></div>}
          {!collapsed && <Tooltip title="Выйти"><Button type="text" icon={<LogoutOutlined />} onClick={handleLogout} /></Tooltip>}
        </div>
      </Sider>
      <Layout>
        <Header className="app-header">
          <Button
            type="text"
            className="collapse-button"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed((value) => !value)}
          />
          <div className="breadcrumbs"><span>IT Management</span><i>/</i><strong>{activeDefinition?.label ?? 'Рабочая область'}</strong></div>
          <div className="header-actions"><span className="system-state"><i /> Система доступна</span><Button aria-label="Уведомления" icon={<BellOutlined />} /></div>
        </Header>
        <Content className="app-content"><Outlet /></Content>
      </Layout>
    </Layout>
  )
}
