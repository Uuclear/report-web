"""
数据导入脚本 - 将现有JSON数据导入数据库
"""
import os
import sys
import json
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import init_db, SessionLocal
from database.crud import (
    create_limis_report,
    create_scetia_report,
    create_scetia_single_page
)


def import_limis_data(json_file: str, pdf_dir: str = None):
    """
    导入limis数据
    
    Args:
        json_file: crawler_results.json 文件路径
        pdf_dir: 本地PDF文件目录
    """
    print(f"\n导入 limis 数据: {json_file}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    db = SessionLocal()
    
    try:
        success_count = 0
        skip_count = 0
        
        for result in data.get('results', []):
            if not result.get('success'):
                continue
            
            report_data = result.get('data', {})
            report_no = report_data.get('报告编号') or result.get('report_no')
            
            if not report_no:
                print(f"  跳过: 无报告编号 - {result.get('source_file')}")
                skip_count += 1
                continue
            
            # 查找本地PDF文件
            local_pdf_path = None
            if pdf_dir:
                # 尝试匹配PDF文件名
                for ext in ['.pdf', '.jpg', '.jpeg']:
                    potential_path = os.path.join(pdf_dir, f"{report_no}{ext}")
                    if os.path.exists(potential_path):
                        local_pdf_path = potential_path
                        break
            
            # 创建记录
            create_limis_report(
                db=db,
                报告编号=report_no,
                委托编号=report_data.get('委托编号'),
                委托日期=report_data.get('委托日期/抽样日期'),
                报告日期=report_data.get('签发日期'),
                工程名称=report_data.get('工程名称'),
                工程部位=report_data.get('工程部位'),
                样品编号=report_data.get('样品编号'),
                样品名称=report_data.get('样品名称'),
                规格型号=report_data.get('规格型号'),
                委托单位=report_data.get('委托单位'),
                生产单位=report_data.get('生产单位'),
                检测机构=report_data.get('检测机构'),
                检验依据=report_data.get('检验依据'),
                报告状态=report_data.get('status'),
                报告下载链接=report_data.get('报告下载链接'),
                本地PDF路径=local_pdf_path
            )
            
            print(f"  导入: {report_no} - {report_data.get('工程名称', '')[:30]}...")
            success_count += 1
        
        print(f"\nlimis 导入完成: 成功 {success_count}, 跳过 {skip_count}")
    
    except Exception as e:
        print(f"导入失败: {e}")
        db.rollback()
    finally:
        db.close()


def import_scetia_data(json_file: str, pdf_dir: str = None):
    """
    导入scetia数据
    
    Args:
        json_file: scetia_query_results.json 文件路径
        pdf_dir: 本地PDF文件目录
    """
    print(f"\n导入 scetia 数据: {json_file}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    db = SessionLocal()
    
    try:
        success_count = 0
        skip_count = 0
        
        for result in data.get('results', []):
            if not result.get('query_success'):
                continue
            
            report_data = result.get('data', {})
            report_no = report_data.get('报告编号') or result.get('report_id')
            
            if not report_no:
                print(f"  跳过: 无报告编号 - {result.get('source_file')}")
                skip_count += 1
                continue
            
            # 查找本地PDF文件
            local_pdf_path = None
            if pdf_dir:
                source_file = result.get('source_file')
                if source_file:
                    potential_path = os.path.join(pdf_dir, source_file)
                    if os.path.exists(potential_path):
                        local_pdf_path = potential_path
            
            # 创建记录
            create_scetia_report(
                db=db,
                报告编号=report_no,
                委托编号=report_data.get('委托编号'),
                委托日期=report_data.get('委托日期'),
                报告日期=report_data.get('报告日期'),
                工程名称=report_data.get('工程名称'),
                工程地址=report_data.get('工程地址'),
                工程部位=report_data.get('工程部位'),
                样品名称=report_data.get('样品名称'),
                样品编号=report_data.get('样品编号'),
                规格=report_data.get('规格'),
                强度等级=report_data.get('强度等级'),
                委托单位=report_data.get('委托单位'),
                施工单位=report_data.get('施工单位'),
                生产单位=report_data.get('生产单位'),
                检测机构=report_data.get('检测机构'),
                检测结论=report_data.get('检测结论'),
                样品检测结论=report_data.get('样品检测结论'),
                委托性质=report_data.get('委托性质'),
                标段=report_data.get('标段'),
                取样人及证书号=report_data.get('取样人及证书号'),
                见证人及证书号=report_data.get('见证人及证书号'),
                防伪码=result.get('security_code'),
                本地PDF路径=local_pdf_path
            )
            
            # 创建单页记录
            create_scetia_single_page(
                db=db,
                委托编号=report_data.get('委托编号'),
                报告编号=report_no,
                工程名称=report_data.get('工程名称'),
                page_number=result.get('page', 1) or 1,
                total_pages=1,
                source_file=result.get('source_file'),
                pdf_path=local_pdf_path,
                security_code=result.get('security_code'),
                confidence=result.get('confidence')
            )
            
            print(f"  导入: {report_no} - {report_data.get('工程名称', '')[:30]}...")
            success_count += 1
        
        print(f"\nscetia 导入完成: 成功 {success_count}, 跳过 {skip_count}")
    
    except Exception as e:
        print(f"导入失败: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """主函数"""
    print("=" * 60)
    print("数据导入脚本")
    print("=" * 60)
    
    # 初始化数据库
    print("\n初始化数据库...")
    init_db()
    
    base_dir = Path(__file__).parent.parent
    
    # 导入limis数据
    limis_json = base_dir / "results" / "crawler_results.json"
    limis_pdf_dir = base_dir / "files_limis"
    
    if limis_json.exists():
        import_limis_data(str(limis_json), str(limis_pdf_dir) if limis_pdf_dir.exists() else None)
    else:
        print(f"文件不存在: {limis_json}")
    
    # 导入scetia数据
    scetia_json = base_dir / "results" / "scetia_query_results.json"
    scetia_pdf_dir = base_dir / "files_scetia"
    
    if scetia_json.exists():
        import_scetia_data(str(scetia_json), str(scetia_pdf_dir) if scetia_pdf_dir.exists() else None)
    else:
        print(f"文件不存在: {scetia_json}")
    
    print("\n" + "=" * 60)
    print("数据导入完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()