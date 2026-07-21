/** Author: Dev2 | Date: 2026-07-16 | Purpose: Initial engineer dashboard with mock operational data. */
import { AlertOutlined, CheckCircleOutlined, ClockCircleOutlined, LaptopOutlined, PlusOutlined, ToolOutlined } from '@ant-design/icons'
import { Button, Card, Tag } from 'antd'
import { lazy, Suspense } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

const EngineerDashboard = lazy(() => import('./EngineerDashboard'))
const ExecutiveDashboard = lazy(() => import('./ExecutiveDashboard'))
const dashboardFallback = <div className="page-container"><div className="page-loading">Формируем дашборд…</div></div>

const metrics = [
  { label: 'Открытые заявки', value: '11', note: '3 с высоким приоритетом', icon: <AlertOutlined />, tone: 'danger' },
  { label: 'Активы в работе', value: '247', note: 'из 263 учтённых', icon: <LaptopOutlined />, tone: 'primary' },
  { label: 'На обслуживании', value: '8', note: '2 ожидают запчасти', icon: <ToolOutlined />, tone: 'warning' },
  { label: 'Сервисы доступны', value: '96%', note: 'обновлено 5 минут назад', icon: <CheckCircleOutlined />, tone: 'success' },
]

const tickets = [
  ['INC-1248', 'Не работает принтер в регистратуре', 'Высокий', 'В работе'],
  ['INC-1247', 'Настройка рабочего места врача', 'Средний', 'Новая'],
  ['INC-1246', 'Нет доступа к сетевой папке', 'Средний', 'Ожидает'],
  ['INC-1245', 'Замена картриджа, кабинет 312', 'Низкий', 'В работе'],
]

export default function Dashboard() {
  const user = useAuthStore((state) => state.user)!
  if (user.role === 'User') return <Navigate to="/tickets" replace />
  if (user.role === 'Engineer') return <Suspense fallback={dashboardFallback}><EngineerDashboard /></Suspense>
  if (user.role === 'Executive' || user.role === 'IT-Head') return <Suspense fallback={dashboardFallback}><ExecutiveDashboard /></Suspense>
  return (
    <div className="page-container">
      <div className="page-heading"><div><span className="eyebrow">IT-отдел</span><h1>Добро пожаловать, {user.fullName.split(' ')[0]}</h1><p>Сводная информация по инфраструктуре и текущим задачам</p></div><Button type="primary" icon={<PlusOutlined />}>Новая заявка</Button></div>
      <div className="prototype-notice">Первый сеанс · интерфейс работает на локальных демонстрационных данных</div>
      <section className="metric-grid">
        {metrics.map((metric) => <Card key={metric.label} className={`metric-card ${metric.tone}`}><div className="metric-icon">{metric.icon}</div><span>{metric.label}</span><strong>{metric.value}</strong><small>{metric.note}</small></Card>)}
      </section>
      <section className="dashboard-grid">
        <Card className="workspace-card" title="Текущие заявки" extra={<Button type="link">Все заявки</Button>}>
          <div className="ticket-list">{tickets.map(([id, title, priority, status]) => <div className="ticket-row" key={id}><div><span>{id}</span><strong>{title}</strong></div><Tag color={priority === 'Высокий' ? 'red' : priority === 'Средний' ? 'gold' : 'cyan'}>{priority}</Tag><Tag>{status}</Tag></div>)}</div>
        </Card>
        <Card className="workspace-card" title="Ближайшие работы"><div className="timeline-list"><div><ClockCircleOutlined /><span><strong>Обновление антивирусных баз</strong><small>Сегодня, 18:00</small></span></div><div><ToolOutlined /><span><strong>Обслуживание сервера архива</strong><small>Завтра, 10:00</small></span></div><div><LaptopOutlined /><span><strong>Инвентаризация поликлиники</strong><small>18 июля</small></span></div></div></Card>
      </section>
    </div>
  )
}
