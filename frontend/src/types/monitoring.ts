/** Author: Dev2 | Date: 2026-09-09 | Purpose: Frontend monitoring view models for the real F08 API. */
export type MonitoringState = 'ok' | 'warning' | 'critical' | 'unknown'
export type MonitoringSource = 'zabbix' | 'kaspersky'

export interface MonitoringAssetRef {
  id: string
  inventoryNumber: string
  model?: string
}

export interface MonitoringHost {
  id: string
  hostIdentifier: string
  displayName: string
  status: MonitoringState
  lastValue: string
  source: MonitoringSource
  updatedAt: string
  asset?: MonitoringAssetRef
}

export interface MonitoringHistoryPoint {
  timestamp: string
  status: MonitoringState
  value: string
  level: number
}

export interface MonitoringFilters {
  page: number
  pageSize: number
  search?: string
  status?: MonitoringState
  source?: MonitoringSource
}

export interface MonitoringListResponse {
  items: MonitoringHost[]
  total: number
  summary: Record<MonitoringState, number>
}
