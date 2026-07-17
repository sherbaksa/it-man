/** Author: Dev2 | Date: 2026-07-16 | Purpose: F09 admin workspace for users, directories, templates and integration settings. */
import { ApiOutlined, DeleteOutlined, EditOutlined, FileTextOutlined, PlusOutlined, SafetyCertificateOutlined, SearchOutlined, TeamOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Col, Descriptions, Form, Input, List, Modal, Popconfirm, Row, Select, Space, Statistic, Switch, Table, Tabs, Tag, Tooltip, message } from 'antd'
import type { TableColumnsType } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { deleteDirectoryItem, getAdminSnapshot, saveAdminUser, saveDirectoryItem, setAdminUserActive, setTemplateEnabled } from '../api/admin'
import { orderTypeLabels } from '../api/orders'
import type { AdminDocumentTemplate, AdminSnapshot, AdminUser, AdminUserFormValues, DirectoryItem, DirectoryKind } from '../types/admin'
import type { Role } from '../types/auth'

const roleLabels: Record<Role, string> = { Admin: 'Администратор', 'IT-Head': 'Руководитель IT', Engineer: 'Инженер', Executive: 'Руководство', User: 'Сотрудник' }
const roleColors: Record<Role, string> = { Admin: 'purple', 'IT-Head': 'blue', Engineer: 'cyan', Executive: 'gold', User: 'default' }
const emptySnapshot: AdminSnapshot = { users: [], departments: [], equipmentTypes: [], templates: [], integrations: [] }

interface DirectoryPanelProps {
  kind: DirectoryKind
  title: string
  description: string
  items: DirectoryItem[]
  onChanged: () => void
}

function DirectoryPanel({ kind, title, description, items, onChanged }: DirectoryPanelProps) {
  const [form] = Form.useForm<{ name: string }>()
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<DirectoryItem>()
  const [saving, setSaving] = useState(false)

  const edit = (item?: DirectoryItem) => { setSelected(item); form.setFieldsValue({ name: item?.name ?? '' }); setOpen(true) }
  const save = async () => {
    const { name } = await form.validateFields()
    setSaving(true)
    await saveDirectoryItem(kind, name, selected?.id)
    setSaving(false); setOpen(false); form.resetFields(); onChanged()
  }
  const remove = async (id: string) => { await deleteDirectoryItem(kind, id); onChanged() }

  return <Card className="admin-directory-card" title={<div><strong>{title}</strong><small>{description}</small></div>} extra={<Button size="small" icon={<PlusOutlined />} onClick={() => edit()}>Добавить</Button>}>
    <List dataSource={items} locale={{ emptyText: 'Записи отсутствуют' }} renderItem={(item) => <List.Item actions={[<Button key="edit" type="text" icon={<EditOutlined />} onClick={() => edit(item)} />, <Popconfirm key="delete" title="Удалить запись?" description="После подключения backend удаление может быть запрещено, если запись используется." okText="Удалить" cancelText="Отмена" onConfirm={() => void remove(item.id)}><Button type="text" danger icon={<DeleteOutlined />} /></Popconfirm>]}><span>{item.name}</span><Tag color={item.isActive ? 'green' : 'default'}>{item.isActive ? 'Активен' : 'Отключён'}</Tag></List.Item>} />
    <Modal title={selected ? `Редактирование: ${selected.name}` : `Новая запись: ${title}`} open={open} onCancel={() => setOpen(false)} onOk={() => void save()} confirmLoading={saving} okText="Сохранить" cancelText="Отмена"><Form form={form} layout="vertical"><Form.Item name="name" label="Наименование" rules={[{ required: true, whitespace: true, message: 'Введите наименование' }, { max: 150 }]}><Input autoFocus /></Form.Item></Form></Modal>
  </Card>
}

export default function Admin() {
  const [snapshot, setSnapshot] = useState(emptySnapshot)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [userForm] = Form.useForm<AdminUserFormValues>()
  const [userOpen, setUserOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<AdminUser>()
  const [savingUser, setSavingUser] = useState(false)
  const [messageApi, contextHolder] = message.useMessage()

  const load = useCallback(async () => {
    setLoading(true)
    try { setSnapshot(await getAdminSnapshot()) } finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  const filteredUsers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('ru')
    return query ? snapshot.users.filter((user) => [user.fullName, user.login, user.departmentName, user.position, user.email].some((value) => value?.toLocaleLowerCase('ru').includes(query))) : snapshot.users
  }, [search, snapshot.users])

  const editUser = (user?: AdminUser) => {
    setSelectedUser(user)
    userForm.resetFields()
    userForm.setFieldsValue(user ? { login: user.login, fullName: user.fullName, role: user.role, departmentId: user.departmentId, position: user.position, email: user.email, phone: user.phone } : { role: 'User' })
    setUserOpen(true)
  }
  const saveUser = async () => {
    const values = await userForm.validateFields()
    setSavingUser(true)
    await saveAdminUser(values, selectedUser?.id)
    setSavingUser(false); setUserOpen(false); await load(); messageApi.success(selectedUser ? 'Пользователь обновлён' : 'Пользователь создан')
  }
  const toggleUser = async (user: AdminUser, isActive: boolean) => { await setAdminUserActive(user.id, isActive); await load(); messageApi.success(isActive ? 'Пользователь активирован' : 'Пользователь деактивирован') }
  const toggleTemplate = async (template: AdminDocumentTemplate, isEnabled: boolean) => { await setTemplateEnabled(template.id, isEnabled); await load(); messageApi.success(isEnabled ? 'Шаблон включён' : 'Шаблон отключён') }

  const userColumns: TableColumnsType<AdminUser> = [
    { title: 'Пользователь', dataIndex: 'fullName', render: (value: string, user) => <span className="admin-user-name"><strong>{value}</strong><small>{user.login}</small></span> },
    { title: 'Роль', dataIndex: 'role', width: 150, render: (role: Role) => <Tag color={roleColors[role]}>{roleLabels[role]}</Tag> },
    { title: 'Подразделение', dataIndex: 'departmentName', width: 170 },
    { title: 'Должность', dataIndex: 'position', width: 190, ellipsis: true, render: (value?: string) => value || '—' },
    { title: 'Активен', dataIndex: 'isActive', width: 90, align: 'center', render: (isActive: boolean, user) => <Tooltip title={user.id === 'mock-admin' ? 'Нельзя отключить текущую демонстрационную учётную запись' : undefined}><Switch checked={isActive} disabled={user.id === 'mock-admin'} onChange={(checked) => void toggleUser(user, checked)} /></Tooltip> },
    { title: '', key: 'actions', width: 62, align: 'center', render: (_, user) => <Button type="text" icon={<EditOutlined />} onClick={() => editUser(user)} /> },
  ]
  const templateColumns: TableColumnsType<AdminDocumentTemplate> = [
    { title: 'Шаблон', dataIndex: 'name', render: (value: string, template) => <span className="admin-template-name"><FileTextOutlined /><span><strong>{value}</strong><small>{template.fileName}</small></span></span> },
    { title: 'Тип', dataIndex: 'type', width: 180, render: (type: AdminDocumentTemplate['type']) => orderTypeLabels[type] },
    { title: 'Полей', dataIndex: 'fieldCount', width: 90, align: 'center' },
    { title: 'Согласование', dataIndex: 'minApproverRole', width: 150, render: (role: AdminDocumentTemplate['minApproverRole']) => roleLabels[role] },
    { title: 'Включён', dataIndex: 'isEnabled', width: 100, align: 'center', render: (isEnabled: boolean, template) => <Switch checked={isEnabled} onChange={(checked) => void toggleTemplate(template, checked)} /> },
  ]

  const tabs = [
    { key: 'users', label: 'Пользователи', children: <Card className="workspace-card admin-users-card"><div className="admin-toolbar"><Input allowClear prefix={<SearchOutlined />} placeholder="ФИО, логин, подразделение…" value={search} onChange={(event) => setSearch(event.target.value)} /><Button type="primary" icon={<PlusOutlined />} onClick={() => editUser()}>Добавить пользователя</Button></div><Table<AdminUser> rowKey="id" columns={userColumns} dataSource={filteredUsers} loading={loading} pagination={{ pageSize: 8, showTotal: (total) => `Всего: ${total}` }} scroll={{ x: 980 }} /></Card> },
    { key: 'directories', label: 'Справочники', children: <Row gutter={[18, 18]}><Col xs={24} xl={12}><DirectoryPanel kind="departments" title="Подразделения" description="Department · используется в пользователях и заявках" items={snapshot.departments} onChanged={() => void load()} /></Col><Col xs={24} xl={12}><DirectoryPanel kind="equipmentTypes" title="Типы оборудования" description="EquipmentType · классификация активов" items={snapshot.equipmentTypes} onChanged={() => void load()} /></Col></Row> },
    { key: 'templates', label: 'Шаблоны документов', children: <Card className="workspace-card admin-templates-card"><Alert type="info" showIcon message="В MVP доступен просмотр и включение шаблонов" description="Загрузка и безопасная валидация DOCX-файлов будет выполняться backend. Локальная форма не отправляет файлы на сервер." /><Table<AdminDocumentTemplate> rowKey="id" columns={templateColumns} dataSource={snapshot.templates} loading={loading} pagination={false} scroll={{ x: 850 }} /></Card> },
    { key: 'integrations', label: 'Настройки интеграций', children: <><Alert className="admin-secret-alert" type="warning" showIcon message="Секреты не отображаются и не редактируются через браузер" description="API-ключи, пароли и webhook-секреты остаются в защищённых переменных окружения на сервере." /><div className="admin-integration-grid">{snapshot.integrations.map((integration) => <Card key={integration.code} className="admin-integration-card" title={<Space><ApiOutlined /><span>{integration.name}</span></Space>} extra={<Tag color={integration.enabled ? 'green' : 'default'}>{integration.enabled ? 'Включена' : 'Отключена'}</Tag>}><Descriptions column={1} size="small"><Descriptions.Item label="URL"><span className="admin-integration-url">{integration.baseUrl}</span></Descriptions.Item><Descriptions.Item label="Режим">{integration.mode}</Descriptions.Item><Descriptions.Item label="Интервал">{integration.pollIntervalMinutes ? `${integration.pollIntervalMinutes} мин.` : 'Событийный'}</Descriptions.Item><Descriptions.Item label="Секрет"><Tag icon={<SafetyCertificateOutlined />} color={integration.secretConfigured ? 'green' : 'default'}>{integration.secretConfigured ? 'Настроен на сервере' : 'Не настроен'}</Tag></Descriptions.Item></Descriptions></Card>)}</div></> },
  ]

  return <div className="page-container admin-page">
    {contextHolder}
    <div className="page-heading"><div><span className="eyebrow">Системное управление</span><h1>Админ-панель</h1><p>Пользователи, справочники, документы и безопасный обзор интеграций</p></div></div>
    <div className="prototype-notice">Локальный режим · изменения хранятся до обновления страницы и подготовлены к API B04/B16</div>
    <Row gutter={[14, 14]} className="admin-stats"><Col xs={12} lg={6}><Card><Statistic prefix={<TeamOutlined />} title="Пользователи" value={snapshot.users.length} /></Card></Col><Col xs={12} lg={6}><Card><Statistic title="Активные" value={snapshot.users.filter((user) => user.isActive).length} /></Card></Col><Col xs={12} lg={6}><Card><Statistic title="Шаблоны" value={snapshot.templates.filter((template) => template.isEnabled).length} /></Card></Col><Col xs={12} lg={6}><Card><Statistic title="Интеграции включены" value={snapshot.integrations.filter((integration) => integration.enabled).length} /></Card></Col></Row>
    <Tabs className="admin-tabs" items={tabs} />
    <Modal title={selectedUser ? `Редактирование: ${selectedUser.fullName}` : 'Новый пользователь'} open={userOpen} onCancel={() => setUserOpen(false)} onOk={() => void saveUser()} confirmLoading={savingUser} okText="Сохранить" cancelText="Отмена" width={760}><Form form={userForm} layout="vertical" className="admin-user-form"><Form.Item name="fullName" label="Ф.И.О." rules={[{ required: true, whitespace: true, message: 'Введите Ф.И.О.' }, { max: 255 }]}><Input /></Form.Item><Form.Item name="login" label="Логин" rules={[{ required: true, whitespace: true, message: 'Введите логин' }, { pattern: /^[a-zA-Z0-9._-]+$/, message: 'Используйте латинские буквы, цифры, точку, дефис или подчёркивание' }]}><Input disabled={Boolean(selectedUser)} /></Form.Item><Form.Item name="role" label="Роль" rules={[{ required: true }]}><Select options={Object.entries(roleLabels).map(([value, label]) => ({ value, label }))} /></Form.Item><Form.Item name="departmentId" label="Подразделение" rules={[{ required: true, message: 'Выберите подразделение' }]}><Select options={snapshot.departments.map((item) => ({ value: item.id, label: item.name }))} /></Form.Item><Form.Item name="position" label="Должность"><Input /></Form.Item><Form.Item name="email" label="Email" rules={[{ type: 'email', message: 'Проверьте email' }]}><Input /></Form.Item><Form.Item name="phone" label="Телефон"><Input /></Form.Item></Form></Modal>
  </div>
}
