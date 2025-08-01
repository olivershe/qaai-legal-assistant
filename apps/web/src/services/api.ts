/**
 * API service for QaAI backend communication
 * Handles REST endpoints and SSE streaming
 */

export interface AssistantQuery {
  mode: 'assist' | 'draft'
  prompt: string
  knowledge: {
    jurisdiction: 'DIFC' | 'DFSA' | 'UAE' | 'OTHER'
    sources: string[]
  }
  vault_project_id?: string
  attachments: string[]
}

export interface VaultProject {
  id: string
  name: string
  visibility: 'private' | 'shared'
  document_count: number
  created_at: string
  updated_at: string
  owner: string
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

class ApiService {
  private baseUrl: string

  constructor() {
    this.baseUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
  }

  /**
   * Assistant query with SSE streaming
   * Returns URL for SSE connection
   */
  getAssistantStreamUrl(query: AssistantQuery): string {
    const params = new URLSearchParams({
      mode: query.mode,
      prompt: query.prompt,
      jurisdiction: query.knowledge.jurisdiction,
      sources: query.knowledge.sources.join(','),
      ...(query.vault_project_id && { vault_project_id: query.vault_project_id }),
      ...(query.attachments.length > 0 && { attachments: query.attachments.join(',') })
    })
    
    return `${this.baseUrl}/api/assistant/query?${params}`
  }

  /**
   * Assistant query for POST requests
   */
  async queryAssistant(query: AssistantQuery): Promise<Response> {
    return fetch(`${this.baseUrl}/api/assistant/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(query),
    })
  }

  /**
   * Vault API methods
   */
  async getVaultProjects(): Promise<VaultProject[]> {
    const response = await fetch(`${this.baseUrl}/api/vault/projects`)
    if (!response.ok) {
      throw new Error(`Failed to fetch vault projects: ${response.statusText}`)
    }
    return response.json()
  }

  async createVaultProject(name: string, visibility: 'private' | 'shared' = 'private'): Promise<VaultProject> {
    const response = await fetch(`${this.baseUrl}/api/vault/projects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, visibility }),
    })
    if (!response.ok) {
      throw new Error(`Failed to create vault project: ${response.statusText}`)
    }
    return response.json()
  }

  async uploadToVault(projectId: string, files: File[]): Promise<void> {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })

    const response = await fetch(`${this.baseUrl}/api/vault/${projectId}/upload`, {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) {
      throw new Error(`Failed to upload files: ${response.statusText}`)
    }
  }

  async searchVault(projectId: string, query: string): Promise<any[]> {
    const params = new URLSearchParams({ query })
    const response = await fetch(`${this.baseUrl}/api/vault/${projectId}/search?${params}`)
    if (!response.ok) {
      throw new Error(`Failed to search vault: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Workflow API methods
   */
  async runWorkflow(workflowId: string, config: WorkflowRunConfig): Promise<Response> {
    return fetch(`${this.baseUrl}/api/workflows/${workflowId}/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(config),
    })
  }

  getWorkflowStreamUrl(workflowId: string, _config: WorkflowRunConfig): string {
    return `${this.baseUrl}/api/workflows/${workflowId}/run`
  }

  async getWorkflowRun(runId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/workflows/runs/${runId}`)
    if (!response.ok) {
      throw new Error(`Failed to get workflow run: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Ingestion API
   */
  async ingestDocuments(files: File[], metadata?: any): Promise<void> {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata))
    }

    const response = await fetch(`${this.baseUrl}/api/ingest`, {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) {
      throw new Error(`Failed to ingest documents: ${response.statusText}`)
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string }> {
    const response = await fetch(`${this.baseUrl}/health`)
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`)
    }
    return response.json()
  }
}

export const apiService = new ApiService()