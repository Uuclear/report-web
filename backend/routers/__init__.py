"""
路由模块初始化
"""
from .scan import router as scan_router
from .upload import router as upload_router
from .query import router as query_router
from .websocket import router as websocket_router

# 直接导出router对象
router = scan_router  # 默认导出scan router