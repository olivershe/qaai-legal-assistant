import { useState, useCallback } from 'react'
import { isSupportedFileType, formatFileSize } from '../utils'

export interface UploadFile {
  id: string
  file: File
  progress: number
  status: 'pending' | 'uploading' | 'completed' | 'error'
  error?: string
  url?: string
}

export interface UseFileUploadOptions {
  maxFileSize?: number // in bytes
  maxFiles?: number
  allowedTypes?: string[]
  onProgress?: (fileId: string, progress: number) => void
  onComplete?: (fileId: string, result: any) => void
  onError?: (fileId: string, error: string) => void
  onAllComplete?: (results: any[]) => void
}

export interface UseFileUploadReturn {
  files: UploadFile[]
  isUploading: boolean
  progress: number
  addFiles: (files: File[]) => void
  removeFile: (fileId: string) => void
  uploadFiles: (uploadFn: (file: File) => Promise<any>) => Promise<void>
  clearFiles: () => void
  retryFile: (fileId: string, uploadFn: (file: File) => Promise<any>) => Promise<void>
}

/**
 * Custom hook for handling file uploads with progress tracking
 * Supports drag-and-drop, validation, progress indication, and error handling
 */
export function useFileUpload(options: UseFileUploadOptions = {}): UseFileUploadReturn {
  const {
    maxFileSize = 50 * 1024 * 1024, // 50MB default
    maxFiles = 10,
    allowedTypes,
    onProgress,
    onComplete,
    onError,
    onAllComplete
  } = options

  const [files, setFiles] = useState<UploadFile[]>([])
  const [isUploading, setIsUploading] = useState(false)

  // Calculate overall progress
  const progress = files.length > 0 
    ? files.reduce((acc, file) => acc + file.progress, 0) / files.length
    : 0

  // Add files with validation
  const addFiles = useCallback((newFiles: File[]) => {
    const validFiles: UploadFile[] = []
    const errors: string[] = []

    for (const file of newFiles) {
      // Check file count limit
      if (files.length + validFiles.length >= maxFiles) {
        errors.push(`Maximum ${maxFiles} files allowed`)
        break
      }

      // Check file size
      if (file.size > maxFileSize) {
        errors.push(`${file.name} is too large (max ${formatFileSize(maxFileSize)})`)
        continue
      }

      // Check file type
      if (allowedTypes && !allowedTypes.includes(file.type)) {
        if (!isSupportedFileType(file.name)) {
          errors.push(`${file.name} is not a supported file type`)
          continue
        }
      }

      // Check for duplicates
      const duplicate = files.find(f => f.file.name === file.name && f.file.size === file.size)
      if (duplicate) {
        errors.push(`${file.name} is already added`)
        continue
      }

      validFiles.push({
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        file,
        progress: 0,
        status: 'pending'
      })
    }

    if (validFiles.length > 0) {
      setFiles(prev => [...prev, ...validFiles])
    }

    if (errors.length > 0) {
      console.warn('File upload errors:', errors)
      // You might want to show these errors to the user via a toast or notification
    }
  }, [files, maxFiles, maxFileSize, allowedTypes])

  // Remove a file
  const removeFile = useCallback((fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }, [])

  // Upload files
  const uploadFiles = useCallback(async (uploadFn: (file: File) => Promise<any>) => {
    if (files.length === 0) return

    setIsUploading(true)
    const uploadPromises: Promise<void>[] = []

    for (const uploadFile of files) {
      if (uploadFile.status !== 'pending') continue

      const promise = (async () => {
        try {
          // Set uploading status
          setFiles(prev => prev.map(f => 
            f.id === uploadFile.id 
              ? { ...f, status: 'uploading' as const, progress: 0 }
              : f
          ))

          // Simulate progress updates (in real implementation, this would come from the upload)
          const progressInterval = setInterval(() => {
            setFiles(prev => prev.map(f => {
              if (f.id === uploadFile.id && f.status === 'uploading' && f.progress < 90) {
                const newProgress = Math.min(f.progress + Math.random() * 20, 90)
                onProgress?.(f.id, newProgress)
                return { ...f, progress: newProgress }
              }
              return f
            }))
          }, 200)

          // Perform the actual upload
          const result = await uploadFn(uploadFile.file)

          clearInterval(progressInterval)

          // Set completed status
          setFiles(prev => prev.map(f => 
            f.id === uploadFile.id 
              ? { ...f, status: 'completed' as const, progress: 100, url: result?.url }
              : f
          ))

          onComplete?.(uploadFile.id, result)

        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Upload failed'
          
          setFiles(prev => prev.map(f => 
            f.id === uploadFile.id 
              ? { ...f, status: 'error' as const, error: errorMessage }
              : f
          ))

          onError?.(uploadFile.id, errorMessage)
        }
      })()

      uploadPromises.push(promise)
    }

    // Wait for all uploads to complete
    await Promise.allSettled(uploadPromises)

    setIsUploading(false)

    // Check if all files completed successfully
    const completedFiles = files.filter(f => f.status === 'completed')
    if (completedFiles.length === files.length) {
      onAllComplete?.(completedFiles.map(f => ({ id: f.id, url: f.url })))
    }
  }, [files, onProgress, onComplete, onError, onAllComplete])

  // Retry a failed upload
  const retryFile = useCallback(async (fileId: string, uploadFn: (file: File) => Promise<any>) => {
    const file = files.find(f => f.id === fileId)
    if (!file || file.status !== 'error') return

    setFiles(prev => prev.map(f => 
      f.id === fileId 
        ? { ...f, status: 'pending' as const, error: undefined, progress: 0 }
        : f
    ))

    // Upload just this file
    await uploadFiles(uploadFn)
  }, [files, uploadFiles])

  // Clear all files
  const clearFiles = useCallback(() => {
    setFiles([])
    setIsUploading(false)
  }, [])

  return {
    files,
    isUploading,
    progress,
    addFiles,
    removeFile,
    uploadFiles,
    clearFiles,
    retryFile
  }
}