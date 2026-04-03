"""
生成Excel格式的对比表格
"""
import json
import pandas as pd
from pathlib import Path
import os


def load_results(json_file: str):
    """加载JSON结果文件"""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_comparison_excel(qreader_file: str, wechat_file: str, output_file: str):
    """创建Excel对比表格"""
    
    # 加载结果
    qreader_data = load_results(qreader_file)
    wechat_data = load_results(wechat_file)
    
    # 创建Excel写入器
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        
        # Sheet 1: 总体对比
        summary_df = pd.DataFrame({
            '指标': ['扫描文件总数', '成功扫描文件数', '失败文件数', '扫描成功率', '识别二维码总数'],
            'QReader': [
                qreader_data['summary']['total_files'],
                qreader_data['summary']['success_files'],
                qreader_data['summary']['total_files'] - qreader_data['summary']['success_files'],
                f"{qreader_data['summary']['success_files'] / qreader_data['summary']['total_files'] * 100:.1f}%",
                qreader_data['summary']['total_qrcodes']
            ],
            'WeChat QRCode': [
                wechat_data['summary']['total_files'],
                wechat_data['summary']['success_files'],
                wechat_data['summary']['total_files'] - wechat_data['summary']['success_files'],
                f"{wechat_data['summary']['success_files'] / wechat_data['summary']['total_files'] * 100:.1f}%",
                wechat_data['summary']['total_qrcodes']
            ],
            '差异': [
                0,
                0,
                0,
                '0%',
                qreader_data['summary']['total_qrcodes'] - wechat_data['summary']['total_qrcodes']
            ],
            'QReader优势': [
                '-',
                '-',
                '-',
                '-',
                f"+{(qreader_data['summary']['total_qrcodes'] - wechat_data['summary']['total_qrcodes']) / wechat_data['summary']['total_qrcodes'] * 100:.1f}%"
            ]
        })
        summary_df.to_excel(writer, sheet_name='总体对比', index=False)
        
        # Sheet 2: 按文件类型对比
        qreader_results = qreader_data['results']
        wechat_results = wechat_data['results']
        
        type_data = []
        for file_type in ['image', 'pdf']:
            qreader_type_files = [r for r in qreader_results if r['type'] == file_type]
            wechat_type_files = [r for r in wechat_results if r['type'] == file_type]
            
            qreader_qr_count = sum(len(r['qrcodes']) for r in qreader_type_files)
            wechat_qr_count = sum(len(r['qrcodes']) for r in wechat_type_files)
            
            type_data.append({
                '文件类型': file_type.upper(),
                '文件数量': len(qreader_type_files),
                'QReader识别数': qreader_qr_count,
                'WeChat识别数': wechat_qr_count,
                '差异': qreader_qr_count - wechat_qr_count,
                'QReader胜率': f"{qreader_qr_count / max(qreader_qr_count, wechat_qr_count) * 100:.1f}%" if max(qreader_qr_count, wechat_qr_count) > 0 else 'N/A'
            })
        
        type_df = pd.DataFrame(type_data)
        type_df.to_excel(writer, sheet_name='文件类型对比', index=False)
        
        # Sheet 3: 按目录对比
        dir_data = []
        for directory in ['files_limis', 'files_scetia']:
            qreader_dir_files = [r for r in qreader_results if directory in r['file']]
            wechat_dir_files = [r for r in wechat_results if directory in r['file']]
            
            qreader_qr_count = sum(len(r['qrcodes']) for r in qreader_dir_files)
            wechat_qr_count = sum(len(r['qrcodes']) for r in wechat_dir_files)
            
            dir_data.append({
                '目录': directory,
                '文件数量': len(qreader_dir_files),
                'QReader识别数': qreader_qr_count,
                'WeChat识别数': wechat_qr_count,
                '差异': qreader_qr_count - wechat_qr_count,
                'QReader胜率': f"{qreader_qr_count / max(qreader_qr_count, wechat_qr_count) * 100:.1f}%" if max(qreader_qr_count, wechat_qr_count) > 0 else 'N/A'
            })
        
        dir_df = pd.DataFrame(dir_data)
        dir_df.to_excel(writer, sheet_name='目录对比', index=False)
        
        # Sheet 4: 详细文件对比
        qreader_map = {Path(r['file']).name: r for r in qreader_results}
        wechat_map = {Path(r['file']).name: r for r in wechat_results}
        
        detailed_data = []
        for filename in sorted(qreader_map.keys()):
            qreader_file = qreader_map[filename]
            wechat_file = wechat_map.get(filename, {'qrcodes': [], 'success': False})
            
            qreader_qr_count = len(qreader_file['qrcodes'])
            wechat_qr_count = len(wechat_file['qrcodes'])
            
            detailed_data.append({
                '文件名': filename,
                '文件类型': qreader_file['type'],
                '扫描状态': '成功' if qreader_file['success'] else '失败',
                'QReader识别数': qreader_qr_count,
                'WeChat识别数': wechat_qr_count,
                '差异': qreader_qr_count - wechat_qr_count,
                '胜者': 'QReader' if qreader_qr_count > wechat_qr_count else ('WeChat' if qreader_qr_count < wechat_qr_count else '平局')
            })
        
        detailed_df = pd.DataFrame(detailed_data)
        detailed_df.to_excel(writer, sheet_name='详细文件对比', index=False)
        
        # Sheet 5: 仅QReader识别的文件
        qreader_only_data = []
        for filename in sorted(qreader_map.keys()):
            qreader_file = qreader_map[filename]
            wechat_file = wechat_map.get(filename, {'qrcodes': []})
            
            qreader_qr_count = len(qreader_file['qrcodes'])
            wechat_qr_count = len(wechat_file['qrcodes'])
            
            if qreader_qr_count > wechat_qr_count:
                qreader_only_data.append({
                    '文件名': filename,
                    '文件类型': qreader_file['type'],
                    'QReader识别数': qreader_qr_count,
                    'WeChat识别数': wechat_qr_count,
                    'QReader独识别数': qreader_qr_count - wechat_qr_count
                })
        
        qreader_only_df = pd.DataFrame(qreader_only_data)
        qreader_only_df.to_excel(writer, sheet_name='QReader优势文件', index=False)
        
        # Sheet 6: 内容对比
        content_data = []
        content_match_count = 0
        unique_qreader_count = 0
        unique_wechat_count = 0
        
        for filename in sorted(qreader_map.keys()):
            qreader_file = qreader_map[filename]
            wechat_file = wechat_map.get(filename, {'qrcodes': []})
            
            qreader_contents = [qr['content'].strip() for qr in qreader_file['qrcodes']]
            wechat_contents = [qr['content'].strip() for qr in wechat_file['qrcodes']]
            
            # 对比每个二维码内容
            for i, qreader_qr in enumerate(qreader_file['qrcodes']):
                content = qreader_qr['content'].strip()
                in_wechat = content in wechat_contents
                
                if 'page' in qreader_qr:
                    page_info = f"页码 {qreader_qr['page']}"
                else:
                    page_info = '图片'
                
                confidence = qreader_qr.get('confidence', 'N/A')
                if isinstance(confidence, float):
                    confidence = f"{confidence:.1%}"
                
                content_data.append({
                    '文件名': filename,
                    '位置': page_info,
                    '二维码序号': i + 1,
                    '二维码内容': content,
                    'QReader识别': '✓',
                    'WeChat识别': '✓' if in_wechat else '✗',
                    'QReader置信度': confidence,
                    'WeChat置信度': 'N/A',
                    '识别状态': '共同识别' if in_wechat else '仅QReader'
                })
                
                if in_wechat:
                    content_match_count += 1
                else:
                    unique_qreader_count += 1
        
        # 添加WeChat独识别的二维码
        for filename in sorted(wechat_map.keys()):
            wechat_file = wechat_map[filename]
            qreader_file = qreader_map.get(filename, {'qrcodes': []})
            
            qreader_contents = [qr['content'].strip() for qr in qreader_file['qrcodes']]
            wechat_contents = [qr['content'].strip() for qr in wechat_file['qrcodes']]
            
            for i, wechat_qr in enumerate(wechat_file['qrcodes']):
                content = wechat_qr['content'].strip()
                if content not in qreader_contents:
                    if 'page' in wechat_qr:
                        page_info = f"页码 {wechat_qr['page']}"
                    else:
                        page_info = '图片'
                    
                    content_data.append({
                        '文件名': filename,
                        '位置': page_info,
                        '二维码序号': i + 1,
                        '二维码内容': content,
                        'QReader识别': '✗',
                        'WeChat识别': '✓',
                        'QReader置信度': 'N/A',
                        'WeChat置信度': 'N/A',
                        '识别状态': '仅WeChat'
                    })
                    
                    unique_wechat_count += 1
        
        content_df = pd.DataFrame(content_data)
        content_df.to_excel(writer, sheet_name='二维码内容对比', index=False)
        
        # Sheet 7: 一致性统计
        consistency_data = [{
            '指标': '共同识别的二维码数',
            '数量': content_match_count
        }, {
            '指标': '仅QReader识别的二维码数',
            '数量': unique_qreader_count
        }, {
            '指标': '仅WeChat QRCode识别的二维码数',
            '数量': unique_wechat_count
        }, {
            '指标': '内容一致性',
            '数量': f"{content_match_count / max(content_match_count + unique_qreader_count + unique_wechat_count, 1) * 100:.1f}%"
        }]
        
        consistency_df = pd.DataFrame(consistency_data)
        consistency_df.to_excel(writer, sheet_name='一致性统计', index=False)
    
    print(f"Excel对比表格已生成: {output_file}")
    print(f"\n包含以下Sheet:")
    print("  1. 总体对比 - 扫描文件和二维码总数对比")
    print("  2. 文类型对比 - 图片和PDF识别效果对比")
    print("  3. 目录对比 - 不同目录识别效果对比")
    print("  4. 详细文件对比 - 所有文件逐一对比")
    print("  5. QReader优势文件 - QReader识别更多的文件列表")
    print("  6. 二维码内容对比 - 每个二维码的详细识别状态")
    print("  7. 一致性统计 - 识别内容一致性分析")


def main():
    qreader_file = r"d:\code\trytry\results\qrcode_results.json"
    wechat_file = r"d:\code\trytry\results\wechat_qrcode_results.json"
    output_file = r"d:\code\trytry\results\二维码识别对比分析.xlsx"
    
    # 安装openpyxl (如果未安装)
    try:
        import openpyxl
    except ImportError:
        print("正在安装 openpyxl...")
        os.system("pip install openpyxl")
    
    create_comparison_excel(qreader_file, wechat_file, output_file)


if __name__ == "__main__":
    main()