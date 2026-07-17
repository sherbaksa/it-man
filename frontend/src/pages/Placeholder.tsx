/** Author: Dev2 | Date: 2026-07-16 | Purpose: Complete route placeholders for upcoming frontend sessions. */
import { ClockCircleOutlined } from '@ant-design/icons'
import { Button, Empty } from 'antd'

export default function Placeholder({ title, description }: { title: string; description: string }) {
  return <div className="page-container"><div className="page-heading"><div><span className="eyebrow">Раздел платформы</span><h1>{title}</h1><p>{description}</p></div></div><div className="placeholder-card"><Empty image={<ClockCircleOutlined className="placeholder-icon" />} description={<><strong>Раздел подготовлен к разработке</strong><span>Функциональность будет добавлена в одном из следующих frontend-сеансов.</span></>}><Button onClick={() => history.back()}>Вернуться назад</Button></Empty></div></div>
}
