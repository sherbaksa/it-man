/** Author: Dev2 | Date: 2026-09-09 | Purpose: Real F08 monitoring API adapter. */
import type { components } from './types'
import { apiClient } from './client'
import type { MonitoringFilters, MonitoringHistoryPoint, MonitoringHost, MonitoringListResponse, MonitoringState } from '../types/monitoring'

type ApiMonitoringStatus = components['schemas']['MonitoringStatusRead']
type ApiMonitoringList = components['schemas']['MonitoringStatusListResponse']
type ApiMonitoringHistory = components['schemas']['MonitoringHistoryResponse']

export const monitoringStateLabels: Record<MonitoringState, string> = {
  ok: 'Работает',
  warning: 'Предупреждение',
  critical: 'Критический',
  unknown: 'Нет данных',
}

export const monitoringSourceLabels = { zabbix: 'Zabbix', kaspersky: 'Kaspersky' } as const
export const monitoringStateLevels: Record<MonitoringState, number> = { unknown: 0, ok: 1, warning: 2, critical: 3 }

const summarize = (items: MonitoringHost[]) => items.reduce<Record<MonitoringState, number>>(
  (summary, host) => ({ ...summary, [host.status]: summary[host.status] + 1 }),
  { ok: 0, warning: 0, critical: 0, unknown: 0 },
)

function mapMonitoringHost(item: ApiMonitoringStatus): MonitoringHost {
  return {
    id: item.id,
    hostIdentifier: item.host_identifier,
    displayName: item.asset?.model || item.host_identifier,
    status: item.status,
    lastValue: item.last_value || 'Нет данных',
    source: item.source,
    updatedAt: item.checked_at,
    asset: item.asset ? {
      id: item.asset.id,
      inventoryNumber: item.asset.inventory_number,
      model: item.asset.model ?? undefined,
    } : undefined,
  }
}

export async function getMonitoringStatus(filters: MonitoringFilters): Promise<MonitoringListResponse> {
  const { data } = await apiClient.get<ApiMonitoringList>('/api/monitoring/status')
  const allItems = data.items.map(mapMonitoringHost)
  const search = filters.search?.trim().toLocaleLowerCase('ru')
  const filtered = allItems.filter((host) =>
    (!search || [host.displayName, host.hostIdentifier, host.lastValue, host.asset?.inventoryNumber, host.asset?.model]
      .some((value) => value?.toLocaleLowerCase('ru').includes(search)))
    && (!filters.status || host.status === filters.status)
    && (!filters.source || host.source === filters.source),
  )
  const start = (filters.page - 1) * filters.pageSize

  return {
    items: filtered.slice(start, start + filters.pageSize),
    total: filtered.length,
    summary: summarize(allItems),
  }
}

export async function getMonitoringHistory(hostIdentifier: string, from?: string, to?: string): Promise<MonitoringHistoryPoint[]> {
  const { data } = await apiClient.get<ApiMonitoringHistory>(
    `/api/monitoring/status/${encodeURIComponent(hostIdentifier)}/history`,
    { params: { from: from || undefined, to: to || undefined } },
  )

  return data.items
    .map((item) => ({
      timestamp: item.checked_at,
      status: item.status,
      level: monitoringStateLevels[item.status],
      value: item.last_value || 'Нет данных',
    }))
    .sort((left, right) => new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime())
}
