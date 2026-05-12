/**
 * 伴读书童 - 时间轴播放器
 * 基于预生成音频的时间轴控制
 */

var TimelinePlayer = {
    audio: null,
    isPlaying: false,
    currentTime: 0,
    audioDuration: 0,
    charTimeline: [],
    totalChars: 0,
    animationFrame: null,
    audioUrl: null,
    onTimeUpdate: null,
    onEnded: null,

    init: function(audioElement) {
        this.audio = audioElement;
        var self = this;

        this.audio.ontimeupdate = function() {
            self.currentTime = self.audio.currentTime;
            if (self.onTimeUpdate) self.onTimeUpdate(self.currentTime);
        };

        this.audio.onended = function() {
            self.isPlaying = false;
            if (self.onEnded) self.onEnded();
        };

        this.audio.onerror = function() {
            self.isPlaying = false;
            console.error('音频播放错误');
        };
    },

    load: function(audioUrl, charTimeline, audioDuration) {
        this.audioUrl = audioUrl;
        this.charTimeline = charTimeline || [];
        this.audioDuration = audioDuration || 0;
        this.totalChars = charTimeline ? charTimeline.length : 0;
        this.audio.src = audioUrl;
        this.currentTime = 0;
    },

    play: function() {
        if (!this.audio) return;
        var self = this;
        this.audio.play().then(function() {
            self.isPlaying = true;
        }).catch(function(e) {
            console.error('播放失败:', e);
        });
    },

    pause: function() {
        if (!this.audio) return;
        this.audio.pause();
        this.isPlaying = false;
    },

    stop: function() {
        if (!this.audio) return;
        this.audio.pause();
        this.audio.currentTime = 0;
        this.currentTime = 0;
        this.isPlaying = false;
    },

    seek: function(time) {
        if (!this.audio) return;
        this.audio.currentTime = Math.max(0, Math.min(time, this.audioDuration));
        this.currentTime = this.audio.currentTime;
    },

    // 获取当前应该显示到第几个字符
    getCurrentCharIndex: function() {
        if (!this.charTimeline || this.charTimeline.length === 0) return 0;

        var time = this.currentTime;
        for (var i = 0; i < this.charTimeline.length; i++) {
            if (this.charTimeline[i] > time) {
                return i;
            }
        }
        return this.charTimeline.length;
    },

    // 获取当前进度百分比
    getProgress: function() {
        if (this.audioDuration <= 0) return 0;
        return (this.currentTime / this.audioDuration) * 100;
    }
};

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TimelinePlayer;
}
