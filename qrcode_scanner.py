"""
二维码扫描器 - 使用 QReader 支持图片和PDF文件
支持格式: jpg, jpeg, png, bmp, pdf
"""
import os
import cv2
import numpy as np
from qreader import QReader
from pathlib import Path
from typing import List, Tuple, Optional
import json
from datetime import datetime

# PDF处理相关
try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("警告: pdf2image 未安装,PDF支持已禁用。安装: pip install pdf2image")


class QRCodeScanner:
    """二维码扫描器"""
    
    def __init__(self, model_size: str = 's', min_confidence: float = 0.5):
        """
        初始化扫描器
        
        Args:
            model_size: QReader模型大小 ('n', 's', 'm', 'l')
            min_confidence: 最小置信度阈值
        """
        print("正在初始化 QReader 模型...")
        self.qreader = QReader(model_size=model_size, min_confidence=min_confidence)
        print("模型加载完成!")
        
        # 支持的图片格式
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        self.pdf_extension = '.pdf'
    
    def scan_image(self, image_path: str) -> Tuple[List[str], List[dict]]:
        """
        扫描图片中的二维码
        
        Args:
            image_path: 图片路径
            
        Returns:
            (解码结果列表, 检测信息列表)
        """
        # 读取图片
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")
        
        # 转换为RGB格式(QReader需要)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 检测和解码
        decoded_texts, detection_infos = self.qreader.detect_and_decode(
            image=img_rgb, 
            return_detections=True
        )
        
        return decoded_texts, detection_infos
    
    def scan_pdf(self, pdf_path: str) -> List[Tuple[int, List[str], List[dict]]]:
        """
        扫描PDF文件中的二维码
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            [(页码, 解码结果列表, 检测信息列表), ...]
        """
        if not PDF_SUPPORT:
            raise ImportError("pdf2image 未安装,无法处理PDF文件")
        
        results = []
        
        # 将PDF转换为图片
        try:
            images = convert_from_path(pdf_path, dpi=300)
        except Exception as e:
            raise ValueError(f"无法转换PDF: {pdf_path}, 错误: {e}")
        
        # 扫描每一页
        for page_num, img_pil in enumerate(images, start=1):
            # PIL Image 转 numpy array (RGB格式)
            img_rgb = np.array(img_pil)
            
            # 检测和解码
            decoded_texts, detection_infos = self.qreader.detect_and_decode(
                image=img_rgb,
                return_detections=True
            )
            
            results.append((page_num, decoded_texts, detection_infos))
        
        return results
    
    def scan_file(self, file_path: str) -> dict:
        """
        扫描单个文件(自动判断类型)
        
        Args:
            file_path: 文件路径
            
        Returns:
            扫描结果字典
        """
        file_path = Path(file_path)
        result = {
            'file': str(file_path),
            'type': 'unknown',
            'success': False,
            'error': None,
            'qrcodes': []
        }
        
        # 检查文件是否存在
        if not file_path.exists():
            result['error'] = '文件不存在'
            return result
        
        # 获取文件扩展名
        ext = file_path.suffix.lower()
        
        try:
            if ext == self.pdf_extension:
                # PDF文件
                result['type'] = 'pdf'
                pages = self.scan_pdf(str(file_path))
                
                for page_num, decoded_texts, detection_infos in pages:
                    for text, info in zip(decoded_texts, detection_infos):
                        if text:  # 只保存成功解码的
                            result['qrcodes'].append({
                                'page': page_num,
                                'content': text,
                                'confidence': float(info.get('confidence', 0)),
                                'bbox': info.get('bbox_xyxy', []).tolist() if hasattr(info.get('bbox_xyxy', []), 'tolist') else info.get('bbox_xyxy', [])
                            })
                
                result['success'] = True
                
            elif ext in self.image_extensions:
                # 图片文件
                result['type'] = 'image'
                decoded_texts, detection_infos = self.scan_image(str(file_path))
                
                for text, info in zip(decoded_texts, detection_infos):
                    if text:  # 只保存成功解码的
                        result['qrcodes'].append({
                            'content': text,
                            'confidence': float(info.get('confidence', 0)),
                            'bbox': info.get('bbox_xyxy', []).tolist() if hasattr(info.get('bbox_xyxy', []), 'tolist') else info.get('bbox_xyxy', [])
                        })
                
                result['success'] = True
            else:
                result['error'] = f'不支持的文件格式: {ext}'
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def scan_directory(self, directory: str, recursive: bool = False) -> List[dict]:
        """
        扫描目录中的所有支持文件
        
        Args:
            directory: 目录路径
            recursive: 是否递归扫描子目录
            
        Returns:
            扫描结果列表
        """
        directory = Path(directory)
        results = []
        
        # 获取所有文件
        if recursive:
            files = directory.rglob('*')
        else:
            files = directory.glob('*')
        
        # 过滤支持的文件类型
        supported_extensions = self.image_extensions | {self.pdf_extension}
        supported_files = [
            f for f in files 
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]
        
        print(f"找到 {len(supported_files)} 个支持文件")
        
        # 扫描每个文件
        for i, file_path in enumerate(supported_files, 1):
            print(f"[{i}/{len(supported_files)}] 扫描: {file_path.name}...", end=' ')
            result = self.scan_file(str(file_path))
            results.append(result)
            
            # 输出简要结果
            if result['success']:
                qr_count = len(result['qrcodes'])
                print(f"✓ 找到 {qr_count} 个二维码")
            else:
                print(f"✗ {result['error']}")
        
        return results


def print_results(results: List[dict]):
    """打印扫描结果"""
    print("\n" + "=" * 70)
    print("扫描结果汇总")
    print("=" * 70)
    
    total_files = len(results)
    success_files = sum(1 for r in results if r['success'])
    total_qrcodes = sum(len(r['qrcodes']) for r in results)
    
    print(f"总文件数: {total_files}")
    print(f"成功扫描: {success_files}")
    print(f"失败: {total_files - success_files}")
    print(f"二维码总数: {total_qrcodes}")
    print("=" * 70)
    
    # 详细结果
    for result in results:
        if result['qrcodes']:
            print(f"\n文件: {Path(result['file']).name}")
            print(f"类型: {result['type']}")
            print("-" * 70)
            
            for i, qr in enumerate(result['qrcodes'], 1):
                if 'page' in qr:
                    print(f"  页码 {qr['page']}, 二维码 {i}:")
                else:
                    print(f"  二维码 {i}:")
                print(f"    内容: {qr['content']}")
                print(f"    置信度: {qr['confidence']:.2%}")


def save_results_to_json(results: List[dict], output_file: str):
    """保存结果到JSON文件"""
    output_data = {
        'scan_time': datetime.now().isoformat(),
        'summary': {
            'total_files': len(results),
            'success_files': sum(1 for r in results if r['success']),
            'total_qrcodes': sum(len(r['qrcodes']) for r in results)
        },
        'results': results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {output_file}")


def main():
    """主函数"""
    # 初始化扫描器
    scanner = QRCodeScanner(model_size='s', min_confidence=0.5)
    
    # 扫描两个目录
    directories = [
        r"d:\code\trytry\files_limis",
        r"d:\code\trytry\files_scetia"
    ]
    
    all_results = []
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"\n{'=' * 70}")
            print(f"扫描目录: {directory}")
            print('=' * 70)
            
            results = scanner.scan_directory(directory, recursive=False)
            all_results.extend(results)
            
            # 打印该目录的结果
            print_results(results)
        else:
            print(f"警告: 目录不存在 - {directory}")
    
    # 保存完整结果到JSON
    output_file = r"d:\code\trytry\results\qrcode_results.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    save_results_to_json(all_results, output_file)
    
    # 打印汇总
    print("\n" + "=" * 70)
    print("所有目录汇总")
    print("=" * 70)
    print(f"总文件数: {len(all_results)}")
    print(f"成功扫描: {sum(1 for r in all_results if r['success'])}")
    print(f"二维码总数: {sum(len(r['qrcodes']) for r in all_results)}")
    print("=" * 70)


if __name__ == "__main__":
    main()