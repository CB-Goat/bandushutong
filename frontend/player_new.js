// ===== 时间轴播放器（统一使用预生成音频）=====
var player = {
    // 文字提前量（模仿自然阅读，让眼睛比耳朵快一点）
    TEXT_AHEAD_OFFSET: 2,
    
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
            // 调试日志（仅每5秒输出一次）
            if (!self._lastLogTime || Date.now() - self._lastLogTime > 5000) {
                self._lastLogTime = Date.now();
                console.log('ontimeupdate: currentTime=' + self.currentTime.toFixed(2) + 's, charIndex=' + self._getDisplayCharIndex());
            }
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
    },

    loadSection: function(sectionId) {
        var self = this;
        // 重置状态，允许更新和保存
        this._hasPlayed = false;
        this._isLeaving = false;
        // 防止重复加载同一个节
        if (this._currentSectionId === sectionId && this.audioUrl) {
            console.log('跳过重复加载节:', sectionId);
            return;
        }
        this._currentSectionId = sectionId;
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
        // 检查是否需要从头开始（已读节再次播放时）
        var section = state.currentSections[state.currentSectionIndex];
        var sectionStatus = (state.catalogStatusMap && state.catalogStatusMap[section.id]) || '';
        console.log('play: section.id=', section ? section.id : 'N/A', 'sectionStatus=', sectionStatus);
        if (sectionStatus === 'read') {
            // 已读节，隐藏所有文字，重置赏析区域，从头开始
            console.log('已读节再次播放，hideAll前 visible数:', document.querySelectorAll('.chalk-char.visible').length);
            reader.hideAll();
            console.log('已读节再次播放，hideAll后 visible数:', document.querySelectorAll('.chalk-char.visible').length);
            // 重置赏析区域（点评和小结会在播放过程中重新添加）
            if (typeof analysisManager !== 'undefined') {
                analysisManager.init();
            }
            document.getElementById('annotationDisplay').classList.remove('active');
            if (this.audio) this.audio.currentTime = 0;
        }
        
        console.log('播放，当前模式:', this.mode, '音频URL:', this.audioUrl, 'readyState:', this.audio.readyState);
        if (this.mode === 'timeline' && this.audioUrl) {
            var self = this;
            if (this.audio.readyState < 3) {
                console.log('音频尚未准备好，等待 canplay 事件...');
                document.getElementById('playBtn').textContent = '\u23F3';
                var onCanPlay = function() {
                    console.log('音频可以播放了，开始播放');
                    self.audio.removeEventListener('canplay', onCanPlay);
                    self._doPlay();
                };
                this.audio.addEventListener('canplay', onCanPlay);
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

    // 根据当前时间计算显示到哪个字符
    _getDisplayCharIndex: function() {
        if (!this.charTimeline || this.charTimeline.length === 0) return 0;
        var time = this.currentTime;
        var charIndex = this.charTimeline.length;
        for (var i = 0; i < this.charTimeline.length; i++) {
            if (this.charTimeline[i] > time) { charIndex = i; break; }
        }
        // 文字提前 TEXT_AHEAD_OFFSET 个字符显示（模仿自然阅读）
        charIndex = Math.min(this.charTimeline.length, charIndex + this.TEXT_AHEAD_OFFSET);
        return charIndex;
    },

    _updateDisplayByTime: function() {
        // 点评播放期间不更新文字显示
        if (state.isPlayingAnnotation) {
            return;
        }
        // currentTime 为 0 说明是刚加载或离开，不更新位置避免覆盖已保存的进度
        if (this.currentTime === 0 && this._hasPlayed) {
            console.log('跳过 currentTime=0 的更新，避免覆盖保存的位置');
            return;
        }
        // 播放过之后标记
        if (this.currentTime > 0) {
            this._hasPlayed = true;
        }
        var charIndex = this._getDisplayCharIndex();
        reader.revealCharsUpTo(charIndex);
        // 同步更新阅读位置（用于断点续读）
        reader._currentPosition = charIndex;
        // 每3秒保存一次进度
        if (!this._lastSaveTime || Date.now() - this._lastSaveTime > 3000) {
            this._lastSaveTime = Date.now();
            console.log('自动保存进度: charIndex=' + charIndex);
            reader.saveProgress(charIndex);
        }
        if (this.audioDuration > 0) {
            document.getElementById('progressFill').style.width = (this.currentTime / this.audioDuration * 100) + '%';
        }
    },

    onAudioEnd: function() {
        console.log('音频播放结束');
        var section = state.currentSections[state.currentSectionIndex];
        var currentIndex = state.currentSectionIndex;
        
        if (section && state.currentBook) {
            fetch(API_BASE + '/sections/' + section.id + '/status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({book_id: state.currentBook.id, status: 'read', user_id: state.currentUser.id})
            }).catch(function() {});
        }
        
        var summary = (section && section.summary) ? section.summary : '';
        if (summary) {
            analysisManager.addSummaryTab(summary);
            // 使用预生成的小结音频（如果有）
            if (section.summary_audio_path && section.summary_audio_duration) {
                console.log('使用预生成小结音频:', section.summary_audio_path);
                this._playSummaryAudio(section);
            } else {
                // 降级：使用浏览器 TTS
                console.log('使用浏览器TTS朗读小结');
                var self = this;
                this._speakComment('让我们回顾一下本篇内容。' + summary, function() {
                    // TTS 朗读结束后恢复标签轮播
                    if (typeof analysisManager !== 'undefined' && analysisManager.resumeRotation) {
                        analysisManager.resumeRotation();
                    }
                });
            }
        }
        // 不自动切换下一节，让用户自行选择
    },

    // 播放预生成的小结音频（复用主 audio 元素，避免手机浏览器拦截）
    _playSummaryAudio: function(section) {
        var self = this;
        
        // 保存原始音频信息
        this._originalAudioSrc = this.audioUrl;
        this._originalAudioMode = this.mode;
        
        // 切换到小结音频
        this.audio.src = section.summary_audio_path;
        this.audio.load();
        
        this.audio.onended = function() {
            console.log('小结音频播放结束');
            // 恢复标签轮播
            if (typeof analysisManager !== 'undefined' && analysisManager.resumeRotation) {
                analysisManager.resumeRotation();
            }
            // 恢复原始音频（不自动播放）
            self._restoreMainAudio(0);
        };
        
        this.audio.onerror = function() {
            console.log('小结音频播放失败');
            if (typeof analysisManager !== 'undefined' && analysisManager.resumeRotation) {
                analysisManager.resumeRotation();
            }
            self._restoreMainAudio(0);
        };
        
        this.audio.play().catch(function() {
            console.log('小结音频播放失败');
            if (typeof analysisManager !== 'undefined' && analysisManager.resumeRotation) {
                analysisManager.resumeRotation();
            }
            self._restoreMainAudio(0);
        });
    },

    // 触发点评播放
    _triggerAnnotationPlayback: function(annotation) {
        console.log('触发点评播放:', annotation);
        var self = this;
        
        // 标记正在播放点评，阻止文字更新
        state.isPlayingAnnotation = true;
        
        // 暂停音频
        this.audio.pause();
        
        // 计算点评在音频中的时间点（基于原始字符位置）
        var annotationStartTime = 0;
        var annotationEndTime = 0;
        var timelineLen = this.charTimeline ? this.charTimeline.length : 0;
        
        if (timelineLen > 0) {
            // 确保索引在有效范围内
            var startIdx = Math.max(0, Math.min(annotation.start_char, timelineLen - 1));
            var endIdx = Math.max(0, Math.min(annotation.end_char, timelineLen - 1));
            
            annotationStartTime = this.charTimeline[startIdx];
            annotationEndTime = this.charTimeline[endIdx];
            
            console.log('点评时间:', startIdx, '->', endIdx, '=', annotationStartTime, '->', annotationEndTime);
        }
        
        // 将音频回退到点评开始位置
        this.audio.currentTime = annotationStartTime;
        this.currentTime = annotationStartTime;
        this.audio.load();
        
        // 文字显示回退到：点评结束位置 + 提前量（因为正常阅读时文字会提前显示）
        // 这样用户能看到完整的点评原文
        var displayChar = Math.min(this.charTimeline.length, annotation.end_char + this.TEXT_AHEAD_OFFSET);
        if (typeof reader !== 'undefined' && reader.revealCharsUpTo) {
            reader.revealCharsUpTo(displayChar);
        }
        
        // 高亮使用原始 annotation 位置（不调整，因为 _highlightAnnotation 直接操作 DOM span）
        if (typeof reader !== 'undefined' && reader._highlightAnnotation) {
            reader._highlightAnnotation(annotation);
        }
        
        // 记录当前 annotation，用于清除
        this._currentAnnotation = annotation;
        
        // 显示点评内容
        if (typeof analysisManager !== 'undefined' && analysisManager.addAnnotationTab) {
            analysisManager.addAnnotationTab(annotation);
        }
        
        // 使用预生成的点评音频（如果有）或浏览器 TTS
        if (annotation.audio_path && annotation.audio_duration) {
            console.log('使用预生成点评音频:', annotation.audio_path);
            this._playAnnotationAudio(annotation, annotationEndTime);
        } else {
            // 降级：使用浏览器 TTS
            console.log('使用浏览器TTS朗读点评');
            var self = this;
            this._speakComment('我们看下这里。' + annotation.original_text + '。' + annotation.comment + '。回到原文。', function() {
                setTimeout(function() {
                    self._resumeAfterAnnotation(annotationEndTime);
                }, 1000);
            });
        }
    },

    // 播放预生成的点评音频（复用主 audio 元素，避免手机浏览器拦截）
    _playAnnotationAudio: function(annotation, annotationEndTime) {
        var self = this;
        
        // 保存原始音频信息，用于恢复
        this._originalAudioSrc = this.audioUrl;
        this._originalAudioMode = this.mode;
        
        // 切换到点评音频
        this.audio.src = annotation.audio_path;
        this.audio.load();
        
        this.audio.onended = function() {
            console.log('点评音频播放结束');
            // 恢复原始音频
            self._restoreMainAudio(annotationEndTime);
        };
        
        this.audio.onerror = function() {
            console.log('点评音频播放失败，降级到TTS');
            self._restoreMainAudio(0);
            self._speakComment('我们看下这里。' + annotation.original_text + '。' + annotation.comment + '。回到原文。', function() {
                setTimeout(function() {
                    self._resumeAfterAnnotation(annotationEndTime);
                }, 1000);
            });
        };
        
        this.audio.play().catch(function() {
            console.log('点评音频播放失败，降级到TTS');
            self._restoreMainAudio(0);
            self._speakComment('我们看下这里。' + annotation.original_text + '。' + annotation.comment + '。回到原文。', function() {
                setTimeout(function() {
                    self._resumeAfterAnnotation(annotationEndTime);
                }, 1000);
            });
        });
    },

    // 恢复主音频并从指定位置继续播放
    _restoreMainAudio: function(resumeTime) {
        if (this._originalAudioSrc) {
            // 恢复音频前标记已播放，防止 currentTime=0 时覆盖位置
            this._hasPlayed = true;
            this.audio.src = this._originalAudioSrc;
            this.audioUrl = this._originalAudioSrc;
            this.mode = this._originalAudioMode;
            this._originalAudioSrc = null;
            this._originalAudioMode = null;
            
            // 点评播放结束，允许文字更新
            state.isPlayingAnnotation = false;
            
            if (resumeTime > 0) {
                var self = this;
                this.audio.onloadedmetadata = function() {
                    self.audio.currentTime = resumeTime;
                    self.audio.play().then(function() {
                        self.isPlaying = true;
                        state.isPlaying = true;
                        document.getElementById('playBtn').textContent = '\u23F8';
                    }).catch(function() {});
                    self.audio.onloadedmetadata = null;
                };
                this.audio.load();
            }
        }
    },

    // 使用浏览器 TTS 朗读文本
    _speakComment: function(text, callback) {
        if (!window.speechSynthesis) {
            if (callback) callback();
            return;
        }
        var utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'zh-CN';
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.onend = function() { if (callback) callback(); };
        utterance.onerror = function() { if (callback) callback(); };
        window.speechSynthesis.speak(utterance);
    },

    // 点评结束后恢复播放
    _resumeAfterAnnotation: function(endTime) {
        console.log('点评播放结束，恢复正文');
        var self = this;
        
        // 清除高亮：遍历所有已高亮的 span，移除样式
        if (typeof reader !== 'undefined') {
            // 方式1：使用 _clearAnnotationHighlight
            if (reader._clearAnnotationHighlight && this._currentAnnotation) {
                reader._clearAnnotationHighlight(this._currentAnnotation);
            }
            // 方式2：直接移除所有高亮样式（确保清除干净）
            var highlighted = document.querySelectorAll('.annotation-highlight, .annotation-underline');
            for (var i = 0; i < highlighted.length; i++) {
                highlighted[i].classList.remove('annotation-highlight', 'annotation-underline');
                highlighted[i].style.backgroundColor = '';
                highlighted[i].style.textDecoration = '';
            }
            this._currentAnnotation = null;
        }
        
        // 恢复播放状态
        state.isPlayingAnnotation = false;
        
        // 恢复点评标签轮播
        if (typeof analysisManager !== 'undefined' && analysisManager.resumeRotation) {
            analysisManager.resumeRotation();
        }
        
        if (this.mode === 'timeline' && this.audioUrl) {
            // 从点评结束位置继续播放
            this.audio.currentTime = endTime;
            this.audio.play().then(function() {
                self.isPlaying = true;
                state.isPlaying = true;
                document.getElementById('playBtn').textContent = '\u23F8';
            }).catch(function() {});
        }
    }
};
