"""
SCETIA 防伪查询爬虫
用于批量查询上海市建设工程检测行业协会的防伪报告
"""
import json
import time
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class ScetiaScraper:
    """SCETIA防伪查询爬虫"""
    
    QUERY_URL = "http://www.scetia.com/Scetia.OnlineExplorer/App_Public/AntiFakeReportQuery.aspx"
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webimage,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    def __init__(self, delay: float = 2.0, timeout: int = 30):
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def parse_qrcode_content(self, content: str) -> Optional[Dict[str, str]]:
        content = content.strip()
        if '|' in content:
            parts = content.split('|')
            if len(parts) >= 2:
                report_id = parts[0].strip()
                security_code = parts[1].strip()
                if len(security_code) == 12:
                    return {'report_id': report_id, 'security_code': security_code}
        return None
    
    def load_qrcode_results(self, json_file: str, target_dir: str = 'files_scetia') -> List[Dict]:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = []
        for item in data.get('results', []):
            file_path = item.get('file', '')
            if target_dir in file_path and item.get('qrcodes'):
                for qr in item['qrcodes']:
                    content = qr.get('content', '')
                    parsed = self.parse_qrcode_content(content)
                    if parsed:
                        results.append({
                            'source_file': Path(file_path).name,
                            'report_id': parsed['report_id'],
                            'security_code': parsed['security_code'],
                            'page': qr.get('page', None),
                            'confidence': qr.get('confidence', 0)
                        })
        return results
    
    def query_report(self, report_id: str, security_code: str) -> Dict:
        result = {
            'report_id': report_id,
            'security_code': security_code,
            'query_success': False,
            'data': {},
            'error': None,
            'query_time': datetime.now().isoformat()
        }
        
        params = {
            'rqstConsignID': report_id,
            'rqstIdentifyingCode': security_code
        }
        
        try:
            response = self.session.post(self.QUERY_URL, data=params, timeout=self.timeout, allow_redirects=True)
            result['query_success'] = response.status_code == 200
            
            if response.status_code == 200:
                parsed = self.parse_response_html(response.text)
                result['data'] = parsed.get('data', {})
                if not parsed.get('has_result'):
                    result['error'] = "未找到报告"
            else:
                result['error'] = f"HTTP状态码: {response.status_code}"
                
        except requests.exceptions.Timeout:
            result['error'] = "请求超时"
        except requests.exceptions.ConnectionError:
            result['error'] = "连接错误"
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def parse_response_html(self, html: str) -> Dict:
        soup = BeautifulSoup(html, 'html.parser')
        parsed = {'has_result': False, 'data': {}}
        
        if '没有能够搜索到' in html or '很抱歉' in html:
            return parsed
        
        parsed['has_result'] = True
        data = parsed['data']
        
        main_table = soup.find('table', id='generalProjectAndConsignInfo')
        if main_table:
            self._extract_main_table(main_table, data)
        
        sample_tables = soup.find_all('table', title=True)
        for table in sample_tables:
            title = table.get('title', '')
            if 'generalSampleInfo' in title:
                self._extract_sample_table(table, data)
                break
        
        return parsed
    
    def _extract_main_table(self, table, data: dict):
        table_html = str(table)
        
        # 用正则提取简单字段
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
        
        # 遍历行提取复杂字段
        rows = table.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            row_text = row.get_text()
            
            # 委托单位
            if '委托单位' in row_text and '工程信息' not in row_text:
                for i, td in enumerate(tds):
                    if '委托单位' in td.get_text():
                        if i + 1 < len(tds):
                            data['委托单位'] = tds[i + 1].get_text(strip=True)
                        break
            
            # 工程名称
            if '工程名称' in row_text:
                span = row.find('span')
                if span:
                    data['工程名称'] = span.get_text(strip=True)
            
            # 工程地址
            if '工程地址' in row_text:
                for i, td in enumerate(tds):
                    if '工程地址' in td.get_text():
                        if i + 1 < len(tds):
                            data['工程地址'] = tds[i + 1].get_text(strip=True)
                        break
            
            # 施工单位
            if '施工单位' in row_text and '检测机构' not in row_text:
                for i, td in enumerate(tds):
                    if td.get_text(strip=True) == '施工单位':
                        if i + 1 < len(tds):
                            data['施工单位'] = tds[i + 1].get_text(strip=True)
                        break
            
            # 取样人及证书号
            if '取样人' in row_text and '证书号' in row_text:
                for i, td in enumerate(tds):
                    if '取样人' in td.get_text():
                        if i + 1 < len(tds):
                            data['取样人及证书号'] = tds[i + 1].get_text(strip=True)
                        break
            
            # 见证单位
            if '见证单位' in row_text and '见证人' not in row_text:
                for i, td in enumerate(tds):
                    if '见证单位' in td.get_text():
                        if i + 1 < len(tds):
                            data['见证单位'] = tds[i + 1].get_text(strip=True)
                        break
            
            # 见证人及证书号
            if '见证人' in row_text and '证书号' in row_text:
                for i, td in enumerate(tds):
                    if '见证人' in td.get_text():
                        if i + 1 < len(tds):
                            data['见证人及证书号'] = tds[i + 1].get_text(strip=True)
                        break
            
            # 委托日期和报告日期
            if '委托日期' in row_text and '报告日期' in row_text:
                for i, td in enumerate(tds):
                    text = td.get_text(strip=True)
                    if '委托日期' in text and i + 1 < len(tds):
                        data['委托日期'] = tds[i + 1].get_text(strip=True)
                    if '报告日期' in text and i + 1 < len(tds):
                        data['报告日期'] = tds[i + 1].get_text(strip=True)
            
            # 检测机构
            if '检测机构信息' in row_text or ('全称' in row_text and '检测机构' not in data):
                span = row.find('span')
                if span:
                    text = span.get_text(strip=True)
                    if text and '全称' not in text and len(text) > 5:
                        data['检测机构'] = text
            
            # 防伪校验码
            if '防伪校验码' in row_text:
                span = row.find('span')
                if span:
                    text = span.get_text(strip=True)
                    if text and len(text) >= 10:
                        data['防伪校验码'] = text
            
            # 报告结论
            if '报告结论' in row_text:
                for a in row.find_all('a'):
                    a_text = a.get_text(strip=True)
                    if '结论' in a_text:
                        match = re.search(r'结论[：:\s]*(.+)', a_text)
                        if match:
                            data['检测结论'] = match.group(1).strip()
                
                match = re.search(r'样品编号[：:\s]*(\S+)', row_text)
                if match:
                    data['样品编号'] = match.group(1)
    
    def _extract_sample_table(self, table, data: dict):
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
    
    def batch_query(self, qrcode_data: List[Dict], output_file: str = None) -> Dict:
        results = []
        total = len(qrcode_data)
        success_count = 0
        fail_count = 0
        
        print(f"开始批量查询，共 {total} 个报告...")
        print("=" * 60)
        
        for i, item in enumerate(qrcode_data, 1):
            print(f"[{i}/{total}] 查询: {item['report_id']}...", end=' ')
            
            query_result = self.query_report(item['report_id'], item['security_code'])
            query_result['source_file'] = item['source_file']
            query_result['page'] = item.get('page')
            query_result['confidence'] = item.get('confidence')
            results.append(query_result)
            
            if query_result['query_success']:
                if query_result['data']:
                    success_count += 1
                    print("[OK] 成功")
                else:
                    fail_count += 1
                    print("[!] 未找到报告")
            else:
                fail_count += 1
                print(f"[X] 失败: {query_result['error']}")
            
            if i < total:
                time.sleep(self.delay)
        
        output = {
            'query_time': datetime.now().isoformat(),
            'source_file': 'results/qrcode_results.json',
            'summary': {
                'total_reports': total,
                'success_count': success_count,
                'fail_count': fail_count,
                'query_url': self.QUERY_URL
            },
            'results': results
        }
        
        if output_file:
            self.save_results(output, output_file)
        
        print("=" * 60)
        print(f"查询完成！成功: {success_count}, 失败/未找到: {fail_count}")
        
        return output
    
    def save_results(self, data: Dict, output_file: str):
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"结果已保存到: {output_file}")


def main():
    scraper = ScetiaScraper(delay=2.0, timeout=30)
    qrcode_file = r"d:\code\trytry\results\qrcode_results.json"
    print(f"加载二维码数据: {qrcode_file}")
    
    qrcode_data = scraper.load_qrcode_results(qrcode_file, target_dir='files_scetia')
    print(f"提取到 {len(qrcode_data)} 个有效二维码")
    
    output_file = r"d:\code\trytry\results\scetia_query_results.json"
    scraper.batch_query(qrcode_data, output_file)


if __name__ == "__main__":
    main()