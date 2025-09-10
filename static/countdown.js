// Timing Sequence Controller
class TimingSequenceController {
    constructor() {
        this.statusInterval = null;
        this.countdownInterval = null;
        this.isRunning = false;
        
        this.initializeElements();
        this.bindEvents();
        this.startStatusPolling();
        this.updateNetworkUrl();
        this.checkAudioStatus();
    }
    
    initializeElements() {
        // Sliders and values
        this.delay1Slider = document.getElementById('delay1Slider');
        this.delay1Value = document.getElementById('delay1Value');
        this.delay2Slider = document.getElementById('delay2Slider');
        this.delay2Value = document.getElementById('delay2Value');
        this.totalTimeDisplay = document.getElementById('totalTimeDisplay');
        
        // Status elements
        this.statusDisplay = document.getElementById('statusDisplay');
        this.countdownDisplay = document.getElementById('countdownDisplay');
        this.phaseIndicator = document.getElementById('phaseIndicator');
        this.progressBar = document.getElementById('progressBar');
        
        // Beep indicators
        this.beep1Indicator = document.getElementById('beep1Indicator');
        this.beep2Indicator = document.getElementById('beep2Indicator');
        this.beep3Indicator = document.getElementById('beep3Indicator');
        
        // Buttons
        this.startButton = document.getElementById('startButton');
        this.stopButton = document.getElementById('stopButton');
        
        // Status elements
        this.audioStatus = document.getElementById('audioStatus');
    }
    
    bindEvents() {
        // Slider events
        this.delay1Slider.addEventListener('input', () => this.updateDelay1());
        this.delay2Slider.addEventListener('input', () => this.updateDelay2());
        
        // Button events
        this.startButton.addEventListener('click', () => this.startSequence());
        this.stopButton.addEventListener('click', () => this.stopSequence());
        
        // Update total time on any delay change
        this.delay1Slider.addEventListener('change', () => this.updateTotalTime());
        this.delay2Slider.addEventListener('change', () => this.updateTotalTime());
    }
    
    updateDelay1() {
        const value = parseFloat(this.delay1Slider.value);
        this.delay1Value.textContent = value + 's';
        this.updateTotalTime();
    }
    
    updateDelay2() {
        const value = parseFloat(this.delay2Slider.value);
        this.delay2Value.textContent = value + 's';
        this.updateTotalTime();
    }
    
    updateTotalTime() {
        const delay1 = parseFloat(this.delay1Slider.value);
        const delay2 = parseFloat(this.delay2Slider.value);
        const totalTime = delay1 + delay2 + 3; // +3 for beep duration + gate open time
        
        this.totalTimeDisplay.textContent = totalTime.toFixed(1);
        
        // Validate total time
        if (totalTime < 8 || totalTime > 20) {
            this.totalTimeDisplay.style.color = '#dc3545';
            this.startButton.disabled = true;
            this.startButton.textContent = '⚠️ Invalid Timing';
        } else {
            this.totalTimeDisplay.style.color = 'white';
            this.startButton.disabled = false;
            this.startButton.textContent = '🚀 Start Sequence';
        }
    }
    
    async startSequence() {
        if (this.isRunning) {
            this.showNotification('Sequence already running!', 'warning');
            return;
        }
        
        const delay1 = parseFloat(this.delay1Slider.value);
        const delay2 = parseFloat(this.delay2Slider.value);
        
        try {
            this.startButton.disabled = true;
            this.startButton.textContent = '⏳ Starting...';
            
            const response = await fetch('/start_sequence', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ delay1, delay2 })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Sequence started successfully!', 'success');
                this.isRunning = true;
                this.updateStatusDisplay('running');
                this.showStopButton();
            } else {
                this.showNotification(result.message, 'error');
                this.startButton.disabled = false;
                this.startButton.textContent = '🚀 Start Sequence';
            }
        } catch (error) {
            console.error('Error starting sequence:', error);
            this.showNotification('Failed to start sequence', 'error');
            this.startButton.disabled = false;
            this.startButton.textContent = '🚀 Start Sequence';
        }
    }
    
    async stopSequence() {
        if (!this.isRunning) {
            this.showNotification('No sequence running!', 'warning');
            return;
        }
        
        try {
            this.stopButton.disabled = true;
            this.stopButton.textContent = '⏳ Stopping...';
            
            const response = await fetch('/stop_sequence', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Sequence stopped!', 'success');
                this.isRunning = false;
                this.updateStatusDisplay('idle');
                this.hideStopButton();
                this.resetBeepIndicators();
            } else {
                this.showNotification(result.message, 'warning');
            }
        } catch (error) {
            console.error('Error stopping sequence:', error);
            this.showNotification('Failed to stop sequence', 'error');
        } finally {
            this.stopButton.disabled = false;
            this.stopButton.textContent = '⏹️ Stop Sequence';
        }
    }
    
    showStopButton() {
        this.startButton.style.display = 'none';
        this.stopButton.style.display = 'block';
    }
    
    hideStopButton() {
        this.startButton.style.display = 'block';
        this.stopButton.style.display = 'none';
        this.startButton.disabled = false;
        this.startButton.textContent = '🚀 Start Sequence';
    }
    
    startStatusPolling() {
        this.statusInterval = setInterval(() => {
            this.updateSequenceStatus();
        }, 100); // Poll every 100ms
    }
    
    async updateSequenceStatus() {
        try {
            const response = await fetch('/sequence_status');
            const status = await response.json();
            
            if (status.running) {
                this.isRunning = true;
                this.updateStatusDisplay(status.phase);
                this.updateCountdown(status);
                this.updateProgress(status);
                this.updateBeepIndicators(status);
            } else {
                if (this.isRunning) {
                    this.isRunning = false;
                    this.updateStatusDisplay('idle');
                    this.resetBeepIndicators();
                    this.hideStopButton();
                }
            }
        } catch (error) {
            console.error('Error updating status:', error);
        }
    }
    
    updateStatusDisplay(phase) {
        // Remove all status classes
        this.statusDisplay.classList.remove('status-idle', 'status-running', 'status-gate-open');
        
        if (phase === 'idle') {
            this.statusDisplay.classList.add('status-idle');
        } else if (phase === 'gate_open') {
            this.statusDisplay.classList.add('status-gate-open');
        } else {
            this.statusDisplay.classList.add('status-running');
        }
    }
    
    updateCountdown(status) {
        if (status.phase === 'delay1') {
            const countdown = Math.max(0, status.countdown);
            this.countdownDisplay.textContent = countdown.toFixed(1);
            this.phaseIndicator.textContent = 'Delay 1: Countdown to Beep 2';
        } else if (status.phase === 'delay2') {
            const countdown = Math.max(0, status.countdown);
            this.countdownDisplay.textContent = countdown.toFixed(1);
            this.phaseIndicator.textContent = 'Delay 2: Countdown to Gate';
        } else if (status.phase === 'gate_open') {
            const countdown = Math.max(0, status.countdown);
            this.countdownDisplay.textContent = 'GATE OPEN';
            this.phaseIndicator.textContent = `Gate Open (${countdown.toFixed(1)}s remaining)`;
        } else if (status.phase === 'complete') {
            this.countdownDisplay.textContent = 'Complete!';
            this.phaseIndicator.textContent = 'Sequence Finished - Ready for Next Run';
        } else {
            this.countdownDisplay.textContent = 'Ready';
            this.phaseIndicator.textContent = 'System Ready';
        }
    }
    
    updateProgress(status) {
        if (status.total_time > 0) {
            const progress = (status.current_time / status.total_time) * 100;
            this.progressBar.style.width = Math.min(100, progress) + '%';
        }
    }
    
    updateBeepIndicators(status) {
        const currentTime = status.current_time;
        const timeline = status.timeline;
        
        // Reset all indicators
        this.resetBeepIndicators();
        
        // Activate indicators based on current time
        if (currentTime >= timeline.beep1 && currentTime < timeline.beep1 + 0.5) {
            this.activateBeep(1);
        }
        if (currentTime >= timeline.beep2 && currentTime < timeline.beep2 + 0.5) {
            this.activateBeep(2);
        }
        if (currentTime >= timeline.beep3 && currentTime < timeline.beep3 + 1.0) {
            this.activateBeep(3);
        }
    }
    
    activateBeep(beepNumber) {
        const indicator = this[`beep${beepNumber}Indicator`];
        indicator.classList.add('beep-active');
        
        // Remove active class after animation
        setTimeout(() => {
            indicator.classList.remove('beep-active');
        }, 500);
    }
    
    resetBeepIndicators() {
        this.beep1Indicator.classList.remove('beep-active');
        this.beep2Indicator.classList.remove('beep-active');
        this.beep3Indicator.classList.remove('beep-active');
    }
    
    updateNetworkUrl() {
        const networkUrl = document.getElementById('networkUrl');
        const hostname = window.location.hostname;
        const port = window.location.port;
        
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            networkUrl.textContent = `http://raspberrypi.local:${port}`;
        } else {
            networkUrl.textContent = `http://${hostname}:${port}`;
        }
    }
    
    async checkAudioStatus() {
        try {
            const response = await fetch('/health');
            const health = await response.json();
            
            if (health.audio_initialized) {
                this.audioStatus.textContent = '✅ Audio System Ready';
                this.audioStatus.style.color = '#28a745';
            } else {
                this.audioStatus.textContent = '❌ Audio System Error';
                this.audioStatus.style.color = '#dc3545';
            }
        } catch (error) {
            this.audioStatus.textContent = '❓ Audio Status Unknown';
            this.audioStatus.style.color = '#ffc107';
        }
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }
}

// Initialize the controller when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.timingController = new TimingSequenceController();
});

// Handle page visibility changes to pause/resume polling
document.addEventListener('visibilitychange', () => {
    if (window.timingController) {
        if (document.hidden) {
            // Page is hidden, could pause polling here if needed
        } else {
            // Page is visible again, ensure polling is active
            if (!window.timingController.statusInterval) {
                window.timingController.startStatusPolling();
            }
        }
    }
}); 