"""
二维码网页爬虫 - 从二维码URL爬取检测报告信息
支持双模式：requests（轻量）和 selenium（浏览器自动化备用）
"""
import os
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

# Selenium 备用模式
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_SUPPORT = True
except ImportError:
    SELENIUM_SUPPORT = False
    print("警告: selenium 未安装，备用模式已禁用。安装: pip install selenium webdriver-manager")


class QRCodeCrawler:
    """二维码网页爬虫"""
    
    # 微信移动端请求头
    WECHAT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36 MicroMessenger/8.0.38.2400(0x28003858) Process/tools WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    # 需要提取的字段
    FIELD_MAPPING = {
        '检测机构': 'testing_org',
        '报告编号': 'report_no',
        '签发日期': 'issue_date',
        '委托编号': 'request_no',
        '委托日期/抽样日期': 'request_date',
        '委托单位': 'client',
        '工程名称': 'project_name',
        '工程部位': 'project_location',
        '样品编号': 'sample_no',
        '样品名称': 'sample_name',
        '规格型号': 'specification',
        '生产单位': 'manufacturer',
        '检验依据': 'test_basis',
    }
    
    def __init__(self, timeout: int = 30, retry_times: int = 3):
        """
        初始化爬虫
        
        Args:
            timeout: 请求超时时间（秒）
            retry_times: 重试次数
        """
        self.timeout = timeout
        self.retry_times = retry_times
        self.session = requests.Session()
        self.session.headers.update(self.WECHAT_HEADERS)
        
    def load_qrcode_results(self, json_file: str, source_dir: str = None) -> List[Dict]:
        """
        从JSON文件加载二维码结果，提取URL类型的二维码
        
        Args:
            json_file: qrcode_results.json 文件路径
            source_dir: 筛选特定目录的结果（如 files_limis）
            
        Returns:
            包含URL二维码的结果列表
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        url_qrcodes = []
        
        for result in data.get('results', []):
            file_path = result.get('file', '')
            
            # 筛选指定目录
            if source_dir and not file_path.startswith(source_dir):
                continue
            
            for qr in result.get('qrcodes', []):
                content = qr.get('content', '')
                
                # 只提取URL类型（以 http 开头）
                if content.startswith('http'):
                    # 从URL中提取报告编号
                    report_no = self.extract_report_no(content)
                    
                    url_qrcodes.append({
                        'source_file': Path(file_path).name,
                        'url': content,
                        'report_no': report_no,
                        'confidence': qr.get('confidence', 0),
                    })
        
        # 去重（基于URL）
        seen_urls = set()
        unique_qrcodes = []
        for qr in url_qrcodes:
            if qr['url'] not in seen_urls:
                seen_urls.add(qr['url'])
                unique_qrcodes.append(qr)
        
        return unique_qrcodes
    
    def extract_report_no(self, url: str) -> str:
        """从URL中提取报告编号"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get('rNo', [''])[0]
    
    def crawl_with_requests(self, url: str) -> Tuple[Dict, bool]:
        """
        使用 requests 爬取页面
        
        Args:
            url: 目标URL
            
        Returns:
            (提取的数据字典, 是否成功获取有效数据)
        """
        data = {}
        success = False
        
        for attempt in range(self.retry_times):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                data = self.parse_report_page(soup)
                
                # 检查是否有有效数据（非"无"值，排除 status 字段）
                data_values = {k: v for k, v in data.items() if k != 'status'}
                valid_values = [v for v in data_values.values() if v and v != '无' and v != '未知']
                if valid_values:
                    success = True
                    break
                else:
                    print(f"  requests 返回空数据，尝试 {attempt + 1}/{self.retry_times}")
                    time.sleep(1)
                    
            except Exception as e:
                print(f"  requests 请求失败: {e}, 尝试 {attempt + 1}/{self.retry_times}")
                time.sleep(1)
        
        return data, success
    
    def parse_report_page(self, soup: BeautifulSoup) -> Dict:
        """
        解析报告页面HTML
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            提取的数据字典
        """
        data = {'status': '未知'}
        
        # 查找报告状态
        status_section = soup.find(string=re.compile('该报告有效'))
        if status_section:
            # 查找状态标签
            status_parent = status_section.parent
            if status_parent:
                # 检查是否被选中（通常有效状态会有特定的样式）
                status_text = status_parent.get_text(strip=True)
                if '有效' in status_text:
                    data['status'] = '有效'
                elif '无效' in status_text:
                    data['status'] = '无效'
        
        # 提取各字段值
        for field_name in self.FIELD_MAPPING.keys():
            value = self.extract_field_value(soup, field_name)
            data[field_name] = value
        
        return data
    
    def extract_field_value(self, soup: BeautifulSoup, field_name: str) -> str:
        """
        提取单个字段值
        
        Args:
            soup: BeautifulSoup对象
            field_name: 字段名称
            
        Returns:
            字段值
        """
        # 查找包含字段名的元素
        field_elem = soup.find(string=re.compile(field_name))
        if not field_elem:
            return '无'
        
        # 字段值通常在同级或下级元素中
        parent = field_elem.parent
        if parent:
            # 查找下一个兄弟元素
            next_elem = parent.find_next_sibling()
            if next_elem:
                value = next_elem.get_text(strip=True)
                if value:
                    return value
            
            # 或者值在同一元素中（如 <p>检测机构：XXX</p>）
            text = parent.get_text(strip=True)
            if field_name in text:
                # 提取冒号后的内容
                parts = text.split(field_name)
                if len(parts) > 1:
                    value = parts[-1].strip()
                    if value.startswith('：') or value.startswith(':'):
                        value = value[1:].strip()
                    return value if value else '无'
        
        return '无'
    
    def extract_download_url(self, driver, original_url: str) -> str:
        """
        从 Selenium driver 中提取报告下载链接
        
        Args:
            driver: Selenium WebDriver 对象
            original_url: 原始查询 URL
            
        Returns:
            下载链接 URL 或 '无'
        """
        try:
            # 获取 testingReportId 和 testingReportNo 变量
            js_vars = driver.execute_script("""
                return {
                    testingReportId: typeof testingReportId !== 'undefined' ? testingReportId : null,
                    testingReportNo: typeof testingReportNo !== 'undefined' ? testingReportNo : null
                };
            """)
            
            r_id = js_vars.get('testingReportId')
            r_no = js_vars.get('testingReportNo')
            
            if r_id and r_no:
                # 调用 /WeChat/GetReportUrl API 获取真正的下载链接
                api_result = driver.execute_script("""
                    return new Promise((resolve, reject) => {
                        var xhr = new XMLHttpRequest();
                        xhr.open('POST', '/WeChat/GetReportUrl', true);
                        xhr.setRequestHeader('Content-Type', 'application/json');
                        xhr.onreadystatechange = function() {
                            if (xhr.readyState === 4) {
                                if (xhr.status === 200) {
                                    try {
                                        var response = JSON.parse(xhr.responseText);
                                        resolve(response);
                                    } catch(e) {
                                        resolve({error: 'parse_error', raw: xhr.responseText});
                                    }
                                } else {
                                    resolve({error: xhr.status});
                                }
                            }
                        };
                        xhr.send(JSON.stringify({testingReportId: testingReportId, testingReportNo: testingReportNo}));
                    });
                """)
                
                # 提取返回的 url 字段
                if api_result and api_result.get('state') == 1 and api_result.get('url'):
                    return api_result.get('url')
                
                # 如果变量不存在，从原始 URL 参数构造 SMSDownload 链接作为备用
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(original_url)
                params = parse_qs(parsed.query)
                url_r_id = params.get('rId', [''])[0]
                url_r_no = params.get('rNo', [''])[0]
                
                if url_r_id and url_r_no:
                    return f"https://zy.jktac.com/WeChat/SMSDownload?rId={url_r_id}&rNo={url_r_no}"
                
        except Exception as e:
            pass
        
        return '无'
    
    def crawl_with_selenium(self, url: str) -> Tuple[Dict, bool]:
        """
        使用 Selenium 爬取页面（备用模式）
        
        Args:
            url: 目标URL
            
        Returns:
            (提取的数据字典, 是否成功)
        """
        if not SELENIUM_SUPPORT:
            return {}, False
        
        data = {}
        success = False
        
        try:
            # 配置 Chrome 选项
            options = Options()
            options.add_argument('--headless')  # 无头模式
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'--user-agent={self.WECHAT_HEADERS["User-Agent"]}')
            
            # 创建 WebDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            try:
                driver.get(url)
                
                # 等待页面加载
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
                
                # 额外等待动态内容加载
                time.sleep(3)
                
                # 提取下载链接（需要在 driver 环境中查找）
                download_url = self.extract_download_url(driver, url)
                
                # 获取页面源码并解析
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                data = self.parse_report_page(soup)
                
                # 添加下载链接
                if download_url:
                    data['报告下载链接'] = download_url
                
                # 检查数据有效性（排除 status 字段）
                data_values = {k: v for k, v in data.items() if k != 'status'}
                valid_values = [v for v in data_values.values() if v and v != '无' and v != '未知']
                success = len(valid_values) > 0
                
            finally:
                driver.quit()
                
        except Exception as e:
            print(f"  Selenium 爬取失败: {e}")
        
        return data, success
    
    def crawl_all(self, qrcode_list: List[Dict], use_selenium_fallback: bool = True) -> List[Dict]:
        """
        爬取所有二维码URL
        
        Args:
            qrcode_list: 二维码信息列表
            use_selenium_fallback: 是否使用 Selenium 备用模式
            
        Returns:
            爬取结果列表
        """
        results = []
        total = len(qrcode_list)
        
        print(f"\n开始爬取 {total} 个URL...")
        print("=" * 60)
        
        for i, qr in enumerate(qrcode_list, 1):
            url = qr['url']
            source_file = qr['source_file']
            report_no = qr['report_no']
            
            print(f"\n[{i}/{total}] {source_file}")
            print(f"  报告编号: {report_no}")
            print(f"  URL: {url}")
            
            result = {
                'source_file': source_file,
                'url': url,
                'report_no': report_no,
                'crawl_mode': None,
                'success': False,
                'data': {},
                'error': None,
            }
            
            # 先尝试 requests
            print("  尝试 requests 模式...")
            data, success = self.crawl_with_requests(url)
            
            if success:
                result['crawl_mode'] = 'requests'
                result['success'] = True
                result['data'] = data
                print(f"  requests 成功!")
            elif use_selenium_fallback and SELENIUM_SUPPORT:
                # 切换到 Selenium
                print("  切换到 Selenium 模式...")
                data, success = self.crawl_with_selenium(url)
                
                if success:
                    result['crawl_mode'] = 'selenium'
                    result['success'] = True
                    result['data'] = data
                    print(f"  Selenium 成功!")
                else:
                    result['error'] = '两种模式均未获取有效数据'
                    print(f"  爬取失败!")
            else:
                result['error'] = 'requests 未获取有效数据'
                result['data'] = data
                print(f"  requests 未获取有效数据")
            
            results.append(result)
        
        return results
    
    def save_results(self, results: List[Dict], output_file: str, source_dir: str = None):
        """
        保存爬取结果到JSON
        
        Args:
            results: 爬取结果列表
            output_file: 输出文件路径
            source_dir: 数据来源目录
        """
        output_data = {
            'crawl_time': datetime.now().isoformat(),
            'source': source_dir or 'unknown',
            'total_urls': len(results),
            'success_count': sum(1 for r in results if r['success']),
            'fail_count': sum(1 for r in results if not r['success']),
            'results': results,
        }
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到: {output_file}")


def print_crawl_summary(results: List[Dict]):
    """打印爬取结果汇总"""
    print("\n" + "=" * 60)
    print("爬取结果汇总")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r['success'])
    fail_count = len(results) - success_count
    
    print(f"总数: {len(results)}")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print("=" * 60)
    
    for result in results:
        if result['success']:
            print(f"\n{result['source_file']} - {result['report_no']}")
            print(f"  模式: {result['crawl_mode']}")
            print("  数据:")
            for key, value in result['data'].items():
                if value and value != '无':
                    print(f"    {key}: {value}")
        else:
            print(f"\n{result['source_file']} - {result['report_no']}")
            print(f"  失败: {result.get('error', '未知错误')}")


def main():
    """主函数"""
    # 配置路径
    qrcode_json = r"d:\code\trytry\results\qrcode_results.json"
    source_dir = r"d:\code\trytry\files_limis"
    output_file = r"d:\code\trytry\results\crawler_results.json"
    
    # 创建爬虫
    crawler = QRCodeCrawler(timeout=30, retry_times=3)
    
    # 加载二维码结果
    print("加载二维码结果...")
    qrcode_list = crawler.load_qrcode_results(qrcode_json, source_dir)
    print(f"找到 {len(qrcode_list)} 个唯一URL:")
    for qr in qrcode_list:
        print(f"  - {qr['source_file']}: {qr['report_no']}")
    
    # 爬取所有URL
    results = crawler.crawl_all(qrcode_list, use_selenium_fallback=True)
    
    # 保存结果
    crawler.save_results(results, output_file, "files_limis")
    
    # 打印汇总
    print_crawl_summary(results)


if __name__ == "__main__":
    main()