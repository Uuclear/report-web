"""
查询接口 - 结果查询（完整字段版本）
筛选：按「报告日期」区间、数据来源（all/limis/scetia/both）
"""
import re
from datetime import date, datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Query, HTTPException

from database import SessionLocal
from database.crud import (
    get_limis_reports,
    get_scetia_reports,
    get_intersection_reports,
    get_all_reports_combined,
    limis_to_dict,
    scetia_to_dict,
)

router = APIRouter()


def _parse_report_date_string(s: Optional[str]) -> Optional[date]:
    """解析库中各类日期字符串为 date，失败返回 None"""
    if not s or not str(s).strip():
        return None
    s = str(s).strip()
    if s in ("-", "—", "无", "未知"):
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s[:10].replace("/", "-").replace(".", "-"), "%Y-%m-%d").date()
        except ValueError:
            continue
    m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _effective_report_date_for_filter(row: Dict[str, Any]) -> Optional[date]:
    """
    用于筛选的「报告日期」：有 Limis 用 Limis 的报告日期，否则用 Scetia。
    两边都有时以 Limis 为准（与业务「主站」一致）。
    """
    limis = row.get("limis")
    scetia = row.get("scetia")
    if limis and getattr(limis, "报告日期", None):
        return _parse_report_date_string(limis.报告日期)
    if scetia and getattr(scetia, "报告日期", None):
        return _parse_report_date_string(scetia.报告日期)
    return None


def _row_in_report_date_range(
    row: Dict[str, Any],
    start: Optional[date],
    end: Optional[date],
) -> bool:
    if not start and not end:
        return True
    d = _effective_report_date_for_filter(row)
    if d is None:
        return True  # 无日期或无法解析时不过滤掉
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True


def _row_matches_source(row: Dict[str, Any], data_source: Optional[str]) -> bool:
    if not data_source or data_source == "all":
        return True
    src = row.get("来源") or ""
    return src == data_source


def _report_date_display(row: Dict[str, Any]) -> str:
    """表格展示用"""
    parts = []
    limis = row.get("limis")
    scetia = row.get("scetia")
    if limis and getattr(limis, "报告日期", None):
        parts.append(f"Limis {limis.报告日期}")
    if scetia and getattr(scetia, "报告日期", None):
        parts.append(f"Scetia {scetia.报告日期}")
    return " / ".join(parts) if parts else "-"


def _apply_filters(
    rows: List[Dict[str, Any]],
    start_date: Optional[str],
    end_date: Optional[str],
    data_source: Optional[str],
) -> List[Dict[str, Any]]:
    start_d = _parse_report_date_string(start_date) if start_date else None
    end_d = _parse_report_date_string(end_date) if end_date else None

    out = []
    for row in rows:
        if not _row_matches_source(row, data_source):
            continue
        if not _row_in_report_date_range(row, start_d, end_d):
            continue
        out.append(row)
    return out


@router.get("/intersection")
async def query_intersection(
    project_name: Optional[str] = Query(None, description="工程名称"),
    sample_name: Optional[str] = Query(None, description="样品名称"),
    start_date: Optional[str] = Query(None, description="报告日期起 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="报告日期止 YYYY-MM-DD"),
    data_source: Optional[str] = Query(None, description="数据来源 all/limis/scetia/both"),
):
    """查询limis和scetia的交集报告"""
    db = SessionLocal()

    try:
        results = get_intersection_reports(db, 工程名称=project_name, 样品名称=sample_name)
        results = _apply_filters(results, start_date, end_date, data_source)

        output = []
        for r in results:
            limis_data = limis_to_dict(r["limis"]) if r["limis"] else None
            scetia_data = scetia_to_dict(r["scetia"]) if r["scetia"] else None

            output.append(
                {
                    "报告编号": r["报告编号"],
                    "委托编号": r["委托编号"],
                    "工程名称": r["工程名称"],
                    "样品名称": r["样品名称"],
                    "来源": r["来源"],
                    "报告日期展示": _report_date_display(r),
                    "limis": limis_data,
                    "scetia": scetia_data,
                }
            )

        return {"total": len(output), "results": output}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/all")
async def query_all(
    project_name: Optional[str] = Query(None, description="工程名称"),
    sample_name: Optional[str] = Query(None, description="样品名称"),
    start_date: Optional[str] = Query(None, description="报告日期起（按库中报告日期）"),
    end_date: Optional[str] = Query(None, description="报告日期止"),
    data_source: Optional[str] = Query(
        None,
        description="数据来源：all | limis | scetia | both(仅交集)",
    ),
):
    """查询所有报告，支持按报告日期区间与来源筛选"""
    db = SessionLocal()

    try:
        results = get_all_reports_combined(db, 工程名称=project_name, 样品名称=sample_name)
        results = _apply_filters(results, start_date, end_date, data_source)

        output = []
        for r in results:
            limis_data = limis_to_dict(r["limis"]) if r.get("limis") else None
            scetia_data = scetia_to_dict(r["scetia"]) if r.get("scetia") else None

            output.append(
                {
                    "报告编号": r["报告编号"],
                    "委托编号": r["委托编号"],
                    "工程名称": r["工程名称"],
                    "样品名称": r["样品名称"],
                    "来源": r.get("来源", "both"),
                    "报告日期展示": _report_date_display(r),
                    "limis": limis_data,
                    "scetia": scetia_data,
                }
            )

        return {"total": len(output), "results": output}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/limis")
async def query_limis(
    project_name: Optional[str] = Query(None, description="工程名称"),
    sample_name: Optional[str] = Query(None, description="样品名称"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """查询limis报告"""
    db = SessionLocal()

    try:
        reports = get_limis_reports(db, 工程名称=project_name, 样品名称=sample_name)
        start_d = _parse_report_date_string(start_date) if start_date else None
        end_d = _parse_report_date_string(end_date) if end_date else None
        results = []
        for r in reports:
            row = {"limis": r, "scetia": None, "来源": "limis"}
            if not _row_in_report_date_range(row, start_d, end_d):
                continue
            results.append(limis_to_dict(r))

        return {"total": len(results), "results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/scetia")
async def query_scetia(
    project_name: Optional[str] = Query(None, description="工程名称"),
    sample_name: Optional[str] = Query(None, description="样品名称"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """查询scetia报告"""
    db = SessionLocal()

    try:
        reports = get_scetia_reports(db, 工程名称=project_name, 样品名称=sample_name)
        results = []
        start_d = _parse_report_date_string(start_date) if start_date else None
        end_d = _parse_report_date_string(end_date) if end_date else None
        for r in reports:
            if not _row_in_report_date_range(
                {"limis": None, "scetia": r, "来源": "scetia"},
                start_d,
                end_d,
            ):
                continue
            results.append(scetia_to_dict(r))

        return {"total": len(results), "results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/statistics")
async def get_statistics():
    """获取统计信息"""
    db = SessionLocal()

    try:
        limis_reports = get_limis_reports(db)
        scetia_reports = get_scetia_reports(db)
        intersection = get_intersection_reports(db)

        return {
            "limis_total": len(limis_reports),
            "scetia_total": len(scetia_reports),
            "intersection_total": len(intersection),
            "unique_reports": len(limis_reports) + len(scetia_reports) - len(intersection),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
