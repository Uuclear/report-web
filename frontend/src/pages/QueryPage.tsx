import { useState, useEffect, useCallback, Fragment, type ReactNode } from 'react'
import { Download, FileDown, ExternalLink, ChevronUp, ChevronDown } from 'lucide-react'
import { formatDate, apiClient, API_BASE } from '../lib/utils'
import type { ReportItem, QueryParams, QueryDataSource } from '../types'

function pdfHref(path?: string) {
  if (!path) return ''
  return path.startsWith('http') ? path : `${API_BASE}${path}`
}

function formatReportDateOnly(dateStr?: string): string {
  if (!dateStr) return '—'
  const formatted = formatDate(dateStr)
  return formatted === '-' ? '—' : formatted
}

type SortKey = '报告编号' | '委托编号' | '工程名称' | '样品名称' | '报告日期' | '数据来源'
type SortOrder = 'asc' | 'desc'

export default function QueryPage() {
  const [reports, setReports] = useState<ReportItem[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const [sortKey, setSortKey] = useState<SortKey>('报告日期')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  const [params, setParams] = useState<QueryParams>({
    start_date: '',
    end_date: '',
    project_name: '',
    sample_name: '',
    data_source: 'all',
  })

  const fetchReports = useCallback(async () => {
    setLoading(true)
    try {
      const queryParams = new URLSearchParams()
      if (params.start_date) queryParams.append('start_date', params.start_date)
      if (params.end_date) queryParams.append('end_date', params.end_date)
      if (params.project_name) queryParams.append('project_name', params.project_name)
      if (params.sample_name) queryParams.append('sample_name', params.sample_name)
      // 不传 'both'，前端过滤掉交集
      if (params.data_source && params.data_source !== 'all' && params.data_source !== 'both') {
        queryParams.append('data_source', params.data_source)
      }

      const data = await apiClient<{ total: number; results: ReportItem[] }>(
        `/query/all?${queryParams.toString()}`
      )
      // 前端过滤掉交集报告（来源为 'both'）
      const filtered = data.results.filter(r => r.来源 !== 'both')
      setReports(filtered)
    } catch (err) {
      console.error('Failed to fetch reports:', err)
    } finally {
      setLoading(false)
    }
  }, [params])

  useEffect(() => {
    fetchReports()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleParamChange = (key: keyof QueryParams, value: string) => {
    setParams((prev) => ({
      ...prev,
      [key]: key === 'data_source' ? (value as QueryDataSource) : value,
    }))
  }

  const handleSearch = () => {
    fetchReports()
  }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortOrder('desc')
    }
  }

  const sortedReports = [...reports].sort((a, b) => {
    let valA: string = ''
    let valB: string = ''

    switch (sortKey) {
      case '报告编号':
        valA = a.报告编号 || ''
        valB = b.报告编号 || ''
        break
      case '委托编号':
        valA = a.委托编号 || ''
        valB = b.委托编号 || ''
        break
      case '工程名称':
        valA = a.工程名称 || ''
        valB = b.工程名称 || ''
        break
      case '样品名称':
        valA = a.样品名称 || ''
        valB = b.样品名称 || ''
        break
      case '报告日期':
        valA = a.limis?.报告日期 || a.scetia?.报告日期 || ''
        valB = b.limis?.报告日期 || b.scetia?.报告日期 || ''
        break
      case '数据来源':
        valA = a.来源 || ''
        valB = b.来源 || ''
        break
    }

    if (sortOrder === 'asc') {
      return valA.localeCompare(valB, 'zh-CN')
    } else {
      return valB.localeCompare(valA, 'zh-CN')
    }
  })

  const handleExport = useCallback(() => {
    const header = [
      '报告编号',
      '委托编号',
      '工程名称',
      '样品名称',
      '报告日期',
      '来源',
      'Limis查询页',
      'Scetia查询页',
      'Limis在线链接',
      'Limis本地下载',
      'Scetia本地下载',
    ]
    const esc = (c: unknown) => `"${String(c ?? '').replace(/"/g, '""')}"`
    const rows = reports.map((r) => {
      const lj = r.limis
      const sc = r.scetia
      return [
        r.报告编号,
        r.委托编号 ?? '',
        r.工程名称 ?? '',
        r.样品名称 ?? '',
        formatReportDateOnly(lj?.报告日期 || sc?.报告日期),
        r.来源 ?? '',
        lj?.query_portal_url ?? '',
        sc?.query_portal_url ?? '',
        lj?.报告下载链接 ?? '',
        lj?.pdf_download_path ? pdfHref(lj.pdf_download_path) : '',
        sc?.pdf_download_path ? pdfHref(sc.pdf_download_path) : '',
      ]
    })
    const csv = [header, ...rows].map((line) => line.map(esc).join(',')).join('\r\n')
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `查询结果_${new Date().toISOString().slice(0, 10)}.csv`
    a.style.display = 'none'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [reports])

  const toggleRow = (reportNo: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev)
      if (next.has(reportNo)) {
        next.delete(reportNo)
      } else {
        next.add(reportNo)
      }
      return next
    })
  }

  const renderPdfLinks = (report: ReportItem) => {
    const lj = report.limis
    const sc = report.scetia
    const nodes: ReactNode[] = []

    if (lj?.pdf_download_path) {
      nodes.push(
        <a
          key="lj-local"
          href={pdfHref(lj.pdf_download_path)}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-700 hover:underline inline-flex items-center gap-1 font-medium"
          onClick={(e) => e.stopPropagation()}
        >
          <Download className="w-3.5 h-3.5 flex-shrink-0" />
          Limis 本地 PDF
        </a>
      )
    }
    if (sc?.pdf_download_path) {
      nodes.push(
        <a
          key="sc-local"
          href={pdfHref(sc.pdf_download_path)}
          target="_blank"
          rel="noopener noreferrer"
          className="text-purple-700 hover:underline inline-flex items-center gap-1 font-medium"
          onClick={(e) => e.stopPropagation()}
        >
          <Download className="w-3.5 h-3.5 flex-shrink-0" />
          Scetia 本地 PDF
        </a>
      )
    }
    if (lj?.报告下载链接) {
      nodes.push(
        <a
          key="lj-online"
          href={lj.报告下载链接}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:underline inline-flex items-center gap-1 text-sm"
          onClick={(e) => e.stopPropagation()}
        >
          <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
          Limis 在线
        </a>
      )
    }

    if (nodes.length === 0) {
      return <span className="text-gray-400">—</span>
    }
    return (
      <div className="flex flex-col gap-1">
        {nodes}
      </div>
    )
  }

  const renderQueryPortals = (report: ReportItem) => {
    const lj = report.limis?.query_portal_url
    const sc = report.scetia?.query_portal_url
    if (!lj && !sc) {
      return <span className="text-gray-400">—</span>
    }
    return (
      <div className="flex flex-col gap-1">
        {lj && (
          <a
            href={lj}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline inline-flex items-center gap-1 text-sm"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
            Limis 查询
          </a>
        )}
        {sc && (
          <a
            href={sc}
            target="_blank"
            rel="noopener noreferrer"
            className="text-purple-600 hover:underline inline-flex items-center gap-1 text-sm"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
            Scetia 查询
          </a>
        )}
      </div>
    )
  }

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortKey !== column) return null
    return sortOrder === 'asc' 
      ? <ChevronUp className="w-4 h-4 inline ml-1" />
      : <ChevronDown className="w-4 h-4 inline ml-1" />
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              {/* 筛选条件行 */}
              <tr className="border-b border-gray-200">
                <td colSpan={8} className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2">
                      <label className="text-sm font-medium text-gray-700">报告日期（起）</label>
                      <input
                        type="date"
                        value={params.start_date}
                        onChange={(e) => handleParamChange('start_date', e.target.value)}
                        className="px-2 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-sm font-medium text-gray-700">报告日期（止）</label>
                      <input
                        type="date"
                        value={params.end_date}
                        onChange={(e) => handleParamChange('end_date', e.target.value)}
                        className="px-2 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-sm font-medium text-gray-700">数据来源</label>
                      <select
                        value={params.data_source ?? 'all'}
                        onChange={(e) => handleParamChange('data_source', e.target.value)}
                        className="px-2 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white text-sm"
                      >
                        <option value="all">全部</option>
                        <option value="limis">仅 Limis</option>
                        <option value="scetia">仅 Scetia</option>
                      </select>
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-sm font-medium text-gray-700">工程名称</label>
                      <input
                        type="text"
                        value={params.project_name}
                        onChange={(e) => handleParamChange('project_name', e.target.value)}
                        placeholder="输入..."
                        className="px-2 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm w-32"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-sm font-medium text-gray-700">样品名称</label>
                      <input
                        type="text"
                        value={params.sample_name}
                        onChange={(e) => handleParamChange('sample_name', e.target.value)}
                        placeholder="输入..."
                        className="px-2 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm w-32"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleSearch}
                      disabled={loading}
                      className="px-3 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    >
                      查询
                    </button>
                    <span className="text-sm text-gray-500">
                      共 {reports.length} 条
                    </span>
                    <button
                      type="button"
                      onClick={handleExport}
                      disabled={reports.length === 0}
                      className="flex items-center gap-1 px-2 py-1 text-gray-700 hover:bg-gray-100 rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed border border-gray-200 text-sm ml-auto"
                    >
                      <FileDown className="w-3.5 h-3.5" />
                      导出 CSV
                    </button>
                  </div>
                </td>
              </tr>
              {/* 表头 */}
              <tr>
                <th
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('数据来源')}
                >
                  数据来源<SortIcon column="数据来源" />
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('报告编号')}
                >
                  报告编号<SortIcon column="报告编号" />
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('委托编号')}
                >
                  委托编号<SortIcon column="委托编号" />
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('工程名称')}
                >
                  工程名称<SortIcon column="工程名称" />
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('样品名称')}
                >
                  样品名称<SortIcon column="样品名称" />
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('报告日期')}
                >
                  报告日期<SortIcon column="报告日期" />
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  PDF 报告
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  查询页面
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center">
                    <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto mb-4" />
                    <p className="text-gray-500">加载中...</p>
                  </td>
                </tr>
              ) : sortedReports.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center">
                    <p className="text-gray-500">暂无数据</p>
                  </td>
                </tr>
              ) : (
                sortedReports.map((report) => (
                  <Fragment key={report.报告编号}>
                    <tr className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex gap-1 flex-wrap">
                          {report.limis && (
                            <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                              Limis
                            </span>
                          )}
                          {report.scetia && (
                            <span className="px-2 py-0.5 bg-purple-100 text-purple-800 rounded text-xs font-medium">
                              Scetia
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm">
                        <button
                          type="button"
                          onClick={() => toggleRow(report.报告编号)}
                          className="font-medium text-indigo-600 hover:text-indigo-800 hover:underline text-left"
                        >
                          {report.报告编号}
                        </button>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                        {report.委托编号 || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate">
                        {report.工程名称 || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                        {report.样品名称 || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                        {formatReportDateOnly(report.limis?.报告日期 || report.scetia?.报告日期)}
                      </td>
                      <td className="px-4 py-3 text-sm">{renderPdfLinks(report)}</td>
                      <td className="px-4 py-3 text-sm">{renderQueryPortals(report)}</td>
                    </tr>

                    {expandedRows.has(report.报告编号) && (
                      <tr className="bg-gray-50">
                        <td colSpan={8} className="px-4 py-3">
                          <div className="grid grid-cols-2 gap-4">
                            {report.limis && (
                              <div className="bg-white rounded-lg p-3 border border-blue-200">
                                <h4 className="font-medium text-blue-800 mb-2 text-sm">Limis 数据</h4>
                                <div className="space-y-1 text-sm">
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">委托日期:</span>
                                    <span className="text-gray-900">{formatDate(report.limis.委托日期)}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">委托单位:</span>
                                    <span className="text-gray-900">{report.limis.委托单位 || '-'}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">检测机构:</span>
                                    <span className="text-gray-900">{report.limis.检测机构 || '-'}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">报告日期:</span>
                                    <span className="text-gray-900">
                                      {formatDate(report.limis.报告日期 || report.limis.签发日期)}
                                    </span>
                                  </div>
                                  <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-100 mt-2">
                                    {report.limis.pdf_download_path && (
                                      <a
                                        href={pdfHref(report.limis.pdf_download_path)}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-700 hover:underline inline-flex items-center gap-1 font-medium"
                                      >
                                        <Download className="w-3.5 h-3.5" />
                                        本地 PDF
                                      </a>
                                    )}
                                    {report.limis.报告下载链接 && (
                                      <a
                                        href={report.limis.报告下载链接}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:underline inline-flex items-center gap-1"
                                      >
                                        <ExternalLink className="w-3.5 h-3.5" />
                                        在线报告
                                      </a>
                                    )}
                                    {report.limis.query_portal_url && (
                                      <a
                                        href={report.limis.query_portal_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:underline inline-flex items-center gap-1"
                                      >
                                        <ExternalLink className="w-3.5 h-3.5" />
                                        Limis 查询页
                                      </a>
                                    )}
                                  </div>
                                </div>
                              </div>
                            )}

                            {report.scetia && (
                              <div className="bg-white rounded-lg p-3 border border-purple-200">
                                <h4 className="font-medium text-purple-800 mb-2 text-sm">Scetia 数据</h4>
                                <div className="space-y-1 text-sm">
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">委托日期:</span>
                                    <span className="text-gray-900">{formatDate(report.scetia.委托日期)}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">报告日期:</span>
                                    <span className="text-gray-900">{formatDate(report.scetia.报告日期)}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">委托单位:</span>
                                    <span className="text-gray-900">{report.scetia.委托单位 || '-'}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">施工单位:</span>
                                    <span className="text-gray-900">{report.scetia.施工单位 || '-'}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">检测结论:</span>
                                    <span className="text-gray-900">{report.scetia.检测结论 || '-'}</span>
                                  </div>
                                  <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-100 mt-2">
                                    {report.scetia.pdf_download_path && (
                                      <a
                                        href={pdfHref(report.scetia.pdf_download_path)}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-purple-700 hover:underline inline-flex items-center gap-1 font-medium"
                                      >
                                        <Download className="w-3.5 h-3.5" />
                                        本地 PDF
                                      </a>
                                    )}
                                    {report.scetia.query_portal_url && (
                                      <a
                                        href={report.scetia.query_portal_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-purple-600 hover:underline inline-flex items-center gap-1"
                                      >
                                        <ExternalLink className="w-3.5 h-3.5" />
                                        Scetia 查询页
                                      </a>
                                    )}
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}