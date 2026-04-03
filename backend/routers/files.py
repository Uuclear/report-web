"""
本地/在线报告下载：优先本地文件，否则跳转 Limis 在线链接
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from config import BASE_DIR
from database import SessionLocal
from database.models import LimisReport, ScetiaReport

router = APIRouter()


def _resolve_under_project(path_str: Optional[str]) -> Optional[Path]:
    """仅允许项目根目录下的真实文件，防止路径穿越"""
    if not path_str or not str(path_str).strip():
        return None
    p = Path(path_str.strip())
    if not p.is_absolute():
        p = (BASE_DIR / p).resolve()
    else:
        p = p.resolve()
    try:
        p.relative_to(BASE_DIR.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None


def _guess_media_type(suffix: str) -> str:
    s = suffix.lower()
    if s == ".pdf":
        return "application/pdf"
    if s in (".jpg", ".jpeg"):
        return "image/jpeg"
    if s == ".png":
        return "image/png"
    return "application/octet-stream"


@router.get("/limis/{report_no:path}/download")
async def download_limis_file(report_no: str):
    """优先返回本地文件，否则 302 到 Limis 在线报告页"""
    db = SessionLocal()
    try:
        r = db.query(LimisReport).filter(LimisReport.报告编号 == report_no).first()
        if not r:
            raise HTTPException(status_code=404, detail="未找到 Limis 报告")

        local = _resolve_under_project(r.本地PDF路径)
        if local:
            return FileResponse(
                path=str(local),
                filename=local.name,
                media_type=_guess_media_type(local.suffix),
            )

        if r.报告下载链接 and str(r.报告下载链接).strip().startswith("http"):
            return RedirectResponse(url=r.报告下载链接.strip())

        raise HTTPException(status_code=404, detail="无本地文件且无在线下载链接")
    finally:
        db.close()


@router.get("/scetia/{report_no:path}/download")
async def download_scetia_file(report_no: str):
    """返回本地已保存的 PDF/图片；Scetia 一般无统一外链，仅本地"""
    db = SessionLocal()
    try:
        r = db.query(ScetiaReport).filter(ScetiaReport.报告编号 == report_no).first()
        if not r:
            raise HTTPException(status_code=404, detail="未找到 Scetia 报告")

        local = _resolve_under_project(r.本地PDF路径)
        if local:
            return FileResponse(
                path=str(local),
                filename=local.name,
                media_type=_guess_media_type(local.suffix),
            )

        raise HTTPException(status_code=404, detail="无本地文件")
    finally:
        db.close()
