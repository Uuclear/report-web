"""
数据库CRUD操作（完整字段版本）
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .models import (
    LimisSinglePage, LimisReport,
    ScetiaSinglePage, ScetiaReport
)


# ============ limis单表操作 ============

def create_limis_single_page(
    db: Session,
    委托编号: str = None,
    报告编号: str = None,
    工程名称: str = None,
    page_number: int = 0,
    total_pages: int = 0,
    source_file: str = None,
    pdf_path: str = None
) -> LimisSinglePage:
    """创建limis单页记录"""
    page = LimisSinglePage(
        委托编号=委托编号,
        报告编号=报告编号,
        工程名称=工程名称,
        page_number=page_number,
        total_pages=total_pages,
        source_file=source_file,
        pdf_path=pdf_path
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def get_limis_single_pages_by_report(db: Session, 报告编号: str) -> List[LimisSinglePage]:
    """获取某报告的所有单页"""
    return db.query(LimisSinglePage).filter(
        LimisSinglePage.报告编号 == 报告编号
    ).order_by(LimisSinglePage.page_number).all()


# ============ limis总表操作 ============

def create_limis_report(
    db: Session,
    报告编号: str,
    委托编号: str = None,
    委托日期: str = None,
    报告日期: str = None,
    工程名称: str = None,
    工程部位: str = None,
    样品编号: str = None,
    样品名称: str = None,
    规格型号: str = None,
    委托单位: str = None,
    生产单位: str = None,
    检测机构: str = None,
    检验依据: str = None,
    报告状态: str = None,
    报告下载链接: str = None,
    本地PDF路径: str = None
) -> LimisReport:
    """创建或更新limis报告"""
    report = db.query(LimisReport).filter(LimisReport.报告编号 == 报告编号).first()
    
    if report:
        if 委托编号: report.委托编号 = 委托编号
        if 委托日期: report.委托日期 = 委托日期
        if 报告日期: report.报告日期 = 报告日期
        if 工程名称: report.工程名称 = 工程名称
        if 工程部位: report.工程部位 = 工程部位
        if 样品编号: report.样品编号 = 样品编号
        if 样品名称: report.样品名称 = 样品名称
        if 规格型号: report.规格型号 = 规格型号
        if 委托单位: report.委托单位 = 委托单位
        if 生产单位: report.生产单位 = 生产单位
        if 检测机构: report.检测机构 = 检测机构
        if 检验依据: report.检验依据 = 检验依据
        if 报告状态: report.报告状态 = 报告状态
        if 报告下载链接: report.报告下载链接 = 报告下载链接
        if 本地PDF路径: report.本地PDF路径 = 本地PDF路径
    else:
        report = LimisReport(
            报告编号=报告编号,
            委托编号=委托编号,
            委托日期=委托日期,
            报告日期=报告日期,
            工程名称=工程名称,
            工程部位=工程部位,
            样品编号=样品编号,
            样品名称=样品名称,
            规格型号=规格型号,
            委托单位=委托单位,
            生产单位=生产单位,
            检测机构=检测机构,
            检验依据=检验依据,
            报告状态=报告状态,
            报告下载链接=报告下载链接,
            本地PDF路径=本地PDF路径
        )
        db.add(report)
    
    db.commit()
    db.refresh(report)
    return report


def get_limis_reports(
    db: Session,
    工程名称: str = None,
    样品名称: str = None
) -> List[LimisReport]:
    """查询limis报告"""
    query = db.query(LimisReport)
    
    if 工程名称:
        query = query.filter(LimisReport.工程名称.contains(工程名称))
    if 样品名称:
        query = query.filter(LimisReport.样品名称.contains(样品名称))
    
    return query.order_by(LimisReport.created_at.desc()).all()


# ============ scetia单表操作 ============

def create_scetia_single_page(
    db: Session,
    委托编号: str = None,
    报告编号: str = None,
    工程名称: str = None,
    page_number: int = 0,
    total_pages: int = 0,
    source_file: str = None,
    pdf_path: str = None,
    security_code: str = None,
    confidence: float = None
) -> ScetiaSinglePage:
    """创建scetia单页记录"""
    page = ScetiaSinglePage(
        委托编号=委托编号,
        报告编号=报告编号,
        工程名称=工程名称,
        page_number=page_number,
        total_pages=total_pages,
        source_file=source_file,
        pdf_path=pdf_path,
        security_code=security_code,
        confidence=confidence
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def get_scetia_single_pages_by_report(db: Session, 报告编号: str) -> List[ScetiaSinglePage]:
    """获取某报告的所有单页"""
    return db.query(ScetiaSinglePage).filter(
        ScetiaSinglePage.报告编号 == 报告编号
    ).order_by(ScetiaSinglePage.page_number).all()


# ============ scetia总表操作 ============

def create_scetia_report(
    db: Session,
    报告编号: str,
    委托编号: str = None,
    委托日期: str = None,
    报告日期: str = None,
    工程名称: str = None,
    工程地址: str = None,
    工程部位: str = None,
    样品名称: str = None,
    样品编号: str = None,
    规格: str = None,
    强度等级: str = None,
    委托单位: str = None,
    施工单位: str = None,
    生产单位: str = None,
    检测机构: str = None,
    检测结论: str = None,
    样品检测结论: str = None,
    委托性质: str = None,
    标段: str = None,
    取样人及证书号: str = None,
    见证人及证书号: str = None,
    防伪码: str = None,
    本地PDF路径: str = None
) -> ScetiaReport:
    """创建或更新scetia报告"""
    report = db.query(ScetiaReport).filter(ScetiaReport.报告编号 == 报告编号).first()
    
    if report:
        if 委托编号: report.委托编号 = 委托编号
        if 委托日期: report.委托日期 = 委托日期
        if 报告日期: report.报告日期 = 报告日期
        if 工程名称: report.工程名称 = 工程名称
        if 工程地址: report.工程地址 = 工程地址
        if 工程部位: report.工程部位 = 工程部位
        if 样品名称: report.样品名称 = 样品名称
        if 样品编号: report.样品编号 = 样品编号
        if 规格: report.规格 = 规格
        if 强度等级: report.强度等级 = 强度等级
        if 委托单位: report.委托单位 = 委托单位
        if 施工单位: report.施工单位 = 施工单位
        if 生产单位: report.生产单位 = 生产单位
        if 检测机构: report.检测机构 = 检测机构
        if 检测结论: report.检测结论 = 检测结论
        if 样品检测结论: report.样品检测结论 = 样品检测结论
        if 委托性质: report.委托性质 = 委托性质
        if 标段: report.标段 = 标段
        if 取样人及证书号: report.取样人及证书号 = 取样人及证书号
        if 见证人及证书号: report.见证人及证书号 = 见证人及证书号
        if 防伪码: report.防伪码 = 防伪码
        if 本地PDF路径: report.本地PDF路径 = 本地PDF路径
    else:
        report = ScetiaReport(
            报告编号=报告编号,
            委托编号=委托编号,
            委托日期=委托日期,
            报告日期=报告日期,
            工程名称=工程名称,
            工程地址=工程地址,
            工程部位=工程部位,
            样品名称=样品名称,
            样品编号=样品编号,
            规格=规格,
            强度等级=强度等级,
            委托单位=委托单位,
            施工单位=施工单位,
            生产单位=生产单位,
            检测机构=检测机构,
            检测结论=检测结论,
            样品检测结论=样品检测结论,
            委托性质=委托性质,
            标段=标段,
            取样人及证书号=取样人及证书号,
            见证人及证书号=见证人及证书号,
            防伪码=防伪码,
            本地PDF路径=本地PDF路径
        )
        db.add(report)
    
    db.commit()
    db.refresh(report)
    return report


def get_scetia_reports(
    db: Session,
    工程名称: str = None,
    样品名称: str = None
) -> List[ScetiaReport]:
    """查询scetia报告"""
    query = db.query(ScetiaReport)
    
    if 工程名称:
        query = query.filter(ScetiaReport.工程名称.contains(工程名称))
    if 样品名称:
        query = query.filter(ScetiaReport.样品名称.contains(样品名称))
    
    return query.order_by(ScetiaReport.created_at.desc()).all()


# ============ 交集查询 ============

def get_intersection_reports(
    db: Session,
    工程名称: str = None,
    样品名称: str = None
) -> List[Dict[str, Any]]:
    """查询limis和scetia的交集报告"""
    limis_reports = get_limis_reports(db, 工程名称=工程名称, 样品名称=样品名称)
    scetia_reports = get_scetia_reports(db, 工程名称=工程名称, 样品名称=样品名称)
    
    limis_numbers = {r.报告编号 for r in limis_reports}
    scetia_numbers = {r.报告编号 for r in scetia_reports}
    
    intersection_numbers = limis_numbers & scetia_numbers
    
    results = []
    for report_no in intersection_numbers:
        limis = next((r for r in limis_reports if r.报告编号 == report_no), None)
        scetia = next((r for r in scetia_reports if r.报告编号 == report_no), None)
        
        if limis and scetia:
            results.append({
                "报告编号": report_no,
                "委托编号": limis.委托编号 or scetia.委托编号,
                "工程名称": limis.工程名称 or scetia.工程名称,
                "样品名称": limis.样品名称 or scetia.样品名称,
                "来源": "both",
                "limis": limis,
                "scetia": scetia
            })
    
    return results


def get_all_reports_combined(
    db: Session,
    工程名称: str = None,
    样品名称: str = None
) -> List[Dict[str, Any]]:
    """查询所有报告（包含交集和单独的报告）"""
    intersection = get_intersection_reports(db, 工程名称, 样品名称)
    limis_reports = get_limis_reports(db, 工程名称=工程名称, 样品名称=样品名称)
    scetia_reports = get_scetia_reports(db, 工程名称=工程名称, 样品名称=样品名称)
    
    intersection_numbers = {r["报告编号"] for r in intersection}
    results = list(intersection)
    
    for r in limis_reports:
        if r.报告编号 not in intersection_numbers:
            results.append({
                "报告编号": r.报告编号,
                "委托编号": r.委托编号,
                "工程名称": r.工程名称,
                "样品名称": r.样品名称,
                "来源": "limis",
                "limis": r,
                "scetia": None
            })
    
    for r in scetia_reports:
        if r.报告编号 not in intersection_numbers:
            results.append({
                "报告编号": r.报告编号,
                "委托编号": r.委托编号,
                "工程名称": r.工程名称,
                "样品名称": r.样品名称,
                "来源": "scetia",
                "limis": None,
                "scetia": r
            })
    
    return results


def _limis_query_portal_url(r: LimisReport) -> str:
    """协会 Limis 报告查询页：优先已存的完整 URL，否则仅带报告编号"""
    from urllib.parse import quote

    link = (r.报告下载链接 or "").strip()
    if link.startswith("http"):
        return link
    return f"https://zy.jktac.com/WeChat/rQuery?rNo={quote(r.报告编号 or '', safe='')}"


def limis_to_dict(r: LimisReport) -> dict:
    """将LimisReport对象转换为字典"""
    from urllib.parse import quote

    enc = quote(r.报告编号 or "", safe="")
    return {
        "id": r.id,
        "报告编号": r.报告编号,
        "委托编号": r.委托编号,
        "委托日期": r.委托日期,
        "报告日期": r.报告日期,
        # 前端曾用「签发日期」展示；库中统一为「报告日期」（对应爬虫「签发日期」）
        "签发日期": r.报告日期,
        "工程名称": r.工程名称,
        "工程部位": r.工程部位,
        "样品编号": r.样品编号,
        "样品名称": r.样品名称,
        "规格型号": r.规格型号,
        "委托单位": r.委托单位,
        "生产单位": r.生产单位,
        "检测机构": r.检测机构,
        "检验依据": r.检验依据,
        "报告状态": r.报告状态,
        "报告下载链接": r.报告下载链接,
        "本地PDF路径": r.本地PDF路径,
        # 相对 API 路径，前端拼 API_BASE
        "pdf_download_path": f"/api/files/limis/{enc}/download",
        "query_portal_url": _limis_query_portal_url(r),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def scetia_to_dict(r: ScetiaReport) -> dict:
    """将ScetiaReport对象转换为字典"""
    from urllib.parse import quote

    try:
        from config import SCETIA_QUERY_URL
    except ImportError:
        SCETIA_QUERY_URL = "http://www.scetia.com/Scetia.OnlineExplorer/App_Public/AntiFakeReportQuery.aspx"

    enc = quote(r.报告编号 or "", safe="")
    return {
        "id": r.id,
        "报告编号": r.报告编号,
        "委托编号": r.委托编号,
        "委托日期": r.委托日期,
        "报告日期": r.报告日期,
        "工程名称": r.工程名称,
        "工程地址": r.工程地址,
        "工程部位": r.工程部位,
        "样品名称": r.样品名称,
        "样品编号": r.样品编号,
        "规格": r.规格,
        "强度等级": r.强度等级,
        "委托单位": r.委托单位,
        "施工单位": r.施工单位,
        "生产单位": r.生产单位,
        "检测机构": r.检测机构,
        "检测结论": r.检测结论,
        "样品检测结论": r.样品检测结论,
        "委托性质": r.委托性质,
        "标段": r.标段,
        "取样人及证书号": r.取样人及证书号,
        "见证人及证书号": r.见证人及证书号,
        "防伪码": r.防伪码,
        "本地PDF路径": r.本地PDF路径,
        "pdf_download_path": f"/api/files/scetia/{enc}/download",
        "query_portal_url": SCETIA_QUERY_URL,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }