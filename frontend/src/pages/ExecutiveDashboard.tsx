/** Author: Dev2 | Date: 2026-09-10 | Purpose: Real simplified leadership dashboard without technical host details. */
import { AlertOutlined, CheckCircleOutlined, ClockCircleOutlined, FileTextOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Empty, Skeleton, Tag } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getApiErrorMessage } from '../api/client'
import { getExecutiveSummary } from '../api/dashboard'
import { useAuthStore } from '../store/authStore'
import type { ExecutiveSummary } from '../types/dashboard'

export default function ExecutiveDashboard() {
  const user = useAuthStore((state) => state.user)!
  const [summary, setSummary] = useState<ExecutiveSummary>()
  const [error, setError] = useState<string>()

  const loadSummary = useCallback(async () => {
    setError(undefined)
    try {
      setSummary(await getExecutiveSummary())
    } catch (loadError) {
      setError(getApiErrorMessage(loadError, 'Не удалось загрузить дашборд руководства'))
    }
  }, [])

  useEffect(() => { void loadSummary() }, [loadSummary])

  if (!summary) {
    return <div className="page-container"><div className="page-heading"><div><span className="eyebrow">Дашборд руководства</span><h1>Обзор IT-инфраструктуры</h1><p>{user.fullName} · ключевые показатели без технической детализации</p></div></div>{error ? <Alert type="error" showIcon message={error} action={<Button size="small" onClick={() => void loadSummary()}>Повторить</Button>} /> : <Skeleton active paragraph={{ rows: 12 }} />}</div>
  }

  const monitoringTotal = summary.monitoring.ok + summary.monitoring.warning + summary.monitoring.critical + summary.monitoring.unknown
  const healthyPercent = monitoringTotal ? Math.round(summary.monitoring.ok / monitoringTotal * 100) : undefined
  const maxCategory = Math.max(...summary.problemCategories.map((category) => category.count), 1)
  const brief = !monitoringTotal
    ? { tone: 'warning', title: 'Нет данных мониторинга', text: 'Системы ещё не передали актуальные состояния в платформу.' }
    : summary.monitoring.critical
    ? { tone: 'danger', title: 'Есть критические сбои', text: `${summary.monitoring.critical} систем требуют немедленного внимания IT-отдела.` }
    : summary.monitoring.warning
      ? { tone: 'warning', title: 'Инфраструктура требует внимания', text: `${summary.monitoring.warning} систем работают с предупреждениями.` }
      : { tone: 'success', title: 'Инфраструктура работает стабильно', text: summary.monitoring.unknown ? `${summary.monitoring.unknown} систем пока не передали актуальные данные.` : 'Критических сбоев и предупреждений нет.' }

  return (
    <div className="page-container executive-dashboard">
      <div className="page-heading"><div><span className="eyebrow">Дашборд руководства</span><h1>Обзор IT-инфраструктуры</h1><p>{user.fullName} · ключевые показатели без технической детализации</p></div><Tag color="cyan">Данные API платформы</Tag></div>
      <div className={`executive-brief ${brief.tone}`}><SafetyCertificateOutlined /><div><strong>{brief.title}</strong><span>{brief.text}</span></div></div>
      <section className="metric-grid executive-metrics">
        <Card className="metric-card danger"><div className="metric-icon"><AlertOutlined /></div><span>Открытые заявки</span><strong>{summary.openTickets}</strong><small>{summary.criticalTickets} критических</small></Card>
        <Card className="metric-card warning"><div className="metric-icon"><ClockCircleOutlined /></div><span>Среднее время решения</span><strong>{summary.averageResolutionHours} ч</strong><small>закрытые заявки за последние 30 дней</small></Card>
        <Card className="metric-card success"><div className="metric-icon"><CheckCircleOutlined /></div><span>Без текущих сбоев</span><strong>{healthyPercent === undefined ? '—' : `${healthyPercent}%`}</strong><small>{monitoringTotal ? `${summary.monitoring.ok} из ${monitoringTotal} систем` : 'данные мониторинга отсутствуют'}</small></Card>
        <Card className="metric-card"><div className="metric-icon"><FileTextOutlined /></div><span>Требуют внимания</span><strong>{summary.monitoring.warning + summary.monitoring.critical}</strong><small>предупреждения и критические сбои</small></Card>
      </section>
      <section className="executive-dashboard-grid">
        <Card className="workspace-card executive-trend-card" title="Динамика заявок за 7 дней" extra={<div className="chart-legend"><span className="created" />Создано <span className="closed" />Закрыто</div>}>
          <div className="executive-chart" aria-label="График динамики заявок">
            <ResponsiveContainer width="100%" height="100%"><LineChart data={summary.trend} margin={{ top: 10, right: 12, left: -22, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="#e4ebee" vertical={false} /><XAxis dataKey="label" tick={{ fill: '#687b84', fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} tick={{ fill: '#687b84', fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ border: '1px solid #dce5e9', borderRadius: 8, boxShadow: '0 8px 24px rgba(16,47,58,.1)' }} /><Line type="monotone" dataKey="created" name="Создано" stroke="#087f8c" strokeWidth={3} dot={{ r: 4, fill: '#087f8c' }} /><Line type="monotone" dataKey="closed" name="Закрыто" stroke="#16815c" strokeWidth={3} dot={{ r: 4, fill: '#16815c' }} /></LineChart></ResponsiveContainer>
          </div>
        </Card>
        <Card className="workspace-card" title="Состояние сервисов" extra={<Tag color="cyan">Сводно</Tag>}>
          <div className="traffic-light-summary"><div className="traffic-light ok"><i /><span><strong>{summary.monitoring.ok}</strong><small>Работают нормально</small></span></div><div className="traffic-light warning"><i /><span><strong>{summary.monitoring.warning}</strong><small>Требует внимания</small></span></div><div className="traffic-light critical"><i /><span><strong>{summary.monitoring.critical}</strong><small>Критические сбои</small></span></div></div>
          <div className="availability-line"><span>Стабильно работают</span><strong>{healthyPercent === undefined ? 'Нет данных' : `${healthyPercent}%`}</strong></div>
          {summary.monitoring.unknown > 0 && <div className="availability-line"><span>Нет актуальных данных</span><strong>{summary.monitoring.unknown}</strong></div>}
        </Card>
        <Card className="workspace-card problem-categories-card" title="Топ-3 проблемные категории" extra={<Tag>По приоритетам · MVP</Tag>}>
          {summary.problemCategories.length ? <div className="problem-categories">{summary.problemCategories.map((category, index) => <div key={category.name}><span><i>{index + 1}</i><strong>{category.name}</strong><em>{category.count} заяв.</em></span><div><i style={{ width: `${category.count / maxCategory * 100}%` }} /></div></div>)}</div> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Открытых заявок нет" />}
        </Card>
        <Card className="workspace-card management-focus-card" title="На контроле руководства">
          <div><span className={summary.criticalTickets ? 'attention' : 'stable'}><AlertOutlined /></span><p><strong>Критические обращения</strong><small>{summary.criticalTickets ? `${summary.criticalTickets} заявок требуют приоритетного контроля` : 'Критических обращений нет'}</small></p></div><div><span className={summary.averageResolutionHours > 8 ? 'attention' : 'stable'}><ClockCircleOutlined /></span><p><strong>Среднее время решения</strong><small>{summary.averageResolutionHours > 8 ? 'Среднее время превышает целевые 8 часов' : 'Среднее время находится в целевом диапазоне до 8 часов'}</small></p></div>
        </Card>
      </section>
    </div>
  )
}
