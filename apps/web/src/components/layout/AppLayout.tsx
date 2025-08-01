import React, { useState } from 'react'
import { AppSidebar } from './AppSidebar'

interface AppLayoutProps {
  children: React.ReactNode
}

/**
 * Main application layout following assistant.profile.json specifications
 * Implements app_shell layout with sidebar and main content area with responsive sidebar
 */
export function AppLayout({ children }: AppLayoutProps) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  
  const sidebarWidth = isSidebarCollapsed ? '64px' : 'var(--sidebar-width, 256px)'
  
  return (
    <div className="flex min-h-screen" style={{ background: 'var(--bg-canvas)' }}>
      {/* Sidebar following assistant.profile.json AppSidebar specs */}
      <AppSidebar 
        isCollapsed={isSidebarCollapsed} 
        onToggleCollapse={setIsSidebarCollapsed} 
      />
      
      {/* Main content area */}
      <main 
        className="flex-1 overflow-auto transition-all duration-300"
        style={{ 
          marginLeft: sidebarWidth,
          maxWidth: `calc(100vw - ${sidebarWidth})`
        }}
      >
        <div 
          className="mx-auto px-6 py-6"
          style={{ 
            maxWidth: 'var(--content-max-width, 1060px)',
            paddingLeft: 'var(--content-padding-x, 24px)',
            paddingRight: 'var(--content-padding-x, 24px)',
            paddingTop: 'var(--content-padding-y, 24px)',
            paddingBottom: 'var(--content-padding-y, 24px)'
          }}
        >
          {children}
        </div>
      </main>
    </div>
  )
}