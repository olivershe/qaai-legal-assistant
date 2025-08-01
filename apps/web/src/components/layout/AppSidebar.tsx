import { Link, useLocation } from 'react-router-dom'
import { 
  MessageSquare, 
  Folder, 
  Workflow, 
  Clock, 
  Library, 
  HelpCircle, 
  Settings, 
  User,
  ChevronDown,
  ChevronLeft
} from 'lucide-react'
import { LucideIconType } from '../../types'

interface NavItem {
  icon: LucideIconType
  label: string
  path: string
  active?: boolean
}

interface AppSidebarProps {
  isCollapsed: boolean
  onToggleCollapse: (collapsed: boolean) => void
}

/**
 * AppSidebar component following assistant.profile.json specifications exactly
 * Implements sections: brand, context, nav, footer as defined in the profile
 * Matches gold standard design with collapsible functionality
 */
export function AppSidebar({ isCollapsed, onToggleCollapse }: AppSidebarProps) {
  const location = useLocation()

  const navItems: NavItem[] = [
    { icon: MessageSquare, label: 'Assistant', path: '/assistant' },
    { icon: Folder, label: 'Vault', path: '/vault' },
    { icon: Workflow, label: 'Workflows', path: '/workflows' },
    { icon: Clock, label: 'History', path: '/history' },
    { icon: Library, label: 'Library', path: '/library' },
  ]

  const footerItems: NavItem[] = [
    { icon: HelpCircle, label: 'Help', path: '/help' },
    { icon: Settings, label: 'Settings', path: '/settings' },
  ]

  return (
    <div 
      className="fixed left-0 top-0 h-full flex flex-col border-r transition-all duration-300"
      style={{
        width: isCollapsed ? '64px' : 'var(--sidebar-width, 256px)',
        backgroundColor: '#FBFAFA',
        borderRightColor: 'rgb(var(--border-default))',
        padding: 'var(--spacing-8, 16px)',
        borderRightWidth: '1px'
      }}
    >
      {/* Brand Section with Collapse Toggle */}
      <div className="mb-6 flex items-center justify-between">
        <div 
          className={`font-semibold transition-opacity ${isCollapsed ? 'opacity-0 w-0 overflow-hidden' : 'opacity-100'}`}
          style={{ 
            color: 'rgb(var(--text-primary))', 
            fontSize: 'var(--font-size-h2)',
            fontFamily: 'var(--font-family)'
          }}
        >
          QaAI
        </div>
        <button
          onClick={() => onToggleCollapse(!isCollapsed)}
          className="p-1 rounded hover:bg-opacity-50 transition-colors"
          style={{
            backgroundColor: 'transparent',
            color: 'rgb(var(--icon-primary))',
            borderRadius: 'var(--radius-sm)'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'rgb(var(--bg-tab-hover))'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent'
          }}
        >
          <ChevronLeft 
            size={16} 
            className={`transition-transform ${isCollapsed ? 'rotate-180' : ''}`}
          />
        </button>
      </div>

      {/* Context Section - Matter Select */}
      {!isCollapsed && (
        <div className="mb-6">
          <button 
            className="w-full flex items-center justify-between px-3 py-2 rounded transition-colors"
            style={{
              backgroundColor: 'transparent',
              color: 'rgb(var(--text-secondary))',
              borderRadius: 'var(--radius-sm)',
              fontSize: 'var(--font-size-label)',
              height: '36px',
              fontFamily: 'var(--font-family)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgb(var(--bg-tab-hover))'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent'
            }}
          >
            <span>CM# Select</span>
            <ChevronDown size={16} />
          </button>
        </div>
      )}

      {/* Navigation Section */}
      <nav className="flex-1">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
            const Icon = item.icon
            
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`flex items-center px-3 py-2 rounded transition-colors ${isCollapsed ? 'justify-center' : ''}`}
                  style={{
                    height: '36px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: isActive ? 'rgb(var(--bg-tab-selected))' : 'transparent',
                    color: isActive ? 'rgb(var(--text-primary))' : 'rgb(var(--text-secondary))',
                    fontSize: 'var(--font-size-body)',
                    fontFamily: 'var(--font-family)'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = 'rgb(var(--bg-tab-hover))'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = 'transparent'
                    }
                  }}
                  title={isCollapsed ? item.label : undefined}
                >
                  <Icon 
                    size={20} 
                    className={isCollapsed ? '' : 'mr-3'} 
                    style={{ color: 'rgb(var(--icon-primary))' }}
                  />
                  {!isCollapsed && (
                    <span className="transition-opacity">{item.label}</span>
                  )}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Footer Section */}
      <div className="border-t pt-4" style={{ borderTopColor: 'rgb(var(--border-muted))' }}>
        <ul className="space-y-1">
          {footerItems.map((item) => {
            const Icon = item.icon
            
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`flex items-center px-3 py-2 rounded transition-colors ${isCollapsed ? 'justify-center' : ''}`}
                  style={{
                    height: '36px',
                    borderRadius: 'var(--radius-sm)',
                    color: 'rgb(var(--text-secondary))',
                    fontSize: 'var(--font-size-body)',
                    fontFamily: 'var(--font-family)'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgb(var(--bg-tab-hover))'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent'
                  }}
                  title={isCollapsed ? item.label : undefined}
                >
                  <Icon 
                    size={20} 
                    className={isCollapsed ? '' : 'mr-3'} 
                    style={{ color: 'rgb(var(--icon-primary))' }}
                  />
                  {!isCollapsed && item.label}
                </Link>
              </li>
            )
          })}
          
          {/* User Section */}
          {!isCollapsed && (
            <li>
              <div 
                className="flex items-center px-3 py-2 rounded"
                style={{
                  height: '36px',
                  borderRadius: 'var(--radius-sm)',
                  color: 'rgb(var(--text-muted))',
                  fontSize: 'var(--font-size-caption)',
                  fontFamily: 'var(--font-family)'
                }}
              >
                <User 
                  size={20} 
                  className="mr-3" 
                  style={{ color: 'rgb(var(--icon-muted))' }}
                />
                demo@qaai.difc
              </div>
            </li>
          )}
        </ul>
      </div>
    </div>
  )
}