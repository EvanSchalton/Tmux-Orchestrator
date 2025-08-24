import React, { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Typography, Tag, Space } from 'antd'
import {
  TeamOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { monitoringApi } from '../services/api'
import type { SystemStatus } from '../services/api'

const { Title } = Typography

const Dashboard: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchStatus = async () => {
    try {
      const response = await monitoringApi.getStatus()
      setStatus(response.data)
      setLoading(false)
    } catch (error) {
      console.error('Failed to fetch status:', error)
      setLoading(false)
    }
  }


  return (
    <div>
      <Title level={2}>Dashboard</Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Agents"
              value={status?.summary.totalAgents || 0}
              prefix={<TeamOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Active"
              value={status?.summary.active || 0}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Idle"
              value={status?.summary.idle || 0}
              valueStyle={{ color: '#1890ff' }}
              prefix={<ClockCircleOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Error"
              value={status?.summary.error || 0}
              valueStyle={{ color: '#f5222d' }}
              prefix={<ExclamationCircleOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="System Services" loading={loading}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Monitor Daemon</span>
                <Tag color={status?.daemonStatus.monitor.running ? 'green' : 'red'}>
                  {status?.daemonStatus.monitor.running ? 'Running' : 'Stopped'}
                </Tag>
              </div>
              {status?.daemonStatus.monitor.running && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>PID: {status.daemonStatus.monitor.pid}</span>
                  <span>Uptime: {Math.floor((status.daemonStatus.monitor.uptimeSeconds || 0) / 60)}m</span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16 }}>
                <span>Messaging Service</span>
                <Tag color={status?.daemonStatus.messaging.running ? 'green' : 'red'}>
                  {status?.daemonStatus.messaging.running ? 'Running' : 'Stopped'}
                </Tag>
              </div>
            </Space>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Quick Stats" loading={loading}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Total Sessions</span>
                <strong>-</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Total Windows</span>
                <strong>-</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Last Update</span>
                <strong>{new Date().toLocaleTimeString()}</strong>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
