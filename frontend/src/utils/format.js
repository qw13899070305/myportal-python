/** 纯函数格式化工具（便于单元测试，不依赖 Vue）。 */

const SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB']

/** 字节数转可读大小。 */
export function formatSize(bytes) {
  const value = Number(bytes)
  if (!Number.isFinite(value) || value <= 0) {
    return '0 B'
  }
  let index = Math.floor(Math.log(value) / Math.log(1024))
  index = Math.min(index, SIZE_UNITS.length - 1)
  const scaled = value / 1024 ** index
  return `${index === 0 ? scaled : scaled.toFixed(1)} ${SIZE_UNITS[index]}`
}

/**
 * 把后端返回的时间解析为本地 Date。
 *
 * 后端统一返回不带时区的 UTC 时间（例如 ``2026-05-27T12:00:00``），
 * 直接 new Date() 会被当成本地时间，因此这里补上 Z。
 */
export function parseServerTime(value) {
  if (!value) {
    return null
  }
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }
  const text = String(value)
  const normalized = /Z$|[+-]\d{2}:?\d{2}$/.test(text) ? text : `${text}Z`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

/** 格式化为本地日期时间；解析失败时返回占位符。 */
export function formatDateTime(value, fallback = '-') {
  const date = parseServerTime(value)
  return date ? date.toLocaleString() : fallback
}

/** 只保留日期部分。 */
export function formatDate(value, fallback = '-') {
  const date = parseServerTime(value)
  return date ? date.toLocaleDateString() : fallback
}

const ICONS = {
  pdf: '📄',
  doc: '📝',
  docx: '📝',
  xls: '📊',
  xlsx: '📊',
  ppt: '📽️',
  pptx: '📽️',
  jpg: '🖼️',
  jpeg: '🖼️',
  png: '🖼️',
  gif: '🖼️',
  webp: '🖼️',
  bmp: '🖼️',
  heic: '🖼️',
  heif: '🖼️',
  mp4: '🎬',
  mov: '🎬',
  '3gp': '🎬',
  m4v: '🎬',
  mp3: '🎵',
  m4a: '🎵',
  wav: '🎵',
  epub: '📚',
  azw3: '📚',
  mobi: '📚',
  chm: '📖',
  zip: '📦',
  txt: '📃',
  md: '📃',
  csv: '📊',
  json: '🧾',
  log: '🧾',
}

/** 根据文件名返回一个 emoji 图标。 */
export function fileIcon(name = '') {
  const ext = String(name).split('.').pop()?.toLowerCase()
  return ICONS[ext] || '📎'
}

/** 提取扩展名（含点，小写）。 */
export function fileExtension(name = '') {
  const index = String(name).lastIndexOf('.')
  return index > 0 ? String(name).slice(index).toLowerCase() : ''
}

//: 能用浏览器原生控件直接播/看的类型（数据源是后端 /files/{id}/raw 字节流）
const MEDIA_KINDS = {
  video: new Set(['mp4', 'mov', '3gp', 'm4v', 'webm']),
  audio: new Set(['mp3', 'm4a', 'wav', 'aac', 'ogg', 'flac']),
  image: new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp']),
}

/**
 * 预览方式：`video` / `audio` / `image` 用原生控件，其余交给后端的 HTML 预览。
 *
 * 判断放在前端是**故意的**：后端只提供字节流（/raw）与数据（/preview、/book），
 * "用什么控件展示"是界面自己的事。
 */
export function previewKind(name = '') {
  const ext = fileExtension(name).replace('.', '')
  for (const [kind, extensions] of Object.entries(MEDIA_KINDS)) {
    if (extensions.has(ext)) return kind
  }
  return 'html'
}

//: 文件分类的中文标签与图标。后端只给机器键（image/document/…），
//: 顺序与 backend/core/filetypes.py 的 CATEGORY_ORDER 保持一致。
export const FILE_CATEGORIES = [
  { key: 'image', label: '图片', icon: '🖼️' },
  { key: 'document', label: '文档', icon: '📄' },
  { key: 'ebook', label: '电子书', icon: '📚' },
  { key: 'video', label: '视频', icon: '🎬' },
  { key: 'audio', label: '音频', icon: '🎵' },
  { key: 'archive', label: '压缩包', icon: '📦' },
  { key: 'other', label: '其他', icon: '📎' },
]

const CATEGORY_BY_KEY = Object.fromEntries(FILE_CATEGORIES.map((item) => [item.key, item]))

/** 分类键 → 中文标签（未知键原样返回，方便排查后端新增的分类）。 */
export function categoryLabel(key) {
  return CATEGORY_BY_KEY[key]?.label || key || '其他'
}

/** 分类键 → 图标。 */
export function categoryIcon(key) {
  return CATEGORY_BY_KEY[key]?.icon || '📎'
}

/** 截断长文本。 */
export function truncate(text, max = 80) {
  const value = String(text ?? '')
  return value.length > max ? `${value.slice(0, max)}…` : value
}
