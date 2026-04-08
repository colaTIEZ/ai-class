## 1. 项目简介

ai-class 是一套面向课程学习场景的智能练习系统。系统将 PDF 资料解析为知识树，支持按知识点范围出题、苏格拉底提示引导、错题回顾和掌握度统计。

当前版本已覆盖三个能力域：

- 课件上传、队列处理、知识树提取
- 测验生成、提示引导、SSE 流式追踪
- 错题本、掌握度、问题上诉无效化

<img width="2560" height="1469" alt="image" src="https://github.com/user-attachments/assets/04956631-977a-4fd4-8bae-20bf58ab7d74" />
<img width="2550" height="1468" alt="image" src="https://github.com/user-attachments/assets/2f88837b-5589-49a4-938b-cc9062df04a7" />
<img width="2516" height="1436" alt="image" src="https://github.com/user-attachments/assets/eec9f44f-0ac2-4a22-a50c-2540d0098baa" />

## 2. 技术栈与架构

### 技术栈

- 前端：Vue 3、Vite、TypeScript、Pinia、Vue Router、TailwindCSS、AntV G6
- 后端：FastAPI、LangGraph、SQLite、SSE

### 关键数据流

1. 用户上传 PDF。
2. 后端做文件和资源校验，任务进入单例队列。
3. 后台解析文档并写入知识树。
4. 前端圈选知识点后发起测验。
5. 后端返回题目并通过 SSE 流推送提示与追踪。
6. 错题与掌握度写入复盘数据，支持上诉无效化。

## 3. 目录结构

- frontend：前端应用
- backend：后端服务与测试
- _bmad-output：规划、实现、测试产物

## 4. 快速启动

### 4.1 启动后端

```powershell
cd d:\code\ai-class\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

启动成功后访问：

- http://localhost:8000/api/v1/health

### 4.2 启动前端

```powershell
cd d:\code\ai-class\frontend
npm install
npm run dev
```

启动成功后访问：

- http://localhost:5173

### 4.3 推荐顺序

先启动后端，再启动前端。前端开发代理会把 /api 转发到 8000 端口。

## 5. 运行配置

后端配置读取 backend/.env 或系统环境变量。

关键配置：

- OPENAI_API_KEY：your-api-key-here
- OPENAI_BASE_URL：your-base-url-here
- OPENAI_MODEL：your-text-generation-model
- OPENAI_EMBEDDING_MODEL=your-embedding-model

关键本地路径：

- 数据库：backend/data/ai_class.db
- 上传目录：backend/data/uploads

## 6. License

本项目采用 MIT License，详见 [LICENSE](LICENSE)。


