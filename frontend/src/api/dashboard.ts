/** Author: Dev2 | Date: 2026-07-16 | Purpose: Local management aggregates matching future dashboard endpoints. */
import { getTickets } from './tickets'
import type { ExecutiveSummary } from '../types/dashboard'
import { buildExecutiveSummary } from '../utils/executiveSummary'

export async function getExecutiveSummary(): Promise<ExecutiveSummary> {
  const { items } = await getTickets({ page: 1, pageSize: 1_000 })
  return buildExecutiveSummary(items)
}
