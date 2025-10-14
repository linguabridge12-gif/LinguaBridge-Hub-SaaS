from flask import Flask, jsonify, abort

app = Flask(__name__)

lessons = []

# Core language intros
core_lessons = [
    (1, "Intro to Spanish", "Greetings, basic phrases, pronunciation, and cultural notes in Spanish.", "Hello in Spanish?", "Hola"),
    (2, "Intro to French", "Greetings, basic phrases, pronunciation, and cultural notes in French.", "Thank you in French?", "Merci"),
    (3, "Intro to German", "Greetings, basic phrases, pronunciation, and cultural notes in German.", "Good morning in German?", "Guten Morgen"),
    (4, "Intro to Italian", "Greetings, basic phrases, pronunciation, and cultural notes in Italian.", "Goodbye in Italian?", "Arrivederci")
]

for id_, title, content, q, a in core_lessons:
    lessons.append({
        "id": id_,
        "title": title,
        "content": content,
        "quiz": [{"question": q, "answer": a}]
    })

# Modules 5 to 120
for i in range(5, 121):
    lessons.append({
        "id": i,
        "title": f"Module {i}",
        "content": f"Module {i} covers advanced language concepts, exercises, listening practice, and conversation scenarios.",
        "quiz": [{"question": f"Key concept of Module {i}?","answer": f"Answer {i}"}]
    })

def get_lesson_by_id(lesson_id):
    return next((l for l in lessons if l['id'] == lesson_id), None)

@app.route('/')
def index():
    lesson_list = [{'id': l['id'], 'title': l['title']} for l in lessons]
    return jsonify({'lessons': lesson_list})

@app.route('/lesson/<int:lesson_id>')
def lesson(lesson_id):
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        abort(404, description="Lesson not found")
    return jsonify(lesson)

if __name__ == '__main__':
    app.run(debug=True)
