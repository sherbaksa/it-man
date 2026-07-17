/** Author: Dev2 | Date: 2026-07-16 | Purpose: Personal operational dashboard for the current IT engineer. */
import { AlertOutlined, ArrowRightOutlined, BellOutlined, CheckCircleOutlined, DesktopOutlined, LaptopOutlined, PlusOutlined, ToolOutlined } from '@ant-design/icons'
import { Button, Card, Progress, Skeleton, Space, Tag } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAssets } from '../api/assets'
import { getTickets, ticketPriorityLabels, ticketStatusLabels } from '../api/tickets'
import { useAuthStore } from '../store/authStore'
import type { Asset } from '../types/asset'
import type { Ticket } from '../types/ticket'

const priorityColors = { low: 'default', medium: 'cyan', high: 'orange', critical: 'red' } as const
const statusColors = { new: 'blue', in_progress: 'gold', done: 'green', rejected: 'default' } as const

export default function EngineerDashboard() {
  const user = useAuthStore((state) => state.user)!
  const navigate = useNavigate()
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    Promise.all([
      getTickets({ page: 1, pageSize: 20, assigneeId: user.id }),
      getAssets({ page: 1, pageSize: 20, responsibleUserId: user.id }),
    ]).then(([ticketResult, assetResult]) => {
      if (!active) return
      setTickets(ticketResult.items)
      setAssets(assetResult.items)
      setLoading(false)
    })
    return () => { active = false }
  }, [user.id])

  const activeTickets = tickets.filter((ticket) => ticket.status === 'new' || ticket.status === 'in_progress')
  const urgentTickets = activeTickets.filter((ticket) => ticket.priority === 'high' || ticket.priority === 'critical')
  const repairAssets = assets.filter((asset) => asset.status === 'repair')
  const today = new Date().toISOString().slice(0, 10)
  const closedToday = tickets.filter((ticket) => ticket.status === 'done' && ticket.closedAt?.slice(0, 10) === today).length

  if (loading) return <div className="page-container"><Skeleton active paragraph={{ rows: 12 }} /></div>

  return (
    <div className="page-container engineer-dashboard">
      <div className="page-heading"><div><span className="eyebrow">Личный кабинет инженера</span><h1>Добро пожаловать, {user.fullName.split(' ')[0]}</h1><p>Ваши назначенные задачи, оборудование и состояние инфраструктуры</p></div><Space wrap><Button icon={<LaptopOutlined />} onClick={() => navigate('/inventory')}>Инвентаризация</Button><Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/tickets?new=1')}>Новая заявка</Button></Space></div>
      <section className="metric-grid engineer-metrics">
        <Card className="metric-card danger"><div className="metric-icon"><AlertOutlined /></div><span>Мои активные заявки</span><strong>{activeTickets.length}</strong><small>{urgentTickets.length} высокого приоритета</small></Card>
        <Card className="metric-card"><div className="metric-icon"><LaptopOutlined /></div><span>Активы под ответственностью</span><strong>{assets.length}</strong><small>{repairAssets.length} требуют ремонта</small></Card>
        <Card className="metric-card success"><div className="metric-icon"><CheckCircleOutlined /></div><span>Закрыто сегодня</span><strong>{closedToday}</strong><small>из назначенных вам заявок</small></Card>
        <Card className="metric-card warning"><div className="metric-icon"><DesktopOutlined /></div><span>Доступность сервисов</span><strong>97%</strong><small>обновлено 5 минут назад</small></Card>
      </section>
      <section className="engineer-dashboard-grid">
        <div className="engineer-main-column">
          <Card className="workspace-card" title="Мои заявки" extra={<Button type="link" onClick={() => navigate('/tickets')}>Все заявки <ArrowRightOutlined /></Button>}>
            {activeTickets.length ? <div className="engineer-ticket-list">{activeTickets.slice(0, 5).map((ticket) => <button key={ticket.id} onClick={() => navigate('/tickets')}><span><small>{ticket.number}</small><strong>{ticket.title}</strong></span><Tag color={priorityColors[ticket.priority]}>{ticketPriorityLabels[ticket.priority]}</Tag><Tag color={statusColors[ticket.status]}>{ticketStatusLabels[ticket.status]}</Tag></button>)}</div> : <div className="dashboard-empty">Нет активных назначенных заявок</div>}
          </Card>
          <Card className="workspace-card" title="Мои активы" extra={<Button type="link" onClick={() => navigate('/inventory')}>Инвентаризация <ArrowRightOutlined /></Button>}>
            {assets.length ? <div className="engineer-asset-list">{assets.slice(0, 5).map((asset) => <button key={asset.id} onClick={() => navigate('/inventory')}><span className="asset-list-icon"><LaptopOutlined /></span><span><strong>{asset.inventoryNumber} · {asset.model || asset.type.name}</strong><small>{asset.location || 'Расположение не указано'} · {asset.hostname || 'без hostname'}</small></span><Tag color={asset.status === 'repair' ? 'gold' : 'green'}>{asset.status === 'repair' ? 'В ремонте' : 'В работе'}</Tag></button>)}</div> : <div className="dashboard-empty">За вами не закреплены активы</div>}
          </Card>
        </div>
        <div className="engineer-side-column">
          <Card className="workspace-card monitoring-summary" title="Сводный статус мониторинга" extra={<Tag color="cyan">Демо</Tag>}>
            <div className="monitoring-score"><Progress type="circle" percent={97} size={100} strokeColor="#16815c" /><div><strong>Инфраструктура стабильна</strong><span>Последняя проверка 5 минут назад</span></div></div>
            <div className="monitoring-states"><span className="ok"><i />Доступно <strong>18</strong></span><span className="warning"><i />Предупреждение <strong>1</strong></span><span className="critical"><i />Критично <strong>0</strong></span></div>
          </Card>
          <Card className="workspace-card" title={<><BellOutlined /> Уведомления</>} extra={<Tag>Заглушка MVP</Tag>}>
            <div className="engineer-notifications"><div><AlertOutlined /><span><strong>Заявка INC-1249 назначена вам</strong><small>Сегодня, 09:15</small></span></div><div><ToolOutlined /><span><strong>Плановое обслуживание сервера</strong><small>Сегодня, 18:00</small></span></div><div><CheckCircleOutlined /><span><strong>Отчёт инвентаризации сформирован</strong><small>Вчера, 16:42</small></span></div></div>
          </Card>
        </div>
      </section>
    </div>
  )
}
