/** Author: Dev2 | Date: 2026-07-16 | Purpose: Ticket queue with filters, lifecycle actions and local attachments. */
import { CheckOutlined, EditOutlined, PaperClipOutlined, PlusOutlined, SearchOutlined, UserSwitchOutlined } from '@ant-design/icons'
import { Button, Card, Col, Descriptions, Drawer, Form, Input, Modal, Row, Select, Space, Statistic, Table, Tag, message } from 'antd'
import type { TableColumnsType, TablePaginationConfig } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { closeTicket, deleteAttachment, getAttachmentBlob, getTickets, saveTicket, takeTicket, ticketAssignees, ticketPriorityLabels, ticketStatusLabels } from '../api/tickets'
import TicketForm from '../components/TicketForm'
import { useAuthStore } from '../store/authStore'
import type { Ticket, TicketAttachment, TicketFilters, TicketFormValues, TicketPriority, TicketStatus } from '../types/ticket'

const statusColors = { new: 'blue', in_progress: 'gold', done: 'green', rejected: 'default' } as const
const priorityColors = { low: 'default', medium: 'cyan', high: 'orange', critical: 'red' } as const
const sourceLabels = { web: 'Веб', max: 'MAX', zabbix_auto: 'Zabbix' } as const
const emptyFilters: TicketFilters = { page: 1, pageSize: 6 }
const formatDateTime = (value?: string) => value ? new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)) : '—'

export default function Tickets() {
  const user = useAuthStore((state) => state.user)!
  const [searchParams, setSearchParams] = useSearchParams()
  const [filters, setFilters] = useState<TicketFilters>(emptyFilters)
  const [draftSearch, setDraftSearch] = useState('')
  const [items, setItems] = useState<Ticket[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [selectedTicket, setSelectedTicket] = useState<Ticket>()
  const [formTicket, setFormTicket] = useState<Ticket | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [closeOpen, setCloseOpen] = useState(false)
  const [resolutionForm] = Form.useForm<{ resolution: string }>()
  const [messageApi, contextHolder] = message.useMessage()

  const loadTickets = useCallback(async () => {
    setLoading(true)
    try {
      const result = await getTickets(filters)
      setItems(result.items)
      setTotal(result.total)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { void loadTickets() }, [loadTickets])
  useEffect(() => {
    if (searchParams.get('new') !== '1') return
    setFormTicket(null)
    setFormOpen(true)
    setSearchParams({}, { replace: true })
  }, [searchParams, setSearchParams])
  const refresh = () => { void loadTickets() }
  const updateFilters = (next: Partial<TicketFilters>) => setFilters((current) => ({ ...current, ...next, page: next.page ?? 1 }))

  const columns: TableColumnsType<Ticket> = [
    { title: 'Номер', dataIndex: 'number', width: 105, render: (value: string) => <strong className="ticket-number">{value}</strong> },
    { title: 'Тема', dataIndex: 'title', ellipsis: true },
    { title: 'Приоритет', dataIndex: 'priority', width: 125, render: (priority: TicketPriority) => <Tag color={priorityColors[priority]}>{ticketPriorityLabels[priority]}</Tag> },
    { title: 'Статус', dataIndex: 'status', width: 115, render: (status: TicketStatus) => <Tag color={statusColors[status]}>{ticketStatusLabels[status]}</Tag> },
    { title: 'Исполнитель', dataIndex: ['assignee', 'fullName'], width: 165, render: (value?: string) => value || 'Не назначен' },
    { title: 'Актив', dataIndex: ['asset', 'inventoryNumber'], width: 125, render: (value?: string) => value || '—' },
    { title: <PaperClipOutlined />, dataIndex: 'attachments', width: 54, align: 'center', render: (attachments: TicketAttachment[]) => attachments.length || '—' },
    { title: 'Создана', dataIndex: 'createdAt', width: 145, render: formatDateTime },
  ]

  const openForm = (ticket?: Ticket) => { setFormTicket(ticket ?? null); setFormOpen(true) }
  const save = async (values: TicketFormValues, files: File[]) => {
    setSaving(true)
    const saved = await saveTicket(values, files, formTicket?.id)
    setSaving(false); setFormOpen(false); setSelectedTicket(selectedTicket?.id === saved.id ? saved : selectedTicket); refresh()
    messageApi.success(formTicket ? 'Заявка обновлена' : `Создана заявка ${saved.number}`)
  }

  const take = async () => {
    if (!selectedTicket) return
    const updated = await takeTicket(selectedTicket.id, { id: user.id, fullName: user.fullName })
    setSelectedTicket(updated); refresh(); messageApi.success('Заявка взята в работу')
  }

  const close = async () => {
    if (!selectedTicket) return
    const { resolution } = await resolutionForm.validateFields()
    const updated = await closeTicket(selectedTicket.id, resolution)
    setSelectedTicket(updated); setCloseOpen(false); resolutionForm.resetFields(); refresh(); messageApi.success('Заявка закрыта')
  }

  const removeAttachment = async (attachment: TicketAttachment) => {
    if (!formTicket) return
    const updated = await deleteAttachment(formTicket.id, attachment.id)
    setFormTicket(updated); setSelectedTicket(selectedTicket?.id === updated.id ? updated : selectedTicket); refresh(); messageApi.success('Вложение удалено')
  }

  const downloadAttachment = (attachment: TicketAttachment) => {
    const blob = getAttachmentBlob(attachment.id)
    if (!blob) { messageApi.error('Локальный файл недоступен после перезапуска'); return }
    const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = attachment.fileName; link.click(); URL.revokeObjectURL(url)
  }

  const pagination: TablePaginationConfig = { current: filters.page, pageSize: filters.pageSize, total, showSizeChanger: true, pageSizeOptions: [6, 12, 24], showTotal: (value: number) => `Всего: ${value}` }

  return (
    <div className="page-container tickets-page">
      {contextHolder}
      <div className="page-heading"><div><span className="eyebrow">Service desk</span><h1>Заявки</h1><p>Регистрация обращений, назначение исполнителей и контроль решения</p></div><Button type="primary" icon={<PlusOutlined />} onClick={() => openForm()}>Новая заявка</Button></div>
      <div className="prototype-notice">Локальный режим · заявки и вложения хранятся до обновления страницы</div>
      <Row gutter={[14, 14]} className="ticket-stats"><Col xs={12} lg={6}><Card><Statistic title="Найдено заявок" value={total} /></Card></Col><Col xs={12} lg={6}><Card><Statistic title="Новые" value={items.filter((item) => item.status === 'new').length} /></Card></Col><Col xs={12} lg={6}><Card><Statistic title="В работе" value={items.filter((item) => item.status === 'in_progress').length} /></Card></Col><Col xs={12} lg={6}><Card><Statistic title="Критические" value={items.filter((item) => item.priority === 'critical').length} /></Card></Col></Row>
      <Card className="workspace-card ticket-workspace">
        <div className="ticket-filters"><Input allowClear prefix={<SearchOutlined />} placeholder="Номер, тема, автор или актив…" value={draftSearch} onChange={(event: React.ChangeEvent<HTMLInputElement>) => setDraftSearch(event.target.value)} onPressEnter={() => updateFilters({ search: draftSearch || undefined })} /><Button type="primary" onClick={() => updateFilters({ search: draftSearch || undefined })}>Найти</Button><Select allowClear placeholder="Все статусы" value={filters.status} options={Object.entries(ticketStatusLabels).map(([value, label]) => ({ value, label }))} onChange={(status?: TicketStatus) => updateFilters({ status })} /><Select allowClear placeholder="Все приоритеты" value={filters.priority} options={Object.entries(ticketPriorityLabels).map(([value, label]) => ({ value, label }))} onChange={(priority?: TicketPriority) => updateFilters({ priority })} /><Select allowClear placeholder="Все исполнители" value={filters.assigneeId} options={ticketAssignees.map((person) => ({ value: person.id, label: person.fullName }))} onChange={(assigneeId?: string) => updateFilters({ assigneeId })} /><Button onClick={() => { setDraftSearch(''); setFilters(emptyFilters) }}>Сбросить</Button></div>
        <Table<Ticket> rowKey="id" columns={columns} dataSource={items} loading={loading} pagination={pagination} scroll={{ x: 1160 }} onChange={(next: TablePaginationConfig) => setFilters((current) => ({ ...current, page: next.current ?? 1, pageSize: next.pageSize ?? current.pageSize }))} onRow={(ticket: Ticket) => ({ onClick: () => setSelectedTicket(ticket) })} rowClassName="ticket-table-row" />
      </Card>
      <Drawer title={<div><span className="drawer-kicker">Карточка заявки</span><strong>{selectedTicket?.number}</strong></div>} width={720} open={Boolean(selectedTicket)} onClose={() => setSelectedTicket(undefined)} extra={selectedTicket && <Button icon={<EditOutlined />} onClick={() => openForm(selectedTicket)}>Редактировать</Button>}>
        {selectedTicket && <><div className="ticket-card-header"><div><Tag color={priorityColors[selectedTicket.priority]}>{ticketPriorityLabels[selectedTicket.priority]}</Tag><Tag color={statusColors[selectedTicket.status]}>{ticketStatusLabels[selectedTicket.status]}</Tag></div><h2>{selectedTicket.title}</h2><p>{selectedTicket.description || 'Описание не добавлено'}</p></div><Descriptions column={1} bordered size="small"><Descriptions.Item label="Автор">{selectedTicket.author.fullName}</Descriptions.Item><Descriptions.Item label="Исполнитель">{selectedTicket.assignee?.fullName || 'Не назначен'}</Descriptions.Item><Descriptions.Item label="Актив">{selectedTicket.asset ? `${selectedTicket.asset.inventoryNumber} · ${selectedTicket.asset.model ?? ''}` : 'Не привязан'}</Descriptions.Item><Descriptions.Item label="Источник">{sourceLabels[selectedTicket.source]}</Descriptions.Item><Descriptions.Item label="Создана">{formatDateTime(selectedTicket.createdAt)}</Descriptions.Item><Descriptions.Item label="Решение">{selectedTicket.resolution || '—'}</Descriptions.Item></Descriptions><div className="ticket-attachments"><strong>Вложения ({selectedTicket.attachments.length})</strong>{selectedTicket.attachments.length ? selectedTicket.attachments.map((attachment) => <Button key={attachment.id} icon={<PaperClipOutlined />} onClick={() => downloadAttachment(attachment)}>{attachment.fileName}</Button>) : <span>Нет вложений</span>}</div>{selectedTicket.status !== 'done' && <Space className="ticket-actions" wrap>{selectedTicket.status === 'new' && <Button type="primary" icon={<UserSwitchOutlined />} onClick={() => void take()}>Взять в работу</Button>}<Button icon={<CheckOutlined />} onClick={() => setCloseOpen(true)}>Закрыть заявку</Button></Space>}</>}
      </Drawer>
      <TicketForm open={formOpen} ticket={formTicket} saving={saving} onCancel={() => setFormOpen(false)} onSave={save} onDeleteAttachment={removeAttachment} onDownloadAttachment={downloadAttachment} />
      <Modal title={`Закрытие ${selectedTicket?.number ?? ''}`} open={closeOpen} onCancel={() => setCloseOpen(false)} onOk={() => void close()} okText="Закрыть заявку" cancelText="Отмена"><Form form={resolutionForm} layout="vertical"><Form.Item name="resolution" label="Решение" rules={[{ required: true, whitespace: true, message: 'Опишите выполненное решение' }]}><Input.TextArea rows={5} maxLength={3000} showCount /></Form.Item></Form></Modal>
    </div>
  )
}
