import os, io, base64
from pathlib import Path
from fastapi import HTTPException
from backend.core.config import settings

def get_file_path(filename: str) -> Path:
    fp = settings.UPLOAD_DIR / filename
    if not fp.exists():
        raise HTTPException(404, "文件不存在")
    return fp

def preview_word(file_path: Path) -> str:
    """使用 mammoth 将 docx 转为 HTML，保留图片和样式"""
    try:
        import mammoth
        with open(file_path, "rb") as f:
            result = mammoth.convert_to_html(f)
        html = result.value
        # 包裹基础样式
        styled = f"""<html><head><meta charset="utf-8"><style>
            body {{ font-family: 'Microsoft YaHei', sans-serif; padding: 20px; max-width: 900px; margin: 0 auto; line-height: 1.8; }}
            img {{ max-width: 100%; height: auto; }}
            table {{ border-collapse: collapse; width: 100%; }}
            td, th {{ border: 1px solid #ddd; padding: 8px; }}
        </style></head><body>{html}</body></html>"""
        return styled
    except ImportError:
        # 降级到 python-docx
        from docx import Document
        doc = Document(str(file_path))
        parts = ["<html><body style='font-family:sans-serif;padding:20px;'>"]
        for para in doc.paragraphs:
            text = para.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            parts.append(f"<p>{text}</p>")
        parts.append("</body></html>")
        return "".join(parts)

def preview_excel(file_path: Path) -> str:
    """Excel 转 HTML 表格，保留多 Sheet"""
    from openpyxl import load_workbook
    wb = load_workbook(str(file_path), read_only=True, data_only=True)
    html = ["<html><head><meta charset='utf-8'><style>"]
    html.append("body{font-family:sans-serif;padding:20px;}")
    html.append("table{border-collapse:collapse;width:100%;margin-bottom:20px;}")
    html.append("td,th{border:1px solid #ddd;padding:8px;text-align:left;}")
    html.append("tr:nth-child(even){background:#f9f9f9;}")
    html.append("</style></head><body>")
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        html.append(f"<h3>📊 {sheet_name}</h3><table>")
        for row in ws.iter_rows(values_only=True):
            html.append("<tr>")
            for cell in row:
                val = str(cell) if cell is not None else ""
                html.append(f"<td>{val}</td>")
            html.append("</tr>")
        html.append("</table><br>")
    html.append("</body></html>")
    return "".join(html)

def preview_ppt(file_path: Path) -> str:
    """PPT 转 HTML 幻灯片，包含文本框"""
    from pptx import Presentation
    prs = Presentation(str(file_path))
    html = ["<html><head><meta charset='utf-8'><style>"]
    html.append("body{font-family:sans-serif;text-align:center;background:#f0f0f0;}")
    html.append(".slide{background:white;margin:20px auto;padding:40px;max-width:800px;")
    html.append("box-shadow:0 2px 10px rgba(0,0,0,0.1);border-radius:8px;}")
    html.append("h2{color:#333;} p{color:#555;line-height:1.6;}")
    html.append("</style></head><body>")
    for i, slide in enumerate(prs.slides, 1):
        texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t = para.text.strip()
                    if t:
                        texts.append(t)
        content = "<br>".join(texts)
        html.append(f"<div class='slide'><h2>📄 第 {i} 页</h2><p>{content}</p></div>")
    html.append("</body></html>")
    return "".join(html)

def preview_pdf_page(file_path: Path, page_num: int = 1) -> bytes:
    """PDF 单页转 JPEG"""
    import fitz
    doc = fitz.open(str(file_path))
    if page_num < 1 or page_num > doc.page_count:
        doc.close()
        raise HTTPException(404, "页码超出范围")
    page = doc.load_page(page_num - 1)
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("jpg")
    doc.close()
    return img_bytes

def get_pdf_page_count(file_path: Path) -> int:
    import fitz
    doc = fitz.open(str(file_path))
    count = doc.page_count
    doc.close()
    return count
