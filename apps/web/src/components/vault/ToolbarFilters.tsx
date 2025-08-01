import { useState, useCallback } from 'react'
import { Search, X } from 'lucide-react'
import { debounce, parseSearchQuery } from '../../utils'

interface ToolbarFiltersProps {
  activeFilter: 'all' | 'private' | 'shared'
  onFilterChange: (filter: 'all' | 'private' | 'shared') => void
  searchQuery: string
  onSearchChange: (query: string) => void
  onSearchSubmit?: (query: string, filters: Record<string, string>) => void
  loading?: boolean
}

/**
 * ToolbarFilters component following vault.profile.json specifications exactly
 * Implements container layout, segmented controls, and search with proper styling
 */
export function ToolbarFilters({
  activeFilter,
  onFilterChange,
  searchQuery,
  onSearchChange,
  onSearchSubmit,
  loading = false
}: ToolbarFiltersProps) {
  const [searchFocused, setSearchFocused] = useState(false)
  const [parsedQuery, setParsedQuery] = useState<{ text: string; filters: Record<string, string> }>({
    text: searchQuery,
    filters: {}
  })

  // Debounced search to avoid excessive API calls
  const debouncedSearch = useCallback(
    debounce((query: string) => {
      const parsed = parseSearchQuery(query)
      setParsedQuery(parsed)
      onSearchSubmit?.(parsed.text, parsed.filters)
    }, 300),
    [onSearchSubmit]
  )

  const handleSearchChange = (value: string) => {
    onSearchChange(value)
    debouncedSearch(value)
  }

  const clearSearch = () => {
    onSearchChange('')
    setParsedQuery({ text: '', filters: {} })
    onSearchSubmit?.('', {})
  }

  const segments = [
    { id: 'all' as const, label: 'All' },
    { id: 'private' as const, label: 'Private' },
    { id: 'shared' as const, label: 'Shared' },
  ]

  return (
    <div 
      className="flex items-center justify-between py-2 border-b"
      style={{ 
        borderBottomColor: 'rgb(var(--border-muted))',
        paddingTop: '8px',
        paddingBottom: '8px',
        gap: '12px'
      }}
    >
      {/* Left Side - Segmented Control */}
      <div className="flex items-center">
        <div 
          className="flex items-center gap-1 p-1 rounded-full"
          style={{ 
            backgroundColor: 'rgb(var(--bg-subtle))',
            borderRadius: 'var(--radius-pill)'
          }}
          role="tablist"
          aria-label="Project visibility filter"
        >
          {segments.map((segment) => {
            const isSelected = activeFilter === segment.id
            
            return (
              <button
                key={segment.id}
                onClick={() => onFilterChange(segment.id)}
                className="px-4 py-2 rounded-full text-sm transition-colors font-medium"
                style={{
                  backgroundColor: isSelected ? 'rgb(var(--bg-tab-selected))' : 'transparent',
                  color: isSelected ? 'rgb(var(--text-primary))' : 'rgb(var(--text-secondary))',
                  borderRadius: 'var(--radius-pill)',
                  fontSize: 'var(--font-size-body)',
                  minWidth: '80px'
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
                role="tab"
                aria-selected={isSelected}
                aria-controls={`projects-${segment.id}`}
                tabIndex={isSelected ? 0 : -1}
              >
                {segment.label}
              </button>
            )
          })}
        </div>

        {/* Filter Pills for Advanced Search */}
        {Object.entries(parsedQuery.filters).length > 0 && (
          <div className="flex items-center gap-2 ml-4">
            {Object.entries(parsedQuery.filters).map(([key, value]) => (
              <span
                key={`${key}:${value}`}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs"
                style={{
                  backgroundColor: 'rgb(var(--bg-badge))',
                  color: 'rgb(var(--text-secondary))',
                  borderRadius: 'var(--radius-pill)',
                  fontSize: 'var(--font-size-caption)'
                }}
              >
                {key}: {value}
                <button
                  onClick={() => {
                    const newQuery = searchQuery.replace(`${key}:${value}`, '').trim()
                    handleSearchChange(newQuery)
                  }}
                  className="ml-1 hover:bg-opacity-50 rounded-full p-0.5"
                  aria-label={`Remove ${key}:${value} filter`}
                >
                  <X size={10} />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Right Side - Search */}
      <div className="relative">
        <div className="relative">
          <Search 
            size={16} 
            className="absolute left-3 top-1/2 transform -translate-y-1/2 pointer-events-none"
            style={{ 
              color: searchFocused || searchQuery ? 'rgb(var(--icon-primary))' : 'rgb(var(--icon-muted))',
              transition: 'color var(--timing-fast, 120ms)'
            }}
          />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                onSearchSubmit?.(parsedQuery.text, parsedQuery.filters)
              }
              if (e.key === 'Escape') {
                clearSearch()
                e.currentTarget.blur()
              }
            }}
            className="pl-10 pr-10 py-2 border rounded-md transition-all"
            style={{
              width: '320px',
              height: '36px',
              backgroundColor: 'rgb(var(--bg-input))',
              borderColor: searchFocused ? 'rgb(var(--border-focus))' : 'rgb(var(--border-default))',
              borderRadius: 'var(--radius-md)',
              color: 'rgb(var(--text-primary))',
              fontSize: 'var(--font-size-body)',
              outline: 'none',
              boxShadow: searchFocused ? '0 0 0 1px rgb(var(--border-focus))' : 'none'
            }}
            disabled={loading}
            aria-label="Search projects"
            aria-describedby="search-help"
          />
          
          {/* Clear search button */}
          {searchQuery && (
            <button
              onClick={clearSearch}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 p-1 rounded-full hover:bg-opacity-50 transition-colors"
              style={{ color: 'rgb(var(--icon-muted))' }}
              aria-label="Clear search"
              tabIndex={0}
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Search Help Text */}
        <div 
          id="search-help"
          className="absolute top-full left-0 mt-1 text-xs opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
          style={{ 
            color: 'rgb(var(--text-muted))',
            fontSize: 'var(--font-size-caption)'
          }}
        >
          Try: jurisdiction:DIFC, type:Law, or simple text search
        </div>

        {/* Loading indicator */}
        {loading && (
          <div 
            className="absolute right-10 top-1/2 transform -translate-y-1/2"
            style={{ color: 'rgb(var(--icon-muted))' }}
          >
            <div className="animate-spin rounded-full h-4 w-4 border-b border-current"></div>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Search suggestions component for advanced search patterns
 */
export function SearchSuggestions({ 
  visible, 
  onSelect 
}: { 
  visible: boolean
  onSelect: (suggestion: string) => void 
}) {
  if (!visible) return null

  const suggestions = [
    { label: 'Filter by DIFC jurisdiction', value: 'jurisdiction:DIFC' },
    { label: 'Find laws only', value: 'type:Law' },
    { label: 'Find regulations', value: 'type:Regulation' },
    { label: 'Recent documents', value: 'recent:7d' },
    { label: 'Shared projects only', value: 'visibility:shared' },
  ]

  return (
    <div 
      className="absolute top-full left-0 right-0 mt-1 py-2 rounded-md border shadow-lg z-10"
      style={{
        backgroundColor: 'rgb(var(--bg-card))',
        borderColor: 'rgb(var(--border-default))',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-lg)'
      }}
    >
      {suggestions.map((suggestion, index) => (
        <button
          key={index}
          onClick={() => onSelect(suggestion.value)}
          className="w-full px-3 py-2 text-left text-sm hover:bg-opacity-50 transition-colors"
          style={{ color: 'rgb(var(--text-primary))' }}
        >
          <div className="font-medium">{suggestion.label}</div>
          <div 
            className="text-xs font-mono"
            style={{ color: 'var(--text-muted)' }}
          >
            {suggestion.value}
          </div>
        </button>
      ))}
    </div>
  )
}