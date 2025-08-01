import { FileText, Scale, Users, FileCheck, Languages, Eye } from 'lucide-react'
import { Link } from 'react-router-dom'
import { LucideIconType } from '../../types'

interface WorkflowCard {
  id: string
  title: string
  description: string
  icon: LucideIconType
  steps: string
  category: 'general' | 'transactional'
}

/**
 * WorkflowGallery following assistant.profile.json WorkflowGallery specifications
 * Implements groups, card layout, and styling as defined in the profile
 */
export function WorkflowGallery() {
  const workflows: WorkflowCard[] = [
    {
      id: 'draft-from-template',
      title: 'Draft from Template',
      description: 'Generate a redlined draft from your template with DIFC-focused legal research',
      icon: FileText,
      steps: '• 3 steps',
      category: 'general'
    },
    {
      id: 'difc-data-protection-check',
      title: 'DIFC Data Protection Check',
      description: 'Checklist-style analysis for DPL 2020 compliance (non-legal-advice)',
      icon: Scale,
      steps: '• 4 steps',
      category: 'general'
    },
    {
      id: 'employment-basics',
      title: 'Employment Basics (DIFC)',
      description: 'Starter offer/contract based on DIFC Law No. 2 of 2019',
      icon: Users,
      steps: '• 2 steps',
      category: 'transactional'
    },
    {
      id: 'document-review',
      title: 'Document Review',
      description: 'Comprehensive review with DIFC legal standards and citations',
      icon: FileCheck,
      steps: '• 3 steps',
      category: 'transactional'
    },
    {
      id: 'translate',
      title: 'Translate',
      description: 'Professional translation with legal terminology preservation',
      icon: Languages,
      steps: '• 2 steps',
      category: 'general'
    },
    {
      id: 'proofread',
      title: 'Proofread',
      description: 'Legal document proofreading with consistency checks',
      icon: Eye,
      steps: '• 1 step',
      category: 'general'
    }
  ]

  const generalWorkflows = workflows.filter(w => w.category === 'general')
  const transactionalWorkflows = workflows.filter(w => w.category === 'transactional')

  const WorkflowCardComponent = ({ workflow }: { workflow: WorkflowCard }) => {
    const Icon = workflow.icon
    
    return (
      <Link
        to={`/workflows/${workflow.id}`}
        className="block group transition-all duration-200"
      >
        <div
          className="p-4 rounded-lg transition-all duration-200 group-hover:shadow-md"
          style={{
            width: '200px',
            minHeight: '120px',
            backgroundColor: '#FBFAFA',
            border: 'none',
            borderRadius: 'var(--radius-lg, 10px)',
            boxShadow: 'var(--shadow-sm)'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = 'var(--shadow-md)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
          }}
        >
          {/* Card Content */}
          <div className="flex flex-col h-full">
            {/* Title */}
            <h3 
              className="text-h2 mb-2"
              style={{
                fontSize: 'var(--font-size-h2)',
                lineHeight: 'var(--line-height-h2)',
                fontWeight: '600',
                color: 'var(--text)'
              }}
            >
              {workflow.title}
            </h3>
            
            {/* Description */}
            <p 
              className="text-caption flex-1 mb-3"
              style={{
                fontSize: 'var(--font-size-caption)',
                lineHeight: 'var(--line-height-caption)',
                color: 'var(--text-muted)'
              }}
            >
              {workflow.description}
            </p>
            
            {/* Meta */}
            <div className="flex items-center gap-2">
              <Icon 
                size={16} 
                className="text-icon-muted"
              />
              <span 
                className="text-caption"
                style={{
                  fontSize: 'var(--font-size-caption)',
                  color: 'var(--text-muted)'
                }}
              >
                {workflow.steps}
              </span>
            </div>
          </div>
        </div>
      </Link>
    )
  }

  return (
    <div className="space-y-8">
      {/* For General Work */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 
            className="text-h2"
            style={{
              fontSize: 'var(--font-size-h2)',
              lineHeight: 'var(--line-height-h2)',
              fontWeight: '600',
              color: 'var(--text)'
            }}
          >
            For General Work
          </h2>
          <button 
            className="text-sm hover:underline transition-colors"
            style={{ 
              color: 'var(--text-link)',
              fontSize: 'var(--font-size-body)'
            }}
          >
            See all
          </button>
        </div>
        
        <div 
          className="grid gap-4"
          style={{
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: '16px'
          }}
        >
          {generalWorkflows.map((workflow) => (
            <WorkflowCardComponent key={workflow.id} workflow={workflow} />
          ))}
        </div>
      </div>

      {/* For Transactional Work */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 
            className="text-h2"
            style={{
              fontSize: 'var(--font-size-h2)',
              lineHeight: 'var(--line-height-h2)',
              fontWeight: '600',
              color: 'var(--text)'
            }}
          >
            For Transactional Work
          </h2>
          <button 
            className="text-sm hover:underline transition-colors"
            style={{ 
              color: 'var(--text-link)',
              fontSize: 'var(--font-size-body)'
            }}
          >
            See all
          </button>
        </div>
        
        <div 
          className="grid gap-4"
          style={{
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: '16px'
          }}
        >
          {transactionalWorkflows.map((workflow) => (
            <WorkflowCardComponent key={workflow.id} workflow={workflow} />
          ))}
        </div>
      </div>
    </div>
  )
}