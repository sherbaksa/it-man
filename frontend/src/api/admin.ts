/** Author: Dev2 | Date: 2026-07-16 | Purpose: Local F09 administration adapter compatible with future B04/B16 APIs. */
import type { AdminDocumentTemplate, AdminSnapshot, AdminUser, AdminUserFormValues, DirectoryItem, DirectoryKind, IntegrationSetting } from '../types/admin'

let departments: DirectoryItem[] = [
  { id: 'dep-it', name: 'IT-отдел', isActive: true },
  { id: 'dep-admin', name: 'Администрация', isActive: true },
  { id: 'dep-polyclinic', name: 'Поликлиника', isActive: true },
  { id: 'dep-registry', name: 'Регистратура', isActive: true },
  { id: 'dep-diagnostics', name: 'Диагностика', isActive: true },
]

let equipmentTypes: DirectoryItem[] = [
  { id: 'type-computer', name: 'Компьютер', isActive: true },
  { id: 'type-printer', name: 'Принтер', isActive: true },
  { id: 'type-server', name: 'Сервер', isActive: true },
  { id: 'type-network', name: 'Сетевое оборудование', isActive: true },
  { id: 'type-other', name: 'Прочее', isActive: true },
]

let users: AdminUser[] = [
  { id: 'mock-admin', login: 'admin', fullName: 'Администратор Тестовый', role: 'Admin', departmentId: 'dep-it', departmentName: 'IT-отдел', position: 'Администратор платформы', email: 'admin@example.local', isActive: true },
  { id: 'mock-ithead', login: 'ithead', fullName: 'Руководитель ИТ', role: 'IT-Head', departmentId: 'dep-it', departmentName: 'IT-отдел', position: 'Руководитель IT-отдела', isActive: true },
  { id: 'mock-engineer', login: 'engineer', fullName: 'Инженер Тестовый', role: 'Engineer', departmentId: 'dep-it', departmentName: 'IT-отдел', position: 'IT-инженер', isActive: true },
  { id: 'mock-executive', login: 'executive', fullName: 'Руководитель Тестовый', role: 'Executive', departmentId: 'dep-admin', departmentName: 'Администрация', position: 'Руководство', isActive: true },
  { id: 'mock-user', login: 'user', fullName: 'Сотрудник Тестовый', role: 'User', departmentId: 'dep-registry', departmentName: 'Регистратура', position: 'Сотрудник', isActive: true },
]

let templates: AdminDocumentTemplate[] = [
  { id: 'template-purchase', name: 'Заявка на закупку оборудования', type: 'purchase_request', fileName: 'purchase_request.docx', fieldCount: 10, minApproverRole: 'IT-Head', isEnabled: true },
  { id: 'template-writeoff', name: 'Акт списания оборудования', type: 'write_off_act', fileName: 'write_off_act.docx', fieldCount: 5, minApproverRole: 'IT-Head', isEnabled: true },
  { id: 'template-work', name: 'Наряд на выполнение работ', type: 'work_order', fileName: 'work_order.docx', fieldCount: 6, minApproverRole: 'IT-Head', isEnabled: true },
]

const integrations: IntegrationSetting[] = [
  { code: 'zabbix', name: 'Zabbix', baseUrl: 'https://zabbix.example.local/api_jsonrpc.php', pollIntervalMinutes: 5, mode: 'Опрос + webhook', enabled: true, secretConfigured: true },
  { code: 'openproject', name: 'OpenProject', baseUrl: 'https://openproject.example.local/api/v3', pollIntervalMinutes: 15, mode: 'REST API + webhook', enabled: false, secretConfigured: false },
  { code: 'espocrm', name: 'EspoCRM', baseUrl: 'https://crm.example.local/api/v1', pollIntervalMinutes: 30, mode: 'REST API', enabled: false, secretConfigured: false },
  { code: 'n8n', name: 'n8n', baseUrl: 'https://n8n.example.local/webhook', mode: 'Входящие webhook', enabled: false, secretConfigured: false },
  { code: 'kaspersky', name: 'Kaspersky Security Center', baseUrl: 'https://ksc.example.local/api/v1.0', pollIntervalMinutes: 15, mode: 'Open API', enabled: false, secretConfigured: false },
]

const wait = () => new Promise((resolve) => window.setTimeout(resolve, 180))
const clone = <T>(value: T): T => structuredClone(value)
const directory = (kind: DirectoryKind) => kind === 'departments' ? departments : equipmentTypes
const replaceDirectory = (kind: DirectoryKind, items: DirectoryItem[]) => { if (kind === 'departments') departments = items; else equipmentTypes = items }

export async function getAdminSnapshot(): Promise<AdminSnapshot> {
  await wait()
  return clone({ users, departments, equipmentTypes, templates, integrations })
}

export async function saveAdminUser(values: AdminUserFormValues, id?: string): Promise<AdminUser> {
  await wait()
  const departmentName = departments.find((item) => item.id === values.departmentId)?.name ?? 'Не указано'
  const existing = users.find((user) => user.id === id)
  const saved: AdminUser = { ...values, id: existing?.id ?? `user-${Date.now()}`, departmentName, isActive: existing?.isActive ?? true }
  users = existing ? users.map((user) => user.id === id ? saved : user) : [...users, saved]
  return clone(saved)
}

export async function setAdminUserActive(id: string, isActive: boolean): Promise<AdminUser> {
  await wait()
  users = users.map((user) => user.id === id ? { ...user, isActive } : user)
  return clone(users.find((user) => user.id === id)!)
}

export async function saveDirectoryItem(kind: DirectoryKind, name: string, id?: string): Promise<DirectoryItem> {
  await wait()
  const items = directory(kind)
  const existing = items.find((item) => item.id === id)
  const saved = { id: existing?.id ?? `${kind}-${Date.now()}`, name: name.trim(), isActive: existing?.isActive ?? true }
  replaceDirectory(kind, existing ? items.map((item) => item.id === id ? saved : item) : [...items, saved])
  return clone(saved)
}

export async function deleteDirectoryItem(kind: DirectoryKind, id: string): Promise<void> {
  await wait()
  replaceDirectory(kind, directory(kind).filter((item) => item.id !== id))
}

export async function setTemplateEnabled(id: string, isEnabled: boolean): Promise<AdminDocumentTemplate> {
  await wait()
  templates = templates.map((template) => template.id === id ? { ...template, isEnabled } : template)
  return clone(templates.find((template) => template.id === id)!)
}
