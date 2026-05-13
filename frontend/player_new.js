// ===== 时间轴播放器（统一使用预生成音频）=====
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
        this.audio.onerror = function(e) {
            console.error('音频播放错误:', e);
            self.isPlaying = false;
            state.isPlaying = false;
            document.getElementById('playBtn').textContent = '\u25B6';
        };
        // 添加 canplay 事件，音频准备好后自动播放
        this.audio.oncanplay = function() {
            console.log('音频可以播放了');
        };
    },

    loadSection: function(sectionId) {
        var self = this;
        console.log('加载节:', sectionId);
        fetch(API_BASE + '/sections/' + sectionId + '/audio-timeline')
            .then(function(r) { 
                console.log('API响应状态:', r.status);
                return r.json(); 
            })
            .then(function(data) {
                console.log('API返回:', data);
                if (data.audio_path && data.char_timeline && data.char_timeline.length > 0) {
                    self.mode = 'timeline';
                    self.audioUrl = data.audio_path;
                    self.audioDuration = data.audio_duration || 0;
                    self.charTimeline = data.char_timeline || [];
                    // 确保路径是完整的
                    if (self.audioUrl.indexOf('http') !== 0 && self.audioUrl.indexOf('/') !== 0) {
                        self.audioUrl = '/api/audio/' + self.audioUrl.replace('audio_files/', '');
                    }
                    self.audio.src = self.audioUrl;
                    console.log('设置音频源:', self.audioUrl);
                    self._hideTTSStatus();
                } else {
                    console.log('无预生成音频，检查TTS状态');
                    self.mode = 'generating';
                    self.audioUrl = null;
                    self._checkTTSStatus();
                }
            })
            .catch(function(e) {
                console.error('加载音频时间轴失败:', e);
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
        console.log('播放，当前模式:', this.mode, '音频URL:', this.audioUrl, 'readyState:', this.audio.readyState);
        if (this.mode === 'timeline' && this.audioUrl) {
            var self = this;
            // readyState: 0=未初始化, 1=已设置src, 2=正在加载, 3=部分加载, 4=完全加载
            if (this.audio.readyState < 3) {
                console.log('音频尚未准备好，等待 canplay 事件...');
                document.getElementById('playBtn').textContent = '\u23F3';
                // 等待音频可以播放
                var onCanPlay = function() {
                    console.log('音频可以播放了，开始播放');
                    self.audio.removeEventListener('canplay', onCanPlay);
                    self._doPlay();
                };
                this.audio.addEventListener('canplay', onCanPlay);
                // 超时处理
                setTimeout(function() {
                    self.audio.removeEventListener('canplay', onCanPlay);
                    if (!self.isPlaying) {
                        console.log('等待超时，尝试直接播放');
                        self._doPlay();
                    }
                }, 3000);
            } else {
                this._doPlay();
            }
        } else if (this.mode === 'generating') {
            this._showTTSStatus('语音正在生成中，请稍候...');
        } else {
            console.log('无法播放，模式:', this.mode, 'URL:', this.audioUrl);
        }
    },

    _doPlay: function() {
        var self = this;
        this.audio.play().then(function() {
            console.log('播放成功');
            self.isPlaying = true;
            state.isPlaying = true;
            document.getElementById('playBtn').textContent = '\u23F8';
        }).catch(function(e) {
            console.error('播放失败:', e);
            document.getElementById('playBtn').textContent = '\u25B6';
            // 不弹出alert，避免打断用户体验
        });
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
        // 文字提前2个汉字显示（阅读友好）
        charIndex = Math.min(this.charTimeline.length, charIndex + 2);
        reader.revealCharsUpTo(charIndex);
        if (this.audioDuration > 0) {
            document.getElementById('progressFill').style.width = (time / this.audioDuration * 100) + '%';
        }
    },

    onAudioEnd: function() {
        console.log('音频播放结束');
        var section = state.currentSections[state.currentSectionIndex];
        var totalSections = state.currentSections.length;
        var currentIndex = state.currentSectionIndex;
        
        console.log('当前节:', currentIndex, '总节数:', totalSections);
        
        if (section && state.currentBook) {
            fetch(API_BASE + '/sections/' + section.id + '/status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({book_id: state.currentBook.id, status: 'read'})
            }).catch(function() {});
        }
        
        var summary = (section && section.summary) ? section.summary : '';
        if (summary) {
            analysisManager.addSummaryTab(summary);
            // 有小结时，等待5秒（显示小结+自动切换）
            if (currentIndex < totalSections - 1) {
                console.log('显示小结，5秒后切换下一节');
                setTimeout(function() { 
                    console.log('准备切换到下一节');
                    reader.nextSection(); 
                }, 5000);
            }
        } else {
            // 无小结时，等待2秒后切换
            if (currentIndex < totalSections - 1) {
                console.log('无小结，2秒后切换下一节');
                setTimeout(function() { 
                    console.log('准备切换到下一节');
                    reader.nextSection(); 
                }, 2000);
            } else {
                console.log('已是最后一节');
            }
        }
    },

    // 触发点评播放
    _triggerAnnotationPlayback: function(annotation) {
        console.log('触发点评播放:', annotation);
        var self = this;
        
        // 暂停音频
        this.audio.pause();
        
        // 高亮点评原文
        if (typeof reader !== 'undefined' && reader._highlightAnnotation) {
            reader._highlightAnnotation(annotation);
        }
        
        // 显示点评内容
        if (typeof analysisManager !== 'undefined') {
            analysisManager.showAnnotation(annotation);
        }
        
        // 等待3秒后恢复播放
        setTimeout(function() {
            console.log('点评播放结束，恢复正文');
            // 清除高亮
            if (typeof reader !== 'undefined' && reader._clearAnnotationHighlight) {
                reader._clearAnnotationHighlight(annotation);
            }
            // 恢复播放
            state.isPlayingAnnotation = false;
            if (self.mode === 'timeline' && self.audioUrl) {
                self.audio.play();
                self.isPlaying = true;
                state.isPlaying = true;
                document.getElementById('playBtn').textContent = '\u23F8';
            }
        }, 3000);
    }
};
