import React, { useState, useRef } from 'react'
import { Download, Save, Paperclip, Layers } from 'lucide-react'

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
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    setAttachments(prev => [...prev, ...files])
  }

  const handleSubmit = () => {
    if (prompt.trim()) {
      console.log('Submit:', { mode, prompt, attachments })
      // TODO: Implement SSE streaming
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
          disabled={!prompt.trim()}
          className="px-4 py-2 rounded font-medium transition-colors disabled:opacity-50"
          style={{
            height: '36px',
            backgroundColor: prompt.trim() ? 'rgb(var(--action-primary-bg))' : 'rgb(var(--bg-subtle))',
            color: prompt.trim() ? 'rgb(var(--action-primary-text))' : 'rgb(var(--text-muted))',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--font-size-body)',
            fontFamily: 'var(--font-family)',
            border: 'none',
            cursor: prompt.trim() ? 'pointer' : 'not-allowed',
            paddingLeft: 'var(--spacing-8)',
            paddingRight: 'var(--spacing-8)'
          }}
          onMouseEnter={(e) => {
            if (prompt.trim()) {
              e.currentTarget.style.backgroundColor = 'rgb(var(--action-primary-hover))'
            }
          }}
          onMouseLeave={(e) => {
            if (prompt.trim()) {
              e.currentTarget.style.backgroundColor = 'rgb(var(--action-primary-bg))'
            }
          }}
        >
          Ask QaAI
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