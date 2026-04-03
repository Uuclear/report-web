export interface ScanResult {
  success: boolean
  report_no: string | null
  source: 'limis' | 'scetia' | null
  data: Record<string, string>
  error?: string
  /** qrcode_crawl | qrcode_query | ai_ocr */
  method?: string | null
}

export interface UploadResult {
  file_id: string
  filename: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  message?: string
}

export interface ProcessingProgress {
  file_id: string
  current: number
  total: number
  status: string
  message?: string
}

export type QueryDataSource = 'all' | 'limis' | 'scetia' | 'both'

export interface ReportItem {
  报告编号: string
  委托编号?: string
  工程名称?: string
  样品名称?: string
  来源?: 'limis' | 'scetia' | 'both'
  /** 后端汇总展示：Limis / Scetia 报告日期 */
  报告日期展示?: string
  limis?: LimisData | null
  scetia?: ScetiaData | null
}

export interface LimisData {
  委托日期?: string
  /** 数据库「报告日期」，对应爬虫「签发日期」 */
  报告日期?: string
  签发日期?: string
  委托单位?: string
  检测机构?: string
  报告下载链接?: string
  /** 相对路径，需拼 API_BASE */
  pdf_download_path?: string
  download_url?: string
  merged_pdf_path?: string
  /** Limis 官方查询页（rQuery 等） */
  query_portal_url?: string
}

export interface ScetiaData {
  委托日期?: string
  报告日期?: string
  委托单位?: string
  施工单位?: string
  检测机构?: string
  检测结论?: string
  pdf_download_path?: string
  merged_pdf_path?: string
  /** 协会防伪/查询页 */
  query_portal_url?: string
}

export interface QueryParams {
  start_date?: string
  end_date?: string
  project_name?: string
  sample_name?: string
  data_source?: QueryDataSource
}

export interface Statistics {
  limis_total: number
  scetia_total: number
  intersection_total: number
  unique_reports: number
}