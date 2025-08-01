import { useCallback, useRef, useState } from 'react'

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
  instrument_type: string
  jurisdiction: string
}

export interface StreamDone {
  type: 'done'
  final_response: string
  citations: Citation[]
}

// Workflow-specific event types
export interface WorkflowStart {
  type: 'workflow_start'
  run_id: string
  workflow_type: string
  timestamp: string
}

export interface WorkflowProgress {
  type: 'progress'
  run_id: string
  node: string
  progress: string
  timestamp: string
}

export interface WorkflowComplete {
  type: 'workflow_complete'
  run_id: string
  success: boolean
  output: any
  citations: Citation[]
  timestamp: string
}

export interface WorkflowError {
  type: 'error'
  run_id: string
  error: string
  node: string
  timestamp: string
}

export type StreamEvent = ThinkingState | TextChunk | Citation | StreamDone | WorkflowStart | WorkflowProgress | WorkflowComplete | WorkflowError

export interface UseSSEStreamOptions {
  onThinkingState?: (state: ThinkingState) => void
  onTextChunk?: (chunk: TextChunk) => void
  onCitation?: (citation: Citation) => void
  onDone?: (done: StreamDone) => void
  onError?: (error: Error) => void
  // Workflow-specific callbacks
  onWorkflowStart?: (start: WorkflowStart) => void
  onWorkflowProgress?: (progress: WorkflowProgress) => void
  onWorkflowComplete?: (complete: WorkflowComplete) => void
  onWorkflowError?: (error: WorkflowError) => void
}

export interface UseSSEStreamReturn {
  isStreaming: boolean
  events: StreamEvent[]
  error: string | null
  startStream: (url: string, options?: RequestInit) => void
  stopStream: () => void
  clearEvents: () => void
}

/**
 * Custom hook for handling SSE streams from the backend
 * Follows examples/assistant_run.py pattern for event handling
 * Supports thinking states, text chunks, citations, and completion events
 */
export function useSSEStream(options: UseSSEStreamOptions = {}): UseSSEStreamReturn {
  const [isStreaming, setIsStreaming] = useState(false)
  const [events, setEvents] = useState<StreamEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const stopStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsStreaming(false)
  }, [])

  const startStream = useCallback(async (url: string, requestOptions: RequestInit = {}) => {
    // Clean up any existing stream
    stopStream()
    setError(null)
    setEvents([])
    setIsStreaming(true)

    try {
      // Create abort controller for this request
      abortControllerRef.current = new AbortController()

      // For POST requests with body, we need to use fetch with SSE
      if (requestOptions.method === 'POST' && requestOptions.body) {
        const response = await fetch(url, {
          ...requestOptions,
          headers: {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
            ...requestOptions.headers,
          },
          signal: abortControllerRef.current.signal,
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        if (!response.body) {
          throw new Error('No response body')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6)
                if (data === '[DONE]') {
                  setIsStreaming(false)
                  return
                }

                try {
                  const event = JSON.parse(data) as StreamEvent
                  setEvents(prev => [...prev, event])

                  // Call appropriate callback
                  switch (event.type) {
                    case 'thinking_state':
                      options.onThinkingState?.(event)
                      break
                    case 'chunk':
                      options.onTextChunk?.(event)
                      break
                    case 'citation':
                      options.onCitation?.(event)
                      break
                    case 'done':
                      options.onDone?.(event)
                      setIsStreaming(false)
                      return
                    case 'workflow_start':
                      options.onWorkflowStart?.(event)
                      break
                    case 'progress':
                      options.onWorkflowProgress?.(event)
                      break
                    case 'workflow_complete':
                      options.onWorkflowComplete?.(event)
                      setIsStreaming(false)
                      return
                    case 'error':
                      options.onWorkflowError?.(event)
                      setIsStreaming(false)
                      return
                  }
                } catch (parseError) {
                  console.warn('Failed to parse SSE event:', data, parseError)
                }
              }
            }
          }
        } finally {
          reader.releaseLock()
        }
      } else {
        // For GET requests, use EventSource
        const eventSource = new EventSource(url)
        eventSourceRef.current = eventSource

        eventSource.onopen = () => {
          setError(null)
        }

        eventSource.onmessage = (event) => {
          if (event.data === '[DONE]') {
            stopStream()
            return
          }

          try {
            const streamEvent = JSON.parse(event.data) as StreamEvent
            setEvents(prev => [...prev, streamEvent])

            // Call appropriate callback
            switch (streamEvent.type) {
              case 'thinking_state':
                options.onThinkingState?.(streamEvent)
                break
              case 'chunk':
                options.onTextChunk?.(streamEvent)
                break
              case 'citation':
                options.onCitation?.(streamEvent)
                break
              case 'done':
                options.onDone?.(streamEvent)
                stopStream()
                return
              case 'workflow_start':
                options.onWorkflowStart?.(streamEvent)
                break
              case 'progress':
                options.onWorkflowProgress?.(streamEvent)
                break
              case 'workflow_complete':
                options.onWorkflowComplete?.(streamEvent)
                stopStream()
                return
              case 'error':
                options.onWorkflowError?.(streamEvent)
                stopStream()
                return
            }
          } catch (parseError) {
            console.warn('Failed to parse SSE event:', event.data, parseError)
          }
        }

        eventSource.onerror = (event) => {
          console.error('SSE error:', event)
          setError('Connection lost. Please try again.')
          stopStream()
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      setIsStreaming(false)
      options.onError?.(err instanceof Error ? err : new Error(errorMessage))
    }
  }, [stopStream, options])

  const clearEvents = useCallback(() => {
    setEvents([])
    setError(null)
  }, [])

  return {
    isStreaming,
    events,
    error,
    startStream,
    stopStream,
    clearEvents,
  }
}