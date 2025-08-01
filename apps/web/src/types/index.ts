/**
 * TypeScript type definitions for QaAI application
 * Following core/models.py from the backend implementation
 */

export type JurisdictionType = 'DIFC' | 'DFSA' | 'UAE' | 'OTHER'

export type InstrumentType = 'Law' | 'Regulation' | 'CourtRule' | 'Rulebook' | 'Notice' | 'Other'

export type AssistantMode = 'assist' | 'draft'

export interface KnowledgeFilter {
  jurisdiction: JurisdictionType
  sources: string[]
}

export interface AssistantQuery {
  mode: AssistantMode
  prompt: string
  knowledge: KnowledgeFilter
  vault_project_id?: string
  attachments: string[]
}

export interface ThinkingState {
  type: 'thinking_state'
  label: string
  timestamp: string
}

export interface TextChunk {
  type: 'chunk'
  text: string
}

export interface Citation {
  type: 'citation'
  title: string
  section?: string
  url?: string
  instrument_type: InstrumentType
  jurisdiction: JurisdictionType
}

export interface StreamDone {
  type: 'done'
  final_response: string
  citations: Citation[]
}

export type StreamEvent = ThinkingState | TextChunk | Citation | StreamDone

export interface VaultProject {
  id: string
  name: string
  visibility: 'private' | 'shared'
  document_count: number
  created_at: string
  updated_at: string
  owner: string
}

export interface DocumentMetadata {
  id: string
  project_id: string
  filename: string
  title: string
  file_path: string
  content_type: string
  size_bytes: number
  jurisdiction: JurisdictionType
  instrument_type: InstrumentType
  upload_date: string
}

export interface WorkflowState {
  prompt?: string
  template_doc_id?: string
  reference_doc_ids: string[]
  jurisdiction: JurisdictionType
  plan?: string
  retrieved_context?: Array<Record<string, any>>
  citations?: Citation[]
  draft?: string
  thinking?: string[]
  error?: string
  model_override?: string
}

export interface EmbeddingDocument {
  id: string
  content: string
  metadata: DocumentMetadata
}

export interface RetrievalResult {
  document: EmbeddingDocument
  score: number
  chunk_index: number
}

export interface WorkflowRunConfig {
  templateDoc?: {
    id: string
    name: string
    mime: string
    sizeBytes: number
  }
  referenceDocs: Array<{
    id: string
    name: string
    mime: string
    sizeBytes: number
  }>
  options: {
    tone: 'Neutral' | 'Firm standard' | 'Client-friendly'
    instructions?: string
    trackChanges: boolean
  }
  context: {
    vaultProjectId?: string
    knowledgeSources: string[]
  }
}

export interface WorkflowRunState {
  status: 'idle' | 'uploading' | 'validating' | 'running' | 'review' | 'completed' | 'error'
  thinkingStates: Array<{
    label: string
    startedAt: string
    endedAt?: string
  }>
  output: {
    docId?: string
    previewUrl?: string
    citations: Citation[]
  }
}

// Design Profile Types
export interface DesignProfile {
  meta: {
    title: string
    purpose: string
    observed_on: string
  }
  colors: {
    semantic: {
      bg: {
        default: string
        canvas: string
        subtle: string
        sidebar: string
        card: string
        input: string
        tab: {
          selected: string
          hover: string
        }
        dropzone: string
        badge: string
      }
      border: {
        default: string
        muted: string
        focus: string
      }
      text: {
        primary: string
        secondary: string
        muted: string
        inverse: string
        placeholder: string
        link: string
      }
      icon: {
        primary: string
        muted: string
      }
      action: {
        primary: {
          bg: string
          text: string
          hoverBg: string
          activeBg: string
        }
      }
      focus: {
        ring: string
      }
      shadow: {
        color: string
      }
    }
  }
  typography: {
    font_family_stack: string[]
    scale: {
      display: { size: number; lineHeight: number; weight: number; tracking: number }
      h1: { size: number; lineHeight: number; weight: number; tracking: number }
      h2: { size: number; lineHeight: number; weight: number; tracking: number }
      body: { size: number; lineHeight: number; weight: number; tracking: number }
      label: { size: number; lineHeight: number; weight: number; tracking: number }
      caption: { size: number; lineHeight: number; weight: number; tracking: number }
    }
  }
  radii: {
    xs: number
    sm: number
    md: number
    lg: number
    xl: number
    pill: number
  }
  shadows: {
    sm: string
    md: string
    lg: string
  }
  spacing: {
    unit: number
    scale: number[]
  }
  layout: {
    app_shell: {
      sidebar: {
        width: number
        paddingX: number
        paddingY: number
        borderRight: boolean
      }
      topbar: {
        height: number
        paddingX: number
      }
      content: {
        maxWidth: number
        paddingX: number
        paddingY: number
      }
    }
  }
  interaction: {
    timings_ms: {
      fast: number
      base: number
      slow: number
    }
    easings: {
      standard: string
    }
    focus_ring: string
    hover_opacity: number
    press_opacity: number
  }
}

// Lucide Icon component type
export type LucideIconType = React.ComponentType<{
  size?: string | number
  className?: string
  style?: React.CSSProperties
  [key: string]: any
}>

// UI Component Props
export interface TabProps {
  id: string
  label: string
  icon?: LucideIconType
  selected?: boolean
}

export interface NavItemProps {
  icon: LucideIconType
  label: string
  path: string
  active?: boolean
}

export interface WorkflowCardProps {
  id: string
  title: string
  description: string
  icon: LucideIconType
  steps: string
  category: 'general' | 'transactional'
}