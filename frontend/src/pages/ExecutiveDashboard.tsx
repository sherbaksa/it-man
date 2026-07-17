/** Author: Dev2 | Date: 2026-07-16 | Purpose: Simplified leadership dashboard without technical host details. */
import { AlertOutlined, CheckCircleOutlined, ClockCircleOutlined, FileTextOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { Card, Skeleton, Tag } from 'antd'
import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getExecutiveSummary } from '../api/dashboard'
import { useAuthStore } from '../store/authStore'
import type { ExecutiveSummary } from '../types/dashboard'

export default function ExecutiveDashboard() {
  const user = useAuthStore((state) => state.user)!
  const [summary, setSummary] = useState<ExecutiveSummary>()

  useEffect(() => { void getExecutiveSummary().then(setSummary) }, [])
  if (!summary) return <div className="page-container"><Skeleton active paragraph={{ rows: 12 }} /></div>

  const monitoringTotal = summary.monitoring.ok + summary.monitoring.warning + summary.monitoring.critical
  const maxCategory = Math.max(...summary.problemCategories.map((category) => category.count), 1)

  return (
    <div className="page-container executive-dashboard">
      <div className="page-heading"><div><span className="eyebrow">Дашборд руководства</span><h1>Обзор IT-инфраструктуры</h1><p>{user.fullName} · ключевые показатели без технической детализации</p></div><Tag color="cyan">Данные обновлены 5 минут назад</Tag></div>
      <div className="executive-brief"><SafetyCertificateOutlined /><div><strong>Инфраструктура работает стабильно</strong><span>Критических сбоев нет. Одна система требует внимания IT-отдела.</span></div></div>
      <section className="metric-grid executive-metrics">
        <Card className="metric-card danger"><div className="metric-icon"><AlertOutlined /></div><span>Открытые заявки</span><strong>{summary.openTickets}</strong><small>{summary.criticalTickets} критическая</small></Card>
        <Card className="metric-card warning"><div className="metric-icon"><ClockCircleOutlined /></div><span>Среднее время решения</span><strong>{summary.averageResolutionHours} ч</strong><small>целевой показатель — до 8 часов</small></Card>
        <Card className="metric-card success"><div className="metric-icon"><CheckCircleOutlined /></div><span>Доступность сервисов</span><strong>{summary.availabilityPercent}%</strong><small>за текущий отчётный период</small></Card>
        <Card className="metric-card"><div className="metric-icon"><FileTextOutlined /></div><span>Закрыто заявок</span><strong>{summary.completedTickets}</strong><small>за доступный период данных</small></Card>
      </section>
      <section className="executive-dashboard-grid">
        <Card className="workspace-card executive-trend-card" title="Динамика заявок за 7 дней" extra={<div className="chart-legend"><span className="created" />Создано <span className="closed" />Закрыто</div>}>
          <div className="executive-chart" aria-label="График динамики заявок">
            <ResponsiveContainer width="100%" height="100%"><LineChart data={summary.trend} margin={{ top: 10, right: 12, left: -22, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="#e4ebee" vertical={false} /><XAxis dataKey="label" tick={{ fill: '#687b84', fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} tick={{ fill: '#687b84', fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ border: '1px solid #dce5e9', borderRadius: 8, boxShadow: '0 8px 24px rgba(16,47,58,.1)' }} /><Line type="monotone" dataKey="created" name="Создано" stroke="#087f8c" strokeWidth={3} dot={{ r: 4, fill: '#087f8c' }} /><Line type="monotone" dataKey="closed" name="Закрыто" stroke="#16815c" strokeWidth={3} dot={{ r: 4, fill: '#16815c' }} /></LineChart></ResponsiveContainer>
          </div>
        </Card>
        <Card className="workspace-card" title="Состояние сервисов" extra={<Tag color="cyan">Сводно</Tag>}>
          <div className="traffic-light-summary"><div className="traffic-light ok"><i /><span><strong>{summary.monitoring.ok}</strong><small>Работают нормально</small></span></div><div className="traffic-light warning"><i /><span><strong>{summary.monitoring.warning}</strong><small>Требует внимания</small></span></div><div className="traffic-light critical"><i /><span><strong>{summary.monitoring.critical}</strong><small>Критические сбои</small></span></div></div>
          <div className="availability-line"><span>Стабильно работают</span><strong>{Math.round(summary.monitoring.ok / monitoringTotal * 100)}%</strong></div>
        </Card>
        <Card className="workspace-card problem-categories-card" title="Топ-3 проблемные категории">
          <div className="problem-categories">{summary.problemCategories.map((category, index) => <div key={category.name}><span><i>{index + 1}</i><strong>{category.name}</strong><em>{category.count} заяв.</em></span><div><i style={{ width: `${category.count / maxCategory * 100}%` }} /></div></div>)}</div>
        </Card>
        <Card className="workspace-card management-focus-card" title="На контроле руководства">
          <div><span className={summary.criticalTickets ? 'attention' : 'stable'}><AlertOutlined /></span><p><strong>Критические обращения</strong><small>{summary.criticalTickets ? `${summary.criticalTickets} заявка требует приоритетного контроля` : 'Критических обращений нет'}</small></p></div><div><span className="stable"><ClockCircleOutlined /></span><p><strong>Соблюдение SLA</strong><small>Среднее время решения находится в целевом диапазоне</small></p></div>
        </Card>
      </section>
    </div>
  )
}
