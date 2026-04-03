"""
limis爬虫服务 - 从二维码URL爬取检测报告信息
支持：微信 UA / 桌面 Chrome UA、正则兜底、URL 中的 rNo 回填报告编号
"""
import re
import asyncio
import aiohttp
from typing import Dict, Tuple
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup

from config import LIMIS_TIMEOUT, LIMIS_RETRY_TIMES


class LimisCrawlerService:
    """limis爬虫服务"""

    WECHAT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36 "
            "MicroMessenger/8.0.38.2400(0x28003858) Process/tools WeChat/arm64 "
            "Weixin NetType/WIFI Language/zh_CN ABI/arm64"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        # 避免 br 解压异常，仅用 gzip/deflate
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    DESKTOP_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }

    FIELD_MAPPING = {
        "检测机构": "testing_org",
        "报告编号": "report_no",
        "签发日期": "issue_date",
        "委托编号": "request_no",
        "委托日期/抽样日期": "request_date",
        "委托单位": "client",
        "工程名称": "project_name",
        "工程部位": "project_location",
        "样品编号": "sample_no",
        "样品名称": "sample_name",
        "规格型号": "specification",
        "生产单位": "manufacturer",
        "检验依据": "test_basis",
    }

    def __init__(self, timeout: int = LIMIS_TIMEOUT, retry_times: int = LIMIS_RETRY_TIMES):
        self.timeout = timeout
        self.retry_times = retry_times

    def extract_report_no(self, url: str) -> str:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get("rNo", [""])[0]

    def _has_valid_data(self, data: Dict) -> bool:
        """是否解析到可用业务字段（status=有效/无效 也算）"""
        for k, v in data.items():
            if k == "status":
                if v in ("有效", "无效"):
                    return True
                continue
            if v is None:
                continue
            s = str(v).strip()
            if s and s not in ("无", "未知"):
                return True
        return False

    def enrich_from_url(self, data: Dict, report_no_url: str) -> None:
        """二维码 URL 中的 rNo 与页面「报告编号」一致，优先回填"""
        if not report_no_url:
            return
        cur = data.get("报告编号")
        if not cur or cur in ("无", "未知", ""):
            data["报告编号"] = report_no_url

    # 用于判断「值里混进了其它字段标签」
    _OTHER_LABEL_MARKERS = (
        "报告编号",
        "签发日期",
        "委托编号",
        "委托日期",
        "抽样日期",
        "委托单位",
        "工程名称",
        "工程部位",
        "样品编号",
        "样品名称",
        "规格型号",
        "生产单位",
        "检测机构",
        "检验依据",
    )

    def _too_long_or_mixed(self, value: str, field_name: str) -> bool:
        """值过长或包含多个其它字段名时视为解析错误，交给正则重试。"""
        if not value or value in ("无", "未知"):
            return False
        if len(value) > 160:
            return True
        hits = 0
        for m in self._OTHER_LABEL_MARKERS:
            if m != field_name and m in value:
                hits += 1
        return hits >= 2

    def _clean_trailing_labels(self, value: str, field_name: str) -> str:
        """若整段文本被误合并，截断到下一个「字段名：」之前。"""
        if not value or value in ("无", "未知"):
            return value
        cut = len(value)
        for lab in self.FIELD_MAPPING.keys():
            if lab == field_name:
                continue
            for sep in (f"{lab}：", f"{lab}:", f"{lab} "):
                pos = value.find(sep)
                if 0 < pos < cut:
                    cut = pos
        out = value[:cut].strip()
        # 去掉本字段名前缀重复
        for sep in (f"{field_name}：", f"{field_name}:", field_name):
            if out.startswith(sep):
                out = out[len(sep) :].strip()
        return out if out else "无"

    def enrich_from_regex(self, html: str, soup: BeautifulSoup, data: Dict) -> None:
        """DOM 解析失败时，从全文用正则兜底"""
        try:
            text = soup.get_text(separator="\n", strip=True)
        except Exception:
            text = html
        text_one = re.sub(r"\s+", " ", text)

        patterns = [
            ("报告编号", r"报告编号[：:\s]*([A-Za-z0-9\-]+)"),
            ("委托编号", r"委托编号[：:\s]*([A-Za-z0-9\-]+)"),
            (
                "签发日期",
                r"(?:签发日期|报告日期)[：:\s]*([\d\-\s年月日\.]+)",
            ),
            (
                "委托日期/抽样日期",
                r"(?:委托日期|抽样日期)[/／]?(?:抽样日期)?[：:\s]*([\d\-\s年月日\.]+)",
            ),
            ("委托单位", r"委托单位[：:\s]*([^\n]{1,160})"),
            ("工程名称", r"工程名称[：:\s]*([^\n]{1,240})"),
            ("工程部位", r"工程部位[：:\s]*([^\n]{1,160})"),
            ("样品编号", r"样品编号[：:\s]*([^\n]{1,80})"),
            ("样品名称", r"样品名称[：:\s]*([^\n]{1,160})"),
            ("规格型号", r"规格型号[：:\s]*([^\n]{1,120})"),
            ("生产单位", r"生产单位[：:\s]*([^\n]{1,160})"),
            ("检测机构", r"检测机构[：:\s]*([^\n]{1,200})"),
            ("检验依据", r"检验依据[：:\s]*([^\n]{1,300})"),
        ]
        for key, pat in patterns:
            cur = data.get(key)
            cur_s = "" if cur is None else str(cur).strip()
            if cur_s and cur_s not in ("无", "未知") and not self._too_long_or_mixed(cur_s, key):
                continue
            m = re.search(pat, text_one)
            if m:
                val = m.group(1).strip()
                if val and val != "无":
                    data[key] = val[:2000]

        # 报告状态
        if data.get("status") == "未知":
            if re.search(r"该报告有效|报告状态[^\n]{0,8}有效|检验结论.*合格", text_one):
                data["status"] = "有效"
            elif re.search(r"该报告无效|报告已失效|检验结论.*不合格", text_one):
                data["status"] = "无效"

    def parse_report_page(self, soup: BeautifulSoup) -> Dict:
        data = {"status": "未知"}

        # 状态：多种文案
        body_text = ""
        try:
            body_text = soup.get_text(separator=" ", strip=True)
        except Exception:
            pass
        if re.search(r"该报告有效|报告有效", body_text) and "无效" not in body_text[:500]:
            data["status"] = "有效"
        elif re.search(r"该报告无效|报告无效|已失效", body_text):
            data["status"] = "无效"
        else:
            status_section = soup.find(string=re.compile("该报告有效|报告状态"))
            if status_section and status_section.parent:
                t = status_section.parent.get_text(strip=True)
                if "有效" in t:
                    data["status"] = "有效"
                elif "无效" in t:
                    data["status"] = "无效"

        for field_name in self.FIELD_MAPPING.keys():
            data[field_name] = self.extract_field_value(soup, field_name)

        return data

    def extract_field_value(self, soup: BeautifulSoup, field_name: str) -> str:
        if field_name == "委托日期/抽样日期":
            field_elem = soup.find(string=re.compile(r"委托日期\s*/\s*抽样日期|委托日期|抽样日期"))
        elif field_name == "签发日期":
            # 页面上常见「报告日期」与签发日期同义
            field_elem = soup.find(string=re.compile(r"签发日期|报告日期"))
        else:
            field_elem = soup.find(string=re.compile(re.escape(field_name)))

        if not field_elem:
            return "无"

        parent = field_elem.parent
        if parent:
            next_elem = parent.find_next_sibling()
            if next_elem:
                value = next_elem.get_text(strip=True)
                if value:
                    value = self._clean_trailing_labels(value, field_name)
                    if self._too_long_or_mixed(value, field_name):
                        return "无"
                    return value

            text = parent.get_text(strip=True)
            if field_name == "签发日期" and ("签发日期" in text or "报告日期" in text):
                for split_lab in ("签发日期", "报告日期"):
                    if split_lab not in text:
                        continue
                    parts = re.split(re.escape(split_lab), text, maxsplit=1)
                    if len(parts) > 1:
                        value = parts[-1].strip()
                        if value.startswith("：") or value.startswith(":"):
                            value = value[1:].strip()
                        value = self._clean_trailing_labels(value, field_name)
                        if self._too_long_or_mixed(value, field_name):
                            return "无"
                        return value if value else "无"
            elif field_name in text or (
                field_name == "委托日期/抽样日期" and ("委托日期" in text or "抽样日期" in text)
            ):
                parts = re.split(re.escape(field_name), text, maxsplit=1)
                if len(parts) > 1:
                    value = parts[-1].strip()
                    if value.startswith("：") or value.startswith(":"):
                        value = value[1:].strip()
                    value = self._clean_trailing_labels(value, field_name)
                    if self._too_long_or_mixed(value, field_name):
                        return "无"
                    return value if value else "无"

        return "无"

    async def crawl_url(self, url: str) -> Tuple[Dict, bool]:
        report_no_url = self.extract_report_no(url)
        data: Dict = {}
        last_html = ""
        success = False

        header_sets = [
            ("wechat", self.WECHAT_HEADERS),
            ("desktop", self.DESKTOP_HEADERS),
        ]

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        for hname, headers in header_sets:
            for attempt in range(self.retry_times):
                try:
                    connector = aiohttp.TCPConnector(limit=1, ssl=True)
                    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
                        async with session.get(url, timeout=timeout, allow_redirects=True) as response:
                            if response.status != 200:
                                print(f"[LIMIS] {hname} HTTP {response.status} (第{attempt + 1}次)")
                                await asyncio.sleep(0.6)
                                continue

                            last_html = await response.text()
                            if len(last_html) < 100:
                                print(f"[LIMIS] {hname} 响应过短 len={len(last_html)}")
                                await asyncio.sleep(0.6)
                                continue

                            soup = BeautifulSoup(last_html, "html.parser")
                            data = self.parse_report_page(soup)
                            self.enrich_from_url(data, report_no_url)
                            self.enrich_from_regex(last_html, soup, data)

                            if self._has_valid_data(data):
                                success = True
                                print(f"[LIMIS] 爬取成功 ua={hname} attempt={attempt + 1}")
                                return data, success

                            print(
                                f"[LIMIS] {hname} 解析无有效字段，重试 "
                                f"{attempt + 1}/{self.retry_times}，html≈{len(last_html)}"
                            )
                except asyncio.TimeoutError:
                    print(f"[LIMIS] {hname} 超时 attempt={attempt + 1}")
                except Exception as e:
                    print(f"[LIMIS] {hname} 异常: {e} attempt={attempt + 1}")

                await asyncio.sleep(0.8)

        # 最后一轮：用最后一次 HTML 再合并一次
        if last_html:
            soup = BeautifulSoup(last_html, "html.parser")
            if not data:
                data = self.parse_report_page(soup)
            self.enrich_from_url(data, report_no_url)
            self.enrich_from_regex(last_html, soup, data)
            success = self._has_valid_data(data)
            if not success and report_no_url:
                # 至少保证有报告编号，便于前端展示 / 走 AI 时有编号
                data.setdefault("报告编号", report_no_url)
                data.setdefault("status", "未知")
                success = True
                print("[LIMIS] 仅保留 URL 中报告编号，页面字段未完全解析")

        return data, success

    async def get_report_data(self, url: str) -> Dict:
        data, success = await self.crawl_url(url)
        report_no = self.extract_report_no(url)
        if data.get("报告编号") in (None, "", "无"):
            data["报告编号"] = report_no

        return {
            "report_no": report_no,
            "url": url,
            "success": success,
            "data": data,
        }
