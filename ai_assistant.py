import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv(
    Path(__file__).with_name(".env"),
    override=True
)

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

BACKUP_MODEL = "gemini-3.1-flash-lite"

SYSTEM_PROMPT = """
Сен Scientific AI Assistant атты ғылыми көмекшісің.

Оқытушыларға, магистранттар мен докторанттарға
ғылыми-зерттеу жұмыстарында көмектесесің.

Міндеттерің:
1. Ғылыми сұрақтарға жауап беру.
2. Ғылыми мақалалар дайындауға көмектесу.
3. Зерттеу тақырыптарын ұсыну.
4. Зерттеу жоспарын құру.
5. Аннотация жазу.
6. Қазақ, орыс және ағылшын тілдеріне аудару.
7. Ғылыми мәтіндерді өңдеу.
8. Ғылыми әдебиеттермен жұмыс істеу.

Ережелер:
- Әдепкі жауап тілі қазақ тілі.
- Пайдаланушы сұраған тілде жауап бер.
- Алдыңғы диалогты ескер.
- Бір сұрақты қайта-қайта қойма.
- Аудармада тек дайын аударманы бер.
- Ғылыми деректерді, авторларды және DOI ойдан шығарма.
- Нақты, түсінікті және пайдалы жауап дайында.
"""


def ask_ai(question, task="Ғылыми сұраққа жауап беру", history=None):

    if not API_KEY:
        return "❌ GEMINI_API_KEY табылмады."

    conversation = []

    for item in (history or [])[-12:]:
        role = item.get("role", "user")
        content = str(item.get("content", "")).strip()

        if content:
            speaker = (
                "Ассистент" if role == "assistant"
                else "Пайдаланушы"
            )
            conversation.append(f"{speaker}: {content}")

    prompt = (
        SYSTEM_PROMPT
        + "\n\nТапсырма:\n" + task
        + "\n\nДиалог:\n" + "\n".join(conversation)
        + "\n\nЖаңа сұрақ:\n" + question
    )

    client = genai.Client(api_key=API_KEY)

    models = list(dict.fromkeys([MODEL, BACKUP_MODEL]))

    for model in models:

        for attempt in range(2):

            try:
                print(f"ЖИ моделі: {model}")

                response = client.interactions.create(
                    model=model,
                    input=prompt
                )

                if response.output_text:
                    return response.output_text.strip()

                return "❌ ЖИ бос жауап қайтарды."

            except Exception as error:

                error_text = str(error)
                print("GEMINI ERROR:", error_text)

                if "503" in error_text:
                    if attempt == 0:
                        print("Сервер бос емес. Қайта тексеру...")
                        time.sleep(3)
                        continue

                    print("Басқа модельге ауысу...")
                    break

                if "404" in error_text:
                    print("Модель қолжетімсіз:", model)
                    break

                if "429" in error_text:
                    return (
                        "❌ Gemini сұраныс лимитіне жетті. "
                        "Лимит жаңарғаннан кейін қайталаңыз."
                    )

                if "401" in error_text or "403" in error_text:
                    return "❌ API кілтін және рұқсаттарын тексеріңіз."

                return "❌ Gemini қатесі. Терминалды тексеріңіз."

    return (
        "❌ Қазір Gemini серверлері бос емес немесе "
        "таңдалған модельдер қолжетімсіз."
    )
