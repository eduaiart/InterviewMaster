// Interview Platform JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Timer functionality
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
                const form = document.getElementById('interview-form');
                if (form) form.submit();
            }
            timeLeft--;
        }, 1000);
    }

    // Character counter
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(function(textarea) {
        textarea.addEventListener('input', function() {
            const length = this.value.length;
            const words = this.value.trim().split(/\s+/).filter(function(word) {
                return word.length > 0;
            }).length;
            console.log('Progress saved');
        });
    });
});