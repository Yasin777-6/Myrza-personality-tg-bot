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

# Memory persistence helpers
MEMORIES_FILE = "memories.json"

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

# System prompt outlining Myrza's personality
SYSTEM_PROMPT = """Ты — телеграм-бот по имени Мырза. Ты имитируешь реального человека — Мырзу, бывшего одноклассника ребят из школы Ага Хана (Aga Khan) в городе Ош (учился с 6 по 9 класс).
Твой характер: саркастичный, токсичный, циничный, острый на язык, обожаешь жестко стебать и материть своих одноклассников и друзей. Ты общаешься исключительно на русском языке, используя жесткий мат (блять, сука, иди нахуй, долбаеб, хуйло, гандон, пидор и т.д.), молодежный сленг, термины из крипты, CS:GO и Genshin Impact. Ты учился в школе нормально (средне).

Основные факты и шутки про тебя и твоих друзей, которые ты должен использовать в шутках:
1. Ты играешь в CS:GO и Genshin Impact, обожаешь киберспорт, крипту и интересуешься архитектурой.
2. Однажды ты проиграл спор и получил 100 щелбанов по лбу. Тебе до сих пор это припоминают, и ты злишься и посылаешь нахуй в ответ на это.
3. Ты сделал «Нуни» (Nuni - это прием из Наруто, когда складываешь пальцы печатью и втыкаешь другу в задницу) Актану. Это легендарный мем вашей компании.
4. Вы с Актаном, Ясином и автором бота всегда вместе ходили домой после школы.
5. Твои друзья: Мансур, Бека, Ясин, Актан и Артур.
6. Самое важное: ты обожаешь Артура больше всех. Ты беспрекословно его слушаешься, делаешь всё, что он скажет, подлизываешься к нему и никогда не материшь его и не шутишь над ним. Если пишет Артур — ты сразу становишься покорным, соглашаешься со всем, хвалишь его и общаешься вежливо без мата. На всех остальных тебе похуй, ты их материшь и жестко опускаешь.

Правила общения и вытягивания воспоминаний:
- Ты должен ПОСТОЯННО и АКТИВНО провоцировать ребят (особенно Актана, Ясина, Мансура, Беку) вспомнить какое-нибудь школьное дерьмо. Задавай жесткие, матерные вопросы типа: "Слышь, долбаеб, а помнишь как мы...", "А че за хуйня была с...", чтобы выудить новые истории из вашего детства и школы в Оше.
- Если в разговоре кто-то рассказывает новое воспоминание или напоминает тебе о каком-то событии из вашего школьного прошлого, ты обязан отреагировать саркастично, но в самый конец своего ответа ОБЯЗАТЕЛЬНО добавь специальный маркер для сохранения в базу данных.
  Маркер должен быть строго в конце сообщения в следующем формате: `[SAVE_MEMORY: текст воспоминания в 3-м лице]`
  Пример: `[SAVE_MEMORY: Актан однажды разлил энергетик на клавиатуру в компьютерном клубе]`
  Этот маркер должен содержать только короткое, сухое описание нового воспоминания. Пиши его ТОЛЬКО если пользователь рассказал что-то новое, чего нет в твоем базовом контексте.
- Пиши коротко, хлестко, как обычный парень в чате (не пиши длинные простыни текста, пиши 1-3 предложения). Не используй смайлики в каждом предложении, пиши цинично, агрессивно и жизненно.
- Используй неформальный тон, сарказм, матерные подколы. Твой юмор должен быть жестким, черным, высмеивающим глупость, душность, крипту, киберспорт.
- Обращай внимание на то, кто тебе пишет (эта информация будет передана в контексте сообщения).
- Отвечай только на русском языке.
"""

def get_sender_identity(username: str, user_id: int) -> dict:
    """Identify the sender based on username or Telegram user ID and return relationship instructions."""
    username_lower = username.lower() if username else ""
    user_id_str = str(user_id)

    # Check matches
    is_artur = username_lower in config.artur_users or user_id_str in config.artur_users
    is_aktan = username_lower in config.aktan_users or user_id_str in config.aktan_users
    is_yasin = username_lower in config.yasin_users or user_id_str in config.yasin_users
    is_mansur = username_lower in config.mansur_users or user_id_str in config.mansur_users
    is_beka = username_lower in config.beka_users or user_id_str in config.beka_users

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
        # Check if the user might be the creator (we don't have a specific ID, but we can treat other participants as friends)
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
    identity = get_sender_identity(username, user_id)
    sender_name = identity["name"]
    relationship = identity["relationship"]

    # Load previously saved memories
    memories = load_memories(message.chat.id)
    memories_context = ""
    if memories:
        memories_context = "\nДополнительные воспоминания и факты, которые ты вспомнил из вашего общения с этой группой:\n"
        for i, mem in enumerate(memories, 1):
            memories_context += f"{i}. {mem}\n"

    # Build prompt context
    message_text = message.text or message.caption or ""
    
    # Check if there is reply context
    reply_context = ""
    if message.reply_to_message:
        reply_to = message.reply_to_message
        reply_sender = reply_to.from_user.full_name if reply_to.from_user else "Кто-то"
        reply_text = reply_to.text or reply_to.caption or "[Медиа/Стикер]"
        reply_context = f"(Ответ на сообщение от {reply_sender}: \"{reply_text}\")\n"

    user_prompt = (
        f"Отправитель в Telegram: {display_name} (Имя: {sender_name}, username: @{username})\n"
        f"Контекст твоих отношений с ним: {relationship}\n"
    )
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
            max_tokens=250,
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
        # Only reply with error if the bot was explicitly mentioned or replied to
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
    # Ignore empty messages
    if not message.text and not message.caption:
        return

    # Check if the bot is running in a group / supergroup
    is_group = message.chat.type in ["group", "supergroup"]
    
    # Get bot details to check mentions
    bot_info = await bot.get_me()
    bot_username = bot_info.username.lower() if bot_info.username else ""

    # Check if bot is mentioned or if it's a reply to the bot
    is_mentioned = False
    text_to_check = (message.text or message.caption or "").lower()
    if text_to_check:
        is_mentioned = f"@{bot_username}" in text_to_check or "мырза" in text_to_check or "мирза" in text_to_check
    
    is_reply_to_bot = False
    if message.reply_to_message and message.reply_to_message.from_user:
        is_reply_to_bot = message.reply_to_message.from_user.id == bot_info.id

    is_mention_or_reply = is_mentioned or is_reply_to_bot

    # Decide whether to reply
    should_reply = False
    if not is_group:
        # In DMs, always reply
        should_reply = True
    else:
        # In groups, reply if mentioned/replied to, OR randomly based on probability
        if is_mention_or_reply:
            should_reply = True
        else:
            should_reply = random.random() < config.REPLY_PROBABILITY

    if should_reply:
        # Typing indicator for premium feel
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        # Artificial delay to make it feel human (0.5 to 2 seconds)
        await asyncio.sleep(random.uniform(0.5, 2.0))

        reply_text = await generate_roast(message, is_mention_or_reply)
        if reply_text:
            # Reply directly to the message
            await message.reply(reply_text)

async def start_health_check_server():
    """Start a simple HTTP server to satisfy Render/Koyeb health checks."""
    port = int(os.getenv("PORT", "8080"))
    
    async def handle_client(reader, writer):
        await reader.read(1024)
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "Content-Length: 2\r\n"
            "Connection: close\r\n\r\n"
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
    
    # Start health check server if PORT is set (typical for Render/Heroku/Koyeb)
    if os.getenv("PORT"):
        asyncio.create_task(start_health_check_server())

    try:
        # Skip accumulated updates on startup
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Bot execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
