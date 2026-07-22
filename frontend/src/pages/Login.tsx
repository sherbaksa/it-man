/** Author: Dev2 | Date: 2026-07-22 | Purpose: Login page connected to the real backend auth contract. */
import { LockOutlined, MedicineBoxOutlined, UserOutlined } from '@ant-design/icons'
import { Alert, Button, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
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
        <div className="login-security"><LockOutlined /><span>Защищённый вход · авторизация через сервер платформы</span></div>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <Typography.Title level={2}>Вход в систему</Typography.Title>
          <Typography.Paragraph>Введите учётные данные, выданные администратором платформы.</Typography.Paragraph>
          {error && <Alert type="error" showIcon message={error} />}
          <Form<LoginPayload> layout="vertical" onFinish={submit} requiredMark={false}>
            <Form.Item name="login" label="Логин" rules={[{ required: true, message: 'Введите логин' }]}>
              <Input size="large" prefix={<UserOutlined />} autoComplete="username" />
            </Form.Item>
            <Form.Item name="password" label="Пароль" rules={[{ required: true, message: 'Введите пароль' }]}>
              <Input.Password size="large" prefix={<LockOutlined />} autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" size="large" block loading={isLoading}>Войти</Button>
          </Form>
          <div className="login-help">Демо-пароли отключены. Если у вас нет учётной записи, обратитесь к администратору платформы.</div>
        </div>
      </section>
    </main>
  )
}
