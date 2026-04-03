"""
WebSocket接口 - 实时进度推送
"""
import json
import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活动连接: {file_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, file_id: str = "default"):
        """接受连接"""
        await websocket.accept()
        
        if file_id not in self.active_connections:
            self.active_connections[file_id] = set()
        
        self.active_connections[file_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, file_id: str = "default"):
        """断开连接"""
        if file_id in self.active_connections:
            self.active_connections[file_id].discard(websocket)
            
            if not self.active_connections[file_id]:
                del self.active_connections[file_id]
    
    async def send_message(self, message: dict, file_id: str = "default"):
        """发送消息给特定file_id的所有连接"""
        if file_id not in self.active_connections:
            return
        
        message_json = json.dumps(message, ensure_ascii=False)
        
        dead_connections = set()
        
        for connection in self.active_connections[file_id]:
            try:
                await connection.send_text(message_json)
            except Exception:
                dead_connections.add(connection)
        
        # 清理断开的连接
        for connection in dead_connections:
            self.disconnect(connection, file_id)
    
    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        message_json = json.dumps(message, ensure_ascii=False)
        
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_text(message_json)
                except Exception:
                    pass


# 全局连接管理器
manager = ConnectionManager()

# 进度存储
progress_data: Dict[str, dict] = {}


def update_progress(file_id: str, progress: int, total: int, status: str, message: str = None, data: dict = None):
    """
    更新进度
    
    Args:
        file_id: 文件ID
        progress: 当前进度
        total: 总数
        status: 状态 (pending, processing, completed, failed)
        message: 消息
        data: 额外数据
    """
    progress_data[file_id] = {
        "file_id": file_id,
        "progress": progress,
        "total": total,
        "status": status,
        "message": message,
        "data": data
    }


async def notify_progress(file_id: str):
    """通知进度更新"""
    if file_id in progress_data:
        await manager.send_message(progress_data[file_id], file_id)


@router.websocket("/progress/{file_id}")
async def websocket_progress(websocket: WebSocket, file_id: str):
    """
    WebSocket进度推送
    
    客户端连接后可接收处理进度更新
    """
    await manager.connect(websocket, file_id)
    
    try:
        # 发送当前进度
        if file_id in progress_data:
            await websocket.send_text(json.dumps(progress_data[file_id], ensure_ascii=False))
        else:
            await websocket.send_text(json.dumps({
                "file_id": file_id,
                "status": "waiting",
                "message": "等待处理开始"
            }, ensure_ascii=False))
        
        # 保持连接，接收客户端消息
        while True:
            data = await websocket.receive_text()
            
            # 处理客户端请求
            try:
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                
                elif message.get("type") == "get_progress":
                    if file_id in progress_data:
                        await websocket.send_text(json.dumps(progress_data[file_id], ensure_ascii=False))
            
            except json.JSONDecodeError:
                pass
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, file_id)


@router.websocket("/scan")
async def websocket_scan(websocket: WebSocket):
    """
    WebSocket扫描接口
    
    接收图片数据，实时返回识别结果
    """
    await manager.connect(websocket, "scan")
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "image":
                    # 处理图片（base64编码）
                    # TODO: 实现实时图片处理
                    await websocket.send_text(json.dumps({
                        "type": "result",
                        "status": "processing",
                        "message": "正在识别..."
                    }, ensure_ascii=False))
                
                elif message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "无效的消息格式"
                }, ensure_ascii=False))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, "scan")


@router.get("/connections")
async def get_active_connections():
    """获取活动连接数"""
    total = sum(len(conns) for conns in manager.active_connections.values())
    return {
        "total_connections": total,
        "files": list(manager.active_connections.keys())
    }