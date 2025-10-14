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
// Feature card click handler
function showFeature(key) {
    const featureMap = {
        languages: {
            title: "🌎 Global Languages",
            description: "From Spanish to Korean, explore 120+ lessons built by experts."
        },
        experience: {
            title: "🎧 Immersive Experience",
            description: "Listen, speak, and practice with interactive quizzes and exercises."
        },
        progress: {
            title: "📈 Personalized Progress",
            description: "Track your learning journey and reach your fluency goals faster."
        }
    };
    const data = featureMap[key];
    if (!data) return;
    
    const titleEl = document.getElementById("feature-title");
    const descEl = document.getElementById("feature-description");
    const container = document.getElementById("feature-details");
    if (titleEl && descEl && container) {
        titleEl.innerText = data.title;
        descEl.innerText = data.description;
        container.style.display = "block";
    }
}

