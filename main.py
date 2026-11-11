import json
import os
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from ai_assistant import ask_ai

load_dotenv(Path(__file__).with_name(".env"), override=True)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

MENU_TASKS = {
    "🔬 Ғылыми тақырып ұсыну":
        "Берілген бағыт бойынша 5 ғылыми тақырып және қысқаша түсіндірме ұсын.",

    "📝 Ғылыми мақала дайындау":
        "Ғылыми мақалаға құрылым мен мазмұн дайындауға көмектес. Дереккөздерді ойдан шығарма.",

    "📚 Әдебиеттермен жұмыс":
        "Ғылыми әдебиеттерді іздеуге арналған кілт сөздер мен іздеу стратегиясын ұсын. Расталмаған мақалаларды нақты жарияланым ретінде көрсетпе.",

    "📋 Зерттеу жоспары":
        "Зерттеу мақсаты, міндеттері, әдістері, кезеңдері мен нәтижелерін жүйелеп жаз.",

    "📄 Аннотация жазу":
        "Берілген ғылыми мәтінге қысқаша академиялық аннотация жаз.",

    "🌐 Мәтінді аудару":
        "Мәтінді аудар.",

    "✍️ Мәтінді өңдеу":
        "Мәтінді академиялық стильде түзет. Бастапқы мағынасын сақта.",

    "🤖 ЖИ-мен сұхбат":
        "Ғылыми сұрақтарға түсінікті және нақты жауап бер."
}

PROMPTS = {
    "🔬 Ғылыми тақырып ұсыну":
        "Ғылыми бағытыңызды жазыңыз.",

    "📝 Ғылыми мақала дайындау":
        "Ғылыми мақала тақырыбын жазыңыз.",

    "📚 Әдебиеттермен жұмыс":
        "Іздейтін ғылыми тақырыпты жазыңыз.",

    "📋 Зерттеу жоспары":
        "Зерттеу тақырыбын жазыңыз.",

    "📄 Аннотация жазу":
        "Аннотация керек мәтінді жіберіңіз.",

    "🌐 Мәтінді аудару":
        "Қай тілге аударайын? Мысалы: ағылшын.",

    "✍️ Мәтінді өңдеу":
        "Өңдейтін мәтінді жіберіңіз.",

    "🤖 ЖИ-мен сұхбат":
        "Ғылыми сұрағыңызды жазыңыз."
}

user_modes = {}
user_history = {}
translation_languages = {}


def telegram(method, payload=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"

    request = urllib.request.Request(
        url,
        data=json.dumps(payload or {}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(request, timeout=50) as response:
        result = json.load(response)

    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram API қатесі"))

    return result["result"]


def keyboard():
    return {
        "keyboard": [[label] for label in MENU_TASKS],
        "resize_keyboard": True
    }


def send(chat_id, text, with_menu=False):
    text = str(text)

    for index in range(0, len(text), 3900):
        body = {
            "chat_id": chat_id,
            "text": text[index:index + 3900]
        }

        if with_menu:
            body["reply_markup"] = keyboard()

        telegram("sendMessage", body)


def language_from(text):
    lower = text.lower()

    if "ағылшын" in lower or "english" in lower:
        return "ағылшын"

    if "орыс" in lower or "русск" in lower:
        return "орыс"

    if "қазақ" in lower or "kazakh" in lower:
        return "қазақ"

    return None


def language_request(text):
    lower = text.lower().strip()

    return (
        "аудар" in lower
        or "тіліне" in lower
        or lower in {
            "ағылшын", "ағылшынша",
            "орыс", "орысша",
            "қазақ", "қазақша",
            "english", "русский", "kazakh"
        }
    )


def handle_message(chat_id, text):
    text = text.strip()

    if not text:
        return

    if text in ("/start", "/reset"):
        user_modes[chat_id] = "🤖 ЖИ-мен сұхбат"
        user_history[chat_id] = []
        translation_languages.pop(chat_id, None)

        send(
            chat_id,
            "🎓 Scientific AI Assistant\n\n"
            "Сәлеметсіз бе! Қажетті бөлімді таңдаңыз.",
            with_menu=True
        )
        return

    if text in MENU_TASKS:
        user_modes[chat_id] = text
        user_history[chat_id] = []
        translation_languages.pop(chat_id, None)

        send(chat_id, PROMPTS[text], with_menu=True)
        return

    mode = user_modes.get(chat_id, "🤖 ЖИ-мен сұхбат")
    task = MENU_TASKS[mode]

    if mode == "🌐 Мәтінді аудару":

        if language_request(text):
            lang = language_from(text)

            if lang:
                translation_languages[chat_id] = lang

                send(
                    chat_id,
                    f"✅ {lang.capitalize()} тіліне аударамын. "
                    "Мәтінді жіберіңіз."
                )
            else:
                send(
                    chat_id,
                    "Қай тілге аудару керек? Мысалы: ағылшын."
                )
            return

        target = translation_languages.get(chat_id)

        if not target:
            send(
                chat_id,
                "Алдымен аудару тілін жазыңыз: "
                "ағылшын, орыс немесе қазақ."
            )
            return

        task = (
            f"Мәтінді {target} тіліне аудар. "
            "Тек дайын аудармасын жаз. "
            "Сұрақ қойма, түсіндірме қоспа."
        )

        context = []

    else:
        context = user_history.get(chat_id, [])

    send(chat_id, "⏳ ЖИ жауабы дайындалып жатыр...")

    answer = ask_ai(text, task, context)

    send(chat_id, answer)

    if mode != "🌐 Мәтінді аудару" and not answer.startswith("❌"):
        user_history[chat_id] = (
            context + [
                {"role": "user", "content": text},
                {"role": "assistant", "content": answer}
            ]
        )[-12:]


def main():
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN жоқ. .env файлын тексеріңіз.")
        return

    bot = telegram("getMe")

    print("✅ Бот қосылды: @" + bot["username"])

    offset = None

    while True:
        try:
            updates = telegram(
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 30
                }
            )

            for update in updates:
                offset = update["update_id"] + 1

                message = update.get("message", {})
                text = message.get("text")

                if text:
                    handle_message(
                        message["chat"]["id"],
                        text
                    )

        except KeyboardInterrupt:
            print("Бот тоқтатылды.")
            break

        except Exception as error:
            print("Қате:", error)
            time.sleep(3)


if __name__ == "__main__":
    main()