// static/script.js
function sendEvent(event_type, lesson_id, meta) {
    fetch('/track', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ event_type, lesson_id, meta: meta || {} })
    }).catch(e => console.debug('track error', e));
}

// example: call when showing quiz
function toggleQuiz(id, lessonId){
    const el = document.getElementById(id);
    const show = (el.style.display === 'none');
    el.style.display = show ? 'block' : 'none';
    sendEvent('show_quiz', lessonId, {visible: show});
}

// automatically track page views for lesson detail pages if lesson-id attr present
document.addEventListener('DOMContentLoaded', () => {
    const el = document.querySelector('[data-lesson-id]');
    if (el) {
        const lid = el.getAttribute('data-lesson-id');
        sendEvent('view_lesson', parseInt(lid), {});
    }
});

