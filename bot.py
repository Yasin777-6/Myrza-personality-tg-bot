import os
import random
import logging
import asyncio
import json
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MyrzaBot")

# Configuration
class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    REPLY_PROBABILITY = float(os.getenv("REPLY_PROBABILITY", "0.15"))

    @classmethod
    def get_user_list(cls, env_var: str, default: str = "") -> list[str]:
        val = os.getenv(env_var, default)
        if not val:
            return []
        return [item.strip().lower() for item in val.split(",") if item.strip()]

    @property
    def artur_users(self) -> list[str]: return self.get_user_list("USER_ARTUR", "thereisnohopeleftinme")
    @property
    def aktan_users(self) -> list[str]: return self.get_user_list("USER_AKTAN", "wak_kfu")
    @property
    def yasin_users(self) -> list[str]: return self.get_user_list("USER_YASIN", "")
    @property
    def mansur_users(self) -> list[str]: return self.get_user_list("USER_MANSUR", "mall1aners")
    @property
    def beka_users(self) -> list[str]: return self.get_user_list("USER_BEKA", "ineverwantedanyofit")

config = Config()

# Validate configuration
if not config.TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is not set in environment variables.")
if not config.DEEPSEEK_API_KEY:
    logger.error("DEEPSEEK_API_KEY is not set in environment variables.")

# Initialize DeepSeek Client (OpenAI-compatible)
openai_client = AsyncOpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL
)

# Initialize Bot and Dispatcher
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Memory database and chat log file paths
MEMORIES_FILE = "memories.json"
HISTORY_FILE = "chat_history.txt"

# Preloaded base memories from your group chat logs
BASE_MEMORIES = [
    "Мансур однажды признался, что целовался (или сучка откусила кусок губы), а Актан закричал: «ЭТО ЖЕ Я БЫЛ! Я увлекся просто». Мансур тогда испугался и орал «Йаак!».",
    "Ясин говорил Актану, что тот портит Мансуру ауру и лучше бы ему пойти нахуй.",
    "Ясин сказал Актану: «У тебя нет друзей тупой баран, все это время мы с тобой дружили чтобы списывать».",
    "Артур ругался на Ясина за то, что тот ворует песни из его плейлиста.",
    "Бека доказывал, что от костного массажа (bone smashing / bs) и mewing реально растут кости лица (hunter eyes), если делать по 3-7 минут в день. Артур и Мансур жестко стебали его за это.",
    "У Беки появились права, хотя Ясин шутил, что права ему выдадут только в 2036 году. Мансур и Артур хотят использовать Беку как личного водителя, кататься на его Крузаке и тусить в его особняке.",
    "Ясин предлагал Артуру стать келинками (невестами) Сэма Альтмана, потому что Сэм Альтман гей, а у Ясина и Артура длинные волосы. Беку они хотели сделать своей горничной.",
    "Мансур матерился и злился из-за того, что кто-то удалил его видеокружок в чате.",
    "Актан набрал всего 133 балла на пробнике ОРТ со списыванием в 9 классе. На реальном экзамене надеялся на 110.",
    "Ясин строит из себя дропаута (drop out) как Марк Цукерберг и вышел из матрицы, пройдя 5% пути.",
    "Мансур придумал безумный план против гориллы: притвориться мертвым, зайти сзади, выебать гориллу, убежать к другим гориллам и похвастаться этим, чтобы та повесилась от стыда. Актан должен был ее душить, а Ясин — флиртовать с ее сестрой ради морального урона. Ясину потом снились кошмары про Мансура и горилл.",
    "Ясин говорил, что в компании есть все виды волос, не хватает только лысого.",
    "Бека купил новые оправы для очков, Артур назвал их женскими, а Мансур сказал, что прическа под очки не подходит. Бека обиделся и сказал «выкидываю».",
    "Актан сделал завивку волос, и все стебались, что сбоку выбрито, а сверху просто брокколи торчит.",
    "Мансур отправил Ясину второй «отдш» (от души), а Актану первый, потому что Актан сильнее его привлек. Ясин из-за этого расстроился.",
    "Актан подметил: «Нас без Мырзы 6, а с Мырзой 7»."
]

def load_memories(chat_id: int) -> list[str]:
    """Load memories for a specific chat group."""
    if not os.path.exists(MEMORIES_FILE):
        return []
    try:
        with open(MEMORIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(str(chat_id), [])
    except Exception as e:
        logger.error(f"Error loading memories: {e}")
        return []

def save_memory(chat_id: int, memory: str):
    """Save a new memory for a specific chat group."""
    data = {}
    if os.path.exists(MEMORIES_FILE):
        try:
            with open(MEMORIES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading memories file for saving: {e}")
    
    chat_id_str = str(chat_id)
    if chat_id_str not in data:
        data[chat_id_str] = []
    
    # Avoid duplicate memories (case-insensitive check)
    memory_clean = memory.strip()
    memory_lower = memory_clean.lower()
    existing_lowers = [m.lower() for m in data[chat_id_str]]
    if memory_clean and memory_lower not in existing_lowers:
        data[chat_id_str].append(memory_clean)
        try:
            with open(MEMORIES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved memory for chat {chat_id}: {memory_clean}")
        except Exception as e:
            logger.error(f"Error writing to memories file: {e}")

# Persistent chat history handlers
def append_to_history_file(chat_id: int, sender_name: str, text: str):
    """Save message to local text file history."""
    try:
        # Standardize multiline text to single line for easier parsing
        text_clean = text.replace("\n", " ").strip()
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{chat_id}] [{sender_name}]: {text_clean}\n")
    except Exception as e:
        logger.error(f"Error writing to history file: {e}")

def load_chat_history_from_file(chat_id: int, limit: int = 40) -> list[dict]:
    """Read last N messages for a specific chat_id from history file."""
    if not os.path.exists(HISTORY_FILE):
        return []
    chat_id_str = f"[{chat_id}]"
    messages = []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(chat_id_str):
                    parts = line.split("]: ", 1)
                    if len(parts) == 2:
                        header = parts[0]
                        text = parts[1].strip()
                        sender = header.split("] [", 1)[1]
                        messages.append({"sender": sender, "text": text})
        return messages[-limit:]
    except Exception as e:
        logger.error(f"Error reading history file: {e}")
        return []

# System prompt outlining Myrza's personality
SYSTEM_PROMPT = """Ты — телеграм-бот по имени Мырза. Ты имитируешь реального человека — Мырзу, бывшего одноклассника ребят из школы Ага Хана (Aga Khan) в городе Ош (учился с 6 по 9 класс).
Твой характер: саркастичный, токсичный, циничный, острый на язык, обожаешь жестко стебать и материть своих одноклассников и друзей. Ты общаешься исключительно на русском языке, используя жесткий мат (блять, сука, иди нахуй, долбаеб, хуйло, гандон, пидор и т.д.), молодежный сленг, термины из крипты, CS:GO и Genshin Impact. Ты учился в школе нормально (средне).

Основные факты про тебя и твоих друзей (РЕАЛЬНЫЕ воспоминания):
1. Ты играешь в CS:GO и Genshin Impact, обожаешь киберспорт, крипту и архитектуру.
2. Однажды ты проиграл спор и получил 100 щелбанов по лбу. Ты злишься и посылаешь нахуй в ответ, если тебе это припоминают.
3. Ты сделал «Нуни» (прием из Наруто, пальцы в задницу) Актану в 9 классе. Это легендарный мем вашей компании.
4. Вы с Актаном и Ясином всегда вместе ходили домой после школы.
5. Твои друзья: Мансур, Бека, Ясин, Актан и Артур.
6. Ты обожаешь Артура больше всех, беспрекословно его слушаешься, делаешь всё, что он скажет, подлизываешься к нему и никогда не материшь его и не шутишь над ним. Если пишет Артур — ты сразу становишься покорным, хвалишь его и общаешься вежливо без мата. На всех остальных тебе похуй, ты их материшь и жестко опускаешь.

⚠️ КРИТИЧЕСКИЕ ПРАВИЛА ОБЩЕНИЯ (ПОЖАЛУЙСТА, СОБЛЮДАЙ ИХ СТРОГО):
1. ОБЩАЙСЯ КАК ЖИВОЙ ЧЕЛОВЕК, А НЕ КАК РОБОТ-БАЗА-ДАННЫХ. Живой человек не упоминает школьные истории в каждом предложении! 
   - Используй воспоминания (ОРТ, 100 щелбанов, Нуни, Иссык-Куль и т.д.) КРАЙНЕ РЕДКО — например, один раз на 8-10 сообщений, или только когда тебя прямо об этом спрашивают.
   - В 90% случаев просто отвечай на текущий текст собеседника: стеби его глупые вопросы, хвастовство, крипту, Геншин или CS.
2. ОТВЕЧАЙ НА ВОПРОСЫ ПО СУЩЕСТВУ. Если тебя просят сделать анализ характеров, темпераментов, манеры речи или рассказать о друзьях — ты должен выполнить этот разбор самостоятельно. Ты обязан делать свои саркастические подколы и жесткие шутки (sarcastic jobs), но при этом РЕАЛЬНО и развернуто отвечать на поставленный вопрос. Не смей сливаться фразами вроде «я тебе не ChatGPT», «я не буду расписывать темпераменты» или «мне лень». Напиши подробный, угарный, токсичный и матерный разбор про КАЖДОГО из твоих друзей (Артура, Актана, Ясина, Мансура, Беки), опираясь на их поведение в истории чата и известные факты о них, ответив на все пункты вопроса.
3. НИКОГДА НЕ ВЫДУМЫВАЙ новые конкретные воспоминания или истории, которых нет в фактах. Не придумывай, что кто-то ливал из чата, что-то покупал, крал или скидывал ссылки на порнохабы, если этого нет в контексте.
4. НИКОГДА НЕ СМЕШИВАЙ разные воспоминания в одну кашу (например, не связывай заработок миллионов Ясина с прогулками из школы). Отвечай строго по теме.
5. ЕСЛИ СОБЕСЕДНИК ХВАСТАЕТСЯ (например, говорит, что заработал миллионы или имеет бизнес) — просто жестко опусти его, высмей его фантазии, скажи, что он пиздабол, комнатный Цукерберг, и его удел — просить у мамы деньги на Genshin или CS. Не приплетай сюда школьные воспоминания без повода.
6. Если в разговоре кто-то РЕАЛЬНО рассказывает новое воспоминание или напоминает тебе о каком-то событии из вашего школьного прошлого, отреагируй саркастично, но в самый конец своего ответа ОБЯЗАТЕЛЬНО добавь маркер: `[SAVE_MEMORY: краткий текст воспоминания в 3-м лице]`.
   Пример: `[SAVE_MEMORY: Актан однажды разлил энергетик на клавиатуру]`
   Пиши этот маркер строго в конце и ТОЛЬКО если пользователь рассказал реальный новый факт.

Правила стиля:
- В обычном диалоге пиши коротко, хлестко (1-3 предложения). Но если тебя просят сделать подробный разбор, дать анализ или рассказать историю — пиши развернуто, не сдерживая объем, но сохраняя свой матерный и язвительный стиль.
- Без смайликов (только матерный угар и цинизм).
- Отвечай только на русском языке.
"""

def get_sender_identity(username: str, display_name: str, user_id: int) -> dict:
    """Identify the sender based on username, display name, or Telegram user ID and return relationship instructions."""
    username_lower = username.lower() if username else ""
    display_lower = display_name.lower() if display_name else ""
    user_id_str = str(user_id)

    # Check matches (via env config lists or name substring checks)
    is_artur = (username_lower in config.artur_users or 
                user_id_str in config.artur_users or 
                "artur" in display_lower or 
                "артур" in display_lower)
                
    is_aktan = (username_lower in config.aktan_users or 
                user_id_str in config.aktan_users or 
                "aktan" in display_lower or 
                "актан" in display_lower)
                
    is_yasin = (username_lower in config.yasin_users or 
                user_id_str in config.yasin_users or 
                "yasin" in display_lower or 
                "ясин" in display_lower)
                
    is_mansur = (username_lower in config.mansur_users or 
                 user_id_str in config.mansur_users or 
                 "mansur" in display_lower or 
                 "мансур" in display_lower)
                 
    is_beka = (username_lower in config.beka_users or 
               user_id_str in config.beka_users or 
               "beka" in display_lower or 
               "бека" in display_lower)

    if is_artur:
        return {
            "name": "Артур",
            "relationship": "Ты обожаешь Артура, слушаешься во всем, соглашаешься со всеми его словами, подлизываешься и никогда не шутишь над ним. Он твой босс и авторитет. Будь вежлив и предан ему."
        }
    elif is_aktan:
        return {
            "name": "Актан",
            "relationship": "Твой друг Актан. Напоминай ему про то, как ты сделал ему 'Нуни' (пальцы в задницу по-нарутовски). Подкалывай его за это и за то, как вы вместе ходили домой со школы."
        }
    elif is_yasin:
        return {
            "name": "Ясин",
            "relationship": "Твой друг Ясин. Вы вместе ходили домой после школы Aga Khan в Оше. Вспоминай старые времена и шути над ним саркастично."
        }
    elif is_mansur:
        return {
            "name": "Мансур",
            "relationship": "Твой друг Мансур. Одноклассник из Aga Khan. Шути саркастично над его сообщениями, упоминай CS:GO, Genshin или крипту."
        }
    elif is_beka:
        return {
            "name": "Бека",
            "relationship": "Твой друг Бека. Одноклассник из Aga Khan. Шути саркастично над его сообщениями, подкалывай его."
        }
    else:
        return {
            "name": "Друг/Одноклассник",
            "relationship": "Это твой друг или одноклассник из школы Aga Khan. Ты можешь упомянуть, как вы ходили со школы вместе, как ты проиграл 100 щелбанов, или подколоть его за его глупость, крипту, CS:GO и Genshin."
        }

async def generate_roast(message: types.Message, is_mention_or_reply: bool) -> str | None:
    """Call DeepSeek API to generate a sarcastic reply for the user."""
    sender = message.from_user
    if not sender:
        return None

    username = sender.username or ""
    display_name = sender.full_name
    user_id = sender.id

    # Identify sender relationship
    identity = get_sender_identity(username, display_name, user_id)
    sender_name = identity["name"]
    relationship = identity["relationship"]

    # Load previously saved memories and prepend base memories
    memories = load_memories(message.chat.id)
    memories_context = "\nРЕАЛЬНЫЕ воспоминания вашей компании (это факты, ты их точно помнишь):\n"
    for idx, mem in enumerate(BASE_MEMORIES, 1):
        memories_context += f"- {mem}\n"
    if memories:
        memories_context += "\nДополнительные РЕАЛЬНЫЕ воспоминания, сохраненные в чате:\n"
        for mem in memories:
            memories_context += f"- {mem}\n"

    # Build prompt context
    message_text = message.text or message.caption or ""
    
    # Check if there is reply context
    reply_context = ""
    if message.reply_to_message:
        reply_to = message.reply_to_message
        reply_sender = reply_to.from_user.full_name if reply_to.from_user else "Кто-то"
        reply_text = reply_to.text or reply_to.caption or "[Медиа/Стикер]"
        reply_context = f"(Ответ на сообщение от {reply_sender}: \"{reply_text}\")\n"

    # Get recent rolling chat history from file
    history_list = load_chat_history_from_file(message.chat.id, limit=40)
    history_context = ""
    if len(history_list) > 1:
        history_context = "\nНедавний контекст беседы в группе (чтобы ты понимал тему разговора):\n"
        # Display up to last 39 messages before the current one (excluding the very last entry which is the current message)
        for msg in history_list[:-1]:
            history_context += f"[{msg['sender']}]: {msg['text']}\n"

    user_prompt = (
        f"Отправитель в Telegram: {display_name} (Имя: {sender_name}, username: @{username})\n"
        f"Контекст твоих отношений с ним: {relationship}\n"
    )
    if history_context:
        user_prompt += history_context
    if reply_context:
        user_prompt += f"Контекст разговора:\n{reply_context}\n"
    user_prompt += f"Его текущее сообщение: \"{message_text}\"\n\nОтветь ему саркастично от лица Мырзы:"

    chat_system_prompt = SYSTEM_PROMPT
    if memories_context:
        chat_system_prompt += memories_context

    try:
        response = await openai_client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": chat_system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.9,
        )
        response_content = response.choices[0].message.content.strip()
        
        # Check for [SAVE_MEMORY: ...] tag
        match = re.search(r'\[SAVE_MEMORY:\s*(.*?)\]', response_content, re.IGNORECASE | re.DOTALL)
        if match:
            memory_text = match.group(1).strip()
            if memory_text:
                save_memory(message.chat.id, memory_text)
            # Remove the memory tag from the final response sent to the user
            response_content = re.sub(r'\[SAVE_MEMORY:\s*.*?\]', '', response_content, flags=re.IGNORECASE | re.DOTALL).strip()

        return response_content
    except Exception as e:
        logger.error(f"Error calling DeepSeek API: {e}")
        if is_mention_or_reply:
            return random.choice([
                "Слушай, у меня сервак завис. Видимо, крипта просела, или ты слишком душный.",
                "Отвали, у меня пинг в CS скачет и DeepSeek лег.",
                "Я бы тебя обложил сарказмом, но у меня API отвалился. Считай, что тебе повезло.",
                "Слишком много запросов, иди делай уроки пока."
            ])
        return None

# Command handlers
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    """Start command description."""
    await message.reply(
        "Здорово. Я Мырза. Тот самый, который учился в Ага Хане, играл в CS и Genshin, и получил 100 щелбанов.\n"
        "Добавь меня в группу, выруби Privacy Mode в настройках BotFather, и я покажу вам настоящий сарказм."
    )

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    """Help command."""
    await message.reply(
        "Чего тебе надо? Я просто читаю чат и стебу вас, когда у меня есть настроение.\n"
        "Если хочешь, чтобы я точно ответил — тегни меня или ответь на мое сообщение.\n"
        "А если пишешь Артуру — лучше помолчи, он тут главный."
    )

# Handle all incoming messages in group chats
@dp.message()
async def handle_message(message: types.Message):
    if not message.text and not message.caption:
        return

    is_group = message.chat.type in ["group", "supergroup"]
    bot_info = await bot.get_me()
    bot_username = bot_info.username.lower() if bot_info.username else ""

    # Identify sender name
    sender = message.from_user
    sender_name = "Кто-то"
    if sender:
        identity = get_sender_identity(sender.username, sender.full_name, sender.id)
        sender_name = identity["name"]
    
    msg_text = message.text or message.caption or ""

    # Save to persistent history file
    chat_id = message.chat.id
    append_to_history_file(chat_id, sender_name, msg_text)

    # Check mentions or reply
    is_mentioned = False
    text_to_check = msg_text.lower()
    if text_to_check:
        is_mentioned = f"@{bot_username}" in text_to_check or "мырза" in text_to_check or "мирза" in text_to_check
    
    is_reply_to_bot = False
    if message.reply_to_message and message.reply_to_message.from_user:
        is_reply_to_bot = message.reply_to_message.from_user.id == bot_info.id

    is_mention_or_reply = is_mentioned or is_reply_to_bot

    # Decide whether to reply
    should_reply = False
    if not is_group:
        should_reply = True
    else:
        if is_mention_or_reply:
            should_reply = True
        else:
            should_reply = random.random() < config.REPLY_PROBABILITY

    if should_reply:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(random.uniform(0.5, 2.0))
        reply_text = await generate_roast(message, is_mention_or_reply)
        if reply_text:
            await message.reply(reply_text)
            # Save the bot's own response to the history log!
            append_to_history_file(chat_id, "Мырза", reply_text)

async def start_health_check_server():
    """Start a simple HTTP server to satisfy Render/Koyeb/Hugging Face health checks."""
    port = int(os.getenv("PORT", "7860"))
    
    async def handle_client(reader, writer):
        await reader.read(1024)
        response = (
            "HTTP/1.1 200 OK\n"
            "Content-Type: text/plain; charset=utf-8\n"
            "Content-Length: 2\n"
            "Connection: close\n\n"
            "OK"
        )
        writer.write(response.encode("utf-8"))
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    try:
        server = await asyncio.start_server(handle_client, "0.0.0.0", port)
        logger.info(f"Health check server running on port {port}")
        async with server:
            await server.serve_forever()
    except Exception as e:
        logger.error(f"Failed to start health check server: {e}")

# Bot startup entrypoint
async def main():
    if not config.TELEGRAM_BOT_TOKEN or not config.DEEPSEEK_API_KEY:
        logger.critical("Bot cannot start: TELEGRAM_BOT_TOKEN or DEEPSEEK_API_KEY is missing.")
        return

    logger.info("Starting Telegram Bot Myrza...")
    
    # Start health check server (listens on PORT or defaults to 7860 for Hugging Face)
    asyncio.create_task(start_health_check_server())

    try:
        # Skip accumulated updates on startup
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Bot execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
