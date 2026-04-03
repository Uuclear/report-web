import { useState, useEffect, useCallback, Fragment, type ReactNode } from 'react'
import { Search, Download, Filter, FileDown, ExternalLink } from 'lucide-react'
import { formatDate, apiClient, API_BASE } from '../lib/utils'
import type { ReportItem, QueryParams, QueryDataSource, Statistics } from '../types'

function pdfHref(path?: string) {
  if (!path) return ''
  return path.startsWith('http') ? path : `${API_BASE}${path}`
}

export default function QueryPage() {
  const [reports, setReports] = useState<ReportItem[]>([])
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<Statistics | null>(null)
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  const [params, setParams] = useState<QueryParams>({
    start_date: '',
    end_date: '',
    project_name: '',
    sample_name: '',
    data_source: 'all',
  })

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiClient<Statistics>('/query/statistics')
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }, [])

  const fetchReports = useCallback(async () => {
    setLoading(true)
    try {
      const queryParams = new URLSearchParams()
      if (params.start_date) queryParams.append('start_date', params.start_date)
      if (params.end_date) queryParams.append('end_date', params.end_date)
      if (params.project_name) queryParams.append('project_name', params.project_name)
      if (params.sample_name) queryParams.append('sample_name', params.sample_name)
      if (params.data_source && params.data_source !== 'all') {
        queryParams.append('data_source', params.data_source)
      }

      const data = await apiClient<{ total: number; results: ReportItem[] }>(
        `/query/all?${queryParams.toString()}`
      )
      setReports(data.results)
    } catch (err) {
      console.error('Failed to fetch reports:', err)
    } finally {
      setLoading(false)
    }
  }, [params])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  useEffect(() => {
    fetchReports()
    // 仅首次进入页面拉取列表；改条件后需点「查询」
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

  const handleExport = useCallback(() => {
    const header = [
      '报告编号',
      '委托编号',
      '工程名称',
      '样品名称',
      '报告日期展示',
      '来源',
      'Limis查询页',
      'Scetia查询页',
      'Limis报告日期',
      'Limis在线链接',
      'Limis本地下载',
      'Scetia报告日期',
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
        r.报告日期展示 ?? '',
        r.来源 ?? '',
        lj?.query_portal_url ?? '',
        sc?.query_portal_url ?? '',
        lj?.报告日期 ?? lj?.签发日期 ?? '',
        lj?.报告下载链接 ?? '',
        lj?.pdf_download_path ? pdfHref(lj.pdf_download_path) : '',
        sc?.报告日期 ?? '',
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

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">结果查询</h1>
        <p className="text-gray-600">查询 limis 和 scetia 报告数据，按报告日期筛选</p>
      </div>

      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
            <p className="text-3xl font-bold text-indigo-600">{stats.limis_total}</p>
            <p className="text-sm text-gray-500 mt-1">Limis报告</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
            <p className="text-3xl font-bold text-purple-600">{stats.scetia_total}</p>
            <p className="text-sm text-gray-500 mt-1">Scetia报告</p>
          </div>
          <div className="bg-green-50 rounded-xl border border-green-200 p-4 text-center">
            <p className="text-3xl font-bold text-green-700">{stats.intersection_total}</p>
            <p className="text-sm text-green-600 mt-1">交集报告</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
            <p className="text-3xl font-bold text-gray-900">{stats.unique_reports}</p>
            <p className="text-sm text-gray-500 mt-1">唯一报告数</p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-5 h-5 text-gray-400" />
          <span className="font-medium text-gray-900">筛选条件</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              报告日期（起）
            </label>
            <input
              type="date"
              value={params.start_date}
              onChange={(e) => handleParamChange('start_date', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              报告日期（止）
            </label>
            <input
              type="date"
              value={params.end_date}
              onChange={(e) => handleParamChange('end_date', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              数据来源
            </label>
            <select
              value={params.data_source ?? 'all'}
              onChange={(e) => handleParamChange('data_source', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
            >
              <option value="all">全部</option>
              <option value="limis">仅 Limis</option>
              <option value="scetia">仅 Scetia</option>
              <option value="both">仅交集（两边都有）</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              工程名称
            </label>
            <input
              type="text"
              value={params.project_name}
              onChange={(e) => handleParamChange('project_name', e.target.value)}
              placeholder="输入工程名称..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              样品名称
            </label>
            <input
              type="text"
              value={params.sample_name}
              onChange={(e) => handleParamChange('sample_name', e.target.value)}
              placeholder="输入样品名称..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <button
            type="button"
            onClick={handleSearch}
            disabled={loading}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Search className="w-4 h-4" />
            查询
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              查询结果
              <span className="ml-2 text-sm font-normal text-gray-500">
                共 {reports.length} 条记录
              </span>
            </h2>
            <button
              type="button"
              onClick={handleExport}
              disabled={reports.length === 0}
              className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed border border-gray-200"
            >
              <FileDown className="w-4 h-4" />
              导出 CSV
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-500">加载中...</p>
          </div>
        ) : reports.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-500">暂无数据</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    报告编号
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    委托编号
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    工程名称
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    样品名称
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    报告日期
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    数据来源
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    PDF 报告
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    查询页面
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {reports.map((report) => (
                  <Fragment key={report.报告编号}>
                    <tr className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <button
                          type="button"
                          onClick={() => toggleRow(report.报告编号)}
                          className="font-medium text-indigo-600 hover:text-indigo-800 hover:underline text-left"
                        >
                          {report.报告编号}
                        </button>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {report.委托编号 || '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                        {report.工程名称 || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {report.样品名称 || '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-700 max-w-[14rem]">
                        {report.报告日期展示 ?? '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex gap-1 flex-wrap">
                          {report.limis && (
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                              Limis
                            </span>
                          )}
                          {report.scetia && (
                            <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs font-medium">
                              Scetia
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm">{renderPdfLinks(report)}</td>
                      <td className="px-6 py-4 text-sm">{renderQueryPortals(report)}</td>
                    </tr>

                    {expandedRows.has(report.报告编号) && (
                      <tr className="bg-gray-50">
                        <td colSpan={8} className="px-6 py-4">
                          <div className="grid grid-cols-2 gap-6">
                            {report.limis && (
                              <div className="bg-white rounded-lg p-4 border border-blue-200">
                                <h4 className="font-medium text-blue-800 mb-3">Limis 数据</h4>
                                <div className="space-y-2 text-sm">
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
                                  <div className="flex flex-wrap gap-3 pt-2 border-t border-gray-100 mt-2">
                                    {report.limis.pdf_download_path && (
                                      <a
                                        href={pdfHref(report.limis.pdf_download_path)}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-700 hover:underline inline-flex items-center gap-1 font-medium"
                                      >
                                        <Download className="w-4 h-4" />
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
                                        <ExternalLink className="w-4 h-4" />
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
                                        <ExternalLink className="w-4 h-4" />
                                        Limis 查询页
                                      </a>
                                    )}
                                  </div>
                                </div>
                              </div>
                            )}

                            {report.scetia && (
                              <div className="bg-white rounded-lg p-4 border border-purple-200">
                                <h4 className="font-medium text-purple-800 mb-3">Scetia 数据</h4>
                                <div className="space-y-2 text-sm">
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
                                  <div className="flex flex-wrap gap-3 pt-2 border-t border-gray-100 mt-2">
                                    {report.scetia.pdf_download_path && (
                                      <a
                                        href={pdfHref(report.scetia.pdf_download_path)}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-purple-700 hover:underline inline-flex items-center gap-1 font-medium"
                                      >
                                        <Download className="w-4 h-4" />
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
                                        <ExternalLink className="w-4 h-4" />
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
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
