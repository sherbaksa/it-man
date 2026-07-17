/** Author: Dev2 | Date: 2026-07-16 | Purpose: ORD list, approval workflow, preview and DOCX download. */
import { CheckOutlined, CloseOutlined, DownloadOutlined, EditOutlined, EyeOutlined, FileAddOutlined, FileDoneOutlined, SearchOutlined, SendOutlined } from '@ant-design/icons'
import { Button, Card, Col, Descriptions, Drawer, Form, Input, Modal, Row, Select, Space, Statistic, Steps, Table, Tag, Timeline, Tooltip, message } from 'antd'
import type { TableColumnsType, TablePaginationConfig } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { approveOrder, createOrderDocx, executeOrder, getOrders, orderStatusLabels, orderTypeLabels, rejectOrder, saveOrder, sendOrderForApproval } from '../api/orders'
import OrderForm from '../components/OrderForm'
import { useAuthStore } from '../store/authStore'
import type { Order, OrderFilters, OrderFormValues, OrderStatus, OrderType } from '../types/order'

const statusColors = { draft: 'default', pending_approval: 'gold', approved: 'green', executed: 'cyan', rejected: 'red' } as const
const emptyFilters: OrderFilters = { page: 1, pageSize: 6 }
const formatDateTime = (value?: string) => value ? new Intl.DateTimeFormat('ru-RU', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)) : '—'

export default function Orders() {
  const user = useAuthStore((state) => state.user)!
  const [filters, setFilters] = useState<OrderFilters>(emptyFilters)
  const [draftSearch, setDraftSearch] = useState('')
  const [items, setItems] = useState<Order[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [selectedOrder, setSelectedOrder] = useState<Order>()
  const [formOrder, setFormOrder] = useState<Order | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectForm] = Form.useForm<{ reason: string }>()
  const [messageApi, contextHolder] = message.useMessage()

  const canCreate = ['Admin', 'IT-Head', 'Engineer'].includes(user.role)
  const canApprove = ['Admin', 'IT-Head', 'Executive'].includes(user.role)
  const loadOrders = useCallback(async () => {
    setLoading(true)
    const result = await getOrders(filters)
    setItems(result.items); setTotal(result.total); setLoading(false)
  }, [filters])
  useEffect(() => { void loadOrders() }, [loadOrders])
  const refresh = () => { void loadOrders() }
  const updateFilters = (next: Partial<OrderFilters>) => setFilters((current) => ({ ...current, ...next, page: next.page ?? 1 }))
  const updateSelected = (order: Order, success: string) => { setSelectedOrder(order); refresh(); messageApi.success(success) }

  const columns: TableColumnsType<Order> = [
    { title: 'Номер', dataIndex: 'number', width: 135, render: (value: string) => <strong className="order-number">{value}</strong> },
    { title: 'Документ', dataIndex: ['template', 'name'], ellipsis: true },
    { title: 'Тип', dataIndex: ['template', 'type'], width: 175, render: (type: OrderType) => orderTypeLabels[type] },
    { title: 'Статус', dataIndex: 'status', width: 145, render: (status: OrderStatus) => <Tag color={statusColors[status]}>{orderStatusLabels[status]}</Tag> },
    { title: 'Автор', dataIndex: ['author', 'fullName'], width: 160 },
    { title: 'Версия', dataIndex: 'version', width: 80, align: 'center' },
    { title: 'Создан', dataIndex: 'createdAt', width: 145, render: formatDateTime },
  ]

  const save = async (values: OrderFormValues) => {
    setSaving(true)
    const saved = await saveOrder(values, user, formOrder?.id)
    setSaving(false); setFormOpen(false); setSelectedOrder(selectedOrder?.id === saved.id ? saved : selectedOrder); refresh(); messageApi.success(formOrder ? `Сохранена версия ${saved.version}` : `Создан документ ${saved.number}`)
  }
  const download = async (order: Order) => {
    const blob = await createOrderDocx(order); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `${order.number}-${order.template.type}.docx`; link.click(); URL.revokeObjectURL(url); messageApi.success('Документ DOCX сформирован')
  }
  const reject = async () => {
    if (!selectedOrder) return
    const { reason } = await rejectForm.validateFields(); updateSelected(await rejectOrder(selectedOrder.id, user, reason), 'Документ отклонён'); setRejectOpen(false); rejectForm.resetFields()
  }
  const workflowIndex = selectedOrder ? ({ draft: 0, pending_approval: 1, approved: 2, executed: 3, rejected: 1 } as const)[selectedOrder.status] : 0
  const pagination: TablePaginationConfig = { current: filters.page, pageSize: filters.pageSize, total, showSizeChanger: true, pageSizeOptions: [6, 12, 24], showTotal: (value: number) => `Всего: ${value}` }

  return (
    <div className="page-container orders-page">
      {contextHolder}
      <div className="page-heading"><div><span className="eyebrow">Организационно-распорядительные документы</span><h1>Документы ОРД</h1><p>Подготовка, согласование и контроль исполнения документов</p></div>{canCreate && <Button type="primary" icon={<FileAddOutlined />} onClick={() => { setFormOrder(null); setFormOpen(true) }}>Создать документ</Button>}</div>
      <div className="prototype-notice">Локальный режим · DOCX формируется в браузере, PDF подключается после backend B15</div>
      <Row gutter={[14, 14]} className="order-stats"><Col xs={12} lg={6}><Card><Statistic title="Всего документов" value={total} /></Card></Col><Col xs={12} lg={6}><Card><Statistic title="Черновики" value={items.filter((item) => item.status === 'draft').length} /></Card></Col><Col xs={12} lg={6}><Card><Statistic title="На согласовании" value={items.filter((item) => item.status === 'pending_approval').length} /></Card></Col><Col xs={12} lg={6}><Card><Statistic title="Согласованы" value={items.filter((item) => item.status === 'approved' || item.status === 'executed').length} /></Card></Col></Row>
      <Card className="workspace-card order-workspace"><div className="order-filters"><Input allowClear prefix={<SearchOutlined />} placeholder="Номер, название или содержимое…" value={draftSearch} onChange={(event: React.ChangeEvent<HTMLInputElement>) => setDraftSearch(event.target.value)} onPressEnter={() => updateFilters({ search: draftSearch || undefined })} /><Button type="primary" onClick={() => updateFilters({ search: draftSearch || undefined })}>Найти</Button><Select allowClear placeholder="Все типы" value={filters.type} options={Object.entries(orderTypeLabels).map(([value, label]) => ({ value, label }))} onChange={(type?: OrderType) => updateFilters({ type })} /><Select allowClear placeholder="Все статусы" value={filters.status} options={Object.entries(orderStatusLabels).map(([value, label]) => ({ value, label }))} onChange={(status?: OrderStatus) => updateFilters({ status })} /><Button onClick={() => { setDraftSearch(''); setFilters(emptyFilters) }}>Сбросить</Button></div><Table<Order> rowKey="id" columns={columns} dataSource={items} loading={loading} pagination={pagination} scroll={{ x: 1060 }} onChange={(next: TablePaginationConfig) => setFilters((current) => ({ ...current, page: next.current ?? 1, pageSize: next.pageSize ?? current.pageSize }))} onRow={(order: Order) => ({ onClick: () => setSelectedOrder(order) })} rowClassName="order-table-row" /></Card>
      <Drawer title={<div><span className="drawer-kicker">Карточка документа</span><strong>{selectedOrder?.number}</strong></div>} width={760} open={Boolean(selectedOrder)} onClose={() => setSelectedOrder(undefined)} extra={selectedOrder && canCreate && selectedOrder.status !== 'executed' && <Button icon={<EditOutlined />} onClick={() => { setFormOrder(selectedOrder); setFormOpen(true) }}>Редактировать</Button>}>
        {selectedOrder && <><div className="order-card-header"><Tag color={statusColors[selectedOrder.status]}>{orderStatusLabels[selectedOrder.status]}</Tag><Tag>Версия {selectedOrder.version}</Tag><h2>{selectedOrder.template.name}</h2><p>{selectedOrder.template.description}</p></div><Steps size="small" current={workflowIndex} status={selectedOrder.status === 'rejected' ? 'error' : 'process'} items={[{ title: 'Черновик' }, { title: selectedOrder.status === 'rejected' ? 'Отклонён' : 'Согласование' }, { title: 'Согласован' }, { title: 'Исполнен' }]} /><Descriptions column={1} bordered size="small" className="order-details">{selectedOrder.template.fieldSchema.map((field) => <Descriptions.Item key={field.key} label={field.label}>{String(selectedOrder.fields[field.key] ?? '—')}</Descriptions.Item>)}</Descriptions>{selectedOrder.rejectionReason && <div className="order-rejection"><CloseOutlined /><span><strong>Причина отклонения</strong><small>{selectedOrder.rejectionReason}</small></span></div>}<Card size="small" title="История документа" className="order-history"><Timeline items={[...selectedOrder.history].reverse().map((item) => ({ color: item.status === 'rejected' ? 'red' : item.status === 'approved' || item.status === 'executed' ? 'green' : 'blue', children: <div><strong>{orderStatusLabels[item.status]}</strong><span>{item.actorName} · {formatDateTime(item.createdAt)}</span>{item.comment && <small>{item.comment}</small>}</div> }))} /></Card><Space wrap className="order-actions"><Button icon={<EyeOutlined />} onClick={() => setPreviewOpen(true)}>Предпросмотр</Button><Button icon={<DownloadOutlined />} onClick={() => void download(selectedOrder)}>Скачать DOCX</Button><Tooltip title="PDF будет формировать backend через LibreOffice"><Button disabled>Скачать PDF</Button></Tooltip>{selectedOrder.status === 'draft' && canCreate && <Button type="primary" icon={<SendOutlined />} onClick={() => void sendOrderForApproval(selectedOrder.id, user).then((order) => updateSelected(order, 'Отправлено на согласование'))}>На согласование</Button>}{selectedOrder.status === 'pending_approval' && canApprove && <><Button type="primary" icon={<CheckOutlined />} onClick={() => void approveOrder(selectedOrder.id, user).then((order) => updateSelected(order, 'Документ согласован'))}>Согласовать</Button><Button danger icon={<CloseOutlined />} onClick={() => setRejectOpen(true)}>Отклонить</Button></>}{selectedOrder.status === 'approved' && canCreate && <Button type="primary" icon={<FileDoneOutlined />} onClick={() => void executeOrder(selectedOrder.id, user).then((order) => updateSelected(order, 'Документ исполнен'))}>Отметить исполненным</Button>}</Space></>}
      </Drawer>
      <OrderForm open={formOpen} order={formOrder} saving={saving} onCancel={() => setFormOpen(false)} onSave={save} />
      <Modal title={`Предпросмотр ${selectedOrder?.number ?? ''}`} open={previewOpen} onCancel={() => setPreviewOpen(false)} footer={<Button onClick={() => setPreviewOpen(false)}>Закрыть</Button>} width={760}>{selectedOrder && <div className="document-preview"><h2>{selectedOrder.template.name}</h2><p><strong>{selectedOrder.number}</strong> · версия {selectedOrder.version}</p>{selectedOrder.template.fieldSchema.map((field) => <div key={field.key}><span>{field.label}</span><strong>{String(selectedOrder.fields[field.key] ?? '—')}</strong></div>)}<small>Демонстрационный предпросмотр. Окончательное оформление определяется серверным DOCX-шаблоном.</small></div>}</Modal>
      <Modal title={`Отклонение ${selectedOrder?.number ?? ''}`} open={rejectOpen} onCancel={() => setRejectOpen(false)} onOk={() => void reject()} okText="Отклонить" okButtonProps={{ danger: true }} cancelText="Отмена"><Form form={rejectForm} layout="vertical"><Form.Item name="reason" label="Причина отклонения" rules={[{ required: true, whitespace: true, message: 'Укажите причину отклонения' }]}><Input.TextArea rows={4} maxLength={1000} showCount /></Form.Item></Form></Modal>
    </div>
  )
}
