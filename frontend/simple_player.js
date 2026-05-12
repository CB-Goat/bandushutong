// ===== 时间轴播放器（统一使用预生成音频）=====
// 替换 index.html 中的 player 对象
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
                    console.log('加载时间轴音频:', self.audioUrl);
                } else {
                    self.mode = 'generating';
                    self.audioUrl = null;
                    console.log('无预生成音频');
                }
            })
            .catch(function() {
                self.mode = 'generating';
                self.audioUrl = null;
            });
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
            this._generateAudio();
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
