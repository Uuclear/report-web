import { useState, useCallback } from 'react'
import { Upload, FileText, CheckCircle, XCircle, Loader2, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { formatFileSize } from '../lib/utils'

interface FileInfo {
  file: File
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  message?: string
  data?: {
    report_no?: string
    source?: string
    info?: Record<string, string>
    /** qrcode_crawl | qrcode_query | ai_ocr */
    method?: string
  }
  expanded?: boolean
}

export default function UploadPage() {
  const [files, setFiles] = useState<FileInfo[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [sourceType, setSourceType] = useState<'auto' | 'limis' | 'scetia'>('auto')

  const generateId = () => Math.random().toString(36).substr(2, 9)

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files) {
      const newFiles: FileInfo[] = Array.from(e.dataTransfer.files).map(file => ({
        file,
        id: generateId(),
        status: 'pending'
      }))
      setFiles(prev => [...prev, ...newFiles])
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles: FileInfo[] = Array.from(e.target.files).map(file => ({
        file,
        id: generateId(),
        status: 'pending'
      }))
      setFiles(prev => [...prev, ...newFiles])
    }
  }, [])

  const removeFile = useCallback((id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id))
  }, [])

  const clearAll = useCallback(() => {
    setFiles([])
  }, [])

  const toggleExpand = useCallback((id: string) => {
    setFiles(prev => prev.map(f => f.id === id ? { ...f, expanded: !f.expanded } : f))
  }, [])

  const uploadFiles = useCallback(async () => {
    if (files.length === 0) return
    setIsUploading(true)

    try {
      // 逐个上传文件，保持ID映射
      for (const fileInfo of files) {
        if (fileInfo.status !== 'pending') continue
        
        setFiles(prev => prev.map(f => f.id === fileInfo.id ? { ...f, status: 'processing' } : f))

        const formData = new FormData()
        formData.append('file', fileInfo.file)
        formData.append('source_type', sourceType)

        const response = await fetch('http://localhost:8080/api/upload/single', {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          setFiles(prev => prev.map(f => f.id === fileInfo.id ? { ...f, status: 'failed', message: `上传失败: ${response.status}` } : f))
          continue
        }

        const result = await response.json()
        // 更新ID为后端返回的file_id，并开始轮询
        setFiles(prev => prev.map(f => f.id === fileInfo.id ? { ...f, id: result.file_id } : f))
        pollProgress(result.file_id, fileInfo.id)
      }
    } catch (err) {
      console.error('Upload error:', err)
      setFiles(prev => prev.map(f => ({ ...f, status: 'failed', message: String(err) })))
    } finally {
      setIsUploading(false)
    }
  }, [files, sourceType])

  const pollProgress = async (backendFileId: string, originalId: string) => {
    let attempts = 0
    const maxAttempts = 120 // 约 3 分钟（1.5s 间隔）

    const poll = async () => {
      attempts += 1
      try {
        const response = await fetch(`http://localhost:8080/api/upload/status/${backendFileId}`)
        const progress = await response.json()

        // 后台尚未登记时会出现 not_found，界面保持「处理中」，避免卡死或显示异常
        if (progress.status === 'not_found') {
          if (attempts >= maxAttempts) {
            setFiles(prev => prev.map(f => {
              if (f.id === backendFileId || f.id === originalId) {
                return { ...f, id: backendFileId, status: 'failed', message: '长时间未获取到处理状态，请重试' }
              }
              return f
            }))
            return
          }
          setTimeout(poll, 1500)
          return
        }

        setFiles(prev => prev.map(f => {
          if (f.id === backendFileId || f.id === originalId) {
            return {
              ...f,
              id: backendFileId,
              status: progress.status === 'processing' ? 'processing' : progress.status,
              message: progress.message,
              data: progress.data
            }
          }
          return f
        }))

        if (progress.status !== 'completed' && progress.status !== 'failed') {
          if (attempts >= maxAttempts) {
            setFiles(prev => prev.map(f => {
              if (f.id === backendFileId || f.id === originalId) {
                return { ...f, id: backendFileId, status: 'failed', message: '处理超时，请重试' }
              }
              return f
            }))
            return
          }
          setTimeout(poll, 1500)
        }
      } catch (err) {
        console.error('Poll error:', err)
        setFiles(prev => prev.map(f => {
          if (f.id === backendFileId || f.id === originalId) {
            return { ...f, status: 'failed', message: '获取状态失败' }
          }
          return f
        }))
      }
    }
    poll()
  }

  const pendingFiles = files.filter(f => f.status === 'pending')
  const completedFiles = files.filter(f => f.status === 'completed')
  const failedFiles = files.filter(f => f.status === 'failed')

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">上传文档</h1>
        <p className="text-gray-600">批量上传图片或PDF文件，自动识别二维码并提取报告信息</p>
      </div>

      {/* Source Type */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <label className="text-sm font-medium text-gray-700 mb-2 block">数据来源</label>
        <div className="flex gap-4">
          {[
            { value: 'auto', label: '自动识别' },
            { value: 'limis', label: 'Limis' },
            { value: 'scetia', label: 'Scetia' }
          ].map(option => (
            <label key={option.value} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="sourceType"
                value={option.value}
                checked={sourceType === option.value}
                onChange={() => setSourceType(option.value as typeof sourceType)}
                className="w-4 h-4 text-indigo-600"
              />
              <span className="text-gray-700">{option.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Upload Area */}
      <div
        className={`relative border-2 border-dashed rounded-xl p-12 transition-colors cursor-pointer ${
          dragActive ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 hover:border-indigo-400 hover:bg-gray-50'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          accept="image/*,.pdf"
          multiple
          onChange={handleFileSelect}
        />
        <div className="text-center">
          <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-lg text-gray-600 mb-2">拖拽文件到此处，或点击选择文件</p>
          <p className="text-sm text-gray-400">支持批量上传 JPG、PNG、PDF 格式</p>
        </div>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">文件列表</h2>
              <p className="text-sm text-gray-500">
                共 {files.length} 个文件，{completedFiles.length} 个完成，{failedFiles.length} 个失败
              </p>
            </div>
            <div className="flex gap-2">
              <button onClick={clearAll} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg flex items-center gap-2">
                <Trash2 className="w-4 h-4" /> 清空
              </button>
              {pendingFiles.length > 0 && (
                <button
                  onClick={uploadFiles}
                  disabled={isUploading}
                  className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium disabled:opacity-50 flex items-center gap-2"
                >
                  {isUploading ? <><Loader2 className="w-4 h-4 animate-spin" /> 上传中...</> : <><Upload className="w-4 h-4" /> 开始上传</>}
                </button>
              )}
            </div>
          </div>

          <div className="divide-y divide-gray-100">
            {files.map(fileItem => (
              <div key={fileItem.id}>
                <div className="px-6 py-4 flex items-center gap-4">
                  <FileText className="w-8 h-8 text-gray-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{fileItem.file.name}</p>
                    <p className="text-xs text-gray-500">{formatFileSize(fileItem.file.size)}</p>
                    {fileItem.message && <p className="text-xs text-gray-500 mt-1">{fileItem.message}</p>}
                  </div>
                  <div className="flex items-center gap-2">
                    {fileItem.status === 'pending' && (
                      <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">待上传</span>
                    )}
                    {fileItem.status === 'processing' && (
                      <div className="flex items-center gap-2 text-indigo-600">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="text-sm">处理中</span>
                      </div>
                    )}
                    {fileItem.status === 'completed' && (
                      <div className="flex items-center gap-2 text-green-600">
                        <CheckCircle className="w-4 h-4" />
                        <span className="text-sm">完成</span>
                      </div>
                    )}
                    {fileItem.status === 'failed' && (
                      <div className="flex items-center gap-2 text-red-600">
                        <XCircle className="w-4 h-4" />
                        <span className="text-sm">失败</span>
                      </div>
                    )}
                    {fileItem.status === 'pending' && (
                      <button onClick={() => removeFile(fileItem.id)} className="p-1 text-gray-400 hover:text-red-500">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                    {fileItem.data && (
                      <button onClick={() => toggleExpand(fileItem.id)} className="p-1 text-gray-400 hover:text-gray-600">
                        {fileItem.expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                      </button>
                    )}
                  </div>
                </div>
                
                {/* 展开显示详细信息 */}
                {fileItem.expanded && fileItem.data && (
                  <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
                    <div className="flex items-center flex-wrap gap-2 mb-3">
                      <span className="px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-sm font-medium">
                        {fileItem.data.source?.toUpperCase()}
                      </span>
                      {fileItem.data.method === 'ai_ocr' && (
                        <span className="px-3 py-1 bg-amber-100 text-amber-900 rounded-full text-sm font-medium">
                          AI 识别
                        </span>
                      )}
                      {(fileItem.data.method === 'qrcode_crawl' || fileItem.data.method === 'qrcode_query') && (
                        <span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-sm font-medium">
                          二维码
                        </span>
                      )}
                      <span className="text-sm text-gray-600">
                        报告编号: {fileItem.data.report_no || '—'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                      {fileItem.data.info && Object.entries(fileItem.data.info).map(([key, value]) => (
                        value && (
                          <div key={key} className="bg-white rounded-lg p-3 border border-gray-200">
                            <p className="text-xs text-gray-500 mb-1">{key}</p>
                            <p className="text-sm text-gray-900 font-medium truncate" title={String(value)}>{String(value)}</p>
                          </div>
                        )
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary */}
      {files.length > 0 && (completedFiles.length > 0 || failedFiles.length > 0) && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-gray-900">{files.length}</p>
            <p className="text-sm text-gray-500">总文件数</p>
          </div>
          <div className="bg-green-50 rounded-xl border border-green-200 p-4 text-center">
            <p className="text-2xl font-bold text-green-700">{completedFiles.length}</p>
            <p className="text-sm text-green-600">处理成功</p>
          </div>
          <div className="bg-red-50 rounded-xl border border-red-200 p-4 text-center">
            <p className="text-2xl font-bold text-red-700">{failedFiles.length}</p>
            <p className="text-sm text-red-600">处理失败</p>
          </div>
        </div>
      )}
    </div>
  )
}