/** Author: Dev2 | Date: 2026-07-16 | Purpose: Ticket and attachment contracts compatible with the future API. */
import type { Asset } from './asset'

export type TicketPriority = 'low' | 'medium' | 'high' | 'critical'
export type TicketStatus = 'new' | 'in_progress' | 'done' | 'rejected'
export type TicketSource = 'web' | 'max' | 'zabbix_auto'

export interface TicketPerson {
  id: string
  fullName: string
}

export interface TicketAttachment {
  id: string
  fileName: string
  contentType: string
  sizeBytes: number
  downloadUrl: string
  createdAt: string
  canDelete: boolean
}

export interface Ticket {
  id: string
  number: string
  title: string
  description?: string
  priority: TicketPriority
  status: TicketStatus
  author: TicketPerson
  assignee?: TicketPerson
  asset?: Pick<Asset, 'id' | 'inventoryNumber' | 'model'>
  resolution?: string
  source: TicketSource
  createdAt: string
  closedAt?: string
  attachments: TicketAttachment[]
}

export interface TicketFilters {
  page: number
  pageSize: number
  status?: TicketStatus
  priority?: TicketPriority
  assigneeId?: string
}

export interface TicketListResponse {
  items: Ticket[]
  total: number
}

export interface TicketFormValues {
  title: string
  description?: string
  priority: TicketPriority
  assetId?: string
  assigneeId?: string
}
