/** Author: Dev2 | Date: 2026-07-16 | Purpose: F09 administration API contracts without secret values. */
import type { Role } from './auth'
import type { OrderType } from './order'

export interface AdminUser {
  id: string
  login: string
  fullName: string
  role: Role
  departmentId: string
  departmentName: string
  position?: string
  email?: string
  phone?: string
  isActive: boolean
}

export interface AdminUserFormValues {
  login: string
  fullName: string
  role: Role
  departmentId: string
  position?: string
  email?: string
  phone?: string
}

export type DirectoryKind = 'departments' | 'equipmentTypes'

export interface DirectoryItem {
  id: string
  name: string
  isActive: boolean
}

export interface AdminDocumentTemplate {
  id: string
  name: string
  type: OrderType
  fileName: string
  fieldCount: number
  minApproverRole: 'IT-Head' | 'Executive'
  isEnabled: boolean
}

export type IntegrationCode = 'zabbix' | 'openproject' | 'espocrm' | 'n8n' | 'kaspersky'

export interface IntegrationSetting {
  code: IntegrationCode
  name: string
  baseUrl: string
  pollIntervalMinutes?: number
  mode: string
  enabled: boolean
  secretConfigured: boolean
}

export interface AdminSnapshot {
  users: AdminUser[]
  departments: DirectoryItem[]
  equipmentTypes: DirectoryItem[]
  templates: AdminDocumentTemplate[]
  integrations: IntegrationSetting[]
}
