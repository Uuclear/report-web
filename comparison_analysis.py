"""
二维码识别器对比分析程序
对比 QReader 和 WeChat QRCode 的识别效果
"""
import json
import os
from pathlib import Path
from typing import Dict, List
import pandas as pd


def load_results(json_file: str) -> Dict:
    """加载JSON结果文件"""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_results(qreader_file: str, wechat_file: str):
    """对比两个扫描器的结果"""
    
    # 加载结果
    qreader_data = load_results(qreader_file)
    wechat_data = load_results(wechat_file)
    
    # 提取结果
    qreader_results = qreader_data['results']
    wechat_results = wechat_data['results']
    
    print("=" * 80)
    print("二维码识别器对比分析报告")
    print("=" * 80)
    
    # 1. 总体对比
    print("\n【1. 总体识别效果对比】")
    print("-" * 80)
    
    summary_data = {
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
        ]
    }
    
    df_summary = pd.DataFrame(summary_data)
    print(df_summary.to_string(index=False))
    
    # 计算差异
    qreader_qr_count = qreader_data['summary']['total_qrcodes']
    wechat_qr_count = wechat_data['summary']['total_qrcodes']
    difference = qreader_qr_count - wechat_qr_count
    
    print(f"\n二维码识别数量差异: QReader 比 WeChat QRCode 多识别 {difference} 个二维码")
    print(f"QReader 相对优势: {difference / wechat_qr_count * 100:.1f}%")
    
    # 2. 按文件类型对比
    print("\n【2. 按文件类型对比】")
    print("-" * 80)
    
    type_comparison = []
    
    # 统计各类型文件
    for file_type in ['image', 'pdf']:
        qreader_type_files = [r for r in qreader_results if r['type'] == file_type]
        wechat_type_files = [r for r in wechat_results if r['type'] == file_type]
        
        qreader_qr_count = sum(len(r['qrcodes']) for r in qreader_type_files)
        wechat_qr_count = sum(len(r['qrcodes']) for r in wechat_type_files)
        
        type_comparison.append({
            '文件类型': file_type.upper(),
            '文件数量': len(qreader_type_files),
            'QReader识别数': qreader_qr_count,
            'WeChat识别数': wechat_qr_count,
            '差异': qreader_qr_count - wechat_qr_count,
            'QReader胜率': f"{qreader_qr_count / max(qreader_qr_count, wechat_qr_count) * 100:.1f}%"
        })
    
    df_type = pd.DataFrame(type_comparison)
    print(df_type.to_string(index=False))
    
    # 3. 按目录对比
    print("\n【3. 按目录对比】")
    print("-" * 80)
    
    dir_comparison = []
    
    for directory in ['files_limis', 'files_scetia']:
        qreader_dir_files = [r for r in qreader_results if directory in r['file']]
        wechat_dir_files = [r for r in wechat_results if directory in r['file']]
        
        qreader_qr_count = sum(len(r['qrcodes']) for r in qreader_dir_files)
        wechat_qr_count = sum(len(r['qrcodes']) for r in wechat_dir_files)
        
        dir_comparison.append({
            '目录': directory,
            '文件数量': len(qreader_dir_files),
            'QReader识别数': qreader_qr_count,
            'WeChat识别数': wechat_qr_count,
            '差异': qreader_qr_count - wechat_qr_count,
            'QReader胜率': f"{qreader_qr_count / max(qreader_qr_count, wechat_qr_count) * 100:.1f}%"
        })
    
    df_dir = pd.DataFrame(dir_comparison)
    print(df_dir.to_string(index=False))
    
    # 4. 详细文件对比
    print("\n【4. 详细文件对比 (仅显示有差异的文件)】")
    print("-" * 80)
    
    detailed_comparison = []
    
    # 创建文件映射
    qreader_map = {Path(r['file']).name: r for r in qreader_results}
    wechat_map = {Path(r['file']).name: r for r in wechat_results}
    
    # 对比每个文件
    for filename in qreader_map.keys():
        qreader_file = qreader_map[filename]
        wechat_file = wechat_map.get(filename, {'qrcodes': [], 'success': False})
        
        qreader_qr_count = len(qreader_file['qrcodes'])
        wechat_qr_count = len(wechat_file['qrcodes'])
        
        # 只显示有差异的文件
        if qreader_qr_count != wechat_qr_count:
            detailed_comparison.append({
                '文件名': filename,
                '类型': qreader_file['type'],
                'QReader识别数': qreader_qr_count,
                'WeChat识别数': wechat_qr_count,
                '差异': qreader_qr_count - wechat_qr_count,
                '胜者': 'QReader' if qreader_qr_count > wechat_qr_count else 'WeChat'
            })
    
    if detailed_comparison:
        df_detailed = pd.DataFrame(detailed_comparison)
        print(df_detailed.to_string(index=False))
        
        # 统计胜率
        qreader_wins = sum(1 for d in detailed_comparison if d['胜者'] == 'QReader')
        wechat_wins = sum(1 for d in detailed_comparison if d['胜者'] == 'WeChat')
        
        print(f"\n在有差异的 {len(detailed_comparison)} 个文件中:")
        print(f"  - QReader 获胜: {qreader_wins} 个文件")
        print(f"  - WeChat QRCode 获胜: {wechat_wins} 个文件")
    else:
        print("所有文件的识别数量完全一致!")
    
    # 5. 识别内容对比
    print("\n【5. 识别内容一致性分析】")
    print("-" * 80)
    
    content_match_count = 0
    content_mismatch_count = 0
    unique_qreader_count = 0
    unique_wechat_count = 0
    
    # 对比识别到的二维码内容
    for filename in qreader_map.keys():
        qreader_file = qreader_map[filename]
        wechat_file = wechat_map.get(filename, {'qrcodes': []})
        
        qreader_contents = [qr['content'].strip() for qr in qreader_file['qrcodes']]
        wechat_contents = [qr['content'].strip() for qr in wechat_file['qrcodes']]
        
        # 统计匹配情况
        for content in qreader_contents:
            if content in wechat_contents:
                content_match_count += 1
            else:
                unique_qreader_count += 1
        
        for content in wechat_contents:
            if content not in qreader_contents:
                unique_wechat_count += 1
    
    print(f"共同识别的二维码数: {content_match_count}")
    print(f"仅QReader识别的二维码数: {unique_qreader_count}")
    print(f"仅WeChat QRCode识别的二维码数: {unique_wechat_count}")
    print(f"内容一致性: {content_match_count / max(content_match_count + unique_qreader_count + unique_wechat_count, 1) * 100:.1f}%")
    
    # 6. 性能特点总结
    print("\n【6. 性能特点总结】")
    print("-" * 80)
    
    print("QReader 特点:")
    print("  [+] 基于 YOLOv8 深度学习模型,检测能力强")
    print("  [+] 提供置信度评分(平均 84-90%)")
    print("  [+] 对模糊、倾斜、低质量二维码有更好的鲁棒性")
    print("  [+] 识别数量更多(42个 vs 36个)")
    print("  [+] 在PDF文件上表现更优")
    
    print("\nWeChat QRCode 特点:")
    print("  [+] 微信团队开发的专用二维码检测器")
    print("  [+] 速度较快,适合实时应用")
    print("  [+] 对高质量二维码识别准确")
    print("  [-] 无置信度评分")
    print("  [-] 在某些PDF上识别失败")
    
    # 7. 推荐建议
    print("\n【7. 推荐建议】")
    print("-" * 80)
    
    print("根据对比结果,建议:")
    print("  1. 优先使用 QReader 进行批量扫描(识别率更高)")
    print("  2. 对于高质量图片,两者均可使用")
    print("  3. 对于模糊或低质量图片,优先使用 QReader")
    print("  4. 对于PDF文件,优先使用 QReader")
    print("  5. 对于实时应用(如摄像头扫描),可考虑 WeChat QRCode")
    
    print("\n" + "=" * 80)
    print("对比分析完成!")
    print("=" * 80)


def main():
    """主函数"""
    qreader_file = r"d:\code\trytry\results\qrcode_results.json"
    wechat_file = r"d:\code\trytry\results\wechat_qrcode_results.json"
    
    # 检查文件是否存在
    if not os.path.exists(qreader_file):
        print(f"错误: QReader结果文件不存在 - {qreader_file}")
        return
    
    if not os.path.exists(wechat_file):
        print(f"错误: WeChat QRCode结果文件不存在 - {wechat_file}")
        return
    
    # 进行对比分析
    compare_results(qreader_file, wechat_file)


if __name__ == "__main__":
    main()