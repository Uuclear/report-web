"""
服务模块初始化
"""
import sys
from pathlib import Path

# 确保可以找到模块
sys.path.insert(0, str(Path(__file__).parent))

from scanner import QRCodeScannerService
from limis_crawler import LimisCrawlerService
from scetia_query import ScetiaQueryService
from ai_ocr import AIOCRService
from pdf_processor import PDFProcessorService
from merger import PDFMergerService

__all__ = [
    "QRCodeScannerService",
    "LimisCrawlerService",
    "ScetiaQueryService",
    "AIOCRService",
    "PDFProcessorService",
    "PDFMergerService",
]