// Simple JavaScript for AI Interview Platform
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }

    // Timer functionality for interview interface
    const timerElement = document.getElementById('timer');
    if (timerElement) {
        let timeLeft = parseInt(timerElement.textContent.split(':')[0]) * 60;
        
        const countdown = setInterval(function() {
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            timerElement.textContent = minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
            
            if (timeLeft <= 0) {
                clearInterval(countdown);
                alert('Time is up! Submitting your interview...');
                document.getElementById('interview-form').submit();
            }
            timeLeft--;
        }, 1000);
    }

    // Auto-save functionality
    const form = document.getElementById('interview-form');
    if (form) {
        const inputs = form.querySelectorAll('textarea, input');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                console.log('Interview progress saved');
            });
        });
    }

    // Character counter
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            const length = this.value.length;
            const words = this.value.trim().split(/\s+/).filter(word => word.length > 0).length;
            const counter = this.parentNode.querySelector('.form-text');
            if (counter) {
                counter.innerHTML = 'Length: ' + length + ' characters | Word count: ' + words;
            }
        });
    });
});