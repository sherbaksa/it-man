/** Author: Dev2 | Date: 2026-07-16 | Purpose: Demonstration login page for all platform roles. */
import { LockOutlined, MedicineBoxOutlined, UserOutlined } from '@ant-design/icons'
import { Alert, Button, Form, Input, Select, Typography } from 'antd'
import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { demoAccounts } from '../api/mocks'
import { useAuthStore } from '../store/authStore'
import type { LoginPayload } from '../types/auth'

export default function Login() {
  const [error, setError] = useState('')
  const login = useAuthStore((state) => state.login)
  const isLoading = useAuthStore((state) => state.isLoading)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const navigate = useNavigate()
  const location = useLocation()

  if (isAuthenticated) return <Navigate to="/" replace />

  const submit = async (values: LoginPayload) => {
    setError('')
    try {
      await login(values)
      const destination = (location.state as { from?: string } | null)?.from ?? '/'
      navigate(destination, { replace: true })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Не удалось выполнить вход')
    }
  }

  return (
    <main className="login-page">
      <section className="login-side">
        <div className="login-brand"><div className="brand-mark large"><MedicineBoxOutlined /></div><div><strong>IT Management</strong><span>Медицинская организация</span></div></div>
        <div className="login-message"><span>Единое рабочее пространство</span><h1>Управление IT-инфраструктурой</h1><p>Инвентаризация, заявки, мониторинг и документы — в защищённом интерфейсе медицинской организации.</p></div>
        <div className="login-security"><LockOutlined /><span>Демонстрационный режим · данные не отправляются на сервер</span></div>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <Typography.Title level={2}>Вход в систему</Typography.Title>
          <Typography.Paragraph>Выберите тестовую роль. Пароль для всех аккаунтов: <strong>demo</strong>.</Typography.Paragraph>
          {error && <Alert type="error" showIcon message={error} />}
          <Form<LoginPayload> layout="vertical" initialValues={{ login: 'engineer', password: 'demo' }} onFinish={submit} requiredMark={false}>
            <Form.Item name="login" label="Тестовый пользователь" rules={[{ required: true }]}>
              <Select size="large" suffixIcon={<UserOutlined />} options={demoAccounts.map((account) => ({ value: account.login, label: `${account.login} — ${account.role}` }))} />
            </Form.Item>
            <Form.Item name="password" label="Пароль" rules={[{ required: true, message: 'Введите пароль' }]}>
              <Input.Password size="large" prefix={<LockOutlined />} autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" size="large" block loading={isLoading}>Войти</Button>
          </Form>
          <div className="login-help">Для рабочего режима авторизация будет подключена к backend API на следующем этапе интеграции.</div>
        </div>
      </section>
    </main>
  )
}
