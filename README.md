# myportal-python

基于 FastAPI + Vue 3 的全栈信息门户，包含用户系统、文件管理、文章发布、实时聊天、后台管理。

## 特性
- JWT 认证与角色控制
- 文件上传 / 下载 / 预览 (含魔数校验)
- Markdown 文章与分类标签
- WebSocket 实时聊天，支持 @提及和撤回
- 通知中心 (站内提醒)
- 暗黑模式切换
- Docker 一键部署

## 快速开始
1. 复制 `.env.example` 为 `.env`，设置强随机 `SECRET_KEY`。
2. 后端：`pip install -r requirements.txt && python app.py`
3. 前端：`cd frontend && npm install && npm run dev`
4. Docker 部署：`docker-compose up -d`

## 许可证
MIT
