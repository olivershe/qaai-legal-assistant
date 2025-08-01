import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, Upload, Sliders } from 'lucide-react'

interface WorkflowRunnerProps {
  workflowId: string
}

/**
 * WorkflowRunner following workflow.draft-from-template.profile.json specifications
 * Implements WorkflowHeader, WorkflowSteps, ThinkingStates as defined
 */
export function WorkflowRunner({ workflowId }: WorkflowRunnerProps) {
  const [isRunning, setIsRunning] = useState(false)
  const [templateFile] = useState<File | null>(null)

  const workflowTitles: Record<string, string> = {
    'draft-from-template': 'Draft from Template',
    'difc-data-protection-check': 'DIFC Data Protection Check',
    'employment-basics': 'Employment Basics (DIFC)',
    'document-review': 'Document Review',
    'translate': 'Translate',
    'proofread': 'Proofread'
  }

  const workflowTitle = workflowTitles[workflowId] || 'Workflow'

  const handleRun = () => {
    setIsRunning(true)
    // TODO: Implement workflow execution with SSE streaming
    setTimeout(() => {
      setIsRunning(false)
    }, 5000)
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumbs and Header */}
      <div>
        <nav className="flex items-center gap-2 mb-4 text-sm">
          <Link 
            to="/assistant" 
            className="hover:underline"
            style={{ color: 'var(--text-link)' }}
          >
            Assistant
          </Link>
          <ChevronRight size={16} style={{ color: 'var(--text-muted)' }} />
          <Link 
            to="/workflows" 
            className="hover:underline"
            style={{ color: 'var(--text-link)' }}
          >
            Workflows
          </Link>
          <ChevronRight size={16} style={{ color: 'var(--text-muted)' }} />
          <span style={{ color: 'var(--text-muted)' }}>{workflowTitle}</span>
        </nav>

        <div className="flex items-center gap-3 mb-2">
          <h1 
            className="text-h1"
            style={{ 
              color: 'var(--text)',
              fontSize: 'var(--font-size-h1)',
              lineHeight: 'var(--line-height-h1)',
              fontWeight: '600'
            }}
          >
            {workflowTitle}
          </h1>
          <span 
            className="px-2 py-1 rounded text-xs font-medium"
            style={{
              backgroundColor: 'var(--bg-badge)',
              color: 'var(--text-2)',
              borderRadius: 'var(--radius-sm, 6px)'
            }}
          >
            WORKFLOW
          </span>
        </div>

        <div className="flex items-center gap-4">
          <button 
            className="text-sm hover:underline"
            style={{ color: 'var(--text-2)' }}
          >
            New thread
          </button>
          <button 
            className="text-sm hover:underline"
            style={{ color: 'var(--text-2)' }}
          >
            Share
          </button>
          <button 
            className="text-sm hover:underline"
            style={{ color: 'var(--text-2)' }}
          >
            Export
          </button>
        </div>
      </div>

      {/* Workflow Steps */}
      <div className="space-y-8">
        {/* Step 1: Upload Template */}
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div 
              className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium"
              style={{
                backgroundColor: 'var(--bg-tab-selected)',
                color: 'var(--text)'
              }}
            >
              H
            </div>
            <div className="flex-1">
              <h3 
                className="text-h2 mb-2"
                style={{
                  fontSize: 'var(--font-size-h2)',
                  lineHeight: 'var(--line-height-h2)',
                  fontWeight: '600',
                  color: 'var(--text)'
                }}
              >
                Please upload the template you would like QaAI to edit.
              </h3>
              <p 
                className="text-caption mb-4"
                style={{
                  fontSize: 'var(--font-size-caption)',
                  color: 'var(--text-muted)'
                }}
              >
                Note that filling in tables and applying significant footnotes are currently a limitation and not fully supported at this time.
              </p>
              
              <div
                className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors"
                style={{
                  backgroundColor: 'var(--bg-dropzone)',
                  borderColor: 'var(--border)',
                  borderRadius: 'var(--radius-md, 8px)'
                }}
              >
                <Upload size={24} className="mx-auto mb-2" style={{ color: 'var(--icon-primary)' }} />
                <p className="mb-2" style={{ color: 'var(--text)' }}>
                  {templateFile ? templateFile.name : 'Drag and drop template here'}
                </p>
                <button 
                  className="px-4 py-2 rounded text-sm transition-colors"
                  style={{
                    backgroundColor: 'var(--btn-bg)',
                    color: 'var(--btn-text)',
                    borderRadius: 'var(--radius-md, 8px)'
                  }}
                >
                  Choose file
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Step 2: Upload References */}
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div 
              className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium"
              style={{
                backgroundColor: 'var(--bg-tab-selected)',
                color: 'var(--text)'
              }}
            >
              H
            </div>
            <div className="flex-1">
              <h3 
                className="text-h2 mb-2"
                style={{
                  fontSize: 'var(--font-size-h2)',
                  lineHeight: 'var(--line-height-h2)',
                  fontWeight: '600',
                  color: 'var(--text)'
                }}
              >
                Please upload the documents you would like QaAI to reference when editing the template.
              </h3>
              
              <div
                className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors"
                style={{
                  backgroundColor: 'var(--bg-dropzone)',
                  borderColor: 'var(--border)',
                  borderRadius: 'var(--radius-md, 8px)'
                }}
              >
                <Upload size={24} className="mx-auto mb-2" style={{ color: 'var(--icon-primary)' }} />
                <p className="mb-2" style={{ color: 'var(--text)' }}>
                  Drag and drop files here
                </p>
                <button 
                  className="px-4 py-2 rounded text-sm transition-colors mb-2"
                  style={{
                    backgroundColor: 'var(--btn-bg)',
                    color: 'var(--btn-text)',
                    borderRadius: 'var(--radius-md, 8px)'
                  }}
                >
                  Choose files
                </button>
                <p 
                  className="text-xs"
                  style={{ color: 'var(--text-muted)' }}
                >
                  Supported types: CSV, Email, Excel, PDF, PowerPoint, Text, Word (.docx). Upload up to 10 files.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Step 3: Options */}
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div 
              className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium"
              style={{
                backgroundColor: 'var(--bg-tab-selected)',
                color: 'var(--text)'
              }}
            >
              <Sliders size={16} />
            </div>
            <div className="flex-1">
              <h3 
                className="text-h2 mb-4"
                style={{
                  fontSize: 'var(--font-size-h2)',
                  lineHeight: 'var(--line-height-h2)',
                  fontWeight: '600',
                  color: 'var(--text)'
                }}
              >
                Configure drafting options (optional)
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-label mb-2" style={{ color: 'var(--text)' }}>
                    Tone & style
                  </label>
                  <select 
                    className="w-full px-3 py-2 border rounded-md"
                    style={{
                      backgroundColor: 'var(--bg-input)',
                      borderColor: 'var(--border)',
                      borderRadius: 'var(--radius-md, 8px)',
                      color: 'var(--text)'
                    }}
                  >
                    <option>Neutral</option>
                    <option>Firm standard</option>
                    <option>Client-friendly</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-label mb-2" style={{ color: 'var(--text)' }}>
                    Key instructions
                  </label>
                  <input
                    type="text"
                    placeholder="E.g., align to precedent X; keep defined terms unchanged."
                    className="w-full px-3 py-2 border rounded-md"
                    style={{
                      backgroundColor: 'var(--bg-input)',
                      borderColor: 'var(--border)',
                      borderRadius: 'var(--radius-md, 8px)',
                      color: 'var(--text)'
                    }}
                  />
                </div>
                
                <div className="flex items-center gap-2">
                  <input 
                    type="checkbox" 
                    id="trackChanges" 
                    defaultChecked 
                    className="rounded"
                  />
                  <label htmlFor="trackChanges" className="text-label" style={{ color: 'var(--text)' }}>
                    Track changes in output
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Send Button */}
        <div className="flex justify-end">
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="px-6 py-2 rounded font-medium transition-colors disabled:opacity-50"
            style={{
              backgroundColor: 'var(--btn-bg)',
              color: 'var(--btn-text)',
              borderRadius: 'var(--radius-md, 8px)',
              fontSize: 'var(--font-size-body)'
            }}
          >
            {isRunning ? 'Running...' : 'Send'}
          </button>
        </div>

        {/* Thinking States (when running) */}
        {isRunning && (
          <div 
            className="p-4 rounded-md border"
            style={{
              backgroundColor: 'var(--bg-subtle)',
              borderColor: 'var(--border-muted)',
              borderRadius: 'var(--radius-md, 8px)'
            }}
          >
            <div className="space-y-2">
              <p className="thinking-state" style={{ color: 'var(--text)' }}>
                Parsing template...
              </p>
              <p className="thinking-state" style={{ color: 'var(--text)' }}>
                Reading references...
              </p>
              <p className="thinking-state" style={{ color: 'var(--text)' }}>
                Drafting with legal style...
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}