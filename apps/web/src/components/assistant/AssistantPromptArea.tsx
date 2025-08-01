import React, { useState, useRef } from 'react'
import { Download, Save, Paperclip, Layers } from 'lucide-react'
import { useSSEStream } from '../../hooks/useSSEStream'
import { apiService } from '../../services/api'

interface AssistantPromptAreaProps {
  mode: 'assist' | 'draft'
}

/**
 * AssistantPromptArea following assistant.profile.json specifications exactly
 * Implements container, prompt_input, prompt_toolbar, and attachments_row
 */
export function AssistantPromptArea({ mode }: AssistantPromptAreaProps) {
  const [prompt, setPrompt] = useState('')
  const [attachments, setAttachments] = useState<File[]>([])
  const [response, setResponse] = useState('')
  const [thinkingStates, setThinkingStates] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const { isStreaming, startStream, stopStream, error } = useSSEStream({
    onThinkingState: (state) => {
      setThinkingStates(prev => [...prev, state.label])
    },
    onTextChunk: (chunk) => {
      setResponse(prev => prev + chunk.text)
    },
    onDone: (done) => {
      console.log('Stream completed:', done)
    },
    onError: (error) => {
      console.error('Stream error:', error)
    }
  })

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    setAttachments(prev => [...prev, ...files])
  }

  const handleSubmit = () => {
    if (prompt.trim() && !isStreaming) {
      // Clear previous response
      setResponse('')
      setThinkingStates([])
      
      // Prepare query
      const query = {
        mode,
        prompt,
        knowledge: {
          jurisdiction: 'DIFC' as const,
          sources: ['DIFC_LAWS', 'DFSA_RULEBOOK', 'DIFC_COURTS_RULES', 'VAULT']
        },
        attachments: attachments.map(f => f.name) // TODO: Upload files and get IDs
      }
      
      // Start SSE stream
      startStream(
        apiService.getAssistantStreamUrl(query), 
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(query)
        }
      )
    }
  }

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div 
      className="rounded-lg border space-y-4"
      style={{
        backgroundColor: '#FBFAFA',
        borderColor: 'rgb(var(--border-default))',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-sm)',
        padding: 'var(--spacing-8)',
        borderWidth: '1px'
      }}
    >
      {/* Prompt Input */}
      <div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask QaAI a question with documents or knowledge sources…"
          className="w-full resize-none border-0 bg-transparent focus:outline-none focus:ring-0"
          style={{
            minHeight: '96px',
            backgroundColor: '#FBFAFA',
            color: 'rgb(var(--text-primary))',
            fontSize: 'var(--font-size-body)',
            lineHeight: 'var(--line-height-body)',
            fontFamily: 'var(--font-family)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--spacing-6)',
            border: 'none',
            outline: 'none'
          }}
          rows={4}
        />
      </div>

      {/* Attachments Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* File Upload Dropzone */}
        <div
          className="border-2 border-dashed rounded-md text-center cursor-pointer transition-colors"
          style={{
            backgroundColor: '#FFFFFF',
            borderColor: 'rgb(var(--border-default))',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--spacing-6)'
          }}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            e.currentTarget.style.backgroundColor = 'rgb(var(--bg-tab-hover))'
          }}
          onDragLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#FFFFFF'
          }}
          onDrop={(e) => {
            e.preventDefault()
            e.currentTarget.style.backgroundColor = '#FFFFFF'
            const files = Array.from(e.dataTransfer.files)
            setAttachments(prev => [...prev, ...files])
          }}
        >
          <Paperclip 
            size={24} 
            className="mx-auto mb-2" 
            style={{ color: 'rgb(var(--icon-primary))' }}
          />
          <p 
            className="font-medium mb-1"
            style={{ 
              color: 'rgb(var(--text-primary))',
              fontSize: 'var(--font-size-body)',
              fontFamily: 'var(--font-family)'
            }}
          >
            Drag or click to upload files
          </p>
          <p 
            style={{ 
              color: 'rgb(var(--text-muted))',
              fontSize: 'var(--font-size-caption)',
              fontFamily: 'var(--font-family)'
            }}
          >
            Choose files from your computer, a Vault project, SharePoint, or Google Drive
          </p>
        </div>

        {/* Knowledge Source Picker */}
        <div
          className="border rounded-md text-center cursor-pointer transition-colors"
          style={{
            backgroundColor: '#FFFFFF',
            borderColor: 'rgb(var(--border-default))',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--spacing-6)',
            borderWidth: '1px'
          }}
        >
          <Layers 
            size={24} 
            className="mx-auto mb-2" 
            style={{ color: 'rgb(var(--icon-primary))' }}
          />
          <p 
            className="font-medium mb-1"
            style={{ 
              color: 'rgb(var(--text-primary))',
              fontSize: 'var(--font-size-body)',
              fontFamily: 'var(--font-family)'
            }}
          >
            Choose knowledge source
          </p>
          <p 
            style={{ 
              color: 'rgb(var(--text-muted))',
              fontSize: 'var(--font-size-caption)',
              fontFamily: 'var(--font-family)'
            }}
          >
            DIFC Laws, DFSA Rulebook, EUR‑Lex and more
          </p>
        </div>
      </div>

      {/* Attachments List */}
      {attachments.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium" style={{ color: 'var(--text-2)' }}>
            Attached files ({attachments.length})
          </p>
          <div className="space-y-1">
            {attachments.map((file, index) => (
              <div 
                key={index}
                className="flex items-center gap-2 px-2 py-1 text-sm rounded"
                style={{ backgroundColor: 'var(--bg-subtle)' }}
              >
                <Paperclip size={14} style={{ color: 'var(--icon-muted)' }} />
                <span style={{ color: 'var(--text-2)' }}>{file.name}</span>
                <button
                  onClick={() => setAttachments(prev => prev.filter((_, i) => i !== index))}
                  className="ml-auto text-xs hover:underline"
                  style={{ color: 'var(--text-muted)' }}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Response Area */}
      {(isStreaming || response || thinkingStates.length > 0 || error) && (
        <div 
          className="border-t pt-4 space-y-3"
          style={{
            borderColor: 'rgb(var(--border-default))',
            marginTop: 'var(--spacing-4)',
            paddingTop: 'var(--spacing-4)'
          }}
        >
          {/* Thinking States */}
          {thinkingStates.length > 0 && (
            <div className="space-y-1">
              {thinkingStates.map((state, index) => (
                <div 
                  key={index}
                  className="text-sm px-2 py-1 rounded"
                  style={{
                    backgroundColor: 'rgb(var(--bg-subtle))',
                    color: 'rgb(var(--text-secondary))',
                    fontSize: 'var(--font-size-caption)',
                    fontFamily: 'var(--font-family)'
                  }}
                >
                  💭 {state}
                </div>
              ))}
              {isStreaming && (
                <div 
                  className="text-sm px-2 py-1 rounded animate-pulse"
                  style={{
                    backgroundColor: 'rgb(var(--bg-subtle))',
                    color: 'rgb(var(--text-secondary))',
                    fontSize: 'var(--font-size-caption)',
                    fontFamily: 'var(--font-family)'
                  }}
                >
                  💭 Thinking...
                </div>
              )}
            </div>
          )}

          {/* Response */}
          {response && (
            <div
              className="prose max-w-none"
              style={{
                color: 'rgb(var(--text-primary))',
                fontSize: 'var(--font-size-body)',
                lineHeight: 'var(--line-height-body)',
                fontFamily: 'var(--font-family)'
              }}
            >
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                {response}
              </pre>
            </div>
          )}

          {/* Error */}
          {error && (
            <div
              className="text-red-600 text-sm px-3 py-2 rounded"
              style={{
                backgroundColor: '#FEF2F2',
                border: '1px solid #FECACA'
              }}
            >
              Error: {error}
            </div>
          )}

          {/* Loading indicator */}
          {isStreaming && (
            <div className="flex items-center gap-2 text-sm">
              <div 
                className="w-2 h-2 rounded-full animate-pulse"
                style={{ backgroundColor: 'rgb(var(--action-primary-bg))' }}
              />
              <span style={{ color: 'rgb(var(--text-secondary))' }}>
                QaAI is responding...
              </span>
              <button
                onClick={stopStream}
                className="ml-auto text-xs px-2 py-1 rounded hover:bg-gray-100"
                style={{ color: 'rgb(var(--text-muted))' }}
              >
                Stop
              </button>
            </div>
          )}
        </div>
      )}

      {/* Toolbar */}
      <div className="flex items-center justify-between pt-2">
        {/* Left Actions */}
        <div className="flex items-center gap-2">
          <button 
            className="flex items-center gap-2 px-3 py-2 rounded transition-colors"
            style={{
              color: 'rgb(var(--text-secondary))',
              fontSize: 'var(--font-size-body)',
              fontFamily: 'var(--font-family)',
              borderRadius: 'var(--radius-md)',
              background: 'none',
              border: 'none',
              cursor: 'pointer'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgb(var(--bg-tab-hover))'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent'
            }}
          >
            <Download size={16} />
            Load prompt
          </button>
          <button 
            className="flex items-center gap-2 px-3 py-2 rounded transition-colors"
            style={{
              color: 'rgb(var(--text-secondary))',
              fontSize: 'var(--font-size-body)',
              fontFamily: 'var(--font-family)',
              borderRadius: 'var(--radius-md)',
              background: 'none',
              border: 'none',
              cursor: 'pointer'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgb(var(--bg-tab-hover))'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent'
            }}
          >
            <Save size={16} />
            Save prompt
          </button>
        </div>

        {/* Right Action - Ask QaAI Button */}
        <button
          onClick={handleSubmit}
          disabled={!prompt.trim() || isStreaming}
          className="px-4 py-2 rounded font-medium transition-colors disabled:opacity-50"
          style={{
            height: '36px',
            backgroundColor: (prompt.trim() && !isStreaming) ? 'rgb(var(--action-primary-bg))' : 'rgb(var(--bg-subtle))',
            color: (prompt.trim() && !isStreaming) ? 'rgb(var(--action-primary-text))' : 'rgb(var(--text-muted))',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--font-size-body)',
            fontFamily: 'var(--font-family)',
            border: 'none',
            cursor: (prompt.trim() && !isStreaming) ? 'pointer' : 'not-allowed',
            paddingLeft: 'var(--spacing-8)',
            paddingRight: 'var(--spacing-8)'
          }}
          onMouseEnter={(e) => {
            if (prompt.trim() && !isStreaming) {
              e.currentTarget.style.backgroundColor = 'rgb(var(--action-primary-hover))'
            }
          }}
          onMouseLeave={(e) => {
            if (prompt.trim() && !isStreaming) {
              e.currentTarget.style.backgroundColor = 'rgb(var(--action-primary-bg))'
            }
          }}
        >
          {isStreaming ? 'Processing...' : 'Ask QaAI'}
        </button>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFileUpload}
        accept=".pdf,.docx,.doc,.txt,.md,.pptx,.xlsx,.csv,.eml"
      />
    </div>
  )
}