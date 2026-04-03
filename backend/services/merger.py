"""
PDF合并服务 - 将同报告编号的单页PDF合并为完整PDF
"""
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

try:
    import PyPDF2
    PYPDF2_SUPPORT = True
except ImportError:
    PYPDF2_SUPPORT = False
    print("警告: PyPDF2未安装，PDF合并功能受限")

from config import MERGED_PDF_DIR


class PDFMergerService:
    """PDF合并服务"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or MERGED_PDF_DIR
    
    def merge_pdfs(
        self,
        pdf_paths: List[str],
        output_name: str,
        report_no: str
    ) -> Optional[str]:
        """
        合并多个PDF
        
        Args:
            pdf_paths: PDF路径列表（按页码顺序）
            output_name: 输出文件名
            report_no: 报告编号
            
        Returns:
            合合后的PDF路径
        """
        if not PYPDF2_SUPPORT or not pdf_paths:
            return None
        
        try:
            # 创建合并器
            merger = PyPDF2.PdfMerger()
            
            # 添加所有PDF
            for pdf_path in pdf_paths:
                if os.path.exists(pdf_path):
                    merger.append(pdf_path)
            
            # 生成输出路径
            output_path = os.path.join(
                self.output_dir,
                f"{report_no}_{datetime.now().strftime('%Y%m%d')}.pdf"
            )
            
            # 写入合并后的PDF
            with open(output_path, 'wb') as f:
                merger.write(f)
            
            merger.close()
            
            return output_path
        
        except Exception as e:
            print(f"PDF合并失败: {e}")
            return None
    
    def merge_single_pages_to_report(
        self,
        single_pages: List[Dict],
        report_no: str
    ) -> Optional[str]:
        """
        将单页记录合并为完整报告
        
        Args:
            single_pages: 单页数据列表 [{pdf_path, page_number}]
            report_no: 报告编号
            
        Returns:
            合并后的PDF路径
        """
        # 按页码排序
        sorted_pages = sorted(single_pages, key=lambda x: x.get('page_number', 0))
        
        # 提取PDF路径
        pdf_paths = [p.get('pdf_path') for p in sorted_pages if p.get('pdf_path')]
        
        if not pdf_paths:
            return None
        
        # 合并
        return self.merge_pdfs(
            pdf_paths=pdf_paths,
            output_name=report_no,
            report_no=report_no
        )
    
    def rename_merged_pdf(
        self,
        pdf_path: str,
        report_no: str,
        project_name: str = None
    ) -> str:
        """
        重命名合并后的PDF
        
        Args:
            pdf_path: PDF路径
            report_no: 报告编号
            project_name: 工程名称（可选）
            
        Returns:
            新PDF路径
        """
        if not os.path.exists(pdf_path):
            return pdf_path
        
        # 生成新文件名
        if project_name:
            # 简化工程名称（去除特殊字符）
            safe_name = "".join(c for c in project_name if c.isalnum() or c in ' -_')[:50]
            new_name = f"{report_no}_{safe_name}.pdf"
        else:
            new_name = f"{report_no}.pdf"
        
        new_path = os.path.join(self.output_dir, new_name)
        
        # 重命名
        try:
            if pdf_path != new_path:
                os.rename(pdf_path, new_path)
            return new_path
        except Exception as e:
            print(f"PDF重命名失败: {e}")
            return pdf_path