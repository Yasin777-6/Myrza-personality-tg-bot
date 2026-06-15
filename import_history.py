import json
import os
import sys

def extract_text(text_val):
    """Recursively extract text from Telegram exported JSON message structures."""
    if isinstance(text_val, str):
        return text_val
    if isinstance(text_val, list):
        out = []
        for item in text_val:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict) and "text" in item:
                out.append(item["text"])
        return "".join(out)
    return ""

def main():
    json_path = "result.json"
    if not os.path.exists(json_path):
        print("\n[!] Error: 'result.json' not found in the current directory.")
        print("    Please export your chat from Telegram Desktop as JSON and save it here as 'result.json'.")
        return

    print("\n--- Telegram Chat History Importer ---")
    chat_id = input("Enter your Telegram Group Chat ID (e.g. -1002235948332): ").strip()
    if not chat_id:
        print("[!] Error: Chat ID is required.")
        return

    # Load JSON file
    print("Reading result.json, please wait...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[!] Error reading JSON: {e}")
        return

    messages = data.get("messages", [])
    print(f"Loaded {len(messages)} messages from export.")

    output_file = "chat_history.txt"
    count = 0
    
    # Append to existing chat history file
    try:
        with open(output_file, "a", encoding="utf-8") as out_f:
            for msg in messages:
                if msg.get("type") != "message":
                    continue
                
                sender = msg.get("from")
                text = extract_text(msg.get("text", ""))
                
                if not sender or not text:
                    continue

                # Standardize sender names to match bot configurations
                sender_lower = sender.lower()
                if "ясин" in sender_lower or "yasin" in sender_lower:
                    sender_std = "Ясин"
                elif "актан" in sender_lower or "aktan" in sender_lower:
                    sender_std = "Актан"
                elif "артур" in sender_lower or "artur" in sender_lower:
                    sender_std = "Артур"
                elif "мансур" in sender_lower or "mansur" in sender_lower:
                    sender_std = "Мансур"
                elif "бека" in sender_lower or "beka" in sender_lower:
                    sender_std = "Бека"
                elif "мырза" in sender_lower or "myrza" in sender_lower:
                    sender_std = "Мырза"
                else:
                    sender_std = sender

                # Clean up text for the log (remove linebreaks)
                text_clean = text.replace("\n", " ").strip()
                if text_clean:
                    out_f.write(f"[{chat_id}] [{sender_std}]: {text_clean}\n")
                    count += 1
        
        print(f"\n[+] Success! Imported {count} messages directly to '{output_file}'.")
        print("    You can now push the updated 'chat_history.txt' to Git/Render/Hugging Face.")
    except Exception as e:
        print(f"[!] Error writing to history file: {e}")

if __name__ == "__main__":
    main()
