import { useState } from 'react'
import { PageHeader } from './PageHeader'
import { AssistantPromptArea } from './AssistantPromptArea'
import { SectionTabs } from '../ui/SectionTabs'
import { WorkflowGallery } from '../workflows/WorkflowGallery'

/**
 * Assistant page following assistant.profile.json structure exactly
 * Implements: PageHeader, AssistantPromptArea, SectionTabs, WorkflowGallery
 */
export function AssistantPage() {
  const [activeTab, setActiveTab] = useState<'assist' | 'draft'>('assist')
  const [activeSection, setActiveSection] = useState<'discover' | 'recent' | 'shared'>('discover')

  return (
    <div className="space-y-6">
      {/* Page Header with tabs */}
      <PageHeader activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Assistant Prompt Area */}
      <AssistantPromptArea mode={activeTab} />

      {/* Section Tabs */}
      <SectionTabs 
        activeSection={activeSection} 
        onSectionChange={setActiveSection} 
      />

      {/* Content based on active section */}
      {activeSection === 'discover' && (
        <WorkflowGallery />
      )}

      {activeSection === 'recent' && (
        <div 
          className="text-center py-12"
          style={{ color: 'var(--text-muted)' }}
        >
          <p>No recent conversations yet.</p>
          <p className="text-sm mt-2">Start a conversation with QaAI to see your recent activity here.</p>
        </div>
      )}

      {activeSection === 'shared' && (
        <div 
          className="text-center py-12"
          style={{ color: 'var(--text-muted)' }}
        >
          <p>No shared conversations yet.</p>
          <p className="text-sm mt-2">Share conversations with colleagues to see them here.</p>
        </div>
      )}
    </div>
  )
}