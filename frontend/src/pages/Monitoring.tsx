/** Author: Dev2 | Date: 2026-07-16 | Purpose: F08 monitoring host list and status history visualization. */
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Card, Col, Descriptions, Drawer, Empty, Input, Row, Select, Statistic, Table, Tag } from 'antd'
import type { TableColumnsType, TablePaginationConfig } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getMonitoringHistory, getMonitoringStatus, monitoringSourceLabels, monitoringStateLabels } from '../api/monitoring'
import type { MonitoringFilters, MonitoringHistoryPoint, MonitoringHost, MonitoringSource, MonitoringState } from '../types/monitoring'

const statusColors = { ok: 'green', warning: 'gold', critical: 'red', unknown: 'default' } as const
const levelLabels: Record<number, string> = { 0: 'Нет данных', 1: 'Работает', 2: 'Предупреждение', 3: 'Критический' }
const emptyFilters: MonitoringFilters = { page: 1, pageSize: 6 }
const emptySummary: Record<MonitoringState, number> = { ok: 0, warning: 0, critical: 0, unknown: 0 }
const formatDateTime = (value?: string) => value ? new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)) : '—'
const formatTime = (value: string) => new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date(value))

export default function Monitoring() {
  const [filters, setFilters] = useState<MonitoringFilters>(emptyFilters)
  const [draftSearch, setDraftSearch] = useState('')
  const [items, setItems] = useState<MonitoringHost[]>([])
  const [total, setTotal] = useState(0)
  const [summary, setSummary] = useState(emptySummary)
  const [loading, setLoading] = useState(false)
  const [selectedHost, setSelectedHost] = useState<MonitoringHost>()
  const [history, setHistory] = useState<MonitoringHistoryPoint[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  const loadStatus = useCallback(async () => {
    setLoading(true)
    try {
      const result = await getMonitoringStatus(filters)
      setItems(result.items)
      setTotal(result.total)
      setSummary(result.summary)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { void loadStatus() }, [loadStatus])
  useEffect(() => {
    if (!selectedHost) { setHistory([]); return }
    setHistoryLoading(true)
    void getMonitoringHistory(selectedHost.hostIdentifier).then(setHistory).finally(() => setHistoryLoading(false))
  }, [selectedHost])

  const updateFilters = (next: Partial<MonitoringFilters>) => setFilters((current) => ({ ...current, ...next, page: next.page ?? 1 }))
  const columns: TableColumnsType<MonitoringHost> = [
    { title: 'Состояние', dataIndex: 'status', width: 145, render: (status: MonitoringState) => <Tag color={statusColors[status]}><span className={`monitoring-status-dot ${status}`} />{monitoringStateLabels[status]}</Tag> },
    { title: 'Хост', dataIndex: 'displayName', width: 190, render: (value: string, host) => <span className="monitoring-host-name"><strong>{value}</strong><small>{host.hostIdentifier}</small></span> },
    { title: 'Последнее значение', dataIndex: 'lastValue', ellipsis: true },
    { title: 'Источник', dataIndex: 'source', width: 115, render: (source: MonitoringSource) => monitoringSourceLabels[source] },
    { title: 'Расположение', dataIndex: 'location', width: 175, ellipsis: true, render: (value?: string) => value || '—' },
    { title: 'Доступность 24 ч', dataIndex: 'availability24h', width: 145, align: 'right', render: (value?: number) => value === undefined ? '—' : <strong className={value < 98 ? 'monitoring-low-availability' : ''}>{value.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%</strong> },
    { title: 'Обновлено', dataIndex: 'updatedAt', width: 145, render: formatDateTime },
  ]
  const pagination: TablePaginationConfig = { current: filters.page, pageSize: filters.pageSize, total, showSizeChanger: true, pageSizeOptions: [6, 12, 24], showTotal: (value: number) => `Всего: ${value}` }

  return (
    <div className="page-container monitoring-page">
      <div className="page-heading"><div><span className="eyebrow">Контроль инфраструктуры</span><h1>Мониторинг</h1><p>Состояние серверов, сетевого оборудования и защищаемых рабочих мест</p></div><Button icon={<ReloadOutlined />} loading={loading} onClick={() => void loadStatus()}>Обновить</Button></div>
      <div className="prototype-notice">Локальный режим · интерфейс использует демонстрационные ответы будущих API `/api/monitoring/status` и `/history`</div>
      <Row gutter={[14, 14]} className="monitoring-stats">
        <Col xs={12} lg={6}><Card className="success"><Statistic title="Работают" value={summary.ok} /></Card></Col>
        <Col xs={12} lg={6}><Card className="warning"><Statistic title="Предупреждения" value={summary.warning} /></Card></Col>
        <Col xs={12} lg={6}><Card className="danger"><Statistic title="Критические" value={summary.critical} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="Нет данных" value={summary.unknown} /></Card></Col>
      </Row>
      <Card className="workspace-card monitoring-workspace">
        <div className="monitoring-filters">
          <Input allowClear prefix={<SearchOutlined />} placeholder="Хост, IP, актив или расположение…" value={draftSearch} onChange={(event) => setDraftSearch(event.target.value)} onPressEnter={() => updateFilters({ search: draftSearch || undefined })} />
          <Button type="primary" onClick={() => updateFilters({ search: draftSearch || undefined })}>Найти</Button>
          <Select allowClear placeholder="Все состояния" value={filters.status} options={Object.entries(monitoringStateLabels).map(([value, label]) => ({ value, label }))} onChange={(status?: MonitoringState) => updateFilters({ status })} />
          <Select allowClear placeholder="Все источники" value={filters.source} options={Object.entries(monitoringSourceLabels).map(([value, label]) => ({ value, label }))} onChange={(source?: MonitoringSource) => updateFilters({ source })} />
          <Button onClick={() => { setDraftSearch(''); setFilters(emptyFilters) }}>Сбросить</Button>
        </div>
        <Table<MonitoringHost> rowKey="id" columns={columns} dataSource={items} loading={loading} pagination={pagination} scroll={{ x: 1160 }} onChange={(next: TablePaginationConfig) => setFilters((current) => ({ ...current, page: next.current ?? 1, pageSize: next.pageSize ?? current.pageSize }))} onRow={(host) => ({ onClick: () => setSelectedHost(host) })} rowClassName="monitoring-table-row" />
      </Card>
      <Drawer title={<div><span className="drawer-kicker">История мониторинга</span><strong>{selectedHost?.displayName}</strong></div>} width={760} open={Boolean(selectedHost)} onClose={() => setSelectedHost(undefined)}>
        {selectedHost && <>
          <div className="monitoring-host-header"><Tag color={statusColors[selectedHost.status]}>{monitoringStateLabels[selectedHost.status]}</Tag><Tag>{monitoringSourceLabels[selectedHost.source]}</Tag><h2>{selectedHost.lastValue}</h2><p>{selectedHost.hostIdentifier} · обновлено {formatDateTime(selectedHost.updatedAt)}</p></div>
          <Descriptions bordered size="small" column={1}><Descriptions.Item label="Актив">{selectedHost.asset ? `${selectedHost.asset.inventoryNumber} · ${selectedHost.asset.model ?? ''}` : 'Не связан с инвентаризацией'}</Descriptions.Item><Descriptions.Item label="Расположение">{selectedHost.location || '—'}</Descriptions.Item><Descriptions.Item label="Доступность за 24 часа">{selectedHost.availability24h?.toLocaleString('ru-RU', { minimumFractionDigits: 2 }) ?? '—'}%</Descriptions.Item></Descriptions>
          <Card size="small" title="Изменение состояния · последние 24 часа" className="monitoring-history-card" loading={historyLoading}>
            {history.length ? <div className="monitoring-history-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={history} margin={{ top: 10, right: 20, left: 12, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" stroke="#e3eaed" /><XAxis dataKey="timestamp" tickFormatter={formatTime} tick={{ fontSize: 10 }} /><YAxis domain={[0, 3]} ticks={[0, 1, 2, 3]} tickFormatter={(value: number) => levelLabels[value]} width={112} tick={{ fontSize: 10 }} /><Tooltip labelFormatter={(label) => formatDateTime(String(label))} formatter={(value) => [levelLabels[Number(value)] ?? value, 'Состояние']} /><Line type="stepAfter" dataKey="level" stroke="#087f8c" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} /></LineChart></ResponsiveContainer></div> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="История отсутствует" />}
          </Card>
          <div className="monitoring-event-list">{history.slice().reverse().map((point) => <div key={point.timestamp}><span className={`monitoring-status-dot ${point.status}`} /><p><strong>{monitoringStateLabels[point.status]}</strong><small>{formatDateTime(point.timestamp)} · {point.value}</small></p></div>)}</div>
        </>}
      </Drawer>
    </div>
  )
}
