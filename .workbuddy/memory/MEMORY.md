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

## 断点系统规范 (2026-06-05 规范化重构)

### 一、设计原则

断点只存储**段内**位置（段内文字偏移 + 段内音频时间），不存储全局位置。全局位置可在进入阅读页时通过该节的各段信息（`start_char`、`end_char`）动态计算得出。

文字显示快于音频 3 个字符（`TEXT_AHEAD_OFFSET = 3`），所以 `text_position` 始终比 `audio_position` 对应的字符位置多 3。

书签就是断点的可视化标记，和断点位置始终一致。

---

### 二、数据字段（读写口径完全一致）

| 字段 | 含义 | 作用域 |
|------|------|--------|
| `current_section_id` | 当前节 ID | 全局 |
| `current_segment_id` | 当前文本段 ID | 全局 |
| `text_position` | **段内**文字偏移（该段第几个字符，从 0 开始）| 段内 |
| `audio_position` | **段内**音频时间（秒）| 段内 |

**注意**：全局文字位置（书签位置）不单独存储，由 `segment.start_char + text_position` 动态计算。

**核心约束**：`text_position` 始终 = `全局位置 - 当前段.start_char`。全局位置不单独存储，由段信息动态计算。

**核心原则**：断点的两个元素（text_position, audio_position）必须成对保存。不成对 → 不保存。不允许任何"拼凑"、"挽救"、"兜底"逻辑。

---

### 三、保存逻辑

#### 3.1 saveProgress(position, options) — 统一入口

**函数签名**：`saveProgress(position, options)`
- `position`：全局文字位置（`this._currentPosition`）。如果调用方没传，函数内部自动取。
- `options.skipApi`：跳过 API 保存（checkpoint 用，避免网络延时卡顿）
- `options.skipLocal`：跳过 localStorage 保存

**内部计算规则**：

1. 已读节（`catalogStatusMap[section.id] === 'read'`）→ 直接 return，不存断点
2. `pos <= 0` → 直接 return（无效位置）
3. 当前段是文本段（`_currentSegment.type === 'text_segment'`）：
   - `segmentId = _currentSegment.id`
   - `textPosition = pos - _currentSegment.start_char`（段内偏移）
   - `audioPosition = player.currentTime`
4. 当前段不是文本段（点评/小结播放中或暂停中）：
   - 取 `_lastTextSegmentId`
   - 在 `player.audioSegments` 中查找该段，用它的 `start_char` 计算段内偏移
   - `textPosition = pos - lastSeg.start_char`
   - `audioPosition = player._lastTextAudioPos`
   - 段找不到 → segmentId 置 0 → return（不成对，不保存）
5. `segmentId === 0` → return（无法准确定位文本段）

#### 3.2 保存时机（4 个）

| 时机 | 触发位置 | 存储目标 | 说明 |
|------|---------|---------|------|
| **页面导航离开** | `showPage` / `browseBackToBooks` | API + localStorage | 先 `saveProgress` 再 `player.stop()`，数据准确。设 `window.__progressJustSaved = true` 门控 |
| **页面刷新/关闭** | `beforeunload` 事件 | API（sendBeacon）| **仅在 `player._currentSegment.type === 'text_segment'` 时保存**（此时 text+audio 直接采集，成对准确）。不在文本段中 → 跳过。门控 `__progressJustSaved` 阻止 showPage 后重复保存 |
| **每段文本音频结束** | `player._onSegmentEnd` | API + localStorage | 当前段结束时，`textPosition = 段长度`，`currentTime > 0` 保证 audio 准确 |
| **段内每 100 字** | `player._updateDisplayByTime` | localStorage only（`skipApi:true`）| 防异常退出丢进度，不调 API 避免卡顿 |

**门控机制**：`showPage`/`browseBackToBooks` 离开阅读页后设 `window.__progressJustSaved = true`，阻止 `beforeunload` 用已停止 player 的脏数据覆盖正确断点。进入 `openBook` 时重置为 `false`。

#### 3.3 后端存储

- `reading_progress` 表字段：`current_section_id`, `current_segment_id`, `text_position`（段内偏移）, `audio_position`（段内音频秒数）
- `/progress/v2` POST 接口接收这些字段
- `current_position` 字段已于 2026-06-05 移除，不再存储全局位置

---

### 四、恢复逻辑（`play()` 方法内）

#### 4.1 整体流程

```
进入阅读页
  ↓
检查是否有可恢复的断点（API 返回 progressV2 或 localStorage 取到）
  ↓ 有断点
1. 根据 current_section_id 和 current_segment_id 定位目标段（targetSeg）
2. 根据 text_position 计算段内偏移（segOffset）
3. 计算断点在全局时间轴上的位置 = 之前所有段的累计时长 + seg.char_timeline[segOffset]
4. 页面渲染到断点位置（之前的所有段文字全部显示，点评/小结标记也显示）
5. 音频从断点时间开始播放
6. 书签标记显示在断点文字附近
```

#### 4.2 段内偏移计算（segOffset）

```javascript
// 统一从 text_position 获取段内偏移
var segOffset = progressV2.text_position || 0;
```

全局文字位置（用于书签显示）由 `segment.start_char + text_position` 计算得出。

#### 4.3 音频恢复时间（resumeTime）

```javascript
// ✅ 正确：用目标段的 char_timeline（段内时间轴）
var segTL = targetSeg.char_timeline;
if (typeof segTL === 'string') { segTL = JSON.parse(segTL); }
resumeTime = segTL[segOffset];

// ❌ 错误（已修复）：segOffset 是段内偏移，不能查全局拼接的 this.charTimeline
// resumeTime = this.charTimeline[segOffset];  // 段号越大偏差越大
```

#### 4.4 页面显示恢复

`_restoreBookmarkAndPosition` 完成：
1. 用 `revealCharsUpTo(globalPosition, {skipAnnotationClear: true})` 显示断点前所有文字
2. 调用 `_highlightAnnotation` 高亮断点之后的点评原文引用
3. 设置 `chalkText.scrollTop` 滚动到断点字符可见
4. 调用 `_showBookmarkAt(globalPosition)` 显示书签标记

**`skipAnnotationClear: true`** 关键：断点恢复时跳过 `annotated` 清理，否则 rAF 异步回调会清除刚添加的点评高亮。

---

### 五、代码位置索引

| 功能 | 文件 | 大致行号 | 函数/代码块 |
|------|------|---------|------------|
| 断点保存 | `frontend/index.html` | ~2890 | `reader.saveProgress` |
| 离开时保存 | `frontend/index.html` | ~6815 | `beforeunload` listener |
| 段结束时保存 | `frontend/index.html` | ~5767 | `player._onSegmentEnd` |
| 100字 checkpoint | `frontend/index.html` | ~5970 | `player._updateDisplayByTime` |
| 断点恢复（播放） | `frontend/index.html` | ~4156 | `player.play()` |
| 页面显示恢复 | `frontend/index.html` | ~3035 | `reader._restoreBookmarkAndPosition` |
| 书签显示 | `frontend/index.html` | ~3185 | `reader._showBookmarkAt` |
| 后端 API | `backend/api.py` | ~1074 | `/progress/v2` POST/GET |
| 后端存储 | `backend/database.py` | ~1978 | `update_progress_v2` / `get_progress_v2` |

---

### 六、关键约束（禁止行为）

1. ❌ **禁止**不成对保存断点 — text_position 和 audio_position 必须同时从同一时刻采集，不允许拼凑
2. ❌ **禁止**从 localStorage 恢复 audio_position 拼接到新计算的 text_position 上 — 不同时刻采集的数据不成对
3. ❌ `text_position` **禁止**存全局位置 — 必须始终 = `pos - start_char`，找不到段 → 不保存
4. ❌ **禁止**`beforeunload` 在非文本段时保存断点 — 只在 `_currentSegment.type === 'text_segment'` 时才能获取成对数据
5. ❌ **禁止**在 checkpoint 保存时调 API — 用 `{skipApi: true}`，100 字一次的网络请求会造成明显延时停顿
6. ❌ **禁止**`segmentId === 0` 时继续保存 — 直接 return
7. ❌ **禁止**用 `this.charTimeline` 查段内偏移 — 必须用 `targetSeg.char_timeline`
8. ❌ **禁止**断点恢复 `revealCharsUpTo` 时清除 `annotated` — 用 `{skipAnnotationClear: true}`
