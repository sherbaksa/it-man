/** Author: Dev2 | Date: 2026-07-16 | Purpose: Paginated inventory workspace backed by a replaceable local API adapter. */
import { DownloadOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Card, Col, Form, Input, Modal, Row, Select, Space, Statistic, Table, Tag, message } from 'antd'
import type { TableColumnsType, TablePaginationConfig } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { assetLocations, assetStatusLabels, assetTypes, exportAssets, getAssets, saveAsset } from '../api/assets'
import AssetCard from '../components/AssetCard'
import type { Asset, AssetFilters, AssetFormValues, AssetStatus } from '../types/asset'
import { downloadBlob } from '../utils/downloadBlob'

const statusColors = { in_use: 'green', repair: 'gold', written_off: 'default', in_stock: 'cyan' } as const
const emptyFilters: AssetFilters = { page: 1, pageSize: 8 }

export default function Inventory() {
  const [filters, setFilters] = useState<AssetFilters>(emptyFilters)
  const [draftSearch, setDraftSearch] = useState('')
  const [items, setItems] = useState<Asset[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [selectedAsset, setSelectedAsset] = useState<Asset>()
  const [formAsset, setFormAsset] = useState<Asset | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm<AssetFormValues>()
  const [messageApi, contextHolder] = message.useMessage()

  const loadAssets = useCallback(async () => {
    setLoading(true)
    try {
      const result = await getAssets(filters)
      setItems(result.items)
      setTotal(result.total)
    } catch {
      messageApi.error('Не удалось загрузить список активов')
    } finally {
      setLoading(false)
    }
  }, [filters, messageApi])

  useEffect(() => { void loadAssets() }, [loadAssets])

  const columns: TableColumnsType<Asset> = [
    { title: 'Инв. номер', dataIndex: 'inventoryNumber', width: 135, sorter: (a, b) => a.inventoryNumber.localeCompare(b.inventoryNumber), render: (value: string) => <strong className="inventory-number">{value}</strong> },
    { title: 'Тип', dataIndex: ['type', 'name'], width: 170 },
    { title: 'Модель', dataIndex: 'model', ellipsis: true, render: (value?: string) => value || '—' },
    { title: 'Серийный номер', dataIndex: 'serialNumber', width: 150, render: (value?: string) => value || '—' },
    { title: 'Статус', dataIndex: 'status', width: 120, render: (status: AssetStatus) => <Tag color={statusColors[status]}>{assetStatusLabels[status]}</Tag> },
    { title: 'Расположение', dataIndex: 'location', width: 180, ellipsis: true, render: (value?: string) => value || '—' },
    { title: 'Ответственный', dataIndex: ['responsibleUser', 'fullName'], width: 170, render: (value?: string) => value || 'Не назначен' },
  ]

  const updateFilters = (next: Partial<AssetFilters>) => setFilters((current) => ({ ...current, ...next, page: next.page ?? 1 }))

  const openForm = (asset?: Asset) => {
    setFormAsset(asset ?? null)
    form.resetFields()
    form.setFieldsValue(asset ? {
      inventoryNumber: asset.inventoryNumber, typeId: asset.type.id, serialNumber: asset.serialNumber,
      model: asset.model, purchaseDate: asset.purchaseDate, status: asset.status, location: asset.location,
      responsibleName: asset.responsibleUser?.fullName, ipAddress: asset.ipAddress, hostname: asset.hostname,
    } : { inventoryNumber: '', status: 'in_stock' })
    setFormOpen(true)
  }

  const submitForm = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      const saved = await saveAsset(values, formAsset?.id)
      setFormOpen(false)
      setSelectedAsset(selectedAsset?.id === saved.id ? saved : selectedAsset)
      await loadAssets()
      messageApi.success(formAsset ? 'Карточка актива обновлена' : 'Актив добавлен')
    } catch (error) {
      if (error instanceof Error) messageApi.error('Не удалось сохранить актив')
    } finally {
      setSaving(false)
    }
  }

  const downloadReport = async () => {
    try {
      const blob = await exportAssets(filters)
      downloadBlob(blob, `assets-${new Date().toISOString().slice(0, 10)}.xlsx`)
      messageApi.success('Отчёт Excel сформирован')
    } catch {
      messageApi.error('Не удалось сформировать отчёт Excel')
    }
  }

  const pagination: TablePaginationConfig = { current: filters.page, pageSize: filters.pageSize, total, showSizeChanger: true, pageSizeOptions: [8, 16, 32], showTotal: (value: number) => `Всего: ${value}` }

  return (
    <div className="page-container inventory-page">
      {contextHolder}
      <div className="page-heading"><div><span className="eyebrow">Учёт оборудования</span><h1>Инвентаризация</h1><p>Активы, размещение, ответственные и техническое состояние</p></div><Space wrap><Button icon={<DownloadOutlined />} onClick={() => void downloadReport()}>Скачать отчёт .xlsx</Button><Button type="primary" icon={<PlusOutlined />} onClick={() => openForm()}>Добавить актив</Button></Space></div>
      <div className="prototype-notice">Локальный режим · фильтрация и постраничная загрузка имитируют будущий API</div>
      <Row gutter={[14, 14]} className="inventory-stats">
        <Col xs={12} lg={6}><Card><Statistic title="Найдено активов" value={total} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="На этой странице" value={items.length} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="В ремонте" value={items.filter((item) => item.status === 'repair').length} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="На складе" value={items.filter((item) => item.status === 'in_stock').length} /></Card></Col>
      </Row>
      <Card className="workspace-card inventory-workspace">
        <div className="inventory-filters">
          <Input allowClear prefix={<SearchOutlined />} placeholder="Инвентарный номер, модель, серийный номер…" value={draftSearch} onChange={(event: React.ChangeEvent<HTMLInputElement>) => setDraftSearch(event.target.value)} onPressEnter={() => updateFilters({ search: draftSearch || undefined })} />
          <Button type="primary" onClick={() => updateFilters({ search: draftSearch || undefined })}>Найти</Button>
          <Select allowClear placeholder="Все типы" value={filters.typeId} options={assetTypes.map((type) => ({ value: type.id, label: type.name }))} onChange={(typeId?: string) => updateFilters({ typeId })} />
          <Select allowClear placeholder="Все статусы" value={filters.status} options={Object.entries(assetStatusLabels).map(([value, label]) => ({ value, label }))} onChange={(status?: AssetStatus) => updateFilters({ status })} />
          <Select allowClear showSearch placeholder="Все расположения" value={filters.location} options={assetLocations.map((location) => ({ value: location, label: location }))} onChange={(location?: string) => updateFilters({ location })} />
          <Button onClick={() => { setDraftSearch(''); setFilters(emptyFilters) }}>Сбросить</Button>
        </div>
        <Table<Asset> rowKey="id" columns={columns} dataSource={items} loading={loading} pagination={pagination} scroll={{ x: 1120 }} onChange={(next: TablePaginationConfig) => setFilters((current) => ({ ...current, page: next.current ?? 1, pageSize: next.pageSize ?? current.pageSize }))} onRow={(asset: Asset) => ({ onClick: () => setSelectedAsset(asset) })} rowClassName="inventory-row" />
      </Card>
      <AssetCard asset={selectedAsset} open={Boolean(selectedAsset)} onClose={() => setSelectedAsset(undefined)} onEdit={(asset) => openForm(asset)} />
      <Modal title={formAsset ? `Редактирование ${formAsset.inventoryNumber}` : 'Новый актив'} open={formOpen} onCancel={() => setFormOpen(false)} onOk={() => void submitForm()} confirmLoading={saving} okText="Сохранить" cancelText="Отмена" width={720}>
        <Form form={form} layout="vertical" className="asset-form">
          <Form.Item name="inventoryNumber" label="Инвентарный номер" rules={[{ required: true, message: 'Укажите инвентарный номер' }, { max: 50 }]}><Input placeholder="INV-00001" /></Form.Item>
          <Form.Item name="typeId" label="Тип оборудования" rules={[{ required: true, message: 'Выберите тип' }]}><Select options={assetTypes.map((type) => ({ value: type.id, label: type.name }))} /></Form.Item>
          <Form.Item name="status" label="Статус" rules={[{ required: true }]}><Select options={Object.entries(assetStatusLabels).map(([value, label]) => ({ value, label }))} /></Form.Item>
          <Form.Item name="model" label="Модель"><Input /></Form.Item><Form.Item name="serialNumber" label="Серийный номер"><Input /></Form.Item><Form.Item name="purchaseDate" label="Дата приобретения"><Input type="date" /></Form.Item>
          <Form.Item name="location" label="Расположение"><Input placeholder="Кабинет или подразделение" /></Form.Item><Form.Item name="responsibleName" label="Ответственный"><Input placeholder="ФИО" /></Form.Item><Form.Item name="hostname" label="Hostname"><Input /></Form.Item>
          <Form.Item name="ipAddress" label="IP-адрес" rules={[{ pattern: /^(?:\d{1,3}\.){3}\d{1,3}$/, message: 'Введите IPv4-адрес' }]}><Input placeholder="192.0.2.10" /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
