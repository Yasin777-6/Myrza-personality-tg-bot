import os
import re
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

HISTORY_FILE = "chat_history.txt"
MEMORIES_OUTPUT = "base_memories.json"

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

def extract_chunk_memories(chunk_msgs, chunk_num, total_chunks, client):
    print(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk_msgs)} messages)...", flush=True)
    
    # Format messages for prompt
    chunk_text = "\n".join([f"[{sender}]: {text}" for sender, text in chunk_msgs])
    
    prompt = f"""Ниже представлен фрагмент реальной переписки из группового чата друзей.
Твоя задача — извлечь из него ВСЕ реальные воспоминания, мемы, шутки, споры, смешные ситуации или факты о ребятах (Артур, Актан, Ясин, Мансур, Бека/Атабек).

Фрагмент переписки:
{chunk_text}

Составь список всех извлеченных воспоминаний/фактов на русском языке.
Каждое воспоминание сформулируй в третьем лице как одно-два понятных предложения.
Формат вывода — строго JSON-массив строк:
[
  "ФАКТ 1",
  "ФАКТ 2",
  ...
]

Правила извлечения:
- Извлекай только реальные факты и шутки, упомянутые в чате.
- Формулируй конкретно (кто что сделал, сказал, где проиграл, про прически, учебу, IELTS, баллы ОРТ, мьюинг, Крузак и т.д.).
- Не придумывай ничего от себя. Если в этом фрагменте нет интересных воспоминаний, верни пустой массив [].
"""

    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Ты эксперт по анализу чатов и извлечению фактов. Отвечай только валидным JSON-массивом строк."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                timeout=25.0
            )
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            
            # Extract the array from the JSON response
            memories = []
            if isinstance(data, list):
                memories = data
            elif isinstance(data, dict):
                for val in data.values():
                    if isinstance(val, list):
                        memories = val
                        break
                else:
                    memories = list(data.values())
            
            print(f"Chunk {chunk_num}/{total_chunks}: Extracted {len(memories)} memories on attempt {attempt}.", flush=True)
            return memories
        except Exception as e:
            print(f"Error on chunk {chunk_num} attempt {attempt}: {e}", flush=True)
            if attempt < 3:
                time.sleep(2)
            else:
                print(f"Failed to process chunk {chunk_num} after 3 attempts.", flush=True)
                return []

def deduplicate_memories(all_memories, client):
    print(f"Deduplicating and consolidating {len(all_memories)} total extracted memories...", flush=True)
    
    # Send in chunks if it is too big, but usually under 200 items is fine.
    # Just in case, if the list is huge, we will slice it to the first 250 items.
    if len(all_memories) > 250:
        print(f"Warning: too many memories ({len(all_memories)}). Truncating to first 250 to prevent context limit issues.", flush=True)
        all_memories = all_memories[:250]
        
    memories_text = "\n".join([f"- {m}" for m in all_memories])
    
    prompt = f"""Ниже представлен список воспоминаний и фактов о друзьях, извлеченных из чата. В нем много дубликатов, похожих фактов или неточных формулировок.
Твоя задача — объединить похожие воспоминания, убрать дубликаты, исправить опечатки и сделать формулировки более живыми и понятными.

Список воспоминаний:
{memories_text}

Объедини их и выведи консолидированный, очищенный и максимально полный список уникальных воспоминаний/фактов на русском языке.
Каждое воспоминание должно быть в третьем лице. Сохрани все уникальные детали (имена, баллы, конкретные случаи).
Формат вывода — строго JSON-массив строк:
[
  "ФАКТ 1",
  "ФАКТ 2",
  ...
]
"""

    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Ты эксперт по редактированию и консолидации данных. Отвечай только валидным JSON-массивом строк."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                timeout=30.0
            )
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            
            consolidated = []
            if isinstance(data, list):
                consolidated = data
            elif isinstance(data, dict):
                for val in data.values():
                    if isinstance(val, list):
                        consolidated = val
                        break
            
            print(f"Consolidated into {len(consolidated)} unique memories on attempt {attempt}.", flush=True)
            return consolidated
        except Exception as e:
            print(f"Error during deduplication on attempt {attempt}: {e}", flush=True)
            if attempt < 3:
                time.sleep(2)
            else:
                print("Deduplication failed after 3 attempts.", flush=True)
                return list(set(all_memories))

def main():
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY not found.", flush=True)
        return
        
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=30.0
    )
    
    messages = load_history()
    if not messages:
        return
        
    print(f"Total messages to process: {len(messages)}", flush=True)
    
    # We split history into chunks of 1500 messages
    chunk_size = 1500
    chunks = [messages[i:i + chunk_size] for i in range(0, len(messages), chunk_size)]
    total_chunks = len(chunks)
    
    all_extracted_memories = []
    
    for idx, chunk in enumerate(chunks, 1):
        memories = extract_chunk_memories(chunk, idx, total_chunks, client)
        all_extracted_memories.extend(memories)
        time.sleep(0.5) # Rate limit safety
        
    all_extracted_memories = [str(m).strip() for m in all_extracted_memories if m]
    
    if not all_extracted_memories:
        print("No memories were extracted.", flush=True)
        return
        
    final_memories = deduplicate_memories(all_extracted_memories, client)
    
    if final_memories:
        with open(MEMORIES_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(final_memories, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(final_memories)} unique memories to {MEMORIES_OUTPUT}!", flush=True)
    else:
        print("Failed to save memories.", flush=True)

if __name__ == "__main__":
    main()
