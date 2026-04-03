"""
数据库模型 - 定义4张表（完整字段）
"""
from datetime import datetime
from pathlib import Path
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from ..config import DATABASE_URL
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import DATABASE_URL

Base = declarative_base()

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class LimisSinglePage(Base):
    """limis单表 - 每一页图片的数据信息"""
    __tablename__ = "limis_single_pages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    委托编号 = Column(String(100), nullable=True)
    报告编号 = Column(String(100), nullable=True)
    工程名称 = Column(String(500), nullable=True)
    page_number = Column(Integer, default=0, comment="第几页，0表示封面或未知")
    total_pages = Column(Integer, default=0, comment="共几页，0表示未知")
    source_file = Column(String(500), nullable=True, comment="原始文件路径")
    pdf_path = Column(String(500), nullable=True, comment="单页PDF路径")
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_limis_report_page', '报告编号', 'page_number'),
    )


class LimisReport(Base):
    """limis总表 - 完整报告信息（包含所有字段）"""
    __tablename__ = "limis_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    报告编号 = Column(String(100), unique=True, nullable=False, index=True)
    委托编号 = Column(String(100), nullable=True)
    委托日期 = Column(String(50), nullable=True, comment="委托日期/抽样日期")
    报告日期 = Column(String(50), nullable=True, comment="签发日期")
    工程名称 = Column(String(500), nullable=True)
    工程部位 = Column(String(500), nullable=True)
    样品编号 = Column(String(100), nullable=True)
    样品名称 = Column(String(200), nullable=True)
    规格型号 = Column(String(200), nullable=True)
    委托单位 = Column(String(200), nullable=True)
    生产单位 = Column(String(200), nullable=True)
    检测机构 = Column(String(200), nullable=True)
    检验依据 = Column(String(500), nullable=True)
    报告状态 = Column(String(50), nullable=True)
    报告下载链接 = Column(String(500), nullable=True)
    本地PDF路径 = Column(String(500), nullable=True, comment="本地PDF文件路径")
    created_at = Column(DateTime, default=datetime.now)


class ScetiaSinglePage(Base):
    """scetia单表 - 每一页图片的数据信息"""
    __tablename__ = "scetia_single_pages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    委托编号 = Column(String(100), nullable=True)
    报告编号 = Column(String(100), nullable=True)
    工程名称 = Column(String(500), nullable=True)
    page_number = Column(Integer, default=0, comment="第几页，0表示封面或未知")
    total_pages = Column(Integer, default=0, comment="共几页，0表示未知")
    source_file = Column(String(500), nullable=True, comment="原始文件路径")
    pdf_path = Column(String(500), nullable=True, comment="单页PDF路径")
    security_code = Column(String(20), nullable=True, comment="防伪码")
    confidence = Column(Float, nullable=True, comment="识别置信度")
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_scetia_report_page', '报告编号', 'page_number'),
    )


class ScetiaReport(Base):
    """scetia总表 - 完整报告信息（包含所有字段）"""
    __tablename__ = "scetia_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    报告编号 = Column(String(100), unique=True, nullable=False, index=True)
    委托编号 = Column(String(100), nullable=True)
    委托日期 = Column(String(50), nullable=True)
    报告日期 = Column(String(50), nullable=True)
    工程名称 = Column(String(500), nullable=True)
    工程地址 = Column(String(500), nullable=True)
    工程部位 = Column(String(200), nullable=True)
    样品名称 = Column(String(200), nullable=True)
    样品编号 = Column(String(100), nullable=True)
    规格 = Column(String(100), nullable=True)
    强度等级 = Column(String(50), nullable=True)
    委托单位 = Column(String(200), nullable=True)
    施工单位 = Column(String(200), nullable=True)
    生产单位 = Column(String(200), nullable=True)
    检测机构 = Column(String(200), nullable=True)
    检测结论 = Column(String(200), nullable=True)
    样品检测结论 = Column(String(200), nullable=True)
    委托性质 = Column(String(50), nullable=True)
    标段 = Column(String(100), nullable=True)
    取样人及证书号 = Column(String(100), nullable=True)
    见证人及证书号 = Column(String(100), nullable=True)
    防伪码 = Column(String(20), nullable=True)
    本地PDF路径 = Column(String(500), nullable=True, comment="本地PDF文件路径")
    created_at = Column(DateTime, default=datetime.now)


def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成")


if __name__ == "__main__":
    init_db()