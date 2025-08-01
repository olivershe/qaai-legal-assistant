import { Sparkles, FileText } from 'lucide-react'

interface PageHeaderProps {
  activeTab: 'assist' | 'draft'
  onTabChange: (tab: 'assist' | 'draft') => void
}

/**
 * PageHeader component following assistant.profile.json PageHeader specifications
 * Matches gold standard design exactly with proper typography and spacing
 */
export function PageHeader({ activeTab, onTabChange }: PageHeaderProps) {
  const tabs = [
    { id: 'assist' as const, label: 'Assist', icon: Sparkles },
    { id: 'draft' as const, label: 'Draft', icon: FileText },
  ]

  return (
    <div>
      {/* Title and Subtitle */}
      <div className="mb-6">
        <h1 
          className="mb-2"
          style={{ 
            color: 'rgb(var(--text-primary))',
            fontSize: 'var(--font-size-h1)',
            lineHeight: 'var(--line-height-h1)',
            fontWeight: '600',
            fontFamily: 'var(--font-family)',
            margin: '0 0 8px 0'
          }}
        >
          Assistant
        </h1>
        <p 
          style={{ 
            color: 'rgb(var(--text-secondary))',
            fontSize: 'var(--font-size-body)',
            lineHeight: 'var(--line-height-body)',
            fontFamily: 'var(--font-family)',
            margin: '0 0 24px 0'
          }}
        >
          Ask complex questions to your professional AI assistant
        </p>
        {/* Separator line */}
        <div 
          style={{ 
            borderBottom: '1px solid rgb(var(--border-muted))',
            marginBottom: '24px'
          }}
        />
      </div>

      {/* Tabs and Actions Row */}
      <div className="flex items-center justify-between">
        {/* Contained Tabs */}
        <div 
          className="flex items-center gap-2 p-1 rounded-full"
          style={{ 
            backgroundColor: 'transparent',
            borderRadius: 'var(--radius-pill)'
          }}
        >
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isSelected = activeTab === tab.id
            
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className="flex items-center gap-2 px-4 py-2 rounded-full transition-all"
                style={{
                  height: '36px',
                  borderRadius: 'var(--radius-pill)',
                  backgroundColor: isSelected ? 'rgb(var(--bg-tab-selected))' : 'transparent',
                  color: isSelected ? 'rgb(var(--text-primary))' : 'rgb(var(--text-secondary))',
                  fontSize: 'var(--font-size-body)',
                  fontFamily: 'var(--font-family)',
                  border: 'none',
                  cursor: 'pointer',
                  transitionDuration: 'var(--timing-base)',
                  transitionTimingFunction: 'var(--easing-standard)'
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = 'rgb(var(--bg-tab-hover))'
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = 'transparent'
                  }
                }}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            )
          })}
        </div>

        {/* Tips Link */}
        <button 
          className="hover:underline transition-colors"
          style={{ 
            color: 'rgb(var(--text-link))',
            fontSize: 'var(--font-size-body)',
            fontFamily: 'var(--font-family)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            textDecoration: 'none'
          }}
        >
          View tips
        </button>
      </div>
    </div>
  )
}