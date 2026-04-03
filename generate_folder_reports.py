"""
为每个文件夹生成二维码识别报告
格式: 序号, 文件名, 二维码内容
"""
import json
import os
from pathlib import Path
from datetime import datetime


def load_results(json_file: str):
    """加载JSON结果文件"""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_folder_report(results: list, directory: str, output_file: str):
    """
    为指定文件夹生成Markdown报告
    
    Args:
        results: 扫描结果列表
        directory: 目录名称 (如 files_limis, files_scetia)
        output_file: 输出文件路径
    """
    # 过滤该目录的文件
    folder_results = [r for r in results if directory in r['file']]
    
    # 统计信息
    total_files = len(folder_results)
    files_with_qr = sum(1 for r in folder_results if len(r['qrcodes']) > 0)
    total_qrcodes = sum(len(r['qrcodes']) for r in folder_results)
    
    # 生成Markdown内容
    md_content = f"""# 二维码识别报告 - {directory}

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 统计信息

- **扫描文件总数**: {total_files}
- **包含二维码的文件数**: {files_with_qr}
- **二维码总数**: {total_qrcodes}

---

## 识别结果详情

"""
    
    # 添加二维码识别详情
    md_content += """| 序号 | 文件名 | 位置 | 二维码内容 |
|------|--------|------|------------------|
"""
    
    seq = 0
    for result in sorted(folder_results, key=lambda x: Path(x['file']).name):
        filename = Path(result['file']).name
        
        if result['qrcodes']:
            for qr in result['qrcodes']:
                seq += 1
                content = qr['content'].strip()
                
                # 处理页码信息
                if 'page' in qr:
                    location = f"页码 {qr['page']}"
                else:
                    location = "图片"
                
                md_content += f"| {seq} | {filename} | {location} | `{content}` |\n"
    
    # 如果该目录没有识别到二维码
    if total_qrcodes == 0:
        md_content += "| - | - | - | **未识别到二维码** |\n"
    
    # 添加文件列表(包括未识别二维码的文件)
    md_content += """---

## 所有扫描文件列表

"""
    
    for i, result in enumerate(sorted(folder_results, key=lambda x: Path(x['file']).name), 1):
        filename = Path(result['file']).name
        qr_count = len(result['qrcodes'])
        status = "✓ 成功" if result['success'] else "✗ 失败"
        qr_status = f"{qr_count} 个二维码" if qr_count > 0 else "无二维码"
        
        md_content += f"""| 序号 | 文件名 | 文件类型 | 扫描状态 | 二维码数量 |
|------|--------|----------|----------|------------|
| {i} | {filename} | {result['type']} | {status} | {qr_status} |

"""
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"报告已生成: {output_file}")
    print(f"  - 扫描文件数: {total_files}")
    print(f"  - 包含二维码的文件数: {files_with_qr}")
    print(f"  - 二维码总数: {total_qrcodes}")


def main():
    """主函数"""
    # 加载QReader结果(使用QReader因为它识别率更高)
    qreader_file = r"d:\code\trytry\results\qrcode_results.json"
    
    if not os.path.exists(qreader_file):
        print(f"错误: 结果文件不存在 - {qreader_file}")
        return
    
    # 加载结果
    data = load_results(qreader_file)
    results = data['results']
    
    # 为两个文件夹生成报告
    folders = [
        ('files_limis', r'd:\code\trytry\files_limis\二维码识别报告.md'),
        ('files_scetia', r'd:\code\trytry\files_scetia\二维码识别报告.md')
    ]
    
    print("=" * 60)
    print("开始生成文件夹报告...")
    print("=" * 60)
    
    for folder_name, output_path in folders:
        print(f"\n处理文件夹: {folder_name}")
        generate_folder_report(results, folder_name, output_path)
    
    print("\n" + "=" * 60)
    print("所有报告已生成完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()