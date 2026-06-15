import re
import os
import json
from collections import Counter
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

HISTORY_FILE = "chat_history.txt"
OUTPUT_FILE = "group_analysis.json"

# Common Russian stop words to filter out for vocabulary analysis
STOP_WORDS = set([
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то", "все", "она", "так", "его", "но", "да", "ты",
    "к", "у", "же", "вы", "за", "бы", "по", "только", "ее", "мне", "было", "вот", "от", "меня", "еще", "нет", "о", "из", "ему",
    "им", "кто", "чтобы", "уже", "когда", "даже", "ну", "вдруг", "ли", "если", "уже", "или", "ни", "быть", "был", "него", "до",
    "вас", "нибудь", "опять", "уж", "вам", "ведь", "там", "потом", "себя", "ничего", "ей", "может", "они", "тут", "где", "есть",
    "надо", "ней", "для", "мы", "тебя", "их", "чем", "была", "сам", "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под",
    "будет", "ж", "тогда", "кто", "этот", "того", "потому", "этого", "какой", "совсем", "ним", "здесь", "этом", "один", "почти",
    "мой", "тем", "чтобы", "нее", "сейчас", "были", "куда", "зачем", "всех", "никогда", "можно", "при", "два", "три", "один",
    "че", "чо", "блять", "сука", "нах", "нахуй", "это", "просто", "как", "так", "типа", "вообще", "вобще", "ща", "еще", "ещё", "это", "этого"
])

def clean_word(word):
    word = word.lower()
    word = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9-]', '', word)
    return word

def analyze_stats():
    if not os.path.exists(HISTORY_FILE):
        print(f"Error: {HISTORY_FILE} not found.")
        return None

    print("Reading chat history...")
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print(f"Total lines: {len(lines)}")
    
    # We will match pattern: [<chat_id>] [<sender_name>]: <text>
    pattern = re.compile(r'^\[(-?\d+)\]\s+\[(.*?)\]:\s*(.*)$')
    
    user_messages = {}
    total_valid = 0

    for line in lines:
        line = line.strip()
        match = pattern.match(line)
        if match:
            chat_id = match.group(1)
            sender = match.group(2).strip()
            text = match.group(3).strip()
            
            # Skip messages from Myrza bot itself to avoid feedback loops in analysis
            if sender == "Мырза" or sender == "Myrza":
                continue
                
            if sender not in user_messages:
                user_messages[sender] = []
            
            user_messages[sender].append(text)
            total_valid += 1

    print(f"Parsed {total_valid} valid messages from users: {list(user_messages.keys())}")
    
    # Generate stats per user
    stats = {}
    for sender, msgs in user_messages.items():
        total_msgs = len(msgs)
        avg_len = sum(len(m) for m in msgs) / total_msgs if total_msgs > 0 else 0
        
        # Word frequency
        all_words = []
        for m in msgs:
            words = m.split()
            for w in words:
                cleaned = clean_word(w)
                if cleaned and len(cleaned) > 2 and cleaned not in STOP_WORDS:
                    all_words.append(cleaned)
        
        top_words = [pair[0] for pair in Counter(all_words).most_common(20)]
        
        stats[sender] = {
            "message_count": total_msgs,
            "avg_length": round(avg_len, 1),
            "top_words": top_words,
            "all_messages": msgs
        }
        
    return stats

def run_llm_analysis(sender, user_stats, api_key):
    print(f"Running LLM analysis for {sender}...")
    
    all_msgs = user_stats[sender]["all_messages"]
    # Filter out empty or extremely short messages
    substantive_msgs = [m for m in all_msgs if len(m) > 15]
    if not substantive_msgs:
        substantive_msgs = all_msgs
        
    # Take a diverse sample of up to 400 messages to fit well in LLM context
    sample_size = min(400, len(substantive_msgs))
    if sample_size > 0:
        step = max(1, len(substantive_msgs) // sample_size)
        sample = [substantive_msgs[i] for i in range(0, len(substantive_msgs), step)][:sample_size]
    else:
        sample = []

    sample_text = "\n".join([f"- {msg}" for msg in sample])
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )
    
    prompt = f"""Ниже представлены реальные сообщения пользователя по имени '{sender}' из нашего группового чата в Telegram.
Проанализируй эти сообщения и составь подробный профиль этого человека.

Пример сообщений пользователя {sender}:
{sample_text}

На основе этих сообщений напиши подробный анализ на русском языке по следующим пунктам:
1. **Характер и темперамент**: Кто он в компании? Какой у него психотип, характер, отношение к жизни и к друзьям? Он спокойный, агрессивный, душный, шутник, хвастун или криптан-мечтатель?
2. **Манера речи и словечки**: Какой сленг, маты, специфические слова или фразы он использует чаще всего? Опиши его стиль письма (короткие/длинные сообщения, знаки препинания, капс и т.д.).
3. **Главные темы общения**: О чем он чаще всего говорит или спорит в чате? (например: компьютерные игры, криптовалюта, учеба, личная жизнь, мемы, мьюинг/внешность и т.д.).
4. **Уникальные мемы и факты**: Какие специфические истории, шутки, подколы или факты о нем видны из сообщений? (например, споры с кем-то, глупые идеи, хвастовство, провалы).

Будь объективен, пиши подробно, но емко. Этот анализ будет использоваться для того, чтобы Telegram-бот Мырза знал реальный характер и манеру речи этого человека и мог использовать эти факты в диалоге.
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Ты профессиональный аналитик поведения и психологии общения в чатах."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling DeepSeek API for {sender}: {e}")
        return "Не удалось сгенерировать профиль из-за ошибки API."

def main():
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY not found in env variables.")
        return

    stats = analyze_stats()
    if not stats:
        return

    target_members = ["Артур", "Актан", "Ясин", "Мансур", "Бека"]
    
    canonical_mapping = {}
    for sender in stats.keys():
        sender_lower = sender.lower()
        if "артур" in sender_lower or "thereisnohope" in sender_lower:
            canonical_mapping[sender] = "Артур"
        elif "актан" in sender_lower or "wak_kfu" in sender_lower or "актана" in sender_lower:
            canonical_mapping[sender] = "Актан"
        elif "ясин" in sender_lower or "yasin" in sender_lower:
            canonical_mapping[sender] = "Ясин"
        elif "мансур" in sender_lower or "mall1aners" in sender_lower:
            canonical_mapping[sender] = "Мансур"
        elif "бека" in sender_lower or "ineverwanted" in sender_lower or "бек" in sender_lower:
            canonical_mapping[sender] = "Бека"

    print("Canonical mappings found:")
    for k, v in canonical_mapping.items():
        print(f"  '{k}' -> '{v}'")

    combined_stats = {}
    for sender, data in stats.items():
        canonical = canonical_mapping.get(sender)
        if not canonical:
            continue
        if canonical not in combined_stats:
            combined_stats[canonical] = {
                "message_count": 0,
                "avg_length": 0,
                "top_words": [],
                "all_messages": []
            }
        
        c_data = combined_stats[canonical]
        c_data["message_count"] += data["message_count"]
        c_data["all_messages"].extend(data["all_messages"])
        c_data["top_words"].extend(data["top_words"])

    for canonical, data in combined_stats.items():
        data["avg_length"] = round(sum(len(m) for m in data["all_messages"]) / data["message_count"], 1)
        all_words = []
        for m in data["all_messages"]:
            for w in m.split():
                cleaned = clean_word(w)
                if cleaned and len(cleaned) > 2 and cleaned not in STOP_WORDS:
                    all_words.append(cleaned)
        data["top_words"] = [pair[0] for pair in Counter(all_words).most_common(20)]

    final_analysis = {}
    for member in target_members:
        if member in combined_stats:
            profile = run_llm_analysis(member, combined_stats, api_key)
            final_analysis[member] = {
                "message_count": combined_stats[member]["message_count"],
                "avg_length": combined_stats[member]["avg_length"],
                "top_words": combined_stats[member]["top_words"],
                "profile": profile
            }
        else:
            print(f"Warning: Member '{member}' not found in chat history statistics.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_analysis, f, ensure_ascii=False, indent=2)

    print(f"Analysis successfully completed and saved to {OUTPUT_FILE}!")

if __name__ == "__main__":
    main()
