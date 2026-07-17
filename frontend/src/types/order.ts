/** Author: Dev2 | Date: 2026-07-16 | Purpose: ORD document, template and dynamic form contracts. */
import type { TicketPerson } from './ticket'

export type OrderType = 'purchase_request' | 'write_off_act' | 'work_order'
export type OrderStatus = 'draft' | 'pending_approval' | 'approved' | 'executed' | 'rejected'
export type OrderFieldType = 'text' | 'textarea' | 'number' | 'date' | 'select'
export type OrderFieldValue = string | number

export interface OrderFieldDefinition {
  key: string
  label: string
  type: OrderFieldType
  required?: boolean
  placeholder?: string
  options?: string[]
  defaultValue?: OrderFieldValue
}

export interface DocumentTemplate {
  id: string
  name: string
  type: OrderType
  description: string
  fieldSchema: OrderFieldDefinition[]
}

export interface OrderEvent {
  id: string
  status: OrderStatus
  actorName: string
  createdAt: string
  comment?: string
}

export interface Order {
  id: string
  number: string
  template: DocumentTemplate
  fields: Record<string, OrderFieldValue>
  status: OrderStatus
  author: TicketPerson
  approver?: TicketPerson
  rejectionReason?: string
  createdAt: string
  approvedAt?: string
  version: number
  history: OrderEvent[]
}

export interface OrderFilters {
  page: number
  pageSize: number
  search?: string
  status?: OrderStatus
  type?: OrderType
}

export interface OrderListResponse {
  items: Order[]
  total: number
}

export interface OrderFormValues {
  templateId: string
  fields: Record<string, OrderFieldValue>
}
