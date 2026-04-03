"""
配置文件 - 后端服务配置
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库配置
DATABASE_URL = f"sqlite:///{BASE_DIR}/data.db"

# 上传目录
UPLOAD_DIR = BASE_DIR / "uploads"
MERGED_PDF_DIR = BASE_DIR / "merged_pdfs"

# 确保目录存在
UPLOAD_DIR.mkdir(exist_ok=True)
MERGED_PDF_DIR.mkdir(exist_ok=True)

# API配置
API_PREFIX = "/api"

# AI OCR配置
AI_OCR_API_KEY = os.getenv("AI_OCR_API_KEY", "aa68716a66dd4f249f9a18b8105d8e05.eUnEVgYSIvW5lMqg")
AI_OCR_MODEL = "glm-4v-flash"
AI_OCR_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# limis爬虫配置
LIMIS_TIMEOUT = 30
LIMIS_RETRY_TIMES = 3

# scetia查询配置
SCETIA_QUERY_URL = "http://www.scetia.com/Scetia.OnlineExplorer/App_Public/AntiFakeReportQuery.aspx"
SCETIA_DELAY = 2.0
SCETIA_TIMEOUT = 30

# 文件处理配置
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
PDF_DPI = 200