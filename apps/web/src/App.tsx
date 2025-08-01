import { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { designProfileService } from './services/design-profiles'
import { AppLayout } from './components/layout/AppLayout'
import { AssistantPage } from './components/assistant/AssistantPage'
import { VaultPage } from './components/vault/VaultPage'
import { WorkflowsPage } from './components/workflows/WorkflowsPage'

function App() {
  useEffect(() => {
    // Apply design profile on app startup
    // Following examples/design/README.md pattern for runtime loading
    designProfileService.applyDesignVariables('assistant').catch(console.error)
  }, [])

  return (
    <div className="design-profile-applied min-h-screen">
      <Router>
        <AppLayout>
          <Routes>
            <Route path="/" element={<Navigate to="/assistant" replace />} />
            <Route path="/assistant" element={<AssistantPage />} />
            <Route path="/vault" element={<VaultPage />} />
            <Route path="/workflows" element={<WorkflowsPage />} />
            <Route path="/workflows/:workflowId" element={<WorkflowsPage />} />
            <Route path="/history" element={<div>History - Coming Soon</div>} />
            <Route path="/library" element={<div>Library - Coming Soon</div>} />
            <Route path="/settings" element={<div>Settings - Coming Soon</div>} />
          </Routes>
        </AppLayout>
      </Router>
    </div>
  )
}

export default App