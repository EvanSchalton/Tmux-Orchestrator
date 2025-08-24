import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import AppLayout from './components/Layout/AppLayout'
import Dashboard from './pages/Dashboard'
import AgentsPage from './pages/AgentsPage'
import SessionsPage from './pages/SessionsPage'
import MetricsPage from './pages/MetricsPage'
import './App.css'

function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1890ff',
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="agents" element={<AgentsPage />} />
            <Route path="sessions" element={<SessionsPage />} />
            <Route path="metrics" element={<MetricsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
