"""
PDF处理服务 - PDF拆分和转换
"""
import os
from pathlib import Path
from typing import List, Tuple
import tempfile

try:
    from pdf2image import convert_from_path
    from PIL import Image
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("警告: pdf2image未安装，PDF处理功能受限")

try:
    import PyPDF2
    PYPDF2_SUPPORT = True
except ImportError:
    PYPDF2_SUPPORT = False
    print("警告: PyPDF2未安装，PDF拆分功能受限")

from config import PDF_DPI, UPLOAD_DIR


class PDFProcessorService:
    """PDF处理服务"""
    
    def __init__(self, dpi: int = PDF_DPI):
        self.dpi = dpi
    
    def get_pdf_page_count(self, pdf_path: str) -> int:
        """获取PDF页数"""
        if not PYPDF2_SUPPORT:
            return 0
        
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return len(reader.pages)
        except Exception as e:
            print(f"获取PDF页数失败: {e}")
            return 0
    
    def split_pdf_to_pages(self, pdf_path: str, output_dir: str = None) -> List[str]:
        """
        将PDF拆分为单页PDF
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录
            
        Returns:
            单页PDF路径列表
        """
        if not PYPDF2_SUPPORT:
            return []
        
        if output_dir is None:
            output_dir = UPLOAD_DIR
        
        output_paths = []
        
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)
                
                for i in range(total_pages):
                    # 创建单页PDF
                    writer = PyPDF2.PdfWriter()
                    writer.add_page(reader.pages[i])
                    
                    # 保存单页PDF
                    pdf_name = Path(pdf_path).stem
                    output_path = os.path.join(output_dir, f"{pdf_name}_page_{i+1}.pdf")
                    
                    with open(output_path, 'wb') as out_f:
                        writer.write(out_f)
                    
                    output_paths.append(output_path)
        
        except Exception as e:
            print(f"PDF拆分失败: {e}")
        
        return output_paths
    
    def pdf_to_images(self, pdf_path: str, output_dir: str = None) -> List[str]:
        """
        将PDF转换为图片
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录
            
        Returns:
            图片路径列表
        """
        if not PDF_SUPPORT:
            return []
        
        if output_dir is None:
            output_dir = UPLOAD_DIR
        
        output_paths = []
        
        try:
            images = convert_from_path(pdf_path, dpi=self.dpi)
            
            pdf_name = Path(pdf_path).stem
            
            for i, image in enumerate(images, 1):
                output_path = os.path.join(output_dir, f"{pdf_name}_page_{i}.jpg")
                image.save(output_path, 'JPEG', quality=95)
                output_paths.append(output_path)
        
        except Exception as e:
            print(f"PDF转换图片失败: {e}")
        
        return output_paths
    
    def process_uploaded_pdf(self, pdf_path: str) -> Tuple[int, List[str]]:
        """
        处理上传的PDF
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            (页数, 图片路径列表)
        """
        page_count = self.get_pdf_page_count(pdf_path)
        image_paths = self.pdf_to_images(pdf_path)
        
        return page_count, image_paths
    
    def get_file_type(self, file_path: str) -> str:
        """
        判断文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            类型: 'image', 'single_pdf', 'multi_pdf', 'unknown'
        """
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']:
            return 'image'
        
        if ext == '.pdf':
            page_count = self.get_pdf_page_count(file_path)
            if page_count == 1:
                return 'single_pdf'
            elif page_count > 1:
                return 'multi_pdf'
        
        return 'unknown'