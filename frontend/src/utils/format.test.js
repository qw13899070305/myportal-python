import { describe, expect, it } from 'vitest'

import {
  FILE_CATEGORIES,
  categoryIcon,
  categoryLabel,
  fileExtension,
  fileIcon,
  formatDate,
  formatSize,
  parseServerTime,
  previewKind,
  truncate,
} from './format'

describe('formatSize', () => {
  it('把 0 与非法值显示为 0 B', () => {
    expect(formatSize(0)).toBe('0 B')
    expect(formatSize(undefined)).toBe('0 B')
    expect(formatSize(-5)).toBe('0 B')
  })

  it('按 1024 进制换算', () => {
    expect(formatSize(512)).toBe('512 B')
    expect(formatSize(1024)).toBe('1.0 KB')
    expect(formatSize(1024 * 1024 * 3)).toBe('3.0 MB')
  })
})

describe('parseServerTime', () => {
  it('把不带时区的后端时间当作 UTC 解析', () => {
    const date = parseServerTime('2026-05-27T12:00:00')
    expect(date).not.toBeNull()
    expect(date.toISOString()).toBe('2026-05-27T12:00:00.000Z')
  })

  it('已经带时区的时间不会被重复处理', () => {
    expect(parseServerTime('2026-05-27T12:00:00Z').toISOString()).toBe(
      '2026-05-27T12:00:00.000Z',
    )
    expect(parseServerTime('2026-05-27T12:00:00+08:00').toISOString()).toBe(
      '2026-05-27T04:00:00.000Z',
    )
  })

  it('非法输入返回 null，formatDate 给出占位符', () => {
    expect(parseServerTime('')).toBeNull()
    expect(parseServerTime('not-a-date')).toBeNull()
    expect(formatDate('not-a-date')).toBe('-')
  })
})

describe('fileIcon / fileExtension', () => {
  it('识别常见扩展名', () => {
    expect(fileIcon('report.pdf')).toBe('📄')
    expect(fileIcon('sheet.XLSX')).toBe('📊')
    expect(fileIcon('unknown.abc')).toBe('📎')
    expect(fileIcon('noextension')).toBe('📎')
  })

  it('提取扩展名', () => {
    expect(fileExtension('a.tar.gz')).toBe('.gz')
    expect(fileExtension('noext')).toBe('')
  })
})

describe('truncate', () => {
  it('超长才截断', () => {
    expect(truncate('abcdef', 3)).toBe('abc…')
    expect(truncate('abc', 10)).toBe('abc')
    expect(truncate(null)).toBe('')
  })
})

describe('previewKind', () => {
  it('视频 / 音频 / 图片交给原生控件', () => {
    expect(previewKind('movie.mp4')).toBe('video')
    expect(previewKind('CLIP.MOV')).toBe('video')
    expect(previewKind('song.mp3')).toBe('audio')
    expect(previewKind('voice.m4a')).toBe('audio')
    expect(previewKind('photo.heic')).toBe('html') // 浏览器解不了 HEIC，走兜底提示页
    expect(previewKind('shot.PNG')).toBe('image')
  })

  it('其余格式走后端 HTML 预览', () => {
    for (const name of ['a.pdf', 'book.epub', 'doc.docx', 'noext']) {
      expect(previewKind(name)).toBe('html')
    }
  })
})

describe('文件分类标签', () => {
  it('后端只给机器键，中文标签在前端翻译', () => {
    expect(categoryLabel('image')).toBe('图片')
    expect(categoryLabel('ebook')).toBe('电子书')
    expect(categoryLabel('other')).toBe('其他')
    expect(categoryIcon('video')).toBe('🎬')
  })

  it('分类键顺序与后端 CATEGORY_ORDER 一致', () => {
    expect(FILE_CATEGORIES.map((item) => item.key)).toEqual([
      'image',
      'document',
      'ebook',
      'video',
      'audio',
      'archive',
      'other',
    ])
  })

  it('未知键原样返回，方便排查后端新增分类', () => {
    expect(categoryLabel('brandnew')).toBe('brandnew')
    expect(categoryLabel('')).toBe('其他')
  })
})
