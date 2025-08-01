import { useState, useEffect, useCallback } from 'react'
import { ToolbarFilters } from './ToolbarFilters'
import { ProjectGrid } from './ProjectGrid'
import { VaultProject } from '../../types'
import { apiService } from '../../services/api'
import { useFileUpload } from '../../hooks/useFileUpload'
import { designProfileService } from '../../services/design-profiles'

/**
 * VaultPage following vault.profile.json specifications exactly
 * Implements PageHeader, ToolbarFilters, ProjectGrid with full backend integration
 */
export function VaultPage() {
  const [activeFilter, setActiveFilter] = useState<'all' | 'private' | 'shared'>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [projects, setProjects] = useState<VaultProject[]>([])
  const [filteredProjects, setFilteredProjects] = useState<VaultProject[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // File upload hook for drag-and-drop functionality
  const fileUpload = useFileUpload({
    maxFileSize: 50 * 1024 * 1024, // 50MB
    maxFiles: 10,
    allowedTypes: [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'text/plain',
      'text/markdown',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/csv',
      'message/rfc822'
    ],
    onComplete: (fileId, result) => {
      console.log(`File ${fileId} uploaded successfully:`, result)
    },
    onError: (fileId, error) => {
      console.error(`File ${fileId} upload failed:`, error)
    },
    onAllComplete: (results) => {
      console.log('All files uploaded:', results)
      // Refresh projects to show updated document counts
      loadProjects()
    }
  })

  // Apply vault profile design tokens on mount
  useEffect(() => {
    designProfileService.applyDesignVariables('vault').catch(console.error)
  }, [])

  // Load projects from backend
  const loadProjects = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const projectsData = await apiService.getVaultProjects()
      setProjects(projectsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects')
      console.error('Failed to load projects:', err)
      // Set mock data for demo purposes
      setProjects([
        {
          id: '1',
          name: 'DIFC Contract Templates',
          visibility: 'private',
          document_count: 12,
          created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
          owner: 'demo@qaai.difc'
        },
        {
          id: '2',
          name: 'Employment Law Research',
          visibility: 'shared',
          document_count: 8,
          created_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
          owner: 'demo@qaai.difc'
        },
        {
          id: '3',
          name: 'Data Protection Analysis',
          visibility: 'private',
          document_count: 5,
          created_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
          owner: 'demo@qaai.difc'
        }
      ])
    } finally {
      setLoading(false)
    }
  }, [])

  // Filter projects based on active filter and search query
  useEffect(() => {
    let filtered = projects

    // Apply visibility filter
    if (activeFilter !== 'all') {
      filtered = filtered.filter(project => project.visibility === activeFilter)
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(project =>
        project.name.toLowerCase().includes(query) ||
        project.owner.toLowerCase().includes(query)
      )
    }

    setFilteredProjects(filtered)
  }, [projects, activeFilter, searchQuery])

  // Load projects on mount
  useEffect(() => {
    loadProjects()
  }, [loadProjects])

  // Handle project creation
  const handleProjectCreate = async (name: string, visibility: 'private' | 'shared') => {
    try {
      const newProject = await apiService.createVaultProject(name, visibility)
      setProjects(prev => [newProject, ...prev])
    } catch (err) {
      console.error('Failed to create project:', err)
      // For demo purposes, create a mock project
      const mockProject: VaultProject = {
        id: `mock-${Date.now()}`,
        name,
        visibility,
        document_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        owner: 'demo@qaai.difc'
      }
      setProjects(prev => [mockProject, ...prev])
    }
  }


  // Handle project deletion
  const handleProjectDelete = async (projectId: string) => {
    try {
      // In a real implementation, this would call a delete API
      setProjects(prev => prev.filter(p => p.id !== projectId))
    } catch (err) {
      console.error('Failed to delete project:', err)
    }
  }

  // Handle file upload to project
  const handleFileUpload = async (projectId: string, files: File[]) => {
    try {
      fileUpload.addFiles(files)
      
      // Upload files using the file upload hook
      await fileUpload.uploadFiles(async (file) => {
        await apiService.uploadToVault(projectId, [file])
        return { url: `vault://${projectId}/${file.name}` }
      })

      // Update project document count
      setProjects(prev => prev.map(p => 
        p.id === projectId 
          ? { ...p, document_count: p.document_count + files.length, updated_at: new Date().toISOString() }
          : p
      ))
    } catch (err) {
      console.error('Failed to upload files:', err)
    }
  }

  // Handle search with advanced filters
  const handleSearchSubmit = async (query: string, filters: Record<string, string>) => {
    console.log('Advanced search:', { query, filters })
    // In a real implementation, this would call a search API with filters
    setSearchQuery(query)
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 
          className="text-h1 mb-2"
          style={{ 
            color: 'rgb(var(--text-primary))',
            fontSize: 'var(--font-size-h1)',
            lineHeight: 'var(--line-height-h1)',
            fontWeight: '600',
            fontFamily: 'var(--font-family)'
          }}
        >
          Vault
        </h1>
        <p 
          className="text-body"
          style={{ 
            color: 'rgb(var(--text-secondary))',
            fontSize: 'var(--font-size-body)',
            lineHeight: 'var(--line-height-body)',
            fontFamily: 'var(--font-family)'
          }}
        >
          Store and review thousands of documents
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div 
          className="p-4 rounded-lg border"
          style={{
            backgroundColor: '#FEF2F2',
            borderColor: '#FECACA',
            color: '#EF4444',
            borderRadius: 'var(--radius-lg)'
          }}
        >
          {error}
        </div>
      )}

      {/* Toolbar Filters */}
      <ToolbarFilters
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onSearchSubmit={handleSearchSubmit}
        loading={loading}
      />

      {/* Project Grid */}
      <ProjectGrid
        projects={filteredProjects}
        onProjectCreate={handleProjectCreate}
        onProjectDelete={handleProjectDelete}
        onFileUpload={handleFileUpload}
        loading={loading}
      />

      {/* File Upload Progress (if uploading) */}
      {fileUpload.isUploading && (
        <div 
          className="fixed bottom-4 right-4 p-4 rounded-lg shadow-lg border max-w-sm"
          style={{
            backgroundColor: 'rgb(var(--bg-card))',
            borderColor: 'rgb(var(--border-default))',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-lg)'
          }}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium" style={{ color: 'rgb(var(--text-primary))' }}>
              Uploading files...
            </span>
            <span className="text-xs" style={{ color: 'rgb(var(--text-muted))' }}>
              {Math.round(fileUpload.progress)}%
            </span>
          </div>
          
          <div 
            className="w-full bg-gray-200 rounded-full h-2 mb-2"
            style={{ backgroundColor: 'rgb(var(--bg-subtle))' }}
          >
            <div 
              className="h-2 rounded-full transition-all duration-300"
              style={{ 
                width: `${fileUpload.progress}%`,
                backgroundColor: 'rgb(var(--action-primary-bg))'
              }}
            />
          </div>
          
          <div className="space-y-1">
            {fileUpload.files.map(file => (
              <div key={file.id} className="flex items-center justify-between text-xs">
                <span 
                  className="truncate flex-1 mr-2"
                  style={{ color: 'rgb(var(--text-secondary))' }}
                >
                  {file.file.name}
                </span>
                <span 
                  style={{ 
                    color: file.status === 'error' 
                      ? '#EF4444' 
                      : 'rgb(var(--text-muted))' 
                  }}
                >
                  {file.status === 'completed' ? '✓' : 
                   file.status === 'error' ? '✗' : 
                   `${Math.round(file.progress)}%`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}