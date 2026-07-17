/** Author: Dev2 | Date: 2026-07-16 | Purpose: Bootstrap React and the shared UI theme. */
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import App from './App'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={ruRU}
      theme={{
        token: {
          colorPrimary: '#087f8c',
          colorInfo: '#087f8c',
          colorSuccess: '#16815c',
          colorWarning: '#b77817',
          colorError: '#c14343',
          borderRadius: 9,
          fontFamily: 'Inter, "Segoe UI", Arial, sans-serif',
        },
      }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>,
)
