# Report Web（文档扫描 / 检测报告管理）

面向检测报告（Limis / Scetia）的 Web 应用：摄像头与批量上传、二维码识别、在线爬取/查询、AI OCR 兜底、SQLite 存储与结果查询（含报告日期筛选、数据来源、PDF 与查询页链接）。

**仓库**：<https://github.com/Uuclear/report-web>

---

## 功能概览

| 模块 | 说明 |
|------|------|
| 扫描文档 | 上传图片/PDF，识别二维码，Limis URL 爬取或 Scetia 查询，失败时 AI OCR |
| 上传文档 | 批量上传、进度轮询、识别结果展开查看 |
| 结果查询 | 按**报告日期**区间、工程/样品、**数据来源**筛选；本地 PDF 优先、在线链接补充；查询页直达 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12（建议）、FastAPI、Uvicorn、SQLAlchemy、SQLite、aiohttp |
| 前端 | React 18、TypeScript、Vite、TailwindCSS、React Router |
| 能力 | 二维码（qreader/OpenCV）、智谱 GLM-4V-Flash（OCR）、BeautifulSoup 爬取 |

---

## 仓库结构

```
.
├── backend/                 # FastAPI 服务
│   ├── main.py              # 入口
│   ├── config.py            # 配置（数据库路径、API 等）
│   ├── database/            # 模型与 CRUD
│   ├── routers/             # scan / upload / query / files
│   ├── services/            # 爬虫、OCR、扫描等
│   └── requirements.txt
├── frontend/                # Vite + React
│   ├── src/
│   └── package.json
├── uploads/                 # 运行时上传目录（已 .gitignore）
├── merged_pdfs/             # 合并 PDF（已 .gitignore）
├── files_limis/、files_scetia/  # 本地样本（默认 .gitignore，避免大文件进仓库）
├── data.db                  # SQLite（已 .gitignore，首次启动自动创建）
├── start_backend.bat        # Windows：启动后端 :8080
├── start_frontend.bat       # Windows：启动前端 :3000
├── .env.example             # 环境变量示例
├── .gitignore
└── README.md
```

---

## 本地开发（完整流程）

### 1. 克隆仓库

```bash
git clone https://github.com/Uuclear/report-web.git
cd report-web
```

### 2. Python 虚拟环境（不要提交 `venv/`）

**Windows（PowerShell）**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. 环境变量

```bash
copy .env.example .env
# 编辑 .env，填入 AI_OCR_API_KEY（智谱开放平台申请）
```

后端通过 `os.getenv("AI_OCR_API_KEY", ...)` 读取；生产环境务必使用环境变量或密钥管理，**勿将真实密钥提交到 Git**。

### 4. 前端依赖

```bash
cd frontend
npm install
cd ..
```

### 5. 启动服务

**后端**（默认端口 **8080**，与前端代理一致）：

```bash
cd backend
# 已激活 venv
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

**前端**（开发服务器 **3000**，`/api` 代理到 `http://localhost:8080`）：

```bash
cd frontend
npm run dev
```

浏览器访问：<http://localhost:3000>  
Swagger：<http://localhost:8080/docs>  
健康检查：<http://localhost:8080/health>

**Windows 快捷方式**：项目根目录双击 `start_backend.bat`、`start_frontend.bat`（依赖根目录下 `venv`）。

---

## 生产部署（推荐思路）

以下为通用流程，请按实际域名、HTTPS 证书与进程管理（systemd、NSSM、Docker 等）调整。

### A. 构建前端

```bash
cd frontend
# 若 API 与页面不同域，构建前设置后端公网根地址（无 /api 后缀）
set VITE_API_URL=https://api.example.com
npm run build
```

产物在 `frontend/dist/`。若前后端**同源**（例如 Nginx 把 `/` 指向前端静态文件、`/api` 反代到后端），也可让 `VITE_API_URL` 为空字符串或当前站点 origin，需与 `frontend/src/lib/utils.ts` 中 `apiClient` 拼接规则一致。

### B. 后端作为 ASGI 服务

```bash
cd backend
# 使用正式环境关闭 --reload
python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

生产建议：`gunicorn` + `uvicorn.workers.UvicornWorker`，或使用 Docker 封装。

### C. Nginx 反向代理示例

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    # ssl_certificate ...;

    location / {
        root /path/to/report-web/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8080/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8080/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### D. 数据与文件

- 数据库文件默认在项目根目录 `data.db`（见 `backend/config.py` 中 `DATABASE_URL`）。
- `uploads/`、`merged_pdfs/` 需在服务器上可写；部署迁移时请一并备份或挂载卷。

### E. CORS

`backend/main.py` 中当前为 `allow_origins=["*"]`，生产环境建议改为具体前端域名。

---

## 常用命令

| 说明 | 命令 |
|------|------|
| 前端开发 | `cd frontend && npm run dev` |
| 前端构建 | `cd frontend && npm run build` |
| 后端开发 | `cd backend && python -m uvicorn main:app --reload --port 8080` |

---

## 数据库

首次启动会自动初始化表：`limis_reports`、`limis_single_pages`、`scetia_reports`、`scetia_single_pages` 等（见 `database` 模块）。

---

## 故障排查

1. **前端连不上 API**：检查后端是否在 `8080`；生产环境检查 `VITE_API_URL` 与 Nginx `/api` 反代。
2. **OCR 失败**：检查 `AI_OCR_API_KEY` 与智谱账户额度。
3. **Limis 爬取字段少**：目标站页面结构或 UA 限制；见后端日志 `[LIMIS]`。

---

## 开源协议

若需添加 License，请在仓库根目录补充 `LICENSE` 文件。

---

## 首次推送到 GitHub（在本机执行）

在已配置 SSH 或 HTTPS 凭据的前提下：

```bash
cd report-web
git init
git add .
git commit -m "chore: initial import report-web"
git branch -M main
git remote add origin https://github.com/Uuclear/report-web.git
git push -u origin main
```

若远程仓库已存在内容，可能需要先 `git pull origin main --allow-unrelated-histories` 再推送，或按 GitHub 提示操作。
