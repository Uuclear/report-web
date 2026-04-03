"""
AI OCR识别服务 - 使用智谱AI GLM-4V-Flash进行OCR识别
"""
import os
import base64
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from io import BytesIO
from pathlib import Path

try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from PIL import Image
    PIL_SUPPORT = True
except ImportError:
    PIL_SUPPORT = False

from config import AI_OCR_API_KEY, AI_OCR_API_URL, AI_OCR_MODEL, PDF_DPI


class AIOCRService:
    """智谱AI OCR识别服务"""
    
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
如果某个字段在报告中找不到或无法识别，请填空字符串""。日期格式请统一为YYYY-MM-DD格式。
重要：每个 JSON 字段只填该字段对应的值，不要把一整行表格、多个字段或字段标签名拼进同一个值里。"""
    
    def __init__(self, max_concurrent: int = 5, timeout: int = 60):
        self.api_key = AI_OCR_API_KEY
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = None

    def _value_looks_like_multi_field(self, v: str, field: str, labels: List[str]) -> bool:
        if not v or len(v) < 30:
            return False
        hits = 0
        for lab in labels:
            if lab != field and lab in v:
                hits += 1
        return hits >= 2

    def _trim_value_to_field(self, v: str, field: str, labels: List[str]) -> str:
        """模型把多字段塞进一个值时，尽量只保留本字段内容。"""
        v = (v or "").strip()
        if not v:
            return ""
        for sep in (f"{field}：", f"{field}:", field + " "):
            if sep in v:
                idx = v.index(sep) + len(sep)
                rest = v[idx:].strip()
                cut = len(rest)
                for lab in labels:
                    if lab == field:
                        continue
                    for s2 in (f"{lab}：", f"{lab}:"):
                        p = rest.find(s2)
                        if 0 < p < cut:
                            cut = p
                return rest[:cut].strip()
        if "\n" in v:
            return v.split("\n", 1)[0].strip()[:400]
        return v[:400] if len(v) > 400 else v

    def sanitize_limis_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data:
            return data
        labels = list(self.LIMIS_FIELDS)
        out: Dict[str, Any] = {}
        for k in labels:
            raw = data.get(k)
            if raw is None:
                out[k] = ""
                continue
            v = str(raw).strip()
            if not v:
                out[k] = ""
                continue
            if self._value_looks_like_multi_field(v, k, labels):
                v = self._trim_value_to_field(v, k, labels)
            if len(v) > 500:
                v = v[:500].rstrip()
            out[k] = v
        return out

    def sanitize_scetia_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data:
            return data
        labels = list(self.SCETIA_FIELDS)
        out: Dict[str, Any] = {}
        for k in labels:
            raw = data.get(k)
            if raw is None:
                out[k] = ""
                continue
            v = str(raw).strip()
            if not v:
                out[k] = ""
                continue
            if self._value_looks_like_multi_field(v, k, labels):
                v = self._trim_value_to_field(v, k, labels)
            if len(v) > 500:
                v = v[:500].rstrip()
            out[k] = v
        return out

    def image_to_base64(self, image_path: str) -> str:
        """将图片转换为base64编码"""
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        ext = Path(image_path).suffix.lower()
        mime_type = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else f'image/{ext[1:]}'
        
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:{mime_type};base64,{base64_data}"
    
    def pil_image_to_base64(self, image: Image.Image) -> str:
        """将PIL Image转换为base64编码"""
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        image_data = buffer.getvalue()
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_data}"
    
    def pdf_to_images(self, pdf_path: str, max_pages: int = 2) -> List[str]:
        """将PDF转换为base64图片"""
        if not PDF_SUPPORT:
            return []
        
        try:
            images = convert_from_path(pdf_path, first_page=1, last_page=max_pages, dpi=PDF_DPI)
            return [self.pil_image_to_base64(img) for img in images]
        except Exception as e:
            print(f"PDF转换失败: {e}")
            return []
    
    async def call_api(self, session: aiohttp.ClientSession, image_base64: str, prompt: str) -> Dict:
        """调用智谱AI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": AI_OCR_MODEL,
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
                AI_OCR_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    # 清理JSON内容
                    content = content.strip()
                    if content.startswith('```json'):
                        content = content[7:]
                    if content.startswith('```'):
                        content = content[3:]
                    if content.endswith('```'):
                        content = content[:-3]
                    content = content.strip()
                    
                    import json
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        print(f"JSON解析失败: {content[:100]}...")
                        return {}
                else:
                    error_text = await response.text()
                    print(f"API请求失败: {response.status} - {error_text[:200]}")
                    return {}
        except asyncio.TimeoutError:
            print("API请求超时")
            return {}
        except Exception as e:
            print(f"API请求异常: {e}")
            return {}
    
    async def recognize_image(
        self,
        image_path: str,
        source_type: str = "limis"
    ) -> Dict:
        """
        识别单个图片
        
        Args:
            image_path: 图片路径
            source_type: 来源类型 (limis/scetia)
            
        Returns:
            识别结果
        """
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async with self.semaphore:
            result = {
                "source_file": Path(image_path).name,
                "source_type": source_type,
                "success": False,
                "data": {},
                "error": None
            }
            
            ext = Path(image_path).suffix.lower()
            prompt = self.LIMIS_PROMPT if source_type == "limis" else self.SCETIA_PROMPT
            
            connector = aiohttp.TCPConnector(limit=self.max_concurrent)
            
            async with aiohttp.ClientSession(connector=connector) as session:
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                    image_base64 = self.image_to_base64(image_path)
                    data = await self.call_api(session, image_base64, prompt)
                    
                    if data:
                        result["success"] = True
                        result["data"] = (
                            self.sanitize_limis_data(data)
                            if source_type == "limis"
                            else self.sanitize_scetia_data(data)
                        )
                    else:
                        result["error"] = "API返回空数据"
                        
                elif ext == '.pdf':
                    base64_images = self.pdf_to_images(image_path)
                    
                    if not base64_images:
                        result["error"] = "PDF转换失败"
                        return result
                    
                    # 处理每一页
                    all_data = {}
                    for i, image_base64 in enumerate(base64_images):
                        page_data = await self.call_api(session, image_base64, prompt)
                        if source_type == "limis":
                            page_data = self.sanitize_limis_data(page_data)
                        else:
                            page_data = self.sanitize_scetia_data(page_data)

                        # 合并数据
                        for key, value in page_data.items():
                            if value and not all_data.get(key):
                                all_data[key] = value
                    
                    if all_data:
                        result["success"] = True
                        result["data"] = all_data
                    else:
                        result["error"] = "所有页面均未提取到数据"
            
            return result