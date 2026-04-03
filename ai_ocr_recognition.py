"""
AI OCR识别 - 使用智谱AI GLM-4V-Flash对无二维码检测报告进行OCR识别
支持图片和PDF文件，异步并发处理
"""
import os
import json
import base64
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from io import BytesIO

try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("警告: pdf2image 未安装，PDF文件将跳过。安装: pip install pdf2image")

try:
    from PIL import Image
    PIL_SUPPORT = True
except ImportError:
    PIL_SUPPORT = False
    print("警告: Pillow 未安装。安装: pip install Pillow")


class AIOCRRecognizer:
    """智谱AI OCR识别器"""
    
    API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    MODEL = "glm-4v-flash"
    
    # limis报告提取字段
    LIMIS_FIELDS = [
        "检测机构", "报告编号", "签发日期",
        "委托编号", "委托日期", "委托单位",
        "工程名称", "工程部位",
        "样品编号", "样品名称", "规格型号",
        "生产单位", "检验依据"
    ]
    
    # scetia报告提取字段
    SCETIA_FIELDS = [
        "委托编号", "报告编号", "委托单位",
        "工程名称", "工程地址", "施工单位",
        "样品名称", "委托日期", "报告日期"
    ]
    
    # limis提取提示词
    LIMIS_PROMPT = """请仔细阅读这张检测报告图片，提取以下关键信息并以JSON格式返回（不要添加任何其他文字说明）：
{
    "检测机构": "",
    "报告编号": "",
    "签发日期": "",
    "委托编号": "",
    "委托日期": "",
    "委托单位": "",
    "工程名称": "",
    "工程部位": "",
    "样品编号": "",
    "样品名称": "",
    "规格型号": "",
    "生产单位": "",
    "检验依据": ""
}
如果某个字段在报告中找不到或无法识别，请填空字符串""。日期格式请统一为YYYY-MM-DD格式。"""
    
    # scetia提取提示词
    SCETIA_PROMPT = """请仔细阅读这张检测报告图片，提取以下关键信息并以JSON格式返回（不要添加任何其他文字说明）：
{
    "委托编号": "",
    "报告编号": "",
    "委托单位": "",
    "工程名称": "",
    "工程地址": "",
    "施工单位": "",
    "样品名称": "",
    "委托日期": "",
    "报告日期": ""
}
如果某个字段在报告中找不到或无法识别，请填空字符串""。日期格式请统一为YYYY-MM-DD格式。"""
    
    def __init__(self, api_key: str, max_concurrent: int = 10, timeout: int = 60):
        """
        初始化识别器
        
        Args:
            api_key: 智谱AI API密钥
            max_concurrent: 最大并发数
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = None
    
    def load_failed_files(self, qrcode_json: str) -> Dict[str, List[str]]:
        """
        从qrcode_results.json加载识别失败的文件
        
        Args:
            qrcode_json: qrcode_results.json文件路径
            
        Returns:
            按目录分类的失败文件列表 {"files_limis": [...], "files_scetia": [...]}
        """
        with open(qrcode_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        failed_files = {
            "files_limis": [],
            "files_scetia": []
        }
        
        for result in data.get('results', []):
            file_path = result.get('file', '')
            
            # 判断文件是否识别失败（qrcodes为空数组）
            if result.get('success', False) and len(result.get('qrcodes', [])) == 0:
                file_name = Path(file_path).name
                
                # 根据路径判断来源目录
                if 'files_limis' in file_path:
                    failed_files["files_limis"].append(file_path)
                elif 'files_scetia' in file_path:
                    failed_files["files_scetia"].append(file_path)
        
        return failed_files
    
    def image_to_base64(self, image_path: str) -> str:
        """
        将图片文件转换为base64编码
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            base64编码字符串
        """
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # 获取图片格式
        ext = Path(image_path).suffix.lower()
        if ext in ['.jpg', '.jpeg']:
            mime_type = 'image/jpeg'
        elif ext == '.png':
            mime_type = 'image/png'
        elif ext == '.gif':
            mime_type = 'image/gif'
        elif ext == '.webp':
            mime_type = 'image/webp'
        else:
            mime_type = 'image/jpeg'  # 默认
        
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:{mime_type};base64,{base64_data}"
    
    def pil_image_to_base64(self, image: Image.Image) -> str:
        """
        将PIL Image对象转换为base64编码
        
        Args:
            image: PIL Image对象
            
        Returns:
            base64编码字符串
        """
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        image_data = buffer.getvalue()
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_data}"
    
    def pdf_to_images(self, pdf_path: str, max_pages: int = 2) -> List[str]:
        """
        将PDF转换为图片（base64编码）
        
        Args:
            pdf_path: PDF文件路径
            max_pages: 最大转换页数
            
        Returns:
            base64编码图片列表
        """
        if not PDF_SUPPORT:
            print(f"  PDF支持未启用，跳过: {pdf_path}")
            return []
        
        try:
            # 转换PDF为图片
            images = convert_from_path(pdf_path, first_page=1, last_page=max_pages, dpi=200)
            
            # 转换为base64
            base64_images = []
            for image in images:
                base64_images.append(self.pil_image_to_base64(image))
            
            return base64_images
        except Exception as e:
            print(f"  PDF转换失败: {e}")
            return []
    
    async def call_api(self, session: aiohttp.ClientSession, image_base64: str, prompt: str) -> Dict:
        """
        调用智谱AI API
        
        Args:
            session: aiohttp会话
            image_base64: base64编码图片
            prompt: 提示词
            
        Returns:
            提取的数据字典
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                }
            ]
        }
        
        try:
            async with session.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # 提取响应内容
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    # 解析JSON
                    try:
                        # 清理可能的非JSON内容
                        content = content.strip()
                        if content.startswith('```json'):
                            content = content[7:]
                        if content.startswith('```'):
                            content = content[3:]
                        if content.endswith('```'):
                            content = content[:-3]
                        content = content.strip()
                        
                        data = json.loads(content)
                        return data
                    except json.JSONDecodeError:
                        print(f"  JSON解析失败: {content[:100]}...")
                        return {}
                else:
                    error_text = await response.text()
                    print(f"  API请求失败: {response.status} - {error_text[:200]}")
                    return {}
        except asyncio.TimeoutError:
            print(f"  API请求超时")
            return {}
        except Exception as e:
            print(f"  API请求异常: {e}")
            return {}
    
    async def process_file(
        self, 
        session: aiohttp.ClientSession,
        file_path: str,
        source_type: str,
        file_index: int,
        total_files: int
    ) -> Dict:
        """
        处理单个文件
        
        Args:
            session: aiohttp会话
            file_path: 文件路径
            source_type: 来源类型 (files_limis/files_scetia)
            file_index: 文件序号
            total_files: 总文件数
            
        Returns:
            处理结果字典
        """
        async with self.semaphore:
            file_name = Path(file_path).name
            print(f"\n[{file_index}/{total_files}] 处理: {file_name}")
            
            result = {
                "source_file": file_name,
                "source_type": source_type,
                "file_path": file_path,
                "success": False,
                "data": {},
                "error": None,
                "process_time": datetime.now().isoformat()
            }
            
            # 判断文件类型
            ext = Path(file_path).suffix.lower()
            
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                # 图片文件
                image_base64 = self.image_to_base64(file_path)
                prompt = self.LIMIS_PROMPT if source_type == "files_limis" else self.SCETIA_PROMPT
                
                data = await self.call_api(session, image_base64, prompt)
                
                if data:
                    result["success"] = True
                    result["data"] = data
                    print(f"  识别成功!")
                else:
                    result["error"] = "API返回空数据"
                    print(f"  识别失败!")
                    
            elif ext == '.pdf':
                # PDF文件
                base64_images = self.pdf_to_images(file_path, max_pages=2)
                
                if not base64_images:
                    result["error"] = "PDF转换失败"
                    print(f"  PDF转换失败!")
                    return result
                
                prompt = self.LIMIS_PROMPT if source_type == "files_limis" else self.SCETIA_PROMPT
                
                # 处理每一页（合并结果）
                all_data = {}
                for i, image_base64 in enumerate(base64_images):
                    print(f"  处理第{i+1}页...")
                    page_data = await self.call_api(session, image_base64, prompt)
                    
                    # 合并数据（优先使用非空值）
                    for key, value in page_data.items():
                        if value and not all_data.get(key):
                            all_data[key] = value
                
                if all_data:
                    result["success"] = True
                    result["data"] = all_data
                    print(f"  识别成功!")
                else:
                    result["error"] = "所有页面均未提取到数据"
                    print(f"  识别失败!")
            else:
                result["error"] = f"不支持的文件类型: {ext}"
                print(f"  不支持的文件类型!")
            
            return result
    
    async def process_all_files(self, failed_files: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
        """
        异步处理所有失败文件
        
        Args:
            failed_files: 按目录分类的失败文件
            
        Returns:
            处理结果
        """
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # 合并所有文件并标记来源
        all_files = []
        for source_type, files in failed_files.items():
            for file_path in files:
                all_files.append((file_path, source_type))
        
        total = len(all_files)
        print(f"\n开始处理 {total} 个文件...")
        print(f"并发限制: {self.max_concurrent}")
        print("=" * 60)
        
        # 创建aiohttp会话
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        
        results = {
            "files_limis": [],
            "files_scetia": []
        }
        
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for i, (file_path, source_type) in enumerate(all_files, 1):
                task = self.process_file(session, file_path, source_type, i, total)
                tasks.append(task)
            
            # 并发执行所有任务
            task_results = await asyncio.gather(*tasks)
            
            # 按来源分类结果
            for result in task_results:
                source_type = result["source_type"]
                results[source_type].append(result)
        
        return results
    
    def save_results(self, results: Dict[str, List[Dict]], output_dir: str):
        """
        保存结果到JSON文件
        
        Args:
            results: 处理结果
            output_dir: 输出目录
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存limis结果
        if results["files_limis"]:
            limis_output = {
                "process_time": datetime.now().isoformat(),
                "source": "files_limis",
                "total_files": len(results["files_limis"]),
                "success_count": sum(1 for r in results["files_limis"] if r["success"]),
                "fail_count": sum(1 for r in results["files_limis"] if not r["success"]),
                "model": self.MODEL,
                "results": results["files_limis"]
            }
            
            limis_file = os.path.join(output_dir, "ai_ocr_limis_results.json")
            with open(limis_file, 'w', encoding='utf-8') as f:
                json.dump(limis_output, f, ensure_ascii=False, indent=2)
            print(f"\nlimis结果已保存: {limis_file}")
        
        # 保存scetia结果
        if results["files_scetia"]:
            scetia_output = {
                "process_time": datetime.now().isoformat(),
                "source": "files_scetia",
                "total_files": len(results["files_scetia"]),
                "success_count": sum(1 for r in results["files_scetia"] if r["success"]),
                "fail_count": sum(1 for r in results["files_scetia"] if not r["success"]),
                "model": self.MODEL,
                "results": results["files_scetia"]
            }
            
            scetia_file = os.path.join(output_dir, "ai_ocr_scetia_results.json")
            with open(scetia_file, 'w', encoding='utf-8') as f:
                json.dump(scetia_output, f, ensure_ascii=False, indent=2)
            print(f"scetia结果已保存: {scetia_file}")
        
        # 保存合并结果
        all_results = results["files_limis"] + results["files_scetia"]
        merged_output = {
            "process_time": datetime.now().isoformat(),
            "total_files": len(all_results),
            "success_count": sum(1 for r in all_results if r["success"]),
            "fail_count": sum(1 for r in all_results if not r["success"]),
            "model": self.MODEL,
            "results": all_results
        }
        
        merged_file = os.path.join(output_dir, "ai_ocr_all_results.json")
        with open(merged_file, 'w', encoding='utf-8') as f:
            json.dump(merged_output, f, ensure_ascii=False, indent=2)
        print(f"合并结果已保存: {merged_file}")


def print_summary(results: Dict[str, List[Dict]]):
    """打印处理结果汇总"""
    print("\n" + "=" * 60)
    print("AI OCR识别结果汇总")
    print("=" * 60)
    
    for source_type, file_results in results.items():
        if not file_results:
            continue
        
        success = sum(1 for r in file_results if r["success"])
        fail = len(file_results) - success
        
        print(f"\n{source_type}:")
        print(f"  总数: {len(file_results)}")
        print(f"  成功: {success}")
        print(f"  失败: {fail}")
        
        # 打印成功识别的数据
        for result in file_results:
            if result["success"]:
                print(f"\n  {result['source_file']}:")
                for key, value in result["data"].items():
                    if value:
                        print(f"    {key}: {value}")
            else:
                print(f"\n  {result['source_file']}: 失败 - {result.get('error', '未知')}")


async def main():
    """主函数"""
    # 配置
    API_KEY = "aa68716a66dd4f249f9a18b8105d8e05.eUnEVgYSIvW5lMqg"
    QRCODE_JSON = r"d:\code\trytry\results\qrcode_results.json"
    OUTPUT_DIR = r"d:\code\trytry\results"
    MAX_CONCURRENT = 10
    
    # 创建识别器
    recognizer = AIOCRRecognizer(
        api_key=API_KEY,
        max_concurrent=MAX_CONCURRENT,
        timeout=60
    )
    
    # 加载识别失败的文件
    print("加载识别失败的文件列表...")
    failed_files = recognizer.load_failed_files(QRCODE_JSON)
    
    print(f"files_limis 失败文件: {len(failed_files['files_limis'])}个")
    print(f"files_scetia 失败文件: {len(failed_files['files_scetia'])}个")
    
    for source_type, files in failed_files.items():
        if files:
            print(f"\n{source_type} 文件列表:")
            for f in files:
                print(f"  - {Path(f).name}")
    
    # 检查是否有文件需要处理
    total_files = sum(len(files) for files in failed_files.values())
    if total_files == 0:
        print("\n没有需要处理的文件!")
        return
    
    # 异步处理所有文件
    results = await recognizer.process_all_files(failed_files)
    
    # 保存结果
    recognizer.save_results(results, OUTPUT_DIR)
    
    # 打印汇总
    print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())