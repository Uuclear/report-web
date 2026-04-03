"""
二维码扫描服务
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Optional
import cv2
import numpy as np

try:
    from qreader import QReader
    QREADER_AVAILABLE = True
except ImportError:
    QREADER_AVAILABLE = False
    print("警告: qreader未安装，使用OpenCV备用方案")

try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("警告: pdf2image未安装，PDF文件将跳过")

from config import PDF_DPI


class QRCodeScannerService:
    """二维码扫描服务"""
    
    def __init__(self):
        if QREADER_AVAILABLE:
            self.qreader = QReader()
        else:
            self.qreader = None
    
    def scan_image(self, image_path: str) -> List[Dict]:
        """扫描图片中的二维码"""
        image = cv2.imread(image_path)
        if image is None:
            print(f"[Scanner] 无法读取图片: {image_path}")
            return []
        
        results = []
        
        if self.qreader:
            try:
                # QReader detect_and_decode 返回字符串列表
                decoded_texts = self.qreader.detect_and_decode(image)
                print(f"[Scanner] QReader返回: {decoded_texts}, 类型: {type(decoded_texts)}")
                
                if decoded_texts:
                    for text in decoded_texts:
                        if isinstance(text, str) and text:
                            print(f"[Scanner] 识别到二维码: {text}")
                            results.append({
                                "content": text,
                                "confidence": 0.9,
                                "bbox": None
                            })
            except Exception as e:
                print(f"[Scanner] QReader错误: {e}")
                import traceback
                traceback.print_exc()
        else:
            # OpenCV备用方案
            detector = cv2.QRCodeDetector()
            decoded_text, points = detector.detectAndDecode(image)
            
            if decoded_text:
                results.append({
                    "content": decoded_text,
                    "confidence": 0.8,
                    "bbox": points
                })
        
        print(f"[Scanner] 最终结果数量: {len(results)}")
        return results
    
    def scan_pdf(self, pdf_path: str, max_pages: int = 10) -> List[Dict]:
        """扫描PDF中的二维码"""
        if not PDF_SUPPORT:
            return []
        
        results = []
        
        try:
            images = convert_from_path(pdf_path, dpi=PDF_DPI, first_page=1, last_page=max_pages)
            
            for i, image in enumerate(images, 1):
                cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                temp_path = f"temp_page_{i}.jpg"
                cv2.imwrite(temp_path, cv_image)
                
                qrcodes = self.scan_image(temp_path)
                os.remove(temp_path)
                
                if qrcodes:
                    results.append({
                        "page": i,
                        "qrcodes": qrcodes
                    })
        
        except Exception as e:
            print(f"PDF扫描失败: {e}")
        
        return results
    
    def classify_qrcode_type(self, content: str) -> Dict:
        """分类二维码类型"""
        content = content.strip()
        
        # limis类型：URL格式
        if content.startswith('http'):
            if 'rNo=' in content:
                import re
                match = re.search(r'rNo=([^&]+)', content)
                if match:
                    return {
                        "type": "limis",
                        "url": content,
                        "report_id": match.group(1),
                        "security_code": None
                    }
            return {
                "type": "limis",
                "url": content,
                "report_id": None,
                "security_code": None
            }
        
        # scetia类型：格式为 "报告编号|防伪码"
        if '|' in content:
            parts = content.split('|')
            if len(parts) >= 2:
                report_id = parts[0].strip()
                security_code = parts[1].strip()
                if len(security_code) == 12:
                    return {
                        "type": "scetia",
                        "url": None,
                        "report_id": report_id,
                        "security_code": security_code
                    }
        
        return {
            "type": "unknown",
            "url": None,
            "report_id": None,
            "security_code": None
        }
    
    def process_file(self, file_path: str) -> Dict:
        """处理单个文件"""
        ext = Path(file_path).suffix.lower()
        
        result = {
            "file": file_path,
            "success": False,
            "qrcodes": [],
            "classified": []
        }
        
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            qrcodes = self.scan_image(file_path)
            result["qrcodes"] = qrcodes
            result["success"] = len(qrcodes) > 0
            
        elif ext == '.pdf':
            qrcodes = self.scan_pdf(file_path)
            result["qrcodes"] = qrcodes
            result["success"] = len(qrcodes) > 0
        
        # 分类二维码
        for qr in result["qrcodes"]:
            if isinstance(qr, dict) and 'content' in qr:
                classified = self.classify_qrcode_type(qr['content'])
                classified['confidence'] = qr.get('confidence', 0)
                classified['page'] = qr.get('page')
                result["classified"].append(classified)
        
        return result