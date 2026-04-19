from flask import Flask, request, jsonify, render_template
import json
import os
import random
import requests

app = Flask(__name__)

# =========================
# 📦 MEMORY
# =========================
MEM_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEM_FILE):
        with open(MEM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

memory = load_memory()

def save_memory():
    with open(MEM_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


# =========================
# 📚 BOOK
# =========================
def load_book():
    try:
        with open("book.txt", "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines()]
            return [l for l in lines if len(l) > 5]
    except:
        return []

book = load_book()


# =========================
# 🐱 BASE
# =========================
BASE_ANSWERS = [
    "мяу. ответ уже существует",
    "ты уже это знаешь",
    "кот наблюдает и молчит",
    "реальность согласилась",
    "ответ ближе, чем вопрос",
    "всё уже сказано"
]    

THINKING_LINES = [
    "Погоди… Сейчас достану хрустальный шар. Я его загнал под диван. Ага… Вот…",
    "Листаю книгу Лилу Деймон «Свалка Историй»… А ты думал, я из головы предсказания выдавать буду? Голова у меня, знаешь ли, для важных дел.",
    "Терпение… Открываю третий глаз."
]

AFTER_LINES = [
    "Еще вопрос? Или с тебя достаточно?",
    "Ну что, продолжим?",
    "Спрашивай дальше, если не боишься ответа."
]


OLLAMA_URL = "http://localhost:11434/api/generate"


# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
def index():
    return render_template("index.html")


# 😼 mood
@app.route("/mood", methods=["POST"])
def mood():
    data = request.json
    name = data.get("name", "человек")

    if name not in memory:
        memory[name] = {"messages": [], "mood": 0}

    memory[name]["mood"] += random.randint(-1, 2)
    memory[name]["mood"] = max(-5, min(5, memory[name]["mood"]))

    m = memory[name]["mood"]

    if m > 2:
        avatar = "/static/cat_happy.png"
    elif m < -2:
        avatar = "/static/cat_angry.png"
    else:
        avatar = "/static/cat.png"

    save_memory()
    return jsonify({"avatar": avatar})


# =========================
# 🧠 УМНЫЙ ВЫБОР ЦИТАТЫ
# =========================
def get_quote(question):
    if not book:
        return "..."

    q_words = set(question.lower().split())

    scored = []

    for line in book:
        line_words = set(line.lower().split())

        # пересечение слов
        score = len(q_words & line_words)

        scored.append((score, line))

    scored.sort(key=lambda x: x[0], reverse=True)

    top = scored[:10]

    # если есть хоть слабое совпадение — берём из топа
    if top and top[0][0] > 0:
        return random.choice(top)[1]

    # иначе просто случайная строка
    return random.choice(book)


# =========================
# 🐱 MAIN BRAIN
# =========================
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    q = data.get("question", "")
    name = data.get("name", "человек")

    if not q:
        return jsonify({"answer": "…"})

    if name not in memory:
        memory[name] = {"messages": [], "mood": 0}

    mood_val = memory[name]["mood"]

    # =========================
    # 📚 ЦИТАТА С УЧЁТОМ ВОПРОСА
    # =========================
    quote = get_quote(q)

    # =========================
    # 🎲 редкий ИИ
    # =========================
    use_ollama = random.random() < 0.1

    # =========================
    # ⚡ БЫСТРЫЙ РЕЖИМ
    # =========================
    if not use_ollama:

        thinking = random.choice(THINKING_LINES)
        after = random.choice(AFTER_LINES)
        base = random.choice(BASE_ANSWERS)

        answer = f"🐱 {thinking}\n\n📚 {quote}\n\n💬 {base}\n\n😼 {after}"

    # =========================
    # 🧠 OLLAMA (редко)
    # =========================
    else:
        prompt = f"""
Ты — кот-оракул.

Используй текст как смысл ответа.

Текст:
{quote}

Вопрос:
{q}

Отвечай коротко как кот.
"""

        try:
            r = requests.post(
                OLLAMA_URL,
                json={
                    "model": "phi3",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 60,
                        "temperature": 0.7
                    }
                }
            )

            answer = r.json().get("response", "кот завис")

        except:
            answer = "кот ушёл в пустоту"

        thinking = random.choice(THINKING_LINES)
        after = random.choice(AFTER_LINES)
        base = random.choice(BASE_ANSWERS)

        answer = f"🐱 {thinking}\n\n🧠 {answer}\n\n💬 {base}\n\n😼 {after}"

    # =========================
    # 💾 MEMORY
    # =========================
    memory[name]["messages"].append({"q": q, "a": answer})
    memory[name]["messages"] = memory[name]["messages"][-10:]
    save_memory()

    return jsonify({"answer": answer})


# =========================
# 🚀 RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
