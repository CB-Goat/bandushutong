# 项目长期笔记

## 部署环境
- **服务器部署方式**：Docker（docker-compose）
- **更新流程**：本地修改 → git push → 服务端 `git pull origin main && docker-compose up -d --build`
- **Git 仓库**：https://github.com/CB-Goat/bandushutong
- **注意**：Windows 环境 git clone 和 git push 需要 `http.sslVerify=false`（用 `git -c http.sslVerify=false push` 或配置全局 `git config --global http.sslVerify false`）
- **代码提交规范**：每次修改代码后，必须立即 commit 并 push 到远程仓库，不要遗漏
- **前端服务**：宝塔 Nginx 直接提供（`/www/dk_project/wwwroot/lit.handy.xin/frontend/`），不在 Docker 容器内

## 技术栈
- 后端：Python Flask（`backend/`），SQLite 数据库
- 前端：原生 HTML + JS（`frontend/index.html` 读者端 + `frontend/admin.html` 管理端，2026-06-04 从 index.html 拆分）
- 部署：Docker / docker-compose

## 已知问题 & 修复记录
- 2026-06-03: 修复音频时间轴弹窗节列表无法加载（缺 API 路由 + 前端状态未恢复）
- 2026-06-03: 修复音频时间轴生成逻辑（v4: force 覆盖 + 按字符比例分配时长）
- 2026-06-03: TTS精品音库 person 值：男声=5003（精品度逍遥），女声=5（精品度小娇）；基础库男声=3，女声=5
