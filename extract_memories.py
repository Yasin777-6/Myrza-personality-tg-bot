import os
import re
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

HISTORY_FILE = "chat_history.txt"
MEMORIES_OUTPUT = "extracted_memories.json"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        print(f"Error: {HISTORY_FILE} not found.")
        return []
    
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    pattern = re.compile(r'^\[(-?\d+)\]\s+\[(.*?)\]:\s*(.*)$')
    messages = []
    
    for line in lines:
        line = line.strip()
        match = pattern.match(line)
        if match:
            sender = match.group(2).strip()
            text = match.group(3).strip()
            if sender != "Мырза" and sender != "Myrza" and len(text) > 0:
                messages.append((sender, text))
                
    return messages

def find_interesting_contexts(messages):
    keywords = ["помнишь", "помню", "когда", "тогда", "мем", "история", "ору", "ахаха", "лол", "нуни", "орт", "щелбан", "брокколи", "завивк", "келин"]
    contexts = []
    
    # We will search for keywords, and extract 8 messages around them
    for i, (sender, text) in enumerate(messages):
        text_lower = text.lower()
        if any(kw in text_lower for kw in keywords):
            start = max(0, i - 4)
            end = min(len(messages), i + 5)
            context_slice = messages[start:end]
            context_str = "\n".join([f"[{s}]: {t}" for s, t in context_slice])
            contexts.append(context_str)
            
    # Sample up to 150 diverse contexts to stay within token limits
    import random
    random.seed(42)
    if len(contexts) > 150:
        contexts = random.sample(contexts, 150)
        
    return contexts

def extract_memories_via_llm(contexts, api_key):
    print(f"Sending {len(contexts)} context snippets to DeepSeek for memory extraction...")
    
    joined_contexts = "\n\n--- КОНТЕКСТ ---\n\n".join(contexts)
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )
    
    prompt = f"""Ниже представлены фрагменты реальных диалогов из группового чата друзей (Артур, Актан, Ясин, Мансур, Бека/Атабек).
Твоя задача — извлечь из этих диалогов РЕАЛЬНЫЕ воспоминания, внутригрупповые мемы, шутки, споры, смешные ситуации или факты о ребятах.

Фрагменты диалогов:
{joined_contexts}

На основе этих диалогов составь список из 20-25 конкретных воспоминаний/фактов на русском языке.
Каждое воспоминание должно быть сформулировано в третьем лице как одно-два понятных, емких предложения.
Формат вывода — строго JSON-массив строк:
[
  "ФАКТ 1",
  "ФАКТ 2",
  ...
]

Правила извлечения:
- Извлекай только РЕАЛЬНЫЕ воспоминания и мемы, которые обсуждаются в чате. Не придумывай ничего от себя.
- Не включай банальные фразы типа "они общаются" или "они шутят". Пиши конкретные факты: кто что сказал, сделал, где проиграл, про какие прически шутили, про учебу, IELTS, баллы ОРТ, споры про mewing/looksmaxxing, Крузаки, мемы про горилл и т.д.
- Каждое воспоминание должно быть самодостаточным.
- Избегай дублирования.
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Ты эксперт по анализу чатов и извлечению фактов. Отвечай только валидным JSON-массивом строк."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        if isinstance(data, dict) and "memories" in data:
            return data["memories"]
        elif isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Check if it has any list values
            for val in data.values():
                if isinstance(val, list):
                    return val
        return []
    except Exception as e:
        print(f"Error extracting memories: {e}")
        return []

def main():
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY not found.")
        return
        
    messages = load_history()
    if not messages:
        return
        
    contexts = find_interesting_contexts(messages)
    print(f"Found {len(contexts)} context snippets.")
    
    memories = extract_memories_via_llm(contexts, api_key)
    
    if memories:
        print(f"Extracted {len(memories)} memories!")
        with open(MEMORIES_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
        print(f"Saved to {MEMORIES_OUTPUT}")
    else:
        print("Failed to extract memories.")

if __name__ == "__main__":
    main()
