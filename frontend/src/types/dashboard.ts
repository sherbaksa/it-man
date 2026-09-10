/** Author: Dev2 | Date: 2026-09-10 | Purpose: Frontend view models for the real management dashboard API. */
export interface TicketTrendPoint {
  date: string
  label: string
  created: number
  closed: number
}

export interface ProblemCategory {
  name: string
  count: number
}

export interface MonitoringSummary {
  ok: number
  warning: number
  critical: number
  unknown: number
}

export interface ExecutiveSummary {
  openTickets: number
  criticalTickets: number
  averageResolutionHours: number
  monitoring: MonitoringSummary
  trend: TicketTrendPoint[]
  problemCategories: ProblemCategory[]
}
