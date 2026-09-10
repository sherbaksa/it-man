/** Author: Dev2 | Date: 2026-09-10 | Purpose: Real management dashboard API adapter for F06. */
import { apiClient } from './client'
import type { components } from './types'
import type { ExecutiveSummary } from '../types/dashboard'

type ApiExecutiveSummary = components['schemas']['ExecutiveSummary']
type ApiMonitoringSummary = components['schemas']['MonitoringSummary']

const priorityLabels = {
  critical: 'Критические',
  high: 'Высокий приоритет',
  medium: 'Средний приоритет',
  low: 'Низкий приоритет',
} as const
const priorityRanks: Record<keyof typeof priorityLabels, number> = { critical: 4, high: 3, medium: 2, low: 1 }

const formatDayLabel = (date: string) => {
  const [year, month, day] = date.split('-')
  return year && month && day ? `${day}.${month}` : date
}

export async function getExecutiveSummary(): Promise<ExecutiveSummary> {
  const [{ data: dashboard }, { data: monitoring }] = await Promise.all([
    apiClient.get<ApiExecutiveSummary>('/api/dashboard/executive'),
    apiClient.get<ApiMonitoringSummary>('/api/monitoring/summary'),
  ])

  const problemCategories = (Object.entries(dashboard.priority_breakdown) as Array<[keyof typeof priorityLabels, number]>)
    .filter(([, count]) => count > 0)
    .sort(([leftPriority, leftCount], [rightPriority, rightCount]) => rightCount - leftCount || priorityRanks[rightPriority] - priorityRanks[leftPriority])
    .slice(0, 3)
    .map(([priority, count]) => ({ name: priorityLabels[priority], count }))

  return {
    openTickets: dashboard.open_tickets,
    criticalTickets: dashboard.priority_breakdown.critical,
    averageResolutionHours: dashboard.average_resolution_hours,
    monitoring,
    trend: dashboard.ticket_trend.map((point) => ({ ...point, label: formatDayLabel(point.date) })),
    problemCategories,
  }
}
