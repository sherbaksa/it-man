/** Author: Dev2 | Date: 2026-07-16 | Purpose: Local assets adapter matching future paginated API behavior. */
import type { Asset, AssetFilters, AssetFormValues, AssetListResponse, AssetStatus, AssetType } from '../types/asset'
import * as XLSX from 'xlsx'

export const assetTypes: AssetType[] = [
  { id: 'computer', name: 'Компьютер' },
  { id: 'printer', name: 'Принтер' },
  { id: 'network', name: 'Сетевое оборудование' },
  { id: 'server', name: 'Сервер' },
  { id: 'other', name: 'Прочее' },
]

export const assetStatusLabels: Record<AssetStatus, string> = {
  in_use: 'В работе',
  repair: 'В ремонте',
  written_off: 'Списано',
  in_stock: 'На складе',
}

export const assetLocations = ['Архив', 'Бухгалтерия', 'Кабинет 101', 'Кабинет 205', 'Кабинет 206', 'Кабинет 312', 'Поликлиника, 2 этаж', 'Регистратура', 'Серверная', 'Склад IT']

const now = '2026-07-16T04:00:00.000Z'
let assets: Asset[] = [
  ['asset-1', 'INV-00231', 'printer', 'HP LaserJet Pro M404dn', 'SN-HPM404-7841', 'Кабинет 205', 'in_use', 'Ответственный 01', '198.51.100.31', 'print-205'],
  ['asset-2', 'INV-00232', 'computer', 'Aquarius Pro P30', 'AQ-P30-1182', 'Регистратура', 'in_use', 'Ответственный 02', '198.51.100.14', 'reg-02'],
  ['asset-3', 'INV-00233', 'printer', 'Pantum M7100DN', 'PT-M7100-0419', 'Склад IT', 'in_stock', '', '', ''],
  ['asset-4', 'INV-00234', 'network', 'MikroTik CRS326-24G', 'MT-CRS-2208', 'Серверная', 'in_use', 'Инженер Тестовый', '192.0.2.5', 'switch-core-02'],
  ['asset-5', 'INV-00235', 'computer', 'Depo Neos MF4', 'DP-MF4-5520', 'Кабинет 312', 'repair', 'Ответственный 03', '', 'pc-312-01'],
  ['asset-6', 'INV-00236', 'server', 'Dell PowerEdge R540', 'DE-R540-9981', 'Серверная', 'in_use', 'Инженер Тестовый', '192.0.2.11', 'archive-01'],
  ['asset-7', 'INV-00105', 'printer', 'HP LaserJet P1102', 'SN-P1102-0101', 'Архив', 'written_off', '', '', ''],
  ['asset-8', 'INV-00237', 'other', 'ИБП APC Smart-UPS 1500', 'APC-1500-7732', 'Серверная', 'in_use', 'Инженер Тестовый', '192.0.2.21', 'ups-main'],
  ['asset-9', 'INV-00238', 'computer', 'IRU Office 310', 'IRU-310-4221', 'Кабинет 101', 'in_stock', '', '', ''],
  ['asset-10', 'INV-00239', 'network', 'TP-Link EAP660 HD', 'TPL-660-8301', 'Поликлиника, 2 этаж', 'in_use', 'Ответственный 04', '203.0.113.20', 'wifi-pol-2'],
  ['asset-11', 'INV-00240', 'printer', 'Kyocera ECOSYS M2040dn', 'KYO-2040-0074', 'Бухгалтерия', 'repair', 'Ответственный 05', '', 'print-buh-01'],
  ['asset-12', 'INV-00241', 'computer', 'Aquarius Pro P30', 'AQ-P30-1220', 'Кабинет 206', 'in_use', 'Ответственный 06', '198.51.100.32', 'pc-206-01'],
].map(([id, inventoryNumber, typeId, model, serialNumber, location, status, responsibleName, ipAddress, hostname], index) => ({
  id,
  inventoryNumber,
  type: assetTypes.find((type) => type.id === typeId)!,
  model,
  serialNumber,
  purchaseDate: `202${index % 5}-0${(index % 8) + 1}-15`,
  location,
  status: status as AssetStatus,
  responsibleUser: responsibleName ? { id: responsibleName === 'Инженер Тестовый' ? 'mock-engineer' : `user-${index}`, fullName: responsibleName } : undefined,
  ipAddress: ipAddress || undefined,
  hostname: hostname || undefined,
  createdAt: now,
  updatedAt: now,
  movements: index % 3 === 0 ? [{ id: `movement-${index}`, fromLocation: 'Склад IT', toLocation: location, initiatorName: 'Инженер Тестовый', movedAt: `2026-0${(index % 6) + 1}-12T06:30:00Z`, comment: 'Передача в эксплуатацию' }] : [],
  repairs: status === 'repair' ? [{ id: `repair-${index}`, openedAt: '2026-07-12T02:15:00Z', description: 'Диагностика неисправности оборудования' }] : [],
}))

const wait = () => new Promise((resolve) => window.setTimeout(resolve, 250))

export async function getAssets(filters: AssetFilters): Promise<AssetListResponse> {
  await wait()
  const search = filters.search?.trim().toLocaleLowerCase('ru')
  const filtered = assets.filter((asset) => {
    const matchesSearch = !search || [asset.inventoryNumber, asset.model, asset.serialNumber, asset.hostname, asset.responsibleUser?.fullName].some((value) => value?.toLocaleLowerCase('ru').includes(search))
    return matchesSearch && (!filters.status || asset.status === filters.status) && (!filters.typeId || asset.type.id === filters.typeId) && (!filters.location || asset.location === filters.location) && (!filters.responsibleUserId || asset.responsibleUser?.id === filters.responsibleUserId)
  })
  const start = (filters.page - 1) * filters.pageSize
  return { items: filtered.slice(start, start + filters.pageSize), total: filtered.length }
}

export async function getAssetById(id?: string): Promise<Asset | undefined> {
  await wait()
  return assets.find((asset) => asset.id === id)
}

export async function saveAsset(values: AssetFormValues, id?: string): Promise<Asset> {
  await wait()
  const existing = assets.find((asset) => asset.id === id)
  const type = assetTypes.find((item) => item.id === values.typeId)!
  const next: Asset = {
    id: existing?.id ?? `asset-${Date.now()}`,
    inventoryNumber: values.inventoryNumber.trim(), type,
    serialNumber: values.serialNumber?.trim() || undefined, model: values.model?.trim() || undefined,
    purchaseDate: values.purchaseDate || undefined, status: values.status,
    location: values.location?.trim() || undefined,
    responsibleUser: values.responsibleName?.trim() ? { id: existing?.responsibleUser?.id ?? `user-${Date.now()}`, fullName: values.responsibleName.trim() } : undefined,
    ipAddress: values.ipAddress?.trim() || undefined, hostname: values.hostname?.trim() || undefined,
    createdAt: existing?.createdAt ?? new Date().toISOString(), updatedAt: new Date().toISOString(),
    movements: existing?.movements ?? [], repairs: existing?.repairs ?? [],
  }
  assets = existing ? assets.map((asset) => asset.id === id ? next : asset) : [next, ...assets]
  return next
}

export function createAssetWorkbook(items: Asset[]): ArrayBuffer {
  const rows = items.map((asset) => [
    asset.inventoryNumber,
    asset.type.name,
    asset.model ?? '',
    asset.serialNumber ?? '',
    assetStatusLabels[asset.status],
    asset.location ?? '',
    asset.responsibleUser?.fullName ?? '',
    asset.purchaseDate ?? '',
    asset.hostname ?? '',
    asset.ipAddress ?? '',
  ])
  const worksheet = XLSX.utils.aoa_to_sheet([
    ['Инвентарный номер', 'Тип', 'Модель', 'Серийный номер', 'Статус', 'Расположение', 'Ответственный', 'Дата приобретения', 'Hostname', 'IP-адрес'],
    ...rows,
  ])
  worksheet['!cols'] = [
    { wch: 20 }, { wch: 24 }, { wch: 28 }, { wch: 22 }, { wch: 14 },
    { wch: 24 }, { wch: 24 }, { wch: 18 }, { wch: 20 }, { wch: 16 },
  ]
  worksheet['!autofilter'] = { ref: worksheet['!ref'] ?? 'A1:J1' }

  const workbook = XLSX.utils.book_new()
  workbook.Props = { Title: 'Отчёт по инвентаризации', Subject: 'Активы IT-инфраструктуры', Author: 'IT Management' }
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Инвентаризация')
  return XLSX.write(workbook, { bookType: 'xlsx', type: 'array', compression: true }) as ArrayBuffer
}

export async function exportAssets(filters: AssetFilters): Promise<Blob> {
  const result = await getAssets({ ...filters, page: 1, pageSize: 10_000 })
  const content = createAssetWorkbook(result.items)
  return new Blob([content], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
}
