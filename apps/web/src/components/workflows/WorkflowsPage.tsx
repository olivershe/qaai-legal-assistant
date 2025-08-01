import { useParams } from 'react-router-dom'
import { WorkflowGallery } from './WorkflowGallery'
import { WorkflowRunner } from './WorkflowRunner'

/**
 * WorkflowsPage - displays workflow gallery or specific workflow runner
 * Routes to WorkflowRunner when workflowId param is present
 */
export function WorkflowsPage() {
  const { workflowId } = useParams()

  if (workflowId) {
    return <WorkflowRunner workflowId={workflowId} />
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 
          className="text-h1 mb-2"
          style={{ 
            color: 'var(--text)',
            fontSize: 'var(--font-size-h1)',
            lineHeight: 'var(--line-height-h1)',
            fontWeight: '600'
          }}
        >
          Workflows
        </h1>
        <p 
          className="text-body"
          style={{ 
            color: 'var(--text-2)',
            fontSize: 'var(--font-size-body)',
            lineHeight: 'var(--line-height-body)'
          }}
        >
          Automated legal processes with step-by-step guidance and DIFC-focused research
        </p>
      </div>

      {/* Workflow Gallery */}
      <WorkflowGallery />
    </div>
  )
}