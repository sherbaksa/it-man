/** Author: Dev2 | Date: 2026-07-16 | Purpose: Local F08 adapter shaped for future monitoring API B13. */
import type { MonitoringFilters, MonitoringHistoryPoint, MonitoringHost, MonitoringListResponse, MonitoringState } from '../types/monitoring'

export const monitoringStateLabels: Record<MonitoringState, string> = {
  ok: 'Работает',
  warning: 'Предупреждение',
  critical: 'Критический',
  unknown: 'Нет данных',
}

export const monitoringSourceLabels = { zabbix: 'Zabbix', kaspersky: 'Kaspersky' } as const
export const monitoringStateLevels: Record<MonitoringState, number> = { unknown: 0, ok: 1, warning: 2, critical: 3 }

const hosts: MonitoringHost[] = [
  { id: 'mon-1', hostIdentifier: '192.0.2.11', displayName: 'archive-01', status: 'ok', lastValue: 'Доступен · ping 2 мс', source: 'zabbix', updatedAt: '2026-07-16T05:27:00Z', location: 'Серверная', availability24h: 99.99, asset: { id: 'asset-6', inventoryNumber: 'INV-00236', model: 'Dell PowerEdge R540' } },
  { id: 'mon-2', hostIdentifier: '192.0.2.5', displayName: 'switch-core-02', status: 'warning', lastValue: 'Загрузка порта uplink 87%', source: 'zabbix', updatedAt: '2026-07-16T05:26:00Z', location: 'Серверная', availability24h: 99.72, asset: { id: 'asset-4', inventoryNumber: 'INV-00234', model: 'MikroTik CRS326-24G' } },
  { id: 'mon-3', hostIdentifier: '192.0.2.21', displayName: 'ups-main', status: 'critical', lastValue: 'Заряд батареи 14%', source: 'zabbix', updatedAt: '2026-07-16T05:28:00Z', location: 'Серверная', availability24h: 96.41, asset: { id: 'asset-8', inventoryNumber: 'INV-00237', model: 'ИБП APC Smart-UPS 1500' } },
  { id: 'mon-4', hostIdentifier: '203.0.113.20', displayName: 'wifi-pol-2', status: 'ok', lastValue: 'Доступен · ping 5 мс', source: 'zabbix', updatedAt: '2026-07-16T05:25:00Z', location: 'Поликлиника, 2 этаж', availability24h: 100, asset: { id: 'asset-10', inventoryNumber: 'INV-00239', model: 'TP-Link EAP660 HD' } },
  { id: 'mon-5', hostIdentifier: '198.51.100.31', displayName: 'print-205', status: 'unknown', lastValue: 'Нет данных 38 минут', source: 'zabbix', updatedAt: '2026-07-16T04:50:00Z', location: 'Кабинет 205', availability24h: 97.36, asset: { id: 'asset-1', inventoryNumber: 'INV-00231', model: 'HP LaserJet Pro M404dn' } },
  { id: 'mon-6', hostIdentifier: '198.51.100.14', displayName: 'reg-02', status: 'ok', lastValue: 'Защита актуальна', source: 'kaspersky', updatedAt: '2026-07-16T05:20:00Z', location: 'Регистратура', availability24h: 99.98, asset: { id: 'asset-2', inventoryNumber: 'INV-00232', model: 'Aquarius Pro P30' } },
  { id: 'mon-7', hostIdentifier: '203.0.113.12', displayName: 'pc-312-01', status: 'warning', lastValue: 'Базы устарели на 3 дня', source: 'kaspersky', updatedAt: '2026-07-16T05:18:00Z', location: 'Кабинет 312', availability24h: 99.15, asset: { id: 'asset-5', inventoryNumber: 'INV-00235', model: 'Depo Neos MF4' } },
  { id: 'mon-8', hostIdentifier: '198.51.100.32', displayName: 'pc-206-01', status: 'ok', lastValue: 'Угроз не обнаружено', source: 'kaspersky', updatedAt: '2026-07-16T05:16:00Z', location: 'Кабинет 206', availability24h: 100, asset: { id: 'asset-12', inventoryNumber: 'INV-00241', model: 'Aquarius Pro P30' } },
]

const sequenceByHost: Record<string, MonitoringState[]> = {
  '192.0.2.5': ['ok', 'ok', 'warning', 'ok', 'warning', 'warning', 'warning', 'warning'],
  '192.0.2.21': ['ok', 'warning', 'warning', 'critical', 'warning', 'critical', 'critical', 'critical'],
  '198.51.100.31': ['ok', 'ok', 'ok', 'warning', 'unknown', 'unknown', 'unknown', 'unknown'],
  '203.0.113.12': ['ok', 'ok', 'ok', 'ok', 'warning', 'warning', 'warning', 'warning'],
}

const wait = () => new Promise((resolve) => window.setTimeout(resolve, 180))
const summarize = (items: MonitoringHost[]) => items.reduce<Record<MonitoringState, number>>((summary, host) => ({ ...summary, [host.status]: summary[host.status] + 1 }), { ok: 0, warning: 0, critical: 0, unknown: 0 })

export async function getMonitoringStatus(filters: MonitoringFilters): Promise<MonitoringListResponse> {
  await wait()
  const search = filters.search?.trim().toLocaleLowerCase('ru')
  const filtered = hosts.filter((host) =>
    (!search || [host.displayName, host.hostIdentifier, host.location, host.asset?.inventoryNumber, host.asset?.model].some((value) => value?.toLocaleLowerCase('ru').includes(search)))
    && (!filters.status || host.status === filters.status)
    && (!filters.source || host.source === filters.source),
  )
  const start = (filters.page - 1) * filters.pageSize
  return { items: filtered.slice(start, start + filters.pageSize), total: filtered.length, summary: summarize(hosts) }
}

export async function getMonitoringHistory(hostIdentifier: string): Promise<MonitoringHistoryPoint[]> {
  await wait()
  const host = hosts.find((item) => item.hostIdentifier === hostIdentifier)
  if (!host) return []
  const sequence = sequenceByHost[hostIdentifier] ?? ['ok', 'ok', 'ok', 'ok', 'ok', 'ok', host.status, host.status]
  const end = new Date(host.updatedAt).getTime()
  return sequence.map((status, index) => ({
    timestamp: new Date(end - (sequence.length - 1 - index) * 3 * 60 * 60 * 1000).toISOString(),
    status,
    level: monitoringStateLevels[status],
    value: index === sequence.length - 1 ? host.lastValue : monitoringStateLabels[status],
  }))
}
