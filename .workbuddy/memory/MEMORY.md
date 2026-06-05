# 项目长期笔记

## 部署环境
- **服务器部署方式**：Docker（docker-compose）
- **更新流程**：本地修改 → git push → 服务端 `git pull origin main && docker-compose up -d --build`
- **Git 仓库**：https://github.com/CB-Goat/bandushutong
- **注意**：Windows 环境 git clone 和 git push 需要 `http.sslVerify=false`（用 `git -c http.sslVerify=false push` 或配置全局 `git config --global http.sslVerify false`）
- **代码提交规范**：每次修改代码后，必须立即 commit 并 push 到远程仓库，不要遗漏
- **前端服务**：宝塔 Nginx 直接提供（`/www/dk_project/wwwroot/lit.handy.xin/frontend/`），但 Docker 容器内有前端文件缓存或反向代理层，**仅改前端 HTML 也必须执行 `docker-compose up -d --build`** 才能清除容器内旧版缓存，否则浏览器会收到旧文件

## 技术栈
- 后端：Python Flask（`backend/`），MySQL 数据库
- 前端：原生 HTML + JS（`frontend/index.html` 读者端 + `frontend/admin.html` 管理端，2026-06-04 从 index.html 拆分）
- 部署：Docker / docker-compose

## 已知问题 & 修复记录
- 2026-06-03: 修复音频时间轴弹窗节列表无法加载（缺 API 路由 + 前端状态未恢复）
- 2026-06-03: 修复音频时间轴生成逻辑（v4: force 覆盖 + 按字符比例分配时长）
- 2026-06-03: TTS精品音库 person 值：男声=5003（精品度逍遥），女声=5（精品度小娇）；基础库男声=3，女声=5
- 2026-06-05: 全面修复页面崩溃问题（详见下方）

## 页面崩溃修复记录 (2026-06-05)
### 根因分析
- **#1 根因**: `_playQuoteAudio`/`_playCommentAudio` 使用 `addEventListener('timeupdate', ...)` 注册监听器，但 `_finishInsertPoint` 仅清除 `on*` 属性，导致 timeupdate 监听器持续累积。同一节播放多个点评后，数十个 timeupdate 回调同时执行 → 崩溃。
- **#2**: `startDeviceCheck()` 创建 setInterval 后立即 clearInterval，设备检查功能完全失效。
- **#3**: `_checkTTSStatus()` 的 setInterval 使用局部变量，非 timeline 模式下永远轮询无法停止。
- **#4**: `showPage` 离开页面时无统一清理机制（仅 readerPage 有部分清理）。
- **#5**: `browse.loadBooks` 异步 fetch 回调操作可能已销毁的 DOM。
- **#6**: `_preloadAllAudio` 临时 Audio 对象不清理。

### 修复内容
1. `_finishInsertPoint`/`_finishSummaryPlayback`/`player.stop()` — 重建 `_annotationAudio` 对象（而非清除 on* 属性），彻底清除所有 addEventListener 残留
2. `startDeviceCheck()` — 删除错误的立即 clearInterval 代码
3. `_checkTTSStatus()` — 改用 `this._ttsCheckInterval` 存储引用，在 `player.stop()` 中清理
4. `showPage` — 离开 readerPage 时清理 analysisManager 轮巡、tabs、调试定时器、TTS 轮询
5. `browse.loadBooks` — 添加 `_loadGen` 版本号机制防止过期回调
6. `_preloadAllAudio` — 预加载完成后清理临时 Audio 对象
7. `_playAnnotationSegment` — 移除冗余 `removeEventListener`（已用 oncanplay 属性）
8. 3 处未追踪 `setTimeout` 改为 `_safeSetTimeout`

### 关键编码规范
- **禁止**在 `_annotationAudio` 上使用 `addEventListener` 注册非自清理的监听器
- 所有 Audio 对象清理必须「重建 `new Audio()`」而非逐个清除事件
- 所有页面导航后必须清理前页面的定时器/轮询/异步回调
- 使用 `addEventListener` 的监听器必须有对应的 `removeEventListener`（或在回调内自清理）
- `oncanplay = handler` 比 `addEventListener('canplay', handler)` 更安全（属性赋值覆盖而非累积）

## 断点系统规范 (2026-06-05 最终版)

### 设计原则

断点 = `text_position` + `audio_position`，必须成对保存，不成对则不保存。不允许任何"拼凑"、"挽救"、"兜底"逻辑。

- text_position：段内文字偏移 = 全局pos - seg.start_char
- audio_position：段内音频时间 = player.currentTime
- 两个值必须来自同一时刻、同一段
- 仅通过 API 写入 MySQL，不存 localStorage

### saveProgress 规则

1. 已读节 → return
2. pos <= 0 → return
3. 不在 `text_segment`（annotation/summary 中或 player 停止）→ return
4. 未登录 → API 不发送
5. 仅在 `player._currentSegment.type === 'text_segment'` 时保存

### 6 个触发入口

| # | 触发时机 | 代码位置 | 位置参数 |
|---|---------|---------|---------|
| 1 | 段内每100字 | `_updateDisplayByTime` | `seg.start_char + offset` |
| 2 | 文本段播完 | `_onSegmentEnd` | `seg.end_char` |
| 3 | 整节播完 | `_onAllSegmentsEnd` | `reader._totalChars` |
| 4 | 用户点暂停 | `toggle()` | `reader._currentPosition` |
| 5 | 点返回退出 | homeBtn → showPage | `reader._currentPosition` |
| 6 | 刷新/关闭标签 | beforeunload | `reader._currentPosition`（门控拦截）|

### 门控机制

```
openBook()           →  __progressJustSaved = false
showPage(非readerPage) →  player.stop() + __progressJustSaved = true
beforeunload         →  true=跳过 / false=sendBeacon
```

showPage 统一处理离场清理：player.stop()、analysisManager、debug timer、TTS 轮询。
homeBtn 只负责 saveProgress + wakeLock 释放 + 导航栏恢复，不重复调用 player.stop()。

### 不保存的情况

| 场景 | 原因 |
|------|------|
| annotation/summary 子过程 | 进入前已在段结束时保存 |
| player 已停止 | `_currentSegment` 为 null |
| beforeunload 被门控拦截 | showPage 已保存 |
| beforeunload 不在文本段 | 数据不成对 |
| beforeunload 音频位置 ≤ 0 | 无有效数据 |
| 已读节 | 不记录断点 |
| browseBackToBooks | 非 readerPage 活动 |
