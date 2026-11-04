import os
import time
import requests
import anthropic

TOKEN = os.environ["TELEGRAM_TOKEN"]
MY_CHAT_ID = os.environ.get("MY_CHAT_ID", "").strip()
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

SYSTEM = (
    "أنت مساعد شخصي ذكي على تيليغرام. جاوب بنفس لغة المستخدم "
    "(لهجة لبنانية إذا كتب بها)، وكن مختصراً وواضحاً."
)

API = f"https://api.telegram.org/bot{TOKEN}"
client = anthropic.Anthropic()  # يقرأ ANTHROPIC_API_KEY من المتغيرات
history = []


def tg(method, **params):
    r = requests.post(f"{API}/{method}", json=params, timeout=70)
    return r.json()


def send(chat_id, text):
    # حد تيليغرام 4096 حرف للرسالة
    for i in range(0, len(text), 4000):
        tg("sendMessage", chat_id=chat_id, text=text[i:i + 4000])


def ask_claude(user_text):
    global history
    history.append({"role": "user", "content": user_text})
    history = history[-30:]
    while history and history[0]["role"] != "user":
        history.pop(0)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM,
        messages=history,
    )
    answer = "".join(b.text for b in resp.content if b.type == "text")
    history.append({"role": "assistant", "content": answer})
    return answer or "(ما في جواب)"


def main():
    print("Bot started")
    offset = None
    while True:
        try:
            data = tg("getUpdates", offset=offset, timeout=50)
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message")
                if not msg or "text" not in msg:
                    continue
                chat_id = str(msg["chat"]["id"])
                text = msg["text"]

                # أول مرة: اعرف الـ chat ID تبعك
                if not MY_CHAT_ID:
                    send(chat_id, f"الـ chat ID تبعك: {chat_id}\n"
                                  "حطه بمتغير MY_CHAT_ID بالسيرفر وأعد التشغيل.")
                    continue

                # تجاهل أي حدا غيرك
                if chat_id != MY_CHAT_ID:
                    continue

                if text.strip() == "/start":
                    send(chat_id, "أهلاً! البوت شغّال. ابعتلي أي سؤال.")
                    continue
                if text.strip() == "/reset":
                    history.clear()
                    send(chat_id, "تم مسح المحادثة.")
                    continue

                tg("sendChatAction", chat_id=chat_id, action="typing")
                try:
                    send(chat_id, ask_claude(text))
                except Exception as e:
                    send(chat_id, f"صار خطأ: {e}")
        except Exception as e:
            print("loop error:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
