/** Author: Dev2 | Date: 2026-07-16 | Purpose: Detailed asset drawer with movement and repair history. */
import { EditOutlined } from '@ant-design/icons'
import { Button, Descriptions, Drawer, Empty, Table, Tabs, Tag } from 'antd'
import type { TableColumnsType } from 'antd'
import { assetStatusLabels } from '../api/assets'
import type { Asset, Movement, Repair } from '../types/asset'

const statusColors = { in_use: 'green', repair: 'gold', written_off: 'default', in_stock: 'cyan' } as const
const formatDate = (value?: string) => value ? new Intl.DateTimeFormat('ru-RU').format(new Date(value)) : '—'

const movementColumns: TableColumnsType<Movement> = [
  { title: 'Дата', dataIndex: 'movedAt', width: 120, render: formatDate },
  { title: 'Откуда', dataIndex: 'fromLocation', render: (value?: string) => value || '—' },
  { title: 'Куда', dataIndex: 'toLocation' },
  { title: 'Инициатор', dataIndex: 'initiatorName' },
  { title: 'Комментарий', dataIndex: 'comment', render: (value?: string) => value || '—' },
]

const repairColumns: TableColumnsType<Repair> = [
  { title: 'Открыт', dataIndex: 'openedAt', width: 110, render: formatDate },
  { title: 'Закрыт', dataIndex: 'closedAt', width: 110, render: formatDate },
  { title: 'Причина', dataIndex: 'description' },
  { title: 'Результат', dataIndex: 'result', render: (value?: string) => value || 'В работе' },
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
        { key: 'repairs', label: `Ремонты (${asset.repairs.length})`, children: asset.repairs.length ? <Table rowKey="id" size="small" pagination={false} columns={repairColumns} dataSource={asset.repairs} scroll={{ x: 560 }} /> : <Empty description="Ремонтов пока нет" /> },
      ]} />
    </Drawer>
  )
}
