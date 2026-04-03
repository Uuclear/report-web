import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** 解析库内常见日期字符串（含「2024年11月22日」），失败返回 null */
function parseDisplayDate(input: string | Date): Date | null {
  if (input instanceof Date) {
    return Number.isNaN(input.getTime()) ? null : input
  }
  const s = input.trim()
  if (!s || s === '-' || s === '—' || s === '无') return null

  const cn = s.match(/^(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?$/)
  if (cn) {
    const y = Number(cn[1])
    const m = Number(cn[2]) - 1
    const day = Number(cn[3])
    const d = new Date(y, m, day)
    return Number.isNaN(d.getTime()) ? null : d
  }

  const sep = s.match(/^(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})/)
  if (sep) {
    const d = new Date(Number(sep[1]), Number(sep[2]) - 1, Number(sep[3]))
    return Number.isNaN(d.getTime()) ? null : d
  }

  const t = Date.parse(s)
  if (!Number.isNaN(t)) return new Date(t)
  return null
}

export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return '-'
  if (date instanceof Date) {
    if (Number.isNaN(date.getTime())) return '-'
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
  }
  const s = date.trim()
  if (s === '-' || s === '—' || s === '无') return '-'

  const parsed = parseDisplayDate(s)
  if (parsed) {
    return parsed.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
  }
  // 无法解析时原样展示（如特殊格式）
  return s
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}/api${endpoint}`
  
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`)
  }

  return response.json()
}

export const API_BASE = API_BASE_URL