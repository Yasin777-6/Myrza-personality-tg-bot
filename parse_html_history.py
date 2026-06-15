import os
import glob
import re
from html.parser import HTMLParser

class TelegramHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.messages = []
        self.depth = 0
        
        # Tracking depths
        self.message_depth = -1
        self.from_depth = -1
        self.text_depth = -1
        
        self.in_from_name = False
        self.in_text = False
        self.last_sender = "Кто-то"
        
        self.current_sender = ""
        self.current_text_parts = []

    def handle_starttag(self, tag, attrs):
        self.depth += 1
        attrs_dict = dict(attrs)
        class_val = attrs_dict.get("class", "")
        
        # Check for message container
        if tag == "div" and "message default" in class_val:
            self.message_depth = self.depth
            self.current_text_parts = []
            if "joined" in class_val:
                self.current_sender = self.last_sender
            else:
                self.current_sender = ""
                
        elif self.message_depth != -1:
            if tag == "div" and class_val == "from_name":
                self.in_from_name = True
                self.from_depth = self.depth
            elif tag == "div" and class_val == "text":
                self.in_text = True
                self.text_depth = self.depth

    def handle_endtag(self, tag):
        if self.message_depth != -1:
            if tag == "div" and self.in_from_name and self.depth == self.from_depth:
                self.in_from_name = False
                self.from_depth = -1
            elif tag == "div" and self.in_text and self.depth == self.text_depth:
                self.in_text = False
                self.text_depth = -1
                
            if self.depth == self.message_depth:
                # Save the complete message
                text = "".join(self.current_text_parts).strip()
                sender = self.current_sender.strip() if self.current_sender else self.last_sender
                if sender and text:
                    self.messages.append({"sender": sender, "text": text})
                self.message_depth = -1
                
        self.depth -= 1

    def handle_data(self, data):
        if self.message_depth != -1:
            if self.in_from_name:
                self.current_sender += data
                self.last_sender = data.strip()
            elif self.in_text:
                self.current_text_parts.append(data)

def get_file_num(filepath):
    """Sort files chronologically: messages.html, messages2.html ... messages12.html"""
    filename = os.path.basename(filepath)
    if filename == "messages.html":
        return 1
    match = re.search(r'messages(\d+)\.html', filename)
    if match:
        return int(match.group(1))
    return 9999

def main():
    print("\n--- HTML Chat History Parser ---")
    
    # Check for HTML files
    html_files = sorted(glob.glob("messages*.html"), key=get_file_num)
    if not html_files:
        print("[!] Error: No messages*.html files found in the current directory.")
        return

    print(f"Found {len(html_files)} HTML files to parse: {', '.join([os.path.basename(f) for f in html_files])}")

    chat_id = input("Enter your Telegram Group Chat ID (e.g. -1002235948332): ").strip()
    if not chat_id:
        print("[!] Error: Chat ID is required.")
        return

    output_file = "chat_history.txt"
    total_messages = 0

    # Open history file for appending
    try:
        with open(output_file, "a", encoding="utf-8") as out_f:
            for filepath in html_files:
                print(f"Parsing {os.path.basename(filepath)}...", end="", flush=True)
                
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        html_content = f.read()
                except Exception as e:
                    print(f" [!] Error reading: {e}")
                    continue
                
                parser = TelegramHTMLParser()
                parser.feed(html_content)
                
                # Write messages to chat_history.txt
                file_count = 0
                for msg in parser.messages:
                    sender = msg["sender"]
                    text = msg["text"]
                    
                    # Normalize sender names to match our bot definitions
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

                    # Clean up text (remove newlines)
                    text_clean = text.replace("\n", " ").strip()
                    if text_clean:
                        out_f.write(f"[{chat_id}] [{sender_std}]: {text_clean}\n")
                        file_count += 1
                        total_messages += 1
                
                print(f" parsed {file_count} messages.")
                
        print(f"\n[+] Success! Imported a total of {total_messages} messages into '{output_file}'.")
        print("    You can now push the updated 'chat_history.txt' to Git/Hugging Face.")
        
    except Exception as e:
        print(f"[!] Error writing to output file: {e}")

if __name__ == "__main__":
    main()
