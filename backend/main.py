"""
FastAPI 主入口
"""
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import API_PREFIX
from database import init_db
from routers import scan, upload, query, websocket, files


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    init_db()
    yield
    # 关闭时清理资源


app = FastAPI(
    title="文档扫描管理系统",
    description="支持摄像头扫描、批量上传、二维码识别、AI OCR、数据库存储和结果查询",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(scan.router, prefix=f"{API_PREFIX}/scan", tags=["扫描"])
app.include_router(upload.router, prefix=f"{API_PREFIX}/upload", tags=["上传"])
app.include_router(query.router, prefix=f"{API_PREFIX}/query", tags=["查询"])
app.include_router(files.router, prefix=f"{API_PREFIX}/files", tags=["文件"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


@app.get("/")
async def root():
    return {"message": "文档扫描管理系统 API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}