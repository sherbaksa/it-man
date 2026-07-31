/** Author: Dev2 | Date: 2026-07-16 | Purpose: Detailed asset drawer with movement and repair history. */
import { EditOutlined } from '@ant-design/icons'
import { Button, Descriptions, Drawer, Empty, Table, Tabs, Tag } from 'antd'
import type { TableColumnsType } from 'antd'
import { assetStatusLabels } from '../api/assets'
import type { Asset, Movement, Repair, RepairStatus } from '../types/asset'

const statusColors = { in_use: 'green', repair: 'gold', written_off: 'default', in_stock: 'cyan' } as const
const repairStatusLabels: Record<RepairStatus, string> = { planned: 'Запланирован', in_progress: 'В работе', done: 'Завершён', cancelled: 'Отменён' }
const repairStatusColors: Record<RepairStatus, string> = { planned: 'blue', in_progress: 'gold', done: 'green', cancelled: 'default' }
const formatDate = (value?: string) => value ? new Intl.DateTimeFormat('ru-RU').format(new Date(value)) : '—'

const movementColumns: TableColumnsType<Movement> = [
  { title: 'Дата', dataIndex: 'movedAt', width: 120, render: formatDate },
  { title: 'Откуда', dataIndex: 'fromLocation', render: (value?: string) => value || '—' },
  { title: 'Куда', dataIndex: 'toLocation' },
  { title: 'Инициатор', dataIndex: 'initiatorName' },
  { title: 'Комментарий', dataIndex: 'comment', render: (value?: string) => value || '—' },
]

const repairColumns: TableColumnsType<Repair> = [
  { title: 'Начало', dataIndex: 'startedAt', width: 110, render: formatDate },
  { title: 'Завершение', dataIndex: 'finishedAt', width: 110, render: formatDate },
  { title: 'Тип ремонта', dataIndex: 'repairType' },
  { title: 'Исполнитель', dataIndex: 'executor', render: (value?: string) => value || '—' },
  { title: 'Стоимость', dataIndex: 'cost', width: 110, render: (value?: string) => value ? `${value} ₽` : '—' },
  { title: 'Статус', dataIndex: 'status', width: 120, render: (value: RepairStatus) => <Tag color={repairStatusColors[value]}>{repairStatusLabels[value]}</Tag> },
]

interface AssetCardProps {
  asset?: Asset
  open: boolean
  onClose: () => void
  onEdit: (asset: Asset) => void
}

export default function AssetCard({ asset, open, onClose, onEdit }: AssetCardProps) {
  if (!asset) return null

  return (
    <Drawer title={<div><span className="drawer-kicker">Карточка актива</span><strong>{asset.inventoryNumber}</strong></div>} width={720} open={open} onClose={onClose} extra={<Button icon={<EditOutlined />} onClick={() => onEdit(asset)}>Редактировать</Button>}>
      <Tabs items={[
        { key: 'main', label: 'Основное', children: <Descriptions column={1} bordered size="small" className="asset-descriptions">
          <Descriptions.Item label="Инвентарный номер">{asset.inventoryNumber}</Descriptions.Item><Descriptions.Item label="Тип">{asset.type.name}</Descriptions.Item><Descriptions.Item label="Модель">{asset.model || '—'}</Descriptions.Item><Descriptions.Item label="Серийный номер">{asset.serialNumber || '—'}</Descriptions.Item><Descriptions.Item label="Статус"><Tag color={statusColors[asset.status]}>{assetStatusLabels[asset.status]}</Tag></Descriptions.Item><Descriptions.Item label="Расположение">{asset.location || '—'}</Descriptions.Item><Descriptions.Item label="Ответственный">{asset.responsibleUser?.fullName || 'Не назначен'}</Descriptions.Item><Descriptions.Item label="Дата приобретения">{formatDate(asset.purchaseDate)}</Descriptions.Item><Descriptions.Item label="Hostname">{asset.hostname || '—'}</Descriptions.Item><Descriptions.Item label="IP-адрес">{asset.ipAddress || '—'}</Descriptions.Item>
        </Descriptions> },
        { key: 'movements', label: `История перемещений (${asset.movements.length})`, children: asset.movements.length ? <Table rowKey="id" size="small" pagination={false} columns={movementColumns} dataSource={asset.movements} scroll={{ x: 620 }} /> : <Empty description="Перемещений пока нет" /> },
        { key: 'repairs', label: `Ремонты (${asset.repairs.length})`, children: asset.repairs.length ? <Table rowKey="id" size="small" pagination={false} columns={repairColumns} dataSource={asset.repairs} scroll={{ x: 760 }} /> : <Empty description="Ремонтов пока нет" /> },
      ]} />
    </Drawer>
  )
}
