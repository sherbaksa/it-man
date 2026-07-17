/** Author: Dev2 | Date: 2026-07-16 | Purpose: Management dashboard aggregate contracts for future API replacement. */
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
}

export interface ExecutiveSummary {
  openTickets: number
  criticalTickets: number
  completedTickets: number
  averageResolutionHours: number
  availabilityPercent: number
  monitoring: MonitoringSummary
  trend: TicketTrendPoint[]
  problemCategories: ProblemCategory[]
}
