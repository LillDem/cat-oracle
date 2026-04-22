from flask import Flask, request, jsonify, render_template
import json
import os
import random
import requests
import re

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
    "всё уже сказано",
    "кот не обязан объяснять",
    "это было очевидно с самого начала",
    "ты просто не хочешь это принять",
    "кот видел хуже",
    "это не тот вопрос",
    "ответ уже случился",
    "ты пришёл слишком поздно",
]

THINKING_LINES = [
    "Погоди… Сейчас достану хрустальный шар… Я его загнал под диван. Ага… Вот…",
    "Листаю книгу Лилу Деймон «Свалка Историй» А ты думал, я из головы предсказания выдавать буду? Голова у меня, знаешь ли, для важных дел.",
    "Терпение… Открываю третий глаз.",
    "Кот смотрит в пустоту…",
    "Что-то шевельнулось в данных…",
    "Ммм… интересный запрос…",
]

AFTER_LINES = [
    "Еще вопрос?",
    "Ну что, продолжим?",
    "Спрашивай дальше.",
    "Или тебе уже хватило?",
    "Кот не гарантирует ответы.",
]

OLLAMA_URL = "http://localhost:11434/api/generate"


# =========================
# 🧠 TEXT UTILS
# =========================
def words(text):
    return set(re.findall(r'\w+', text.lower()))


# =========================
# 🧠 УМНЫЙ ВЫБОР ЦИТАТЫ
# =========================
def get_quote(question, name):
    if not book:
        return "..."

    if random.random() < 0.3:
        return random.choice(book)

    q_words = words(question)

    scored = []
    for line in book:
        line_words = words(line)
        score = len(q_words & line_words) / (len(line_words) + 1)
        scored.append((score, line))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:5]

    recent = [m["a"] for m in memory.get(name, {}).get("messages", [])]
    filtered = [line for _, line in top if line not in str(recent)]

    if filtered:
        return random.choice(filtered)

    return random.choice(top)[1]


# =========================
# 🐱 ПОВЕДЕНИЕ КОТА
# =========================
def adapt_base(base, q):
    q = q.lower()

    if "почему" in q:
        return "кот не объясняет"

    if "люблю" in q:
        return "это опасный вопрос"

    if "смерть" in q:
        return "кот смотрит дольше обычного"

    return base


# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
def index():
    return render_template("index.html")


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

    quote = get_quote(q, name)

    if random.random() < 0.03:
        return jsonify({"answer": "🐱 кот смотрит на тебя слишком долго…"})

    mode = random.choice(["full", "short", "weird", "prophecy"])

    # 👇 уменьшили шанс ИИ
    use_ollama = random.random() < (0.15 + mood_val * 0.03)

    thinking = random.choice(THINKING_LINES)
    after = random.choice(AFTER_LINES)
    base = adapt_base(random.choice(BASE_ANSWERS), q)

    # =========================
    # 🤖 OLLAMA
    # =========================
    if use_ollama:
        prompt = f"""
Ты — кот-оракул.

Ответ должен быть:
- короткий
- цельный (не обрывай мысль)
- странный, но понятный

Текст:
{quote}

Вопрос:
{q}

Ответ:
"""

        try:
            r = requests.post(
                OLLAMA_URL,
                json={
                    "model": "phi3",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 80,
                        "temperature": 0.9
                    }
                }
            )

            ai_text = r.json().get("response", "").strip()

            # 👇 если модель тупит — не палим это
            if not ai_text or len(ai_text) < 10:
                ai_text = quote

            # 👇 если обрыв — аккуратно чинится
            if ai_text.endswith(("…", "...", "-", "—")):
                ai_text = ai_text + " кот не договорил"

        except:
            ai_text = quote

    else:
        ai_text = quote

    # =========================
    # 🎭 ФОРМАТЫ (НЕ ТРОГАЛ)
    # =========================
    if mode == "full":
        answer = f"🐱 {thinking}\n\n📚 {ai_text}\n\n💬 {base}\n\n😼 {after}"

    elif mode == "short":
        answer = f"🐱 {ai_text}"

    elif mode == "weird":
        answer = f"🐱 ...\n{base}\n{ai_text}\nкот замолчал"

    elif mode == "prophecy":
        answer = f"🔮 {ai_text}\n\nкот отвернулся"

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
