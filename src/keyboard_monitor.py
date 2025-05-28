import pynput.keyboard
import time
from typing import List, Callable
from Levenshtein import distance as levenshtein_distance

# Placeholder for lockdown function (to be imported from lockdown.py later)
def trigger_lockdown():
    print("[INFO] [trigger_lockdown]: Lockdown triggered")
    print("Haram content detected! Triggering lockdown...") # Debugging, replace with actual lockdown call

class KeyboardMonitor:
    def __init__(self, keywords: List[str], buffer_size: int = 20, lock_callback: Callable = trigger_lockdown):
        """
        Initialize the keyboard monitor.
        """
        print("[DEBUG] [KeyboardMonitor.__init__]: Initializing keyboard monitor")
        print(f"[DEBUG] [KeyboardMonitor.__init__]: Keywords: {keywords}")
        print(f"[DEBUG] [KeyboardMonitor.__init__]: Buffer size: {buffer_size}")
        
        self.keywords = [k.lower() for k in keywords]
        self.buffer_size = buffer_size
        self.keystroke_buffer = [] # List of lists, each containing chars of a word
        self.current_word = [] # List for current word's characters
        self.lock_callback = lock_callback
        self.listener = None
        print("[INFO] [KeyboardMonitor.__init__]: Keyboard monitor initialized successfully")
    
    def on_press(self, key):
        """
        Handle each keypress, build words as char lists (including spaces), and check on Enter or buffer full.
        """
        print(f"[DEBUG] [KeyboardMonitor.on_press]: Key pressed: {key}")
        try:
            if hasattr(key, 'char') and key.char is not None:
                char = key.char.lower()
                # If current_word ends with a space, treat that as a word boundary
                if self.current_word and self.current_word[-1] == ' ':
                    self.keystroke_buffer.append(self.current_word[:-1])  # exclude the space
                    print(f"[DEBUG] [KeyboardMonitor.on_press]: New word started, added word: {self.current_word[:-1]}")
                    self.current_word = []
                self.current_word.append(char)
                print(f"[DEBUG] [KeyboardMonitor.on_press]: Added character to current word: {char}")

            elif key == pynput.keyboard.Key.space:
                self.current_word.append(' ')
                print("[DEBUG] [KeyboardMonitor.on_press]: Space key added as character")

            elif key == pynput.keyboard.Key.backspace:
                if self.current_word:
                    removed_char = self.current_word.pop()
                    print(f"[DEBUG] [KeyboardMonitor.on_press]: Backspace removed char: {removed_char}")
                elif self.keystroke_buffer:
                    # Pop last word from buffer and move to current_word
                    popped_word = self.keystroke_buffer.pop()
                    self.current_word = popped_word
                    print(f"[DEBUG] [KeyboardMonitor.on_press]: Backspace retrieved word from buffer: {popped_word}")
                else:
                    print("[DEBUG] [KeyboardMonitor.on_press]: Backspace ignored (empty buffer and current word)")

            elif key == pynput.keyboard.Key.enter:
                if self.current_word:
                    # If current word ends in space, strip it before saving
                    if self.current_word[-1] == ' ':
                        self.keystroke_buffer.append(self.current_word[:-1])
                        print(f"[DEBUG] [KeyboardMonitor.on_press]: Enter key detected, added word: {self.current_word[:-1]}")
                    else:
                        self.keystroke_buffer.append(self.current_word)
                        print(f"[DEBUG] [KeyboardMonitor.on_press]: Enter key detected, added word: {self.current_word}")
                    self.current_word = []
                print("[DEBUG] [KeyboardMonitor.on_press]: Checking buffer for keywords")
                self.check_buffer()

            # Final buffer check if limit exceeded
            if len(self.keystroke_buffer) > self.buffer_size:
                print("[DEBUG] [KeyboardMonitor.on_press]: Buffer full, checking keywords")
                self.check_buffer()

        except Exception as e:
            print(f"[ERROR] [KeyboardMonitor.on_press]: Error processing key press: {e}")
            print(f"[ERROR] [KeyboardMonitor.on_press]: Current buffer: {self.keystroke_buffer}, Current word: {self.current_word}")

    
    def check_buffer(self):
        """
        Check buffer for blocked keywords using Levenshtein distance.
        """
        print("[DEBUG] [KeyboardMonitor.check_buffer]: Checking buffer for keywords")
        print(f"[DEBUG] [KeyboardMonitor.check_buffer]: Current buffer: {self.keystroke_buffer}")
        for word_chars in self.keystroke_buffer:
            if not word_chars:  # Skip empty words
                continue
            word = ''.join(word_chars).lower()
            print(f"[DEBUG] [KeyboardMonitor.check_buffer]: Checking word: {word}")
            for keyword in self.keywords:
                # Use Levenshtein distance with threshold of 1 for fuzzy matching
                if levenshtein_distance(word, keyword) <= 1 or word == keyword:
                    print(f"[INFO] [KeyboardMonitor.check_buffer]: Keyword detected: {keyword} (matched: {word})")
                    self.lock_callback()
                    self.keystroke_buffer.clear()
                    self.current_word = []
                    print("[INFO] [KeyboardMonitor.check_buffer]: Buffer and current word cleared after keyword detection")
                    return
        # If buffer is full and no match, clear buffer
        if len(self.keystroke_buffer) >= self.buffer_size:
            print("[INFO] [KeyboardMonitor.check_buffer]: Buffer full, no keywords detected, clearing buffer")
            self.keystroke_buffer.clear()
            self.current_word = []
    
    def start(self):
        """
        Start the keyboard listener.
        """
        print("[INFO] [KeyboardMonitor.start]: Starting keyboard listener")
        self.listener = pynput.keyboard.Listener(on_press=self.on_press)
        self.listener.start()
        print("[INFO] [KeyboardMonitor.start]: Keyboard listener started successfully")
    
    def stop(self):
        """
        Stop the keyboard listener.
        """
        print("[INFO] [KeyboardMonitor.stop]: Stopping keyboard listener")
        if self.listener:
            self.listener.stop()
            self.listener = None
            print("[INFO] [KeyboardMonitor.stop]: Keyboard listener stopped successfully")
        else:
            print("[WARNING] [KeyboardMonitor.stop]: No active listener to stop")

def main():
    print("[INFO] [main]: Starting main function")
    blocked_keywords = ["porn", "adult", "nsfw", "xxx", "sex", "nude", "hentai", "erotic", "fetish", "kink", "mature", "spicy", "fitgirl", "dodi", "pussy", "anal", "boobs", "sexy", "naked", "bikini", "lingerie", "striptease"]
    print(f"[DEBUG] [main]: Blocked keywords loaded: {len(blocked_keywords)}")
    monitor = KeyboardMonitor(keywords=blocked_keywords, buffer_size=10)
    monitor.start()
    print("[INFO] [main]: Keyboard monitor running")
    try:
        while True:
            time.sleep(1) # Keep main thread alive
    except KeyboardInterrupt:
        print("[INFO] [main]: Keyboard interrupt detected, stopping monitor")
        monitor.stop()
        print("[INFO] [main]: Keyboard monitor terminated")

if __name__ == "__main__":
    print("[INFO] [__main__]: Starting keyboard monitor application")
    main()
    print("[INFO] [__main__]: Application terminated")