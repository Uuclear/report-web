"""
上传接口 - 批量上传和文件处理
"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List, Dict, Any
from pydantic import BaseModel

from database import (
    SessionLocal,
    create_limis_report,
    create_limis_single_page,
    create_scetia_report,
    create_scetia_single_page,
)

router = APIRouter()


def _norm(val) -> str:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s in ("无", "未知"):
        return None
    return s


def persist_limis_after_crawl(file_path: str, crawl_result: Dict[str, Any]) -> None:
    """识别成功后写入 limis 单表 + 总表"""
    data = crawl_result.get("data") or {}
    report_no = crawl_result.get("report_no")
    if not report_no:
        return
    url = crawl_result.get("url")
    # Selenium 可能解析出真实 PDF 下载链，优先于二维码查询 URL
    dl = (data.get("报告下载链接") or "").strip()
    report_link = dl if dl.startswith("http") else url
    db = SessionLocal()
    try:
        create_limis_single_page(
            db,
            委托编号=_norm(data.get("委托编号")),
            报告编号=report_no,
            工程名称=_norm(data.get("工程名称")),
            page_number=0,
            total_pages=0,
            source_file=file_path,
        )
        create_limis_report(
            db,
            报告编号=report_no,
            委托编号=_norm(data.get("委托编号")),
            委托日期=_norm(data.get("委托日期/抽样日期")),
            报告日期=_norm(data.get("签发日期")),
            工程名称=_norm(data.get("工程名称")),
            工程部位=_norm(data.get("工程部位")),
            样品编号=_norm(data.get("样品编号")),
            样品名称=_norm(data.get("样品名称")),
            规格型号=_norm(data.get("规格型号")),
            委托单位=_norm(data.get("委托单位")),
            生产单位=_norm(data.get("生产单位")),
            检测机构=_norm(data.get("检测机构")),
            检验依据=_norm(data.get("检验依据")),
            报告状态=_norm(data.get("status")),
            报告下载链接=report_link,
            本地PDF路径=file_path,
        )
    finally:
        db.close()


def persist_scetia_after_query(
    file_path: str,
    report_id: str,
    security_code: str,
    query_result: Dict[str, Any],
    confidence: float = None,
) -> None:
    """识别成功后写入 scetia 单表 + 总表"""
    d = query_result.get("data") or {}
    db = SessionLocal()
    try:
        create_scetia_single_page(
            db,
            委托编号=_norm(d.get("委托编号")),
            报告编号=report_id,
            工程名称=_norm(d.get("工程名称")),
            page_number=0,
            total_pages=0,
            source_file=file_path,
            security_code=security_code,
            confidence=confidence,
        )
        create_scetia_report(
            db,
            报告编号=report_id,
            委托编号=_norm(d.get("委托编号")),
            委托日期=_norm(d.get("委托日期")),
            报告日期=_norm(d.get("报告日期")),
            工程名称=_norm(d.get("工程名称")),
            工程地址=_norm(d.get("工程地址")),
            工程部位=_norm(d.get("工程部位")),
            样品名称=_norm(d.get("样品名称")),
            样品编号=_norm(d.get("样品编号")),
            规格=_norm(d.get("规格")),
            强度等级=_norm(d.get("强度等级")),
            委托单位=_norm(d.get("委托单位")),
            施工单位=_norm(d.get("施工单位")),
            生产单位=_norm(d.get("生产单位")),
            检测机构=_norm(d.get("检测机构")),
            检测结论=_norm(d.get("检测结论")),
            样品检测结论=_norm(d.get("样品检测结论")),
            委托性质=_norm(d.get("委托性质")),
            标段=_norm(d.get("标段")),
            取样人及证书号=_norm(d.get("取样人及证书号")),
            见证人及证书号=_norm(d.get("见证人及证书号")),
            防伪码=security_code,
            本地PDF路径=file_path,
        )
    finally:
        db.close()


def persist_limis_after_ocr(file_path: str, data: Dict[str, Any]) -> None:
    """AI OCR（limis 字段模板）成功后写入 limis 单表 + 总表"""
    report_no = _norm(data.get("报告编号"))
    if not report_no:
        return
    db = SessionLocal()
    try:
        create_limis_single_page(
            db,
            委托编号=_norm(data.get("委托编号")),
            报告编号=report_no,
            工程名称=_norm(data.get("工程名称")),
            page_number=0,
            total_pages=0,
            source_file=file_path,
        )
        create_limis_report(
            db,
            报告编号=report_no,
            委托编号=_norm(data.get("委托编号")),
            委托日期=_norm(data.get("委托日期")),
            报告日期=_norm(data.get("签发日期")),
            工程名称=_norm(data.get("工程名称")),
            工程部位=_norm(data.get("工程部位")),
            样品编号=_norm(data.get("样品编号")),
            样品名称=_norm(data.get("样品名称")),
            规格型号=_norm(data.get("规格型号")),
            委托单位=_norm(data.get("委托单位")),
            生产单位=_norm(data.get("生产单位")),
            检测机构=_norm(data.get("检测机构")),
            检验依据=_norm(data.get("检验依据")),
            报告状态="AI识别",
            报告下载链接=None,
            本地PDF路径=file_path,
        )
    finally:
        db.close()


def persist_scetia_after_ocr(file_path: str, data: Dict[str, Any]) -> None:
    """AI OCR（scetia 字段模板）成功后写入 scetia 单表 + 总表"""
    report_no = _norm(data.get("报告编号"))
    if not report_no:
        return
    db = SessionLocal()
    try:
        create_scetia_single_page(
            db,
            委托编号=_norm(data.get("委托编号")),
            报告编号=report_no,
            工程名称=_norm(data.get("工程名称")),
            page_number=0,
            total_pages=0,
            source_file=file_path,
            security_code=None,
            confidence=None,
        )
        create_scetia_report(
            db,
            报告编号=report_no,
            委托编号=_norm(data.get("委托编号")),
            委托日期=_norm(data.get("委托日期")),
            报告日期=_norm(data.get("报告日期")),
            工程名称=_norm(data.get("工程名称")),
            工程地址=_norm(data.get("工程地址")),
            工程部位=None,
            样品名称=_norm(data.get("样品名称")),
            样品编号=None,
            规格=None,
            强度等级=None,
            委托单位=_norm(data.get("委托单位")),
            施工单位=_norm(data.get("施工单位")),
            生产单位=None,
            检测机构=None,
            检测结论=None,
            样品检测结论=None,
            委托性质=None,
            标段=None,
            取样人及证书号=None,
            见证人及证书号=None,
            防伪码=None,
            本地PDF路径=file_path,
        )
    finally:
        db.close()


async def run_ai_ocr_upload(file_path: str, source_type: str) -> Dict[str, Any]:
    """
    无二维码或在线查询失败时的 AI OCR。
    source_type: auto 时先尝试 limis 模板，再尝试 scetia 模板。
    """
    from services.ai_ocr import AIOCRService

    ai = AIOCRService()

    async def try_one(st: str) -> Dict[str, Any]:
        return await ai.recognize_image(file_path, st)

    if source_type == "limis":
        r = await try_one("limis")
        if r.get("success"):
            d = r.get("data") or {}
            rn = _norm(d.get("报告编号"))
            if rn:
                return {"success": True, "source": "limis", "report_no": rn, "data": d, "raw": r}
        return {
            "success": False,
            "error": r.get("error") or "未能提取报告编号",
            "data": r.get("data") or {},
            "raw": r,
        }

    if source_type == "scetia":
        r = await try_one("scetia")
        if r.get("success"):
            d = r.get("data") or {}
            rn = _norm(d.get("报告编号"))
            if rn:
                return {"success": True, "source": "scetia", "report_no": rn, "data": d, "raw": r}
        return {
            "success": False,
            "error": r.get("error") or "未能提取报告编号",
            "data": r.get("data") or {},
            "raw": r,
        }

    # auto：先试 limis，再试 scetia
    r1 = await try_one("limis")
    if r1.get("success"):
        d1 = r1.get("data") or {}
        rn1 = _norm(d1.get("报告编号"))
        if rn1:
            return {"success": True, "source": "limis", "report_no": rn1, "data": d1, "raw": r1}

    r2 = await try_one("scetia")
    if r2.get("success"):
        d2 = r2.get("data") or {}
        rn2 = _norm(d2.get("报告编号"))
        if rn2:
            return {"success": True, "source": "scetia", "report_no": rn2, "data": d2, "raw": r2}

    return {
        "success": False,
        "error": "AI 未能识别出有效报告编号",
        "data": (r2.get("data") or r1.get("data") or {}),
        "raw": r2,
    }


class UploadResult(BaseModel):
    file_id: str
    filename: str
    status: str
    message: str = None
    data: Dict[str, Any] = None


# 存储处理状态
processing_status: Dict[str, Dict[str, Any]] = {}


async def process_file_task(file_path: str, file_id: str, source_type: str = "auto"):
    """后台处理：先二维码+在线拉取，失败或无码则 AI OCR"""
    try:
        processing_status[file_id] = {
            "status": "processing",
            "message": "正在扫描二维码…",
            "data": None,
        }

        from services.scanner import QRCodeScannerService

        scanner = QRCodeScannerService()
        result = scanner.process_file(file_path)

        print(f"[UPLOAD] Scanner result: {result}")

        if result.get("success") and result.get("classified"):
            qr = result["classified"][0]
            print(f"[UPLOAD] Classified QR: {qr}")

            if qr.get("type") == "limis":
                from services.limis_crawler import LimisCrawlerService

                crawler = LimisCrawlerService()
                url = qr.get("url")
                print(f"[UPLOAD] Limis URL: {url}")
                crawl_result = await crawler.get_report_data(url)

                if crawl_result["success"]:
                    try:
                        persist_limis_after_crawl(file_path, crawl_result)
                    except Exception as db_err:
                        print(f"[UPLOAD] limis 落库失败: {db_err}")
                    processing_status[file_id] = {
                        "status": "completed",
                        "message": f"识别成功: {crawl_result['report_no']}",
                        "data": {
                            "report_no": crawl_result["report_no"],
                            "source": "limis",
                            "info": crawl_result["data"],
                            "method": "qrcode_crawl",
                        },
                    }
                    return

            elif qr.get("type") == "scetia":
                from services.scetia_query import ScetiaQueryService

                query = ScetiaQueryService()
                report_id = qr.get("report_id")
                security_code = qr.get("security_code")
                print(f"[UPLOAD] Scetia: report_id={report_id}, security_code={security_code}")

                query_result = await query.query_report(report_id, security_code)

                if query_result["query_success"]:
                    try:
                        persist_scetia_after_query(
                            file_path,
                            report_id,
                            security_code,
                            query_result,
                            qr.get("confidence"),
                        )
                    except Exception as db_err:
                        print(f"[UPLOAD] scetia 落库失败: {db_err}")
                    processing_status[file_id] = {
                        "status": "completed",
                        "message": f"识别成功: {report_id}",
                        "data": {
                            "report_no": report_id,
                            "source": "scetia",
                            "info": query_result["data"],
                            "method": "qrcode_query",
                        },
                    }
                    return

        # 无有效二维码、类型未知、或在线拉取失败 → AI OCR
        processing_status[file_id] = {
            "status": "processing",
            "message": "未识别到有效二维码或在线查询失败，正在使用 AI 识别…",
            "data": None,
        }

        ai_out = await run_ai_ocr_upload(file_path, source_type or "auto")

        if ai_out.get("success"):
            try:
                if ai_out.get("source") == "limis":
                    persist_limis_after_ocr(file_path, ai_out.get("data") or {})
                else:
                    persist_scetia_after_ocr(file_path, ai_out.get("data") or {})
            except Exception as db_err:
                print(f"[UPLOAD] AI 结果落库失败: {db_err}")

            processing_status[file_id] = {
                "status": "completed",
                "message": f"AI 识别成功: {ai_out.get('report_no')}",
                "data": {
                    "report_no": ai_out.get("report_no"),
                    "source": ai_out.get("source"),
                    "info": ai_out.get("data") or {},
                    "method": "ai_ocr",
                },
            }
            return

        processing_status[file_id] = {
            "status": "failed",
            "message": ai_out.get("error") or "AI 识别失败",
            "data": {
                "info": ai_out.get("data") or {},
                "method": "ai_ocr",
            },
        }

    except Exception as e:
        import traceback

        print(f"[UPLOAD] Error: {e}")
        traceback.print_exc()
        processing_status[file_id] = {
            "status": "failed",
            "message": str(e),
            "data": None,
        }


@router.post("/single", response_model=UploadResult)
async def upload_single(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_type: str = "auto"
):
    """单文件上传"""
    file_id = str(uuid.uuid4())
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1]
    save_path = os.path.join(upload_dir, f"{file_id}{file_ext}")
    
    try:
        content = await file.read()
        with open(save_path, 'wb') as f:
            f.write(content)

        # 立即登记状态，避免客户端首轮轮询拿到 not_found 而一直卡在「处理中」
        processing_status[file_id] = {
            "status": "processing",
            "message": "已接收，正在识别…",
            "data": None,
        }

        background_tasks.add_task(process_file_task, save_path, file_id, source_type)
        
        return UploadResult(
            file_id=file_id,
            filename=file.filename,
            status="pending",
            message="文件已上传，正在后台处理"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=List[UploadResult])
async def upload_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    source_type: str = "auto"
):
    """批量上传文件"""
    results = []
    for file in files:
        result = await upload_single(background_tasks, file, source_type)
        results.append(result)
    return results


@router.get("/status/{file_id}")
async def get_processing_status(file_id: str):
    """获取处理状态"""
    status = processing_status.get(file_id, {
        "status": "not_found",
        "message": "文件ID不存在",
        "data": None
    })
    return {
        "file_id": file_id,
        "status": status.get("status"),
        "message": status.get("message"),
        "data": status.get("data")
    }


@router.get("/list")
async def list_uploaded_files():
    """列出已上传的文件"""
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    files = []
    
    if os.path.exists(upload_dir):
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)
            if os.path.isfile(file_path):
                files.append({
                    "filename": filename,
                    "size": os.path.getsize(file_path),
                    "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })
    
    return {"files": files, "total": len(files)}