import React, { useState, useEffect } from 'react'

interface CostData {
  total_cost: number
  daily_cost: number
  email_count: number
  avg_cost_per_email: number
}

export default function CostMonitor({ userId }: { userId: string }) {
  const [costData, setCostData] = useState<CostData | null>(null)

  useEffect(() => {
    const fetchCostData = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/emails/costs/${userId}`)
        if (response.ok) {
          const data = await response.json()
          setCostData(data)
        }
      } catch (error) {
        console.error('Failed to fetch cost data:', error)
      }
    }

    fetchCostData()
  }, [userId])

  if (!costData) return null

  return (
    <div className="cost-monitor">
      <h3>💰 Processing Costs</h3>
      <div className="cost-stats">
        <div className="cost-stat">
          <span className="cost-label">Total Cost:</span>
          <span className="cost-value">${costData.total_cost.toFixed(4)}</span>
        </div>
        <div className="cost-stat">
          <span className="cost-label">Today:</span>
          <span className="cost-value">${costData.daily_cost.toFixed(4)}</span>
        </div>
        <div className="cost-stat">
          <span className="cost-label">Avg per Email:</span>
          <span className="cost-value">${costData.avg_cost_per_email.toFixed(4)}</span>
        </div>
      </div>
    </div>
  )
}