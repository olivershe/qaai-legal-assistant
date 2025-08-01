
interface SectionTabsProps {
  activeSection: 'discover' | 'recent' | 'shared'
  onSectionChange: (section: 'discover' | 'recent' | 'shared') => void
}

/**
 * SectionTabs component following assistant.profile.json SectionTabs specifications
 * Matches gold standard design with exact underline styling and spacing
 */
export function SectionTabs({ activeSection, onSectionChange }: SectionTabsProps) {
  const tabs = [
    { id: 'discover' as const, label: 'Discover' },
    { id: 'recent' as const, label: 'Recent' },
    { id: 'shared' as const, label: 'Shared with you' },
  ]

  return (
    <div className="border-b" style={{ borderBottomColor: 'rgb(var(--border-muted))' }}>
      <nav className="flex" style={{ gap: 'var(--spacing-12)' }}>
        {tabs.map((tab) => {
          const isActive = activeSection === tab.id
          
          return (
            <button
              key={tab.id}
              onClick={() => onSectionChange(tab.id)}
              className="relative transition-colors"
              style={{
                color: isActive ? 'rgb(var(--text-primary))' : 'rgb(var(--text-secondary))',
                fontSize: 'var(--font-size-body)',
                lineHeight: 'var(--line-height-body)',
                fontFamily: 'var(--font-family)',
                paddingBottom: 'var(--spacing-4)',
                paddingTop: 'var(--spacing-4)',
                background: 'none',
                border: 'none',
                cursor: 'pointer'
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = 'rgb(var(--text-primary))'
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = 'rgb(var(--text-secondary))'
                }
              }}
            >
              {tab.label}
              
              {/* Active underline */}
              {isActive && (
                <div
                  className="absolute bottom-0 left-0 right-0"
                  style={{
                    backgroundColor: 'rgb(var(--text-primary))',
                    height: '2px',
                    borderRadius: '1px'
                  }}
                />
              )}
            </button>
          )
        })}
      </nav>
    </div>
  )
}