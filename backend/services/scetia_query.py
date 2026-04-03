"""
scetia防伪查询服务
"""
import re
import asyncio
import aiohttp
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup

from config import SCETIA_QUERY_URL, SCETIA_TIMEOUT


class ScetiaQueryService:
    """scetia防伪查询服务"""
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webimage,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    def __init__(self, timeout: int = SCETIA_TIMEOUT):
        self.timeout = timeout
    
    def parse_qrcode_content(self, content: str) -> Optional[Dict[str, str]]:
        """
        解析二维码内容
        
        Args:
            content: 二维码内容（格式：报告编号|防伪码）
            
        Returns:
            {report_id, security_code} 或 None
        """
        content = content.strip()
        if '|' in content:
            parts = content.split('|')
            if len(parts) >= 2:
                report_id = parts[0].strip()
                security_code = parts[1].strip()
                if len(security_code) == 12:
                    return {'report_id': report_id, 'security_code': security_code}
        return None
    
    async def query_report(self, report_id: str, security_code: str) -> Dict:
        """
        查询报告
        
        Args:
            report_id: 报告编号
            security_code: 防伪码
            
        Returns:
            查询结果
        """
        result = {
            'report_id': report_id,
            'security_code': security_code,
            'query_success': False,
            'data': {},
            'error': None
        }
        
        params = {
            'rqstConsignID': report_id,
            'rqstIdentifyingCode': security_code
        }
        
        try:
            connector = aiohttp.TCPConnector(limit=1)
            
            async with aiohttp.ClientSession(headers=self.HEADERS, connector=connector) as session:
                async with session.post(
                    SCETIA_QUERY_URL,
                    data=params,
                    timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        parsed = self.parse_response_html(html)
                        result['data'] = parsed.get('data', {})
                        result['query_success'] = True
                        
                        if not parsed.get('has_result'):
                            result['error'] = "未找到报告"
                    else:
                        result['error'] = f"HTTP状态码: {response.status}"
        
        except asyncio.TimeoutError:
            result['error'] = "请求超时"
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def parse_response_html(self, html: str) -> Dict:
        """解析响应HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        parsed = {'has_result': False, 'data': {}}
        
        if '没有能够搜索到' in html or '很抱歉' in html:
            return parsed
        
        parsed['has_result'] = True
        data = parsed['data']
        
        # 提取主表信息
        main_table = soup.find('table', id='generalProjectAndConsignInfo')
        if main_table:
            self._extract_main_table(main_table, data)
        
        # 提取样品表信息
        sample_tables = soup.find_all('table', title=True)
        for table in sample_tables:
            title = table.get('title', '')
            if 'generalSampleInfo' in title:
                self._extract_sample_table(table, data)
                break
        
        return parsed
    
    def _extract_main_table(self, table, data: dict):
        """提取主表数据"""
        table_html = str(table)
        
        patterns = {
            '委托编号': r'委托编号[：:\s]*<span[^>]*>([^<]+)</span>',
            '报告编号': r'报告编号[：:\s]*<span[^>]*>([^<]+)</span>',
            '委托性质': r'委托性质[：:\s]*<span[^>]*>([^<]+)</span>',
            '标段': r'标段[：:\s]*<span[^>]*>([^<]+)</span>',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, table_html)
            if match:
                data[field] = match.group(1).strip()
        
        rows = table.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            row_text = row.get_text()
            
            if '委托单位' in row_text and '工程信息' not in row_text:
                for i, td in enumerate(tds):
                    if '委托单位' in td.get_text():
                        if i + 1 < len(tds):
                            data['委托单位'] = tds[i + 1].get_text(strip=True)
                        break
            
            if '工程名称' in row_text:
                span = row.find('span')
                if span:
                    data['工程名称'] = span.get_text(strip=True)
            
            if '工程地址' in row_text:
                for i, td in enumerate(tds):
                    if '工程地址' in td.get_text():
                        if i + 1 < len(tds):
                            data['工程地址'] = tds[i + 1].get_text(strip=True)
                        break
            
            if '施工单位' in row_text and '检测机构' not in row_text:
                for i, td in enumerate(tds):
                    if td.get_text(strip=True) == '施工单位':
                        if i + 1 < len(tds):
                            data['施工单位'] = tds[i + 1].get_text(strip=True)
                        break
            
            if '委托日期' in row_text and '报告日期' in row_text:
                for i, td in enumerate(tds):
                    text = td.get_text(strip=True)
                    if '委托日期' in text and i + 1 < len(tds):
                        data['委托日期'] = tds[i + 1].get_text(strip=True)
                    if '报告日期' in text and i + 1 < len(tds):
                        data['报告日期'] = tds[i + 1].get_text(strip=True)
            
            if '检测机构信息' in row_text or ('全称' in row_text and '检测机构' not in data):
                span = row.find('span')
                if span:
                    text = span.get_text(strip=True)
                    if text and '全称' not in text and len(text) > 5:
                        data['检测机构'] = text
    
    def _extract_sample_table(self, table, data: dict):
        """提取样品表数据"""
        table_html = str(table)
        
        patterns = {
            '样品编号': r'id="_[^"]*_sample_ID"[^>]*>([^<]+)<',
            '样品名称': r'id="_[^"]*_sampleName"[^>]*>([^<]+)<',
            '生产单位': r'id="_[^"]*_produce_Factory"[^>]*>([^<]+)<',
            '规格': r'id="_[^"]*_specName"[^>]*>([^<]+)<',
            '强度等级': r'id="_[^"]*_gradeName"[^>]*>([^<]+)<',
            '工程部位': r'id="_[^"]*_proJect_Part"[^>]*>([^<]+)<',
            '样品检测结论': r'id="_[^"]*_exam_Result"[^>]*>([^<]+)<',
        }
        
        for field, pattern in patterns.items():
            if field not in data:
                match = re.search(pattern, table_html)
                if match:
                    data[field] = match.group(1).strip()
    
    async def get_report_data(self, qr_content: str) -> Dict:
        """
        根据二维码内容获取报告数据
        
        Args:
            qr_content: 二维码内容
            
        Returns:
            报告数据
        """
        parsed = self.parse_qrcode_content(qr_content)
        
        if not parsed:
            return {
                "success": False,
                "error": "二维码格式无效",
                "data": {}
            }
        
        result = await self.query_report(parsed['report_id'], parsed['security_code'])
        
        return {
            "report_id": parsed['report_id'],
            "security_code": parsed['security_code'],
            "success": result['query_success'],
            "data": result['data'],
            "error": result['error']
        }