"""
扫描接口 - 摄像头扫描和图片处理
"""
import os
import uuid
import traceback
from fastapi import APIRouter, UploadFile, File, Query
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()


class ScanResult(BaseModel):
    """扫描结果模型"""

    success: bool
    report_no: Optional[str] = None
    source: Optional[str] = None
    data: dict = {}
    error: Optional[str] = None
    # qrcode_crawl | qrcode_query | ai_ocr
    method: Optional[str] = None


@router.post("/image", response_model=ScanResult)
async def scan_image(
    file: UploadFile = File(...),
    source_type: str = Query("auto", description="auto / limis / scetia，无二维码时 AI 模板"),
):
    """扫描上传的图片：先二维码+在线拉取，失败或无码则 AI OCR"""
    temp_path = None
    try:
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        ext = os.path.splitext(file.filename or "scan")[1] or ".jpg"
        temp_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}{ext}")

        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        print(f"[SCAN] 文件已保存: {temp_path}")

        from services.scanner import QRCodeScannerService

        scanner = QRCodeScannerService()
        print("[SCAN] 开始扫描二维码…")
        result = scanner.process_file(temp_path)
        print(
            f"[SCAN] 扫描结果: success={result.get('success')}, "
            f"classified={len(result.get('classified', []))}"
        )

        if result.get("success") and result.get("classified"):
            qr = result["classified"][0]
            print(f"[SCAN] 二维码类型: {qr.get('type')}")

            if qr.get("type") == "limis":
                from services.limis_crawler import LimisCrawlerService

                crawler = LimisCrawlerService()
                print(f"[SCAN] 爬取 limis: {qr.get('url')}")
                crawl_result = await crawler.get_report_data(qr["url"])

                if crawl_result["success"]:
                    return ScanResult(
                        success=True,
                        report_no=crawl_result["report_no"],
                        source="limis",
                        data=crawl_result["data"],
                        method="qrcode_crawl",
                    )

            elif qr.get("type") == "scetia":
                from services.scetia_query import ScetiaQueryService

                query = ScetiaQueryService()
                report_id = qr.get("report_id")
                security_code = qr.get("security_code")
                print(f"[SCAN] 查询 scetia: {report_id}")

                query_result = await query.query_report(report_id, security_code)

                if query_result.get("query_success"):
                    return ScanResult(
                        success=True,
                        report_no=report_id,
                        source="scetia",
                        data=query_result.get("data") or {},
                        method="qrcode_query",
                    )

        # 无码、类型未知、或在线拉取失败 → AI OCR（与上传接口共用逻辑）
        print("[SCAN] 进入 AI OCR 回退…")
        from routers.upload import run_ai_ocr_upload

        ai_out = await run_ai_ocr_upload(temp_path, source_type or "auto")

        if ai_out.get("success"):
            return ScanResult(
                success=True,
                report_no=ai_out.get("report_no"),
                source=ai_out.get("source"),
                data=ai_out.get("data") or {},
                method="ai_ocr",
            )

        return ScanResult(
            success=False,
            error=ai_out.get("error") or "未能识别报告信息",
            data=ai_out.get("data") or {},
            method="ai_ocr",
        )

    except Exception as e:
        print(f"[SCAN] 错误: {e}")
        traceback.print_exc()
        return ScanResult(success=False, error=f"处理失败: {str(e)}")

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@router.post("/batch", response_model=List[ScanResult])
async def scan_batch(
    files: List[UploadFile] = File(...),
    source_type: str = Query("auto"),
):
    """批量扫描多个文件"""
    results = []
    for f in files:
        result = await scan_image(f, source_type)
        results.append(result)
    return results


@router.get("/test")
async def test_scan():
    """测试接口"""
    return {"message": "扫描服务正常运行"}
