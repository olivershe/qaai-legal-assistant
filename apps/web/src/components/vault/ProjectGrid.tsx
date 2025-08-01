import { useState, useCallback } from 'react'
import { FolderPlus, Folder, MoreVertical, Eye, Edit, Share, Trash, FileText } from 'lucide-react'
import { VaultProject } from '../../types'
import { formatRelativeDate } from '../../utils'

interface ProjectGridProps {
  projects: VaultProject[]
  onProjectCreate: (name: string, visibility: 'private' | 'shared') => Promise<void>
  onProjectDelete: (projectId: string) => Promise<void>
  onFileUpload: (projectId: string, files: File[]) => Promise<void>
  loading?: boolean
}

/**
 * ProjectGrid component following vault.profile.json specifications exactly
 * Implements layout, NewProjectCard, ProjectCard with proper interactions
 */
export function ProjectGrid({ 
  projects, 
  onProjectCreate, 
  onProjectDelete, 
  onFileUpload,
  loading = false 
}: ProjectGridProps) {
  const [dragOverProject, setDragOverProject] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectVisibility, setNewProjectVisibility] = useState<'private' | 'shared'>('private')
  const [activeMenu, setActiveMenu] = useState<string | null>(null)

  // Handle drag and drop for project creation
  const handleNewProjectDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files)
    
    if (files.length > 0) {
      const projectName = `New Project - ${new Date().toLocaleDateString()}`
      await onProjectCreate(projectName, 'private')
      // In a real implementation, we'd get the created project ID and upload files
      console.log('Would upload files to new project:', files)
    }
  }, [onProjectCreate])

  // Handle drag and drop for existing projects
  const handleProjectDrop = useCallback(async (e: React.DragEvent, projectId: string) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOverProject(null)
    
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      await onFileUpload(projectId, files)
    }
  }, [onFileUpload])

  const handleCreateProject = async () => {
    if (newProjectName.trim()) {
      await onProjectCreate(newProjectName.trim(), newProjectVisibility)
      setNewProjectName('')
      setShowCreateForm(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--border)' }}>
        </div>
      </div>
    )
  }

  return (
    <div>
      {/* Grid Layout following vault.profile.json specifications */}
      <div 
        className="grid gap-4 pt-4"
        style={{
          gridTemplateColumns: 'repeat(5, minmax(240px, 1fr))',
          gap: '16px',
          rowGap: '16px'
        }}
      >
        {/* New Project Card - Always first in grid */}
        <div
          className="relative p-4 border-2 border-dashed rounded-lg text-center cursor-pointer transition-all group"
          style={{
            minWidth: '260px',
            minHeight: '160px',
            backgroundColor: 'var(--bg-card)',
            borderColor: 'var(--border)',
            borderRadius: 'var(--radius-lg, 10px)',
            boxShadow: 'var(--shadow-sm)',
            padding: '16px'
          }}
          onDragOver={(e) => {
            e.preventDefault()
            e.currentTarget.style.backgroundColor = 'var(--bg-tab-hover)'
            e.currentTarget.style.borderColor = 'var(--border-focus)'
          }}
          onDragLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--bg-card)'
            e.currentTarget.style.borderColor = 'var(--border)'
          }}
          onDrop={handleNewProjectDrop}
          onClick={() => setShowCreateForm(true)}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = 'var(--shadow-md)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
          }}
        >
          <div className="flex flex-col items-center justify-center h-full">
            <FolderPlus 
              size={24} 
              className="mb-3"
              style={{ color: 'var(--icon-primary)' }}
            />
            <h3 
              style={{
                fontSize: 'var(--font-size-h2)',
                lineHeight: 'var(--line-height-h2)',
                fontWeight: '600',
                color: 'var(--text)',
                marginBottom: '8px'
              }}
            >
              New project
            </h3>
            <p 
              className="mb-3 text-center"
              style={{
                fontSize: 'var(--font-size-caption)',
                lineHeight: 'var(--line-height-caption)',
                color: 'var(--text-muted)'
              }}
            >
              Each project can contain up to 10,000 files
            </p>
            <div 
              className="px-3 py-1 rounded text-sm transition-colors"
              style={{
                color: 'var(--text-2)',
                backgroundColor: 'transparent',
                borderRadius: 'var(--radius-sm, 6px)'
              }}
            >
              Create
            </div>
          </div>

          {/* Drag hint overlay */}
          <div className="absolute inset-2 border-2 border-dashed rounded-lg opacity-0 group-hover:opacity-50 transition-opacity pointer-events-none"
               style={{ borderColor: 'var(--border-focus)' }}>
            <div className="flex items-center justify-center h-full">
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Drop files to create & upload
              </span>
            </div>
          </div>
        </div>

        {/* Project Cards */}
        {projects.map((project) => (
          <div
            key={project.id}
            className="relative p-4 border rounded-lg cursor-pointer transition-all group"
            style={{
              minWidth: '240px',
              minHeight: '140px',
              backgroundColor: dragOverProject === project.id ? 'var(--bg-tab-hover)' : 'var(--bg-card)',
              borderColor: dragOverProject === project.id ? 'var(--border-focus)' : 'var(--border)',
              borderRadius: 'var(--radius-lg, 10px)',
              boxShadow: 'var(--shadow-sm)',
              borderWidth: dragOverProject === project.id ? '2px' : '1px',
              padding: '16px'
            }}
            onDragOver={(e) => {
              e.preventDefault()
              setDragOverProject(project.id)
            }}
            onDragLeave={(e) => {
              // Only clear if leaving the entire card area
              const rect = e.currentTarget.getBoundingClientRect()
              const x = e.clientX
              const y = e.clientY
              if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
                setDragOverProject(null)
              }
            }}
            onDrop={(e) => handleProjectDrop(e, project.id)}
            onMouseEnter={(e) => {
              if (dragOverProject !== project.id) {
                e.currentTarget.style.boxShadow = 'var(--shadow-md)'
              }
            }}
            onMouseLeave={(e) => {
              if (dragOverProject !== project.id) {
                e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
              }
            }}
            role="gridcell"
            aria-label={`Project: ${project.name}`}
            tabIndex={0}
          >
            <div className="flex flex-col h-full">
              {/* Header with thumbnail and menu */}
              <div className="flex items-start justify-between mb-3">
                {/* Thumbnail */}
                <div 
                  className="flex items-center justify-center"
                  style={{
                    width: '48px',
                    height: '48px',
                    backgroundColor: 'var(--bg-subtle)',
                    borderRadius: 'var(--radius-md, 8px)'
                  }}
                >
                  <Folder size={24} style={{ color: 'var(--icon-primary)' }} />
                </div>
                
                {/* Menu */}
                <div className="relative">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setActiveMenu(activeMenu === project.id ? null : project.id)
                    }}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded"
                    style={{ color: 'var(--icon-muted)' }}
                    aria-label="Project menu"
                  >
                    <MoreVertical size={16} />
                  </button>
                  
                  {activeMenu === project.id && (
                    <div 
                      className="absolute right-0 top-full mt-1 py-1 rounded shadow-lg border z-10"
                      style={{
                        backgroundColor: 'var(--bg-card)',
                        borderColor: 'var(--border)',
                        borderRadius: 'var(--radius-md, 8px)',
                        boxShadow: 'var(--shadow-lg)',
                        minWidth: '120px'
                      }}
                      role="menu"
                    >
                      <button 
                        className="w-full px-3 py-2 text-left text-sm hover:bg-opacity-50 flex items-center gap-2"
                        style={{ color: 'var(--text)' }}
                        role="menuitem"
                      >
                        <Eye size={14} />
                        Open
                      </button>
                      <button 
                        className="w-full px-3 py-2 text-left text-sm hover:bg-opacity-50 flex items-center gap-2"
                        style={{ color: 'var(--text)' }}
                        role="menuitem"
                      >
                        <Edit size={14} />
                        Rename
                      </button>
                      <button 
                        className="w-full px-3 py-2 text-left text-sm hover:bg-opacity-50 flex items-center gap-2"
                        style={{ color: 'var(--text)' }}
                        role="menuitem"
                      >
                        <Share size={14} />
                        Share
                      </button>
                      <hr style={{ borderColor: 'var(--border-muted)', margin: '4px 0' }} />
                      <button 
                        className="w-full px-3 py-2 text-left text-sm hover:bg-opacity-50 flex items-center gap-2"
                        style={{ color: 'var(--destructive, #ef4444)' }}
                        onClick={() => onProjectDelete(project.id)}
                        role="menuitem"
                      >
                        <Trash size={14} />
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Project Title */}
              <h3 
                className="flex-1 mb-3"
                style={{
                  fontSize: 'var(--font-size-h2)',
                  lineHeight: 'var(--line-height-h2)',
                  fontWeight: '600',
                  color: 'var(--text)'
                }}
              >
                {project.name}
              </h3>
              
              {/* Metadata */}
              <div className="flex items-center gap-2 flex-wrap">
                <span 
                  className="px-2 py-1 rounded text-xs capitalize"
                  style={{
                    backgroundColor: project.visibility === 'shared' ? 'var(--bg-tab-selected)' : 'var(--bg-badge)',
                    color: 'var(--text-2)',
                    borderRadius: 'var(--radius-sm, 6px)'
                  }}
                >
                  {project.visibility}
                </span>
                <span 
                  style={{
                    fontSize: 'var(--font-size-caption)',
                    color: 'var(--text-muted)'
                  }}
                >
                  {formatRelativeDate(project.updated_at)}
                </span>
                {project.document_count > 0 && (
                  <>
                    <span style={{ color: 'var(--text-muted)' }}>•</span>
                    <span 
                      className="flex items-center gap-1"
                      style={{
                        fontSize: 'var(--font-size-caption)',
                        color: 'var(--text-muted)'
                      }}
                    >
                      <FileText size={12} />
                      {project.document_count} files
                    </span>
                  </>
                )}
                {/* Attention indicator */}
                {project.updated_at && new Date(project.updated_at) > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) && (
                  <div 
                    className="w-2 h-2 rounded-full ml-auto"
                    style={{ backgroundColor: '#1F7AE0' }}
                    title="Recent activity"
                  />
                )}
              </div>
            </div>

            {/* Drop overlay */}
            {dragOverProject === project.id && (
              <div className="absolute inset-2 border-2 border-dashed rounded-lg flex items-center justify-center bg-opacity-50"
                   style={{ 
                     borderColor: 'var(--border-focus)',
                     backgroundColor: 'var(--bg-subtle)'
                   }}>
                <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                  Drop files to upload
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Empty State */}
      {projects.length === 0 && (
        <div className="text-center py-12">
          <Folder 
            size={48} 
            className="mx-auto mb-4" 
            style={{ color: 'var(--icon-muted)' }}
          />
          <h3 
            className="mb-2"
            style={{
              fontSize: 'var(--font-size-h2)',
              color: 'var(--text)'
            }}
          >
            No projects yet
          </h3>
          <p style={{ color: 'var(--text-muted)' }}>
            Create a new project or drag files here to get started.
          </p>
        </div>
      )}

      {/* Create Project Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div 
            className="p-6 rounded-lg max-w-md w-full mx-4"
            style={{
              backgroundColor: 'var(--bg-card)',
              borderRadius: 'var(--radius-lg, 10px)',
              boxShadow: 'var(--shadow-lg)'
            }}
          >
            <h3 
              className="mb-4"
              style={{
                fontSize: 'var(--font-size-h2)',
                fontWeight: '600',
                color: 'var(--text)'
              }}
            >
              Create New Project
            </h3>
            
            <div className="space-y-4">
              <div>
                <label 
                  className="block mb-2"
                  style={{
                    fontSize: 'var(--font-size-label)',
                    color: 'var(--text)'
                  }}
                >
                  Project Name
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    borderColor: 'var(--border)',
                    borderRadius: 'var(--radius-md, 8px)',
                    color: 'var(--text)'
                  }}
                  placeholder="Enter project name..."
                  autoFocus
                />
              </div>
              
              <div>
                <label 
                  className="block mb-2"
                  style={{
                    fontSize: 'var(--font-size-label)',
                    color: 'var(--text)'
                  }}
                >
                  Visibility
                </label>
                <select
                  value={newProjectVisibility}
                  onChange={(e) => setNewProjectVisibility(e.target.value as 'private' | 'shared')}
                  className="w-full px-3 py-2 border rounded-md"
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    borderColor: 'var(--border)',
                    borderRadius: 'var(--radius-md, 8px)',
                    color: 'var(--text)'
                  }}
                >
                  <option value="private">Private</option>
                  <option value="shared">Shared</option>
                </select>
              </div>
            </div>
            
            <div className="flex gap-2 mt-6">
              <button
                onClick={() => setShowCreateForm(false)}
                className="flex-1 px-4 py-2 rounded transition-colors"
                style={{
                  backgroundColor: 'var(--bg-subtle)',
                  color: 'var(--text-2)',
                  borderRadius: 'var(--radius-md, 8px)'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleCreateProject}
                disabled={!newProjectName.trim()}
                className="flex-1 px-4 py-2 rounded transition-colors disabled:opacity-50"
                style={{
                  backgroundColor: 'var(--btn-bg)',
                  color: 'var(--btn-text)',
                  borderRadius: 'var(--radius-md, 8px)'
                }}
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Click outside to close menu */}
      {activeMenu && (
        <div 
          className="fixed inset-0 z-5"
          onClick={() => setActiveMenu(null)}
        />
      )}
    </div>
  )
}