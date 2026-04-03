import { useState, useCallback } from 'react'
import { Camera, Upload, RotateCcw, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import type { ScanResult } from '../types'

export default function ScanPage() {
  const [isScanning, setIsScanning] = useState(false)
  const [result, setResult] = useState<ScanResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const handleFileSelect = useCallback(async (file: File) => {
    setIsScanning(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(
        'http://localhost:8080/api/scan/image?source_type=auto',
        {
          method: 'POST',
          body: formData,
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data: ScanResult = await response.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '扫描失败')
    } finally {
      setIsScanning(false)
    }
  }, [])

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

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }, [handleFileSelect])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0])
    }
  }, [handleFileSelect])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">扫描文档</h1>
        <p className="text-gray-600">上传图片或PDF文件，自动识别二维码并提取报告信息</p>
      </div>

      {/* Upload Area */}
      <div
        className={`relative border-2 border-dashed rounded-xl p-12 transition-colors ${
          dragActive
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-gray-300 hover:border-indigo-400 hover:bg-gray-50'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-upload"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          accept="image/*,.pdf"
          onChange={handleInputChange}
        />

        <div className="text-center">
          {isScanning ? (
            <div className="flex flex-col items-center">
              <Loader2 className="w-16 h-16 text-indigo-600 animate-spin mb-4" />
              <p className="text-lg text-gray-600">正在识别中...</p>
            </div>
          ) : (
            <>
              <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-lg text-gray-600 mb-2">
                拖拽文件到此处，或点击选择文件
              </p>
              <p className="text-sm text-gray-400">
                支持 JPG、PNG、PDF 格式
              </p>
            </>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-red-800 font-medium">扫描失败</p>
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Result Display */}
      {result && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className={`px-6 py-4 ${
            result.success ? 'bg-green-50' : 'bg-yellow-50'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {result.success ? (
                  <CheckCircle className="w-6 h-6 text-green-600" />
                ) : (
                  <XCircle className="w-6 h-6 text-yellow-600" />
                )}
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">
                    {result.success ? '识别成功' : '识别失败'}
                  </h2>
                  {result.report_no && (
                    <p className="text-sm text-gray-600">
                      报告编号: {result.report_no}
                    </p>
                  )}
                </div>
              </div>
              <button
                onClick={reset}
                className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-white rounded-lg transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                重新扫描
              </button>
            </div>
          </div>

          {result.success && result.data && Object.keys(result.data).length > 0 && (
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(result.data).map(([key, value]) => (
                  value && (
                    <div key={key} className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-500 mb-1">{key}</p>
                      <p className="text-gray-900 font-medium">{value}</p>
                    </div>
                  )
                ))}
              </div>
            </div>
          )}

          {result.source && (
            <div className="px-6 pb-4">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                result.source === 'limis'
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-purple-100 text-purple-800'
              }`}>
                数据来源: {result.source.toUpperCase()}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Camera Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="text-center">
          <Camera className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">摄像头扫描</h3>
          <p className="text-gray-600 mb-4">
            使用摄像头实时扫描文档（需要浏览器支持）
          </p>
          <button className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium">
            打开摄像头
          </button>
        </div>
      </div>
    </div>
  )
}