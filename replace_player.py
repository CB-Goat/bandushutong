"""
服务器端执行脚本：替换 index.html 中的播放器代码
用法：python3 replace_player.py
"""
import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到 player 对象的起始和结束行
start_line = -1
end_line = -1
for i, line in enumerate(lines):
    if '// ===== 时间轴播放器' in line:
        start_line = i
    if '// ===== 点评编辑器' in line:
        end_line = i
        break

if start_line == -1 or end_line == -1:
    print("未找到播放器代码边界！start={}, end={}".format(start_line, end_line))
    exit(1)

print("找到播放器代码: 第{}行 到 第{}行".format(start_line + 1, end_line + 1))

# 新的播放器代码
new_player = r'''        // ===== 时间轴播放器（统一使用预生成音频）=====
        var player = {
            audio: document.getElementById('audioPlayer'),
            mode: 'timeline',
            audioUrl: null,
            audioDuration: 0,
            charTimeline: [],
            isPlaying: false,
            currentTime: 0,

            init: function() {
                var self = this;
                this.audio.ontimeupdate = function() {
                    self.currentTime = self.audio.currentTime;
                    self._updateDisplayByTime();
                };
                this.audio.onended = function() {
                    self.isPlaying = false;
                    state.isPlaying = false;
                    document.getElementById('playBtn').textContent = '\u25B6';
                    self.onAudioEnd();
                };
                this.audio.onerror = function() {
                    console.error('音频播放错误');
                    self.isPlaying = false;
                    state.isPlaying = false;
                    document.getElementById('playBtn').textContent = '\u25B6';
                };
            },

            loadSection: function(sectionId) {
                var self = this;
                fetch(API_BASE + '/sections/' + sectionId + '/audio-timeline')
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data.audio_path && data.char_timeline && data.char_timeline.length > 0) {
                            self.mode = 'timeline';
                            self.audioUrl = data.audio_path;
                            self.audioDuration = data.audio_duration || 0;
                            self.charTimeline = data.char_timeline || [];
                            self.audio.src = self.audioUrl;
                            self._hideTTSStatus();
                        } else {
                            self.mode = 'generating';
                            self.audioUrl = null;
                            self._checkTTSStatus();
                        }
                    })
                    .catch(function() {
                        self.mode = 'generating';
                        self.audioUrl = null;
                        self._checkTTSStatus();
                    });
            },

            _checkTTSStatus: function() {
                var self = this;
                if (!state.currentBook) return;
                fetch(API_BASE + '/books/' + state.currentBook.id + '/tts-status')
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        var status = data.tts_status || 'none';
                        var progress = data.tts_progress || '';
                        if (status === 'done') {
                            self._hideTTSStatus();
                            var section = state.currentSections[state.currentSectionIndex];
                            if (section) self.loadSection(section.id);
                        } else if (status === 'generating') {
                            self._showTTSStatus('正在生成语音 ' + progress + '...');
                            setTimeout(function() { self._checkTTSStatus(); }, 5000);
                        } else if (status === 'error') {
                            self._showTTSStatus('语音生成失败，请重新上传书籍');
                        } else {
                            self._showTTSStatus('语音尚未生成，请等待...');
                            setTimeout(function() { self._checkTTSStatus(); }, 5000);
                        }
                    })
                    .catch(function() {});
            },

            _showTTSStatus: function(msg) {
                var el = document.getElementById('ttsStatusBar');
                if (!el) {
                    el = document.createElement('div');
                    el.id = 'ttsStatusBar';
                    el.style.cssText = 'background:rgba(255,193,7,0.15);color:#856404;padding:8px 15px;font-size:13px;text-align:center;border-radius:6px;margin-bottom:10px;';
                    var container = document.querySelector('.chalkboard');
                    if (container) container.insertBefore(el, container.firstChild);
                }
                el.textContent = msg;
                el.style.display = 'block';
            },

            _hideTTSStatus: function() {
                var el = document.getElementById('ttsStatusBar');
                if (el) el.style.display = 'none';
            },

            toggle: function() {
                if (this.isPlaying) { this.pause(); } else { this.play(); }
            },

            play: function() {
                if (this.mode === 'timeline' && this.audioUrl) {
                    this.audio.play();
                    this.isPlaying = true;
                    state.isPlaying = true;
                    document.getElementById('playBtn').textContent = '\u23F8';
                } else if (this.mode === 'generating') {
                    this._showTTSStatus('语音正在生成中，请稍候...');
                }
            },

            pause: function() {
                this.audio.pause();
                this.isPlaying = false;
                state.isPlaying = false;
                document.getElementById('playBtn').textContent = '\u25B6';
            },

            stop: function() {
                this.audio.pause();
                this.audio.currentTime = 0;
                this.isPlaying = false;
                state.isPlaying = false;
                this.currentTime = 0;
                document.getElementById('playBtn').textContent = '\u25B6';
            },

            _updateDisplayByTime: function() {
                if (!this.charTimeline || this.charTimeline.length === 0) return;
                var time = this.currentTime;
                var charIndex = this.charTimeline.length;
                for (var i = 0; i < this.charTimeline.length; i++) {
                    if (this.charTimeline[i] > time) { charIndex = i; break; }
                }
                reader.revealCharsUpTo(charIndex);
                if (this.audioDuration > 0) {
                    document.getElementById('progressFill').style.width = (time / this.audioDuration * 100) + '%';
                }
            },

            _generateAudio: function() {
                var self = this;
                var section = state.currentSections[state.currentSectionIndex];
                if (!section) return;
                document.getElementById('playBtn').textContent = '\u23F3';
                fetch(API_BASE + '/sections/' + section.id + '/generate-audio', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                }).then(function(r) { return r.json(); }).then(function(data) {
                    if (data.success) {
                        self.loadSection(section.id);
                        var checkReady = function() {
                            if (self.mode === 'timeline' && self.audioUrl) {
                                self.audio.play();
                                self.isPlaying = true;
                                state.isPlaying = true;
                                document.getElementById('playBtn').textContent = '\u23F8';
                            } else { setTimeout(checkReady, 300); }
                        };
                        setTimeout(checkReady, 300);
                    } else {
                        document.getElementById('playBtn').textContent = '\u25B6';
                        alert('音频生成失败: ' + (data.error || '未知错误'));
                    }
                }).catch(function(e) {
                    document.getElementById('playBtn').textContent = '\u25B6';
                    alert('请求失败: ' + e.message);
                });
            },

            onAudioEnd: function() {
                var section = state.currentSections[state.currentSectionIndex];
                if (section && state.currentBook) {
                    fetch(API_BASE + '/sections/' + section.id + '/status', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({book_id: state.currentBook.id, status: 'read'})
                    }).catch(function() {});
                }
                var summary = (section && section.summary) ? section.summary : '';
                if (summary) analysisManager.addSummaryTab(summary);
                if (state.currentSectionIndex < state.currentSections.length - 1) {
                    setTimeout(function() { reader.nextSection(); }, 3000);
                }
            }
        };

'''

# 替换
new_lines = lines[:start_line] + [new_player] + lines[end_line:]

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("替换完成！原{}行 -> 新{}行".format(end_line - start_line, len(new_player.split('\n'))))
