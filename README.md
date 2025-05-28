ImaanGuard
Stealth Windows System Lockdown & Keyword Detection Tool
Helping users break digital addictions and enforce self-control with uncompromising lockdown measures.

Overview
ImaanGuard is a powerful, stealthy Windows application designed to detect forbidden keywords in real-time keystrokes and instantly lock down the system. It disables all inputs except a registered wired mouse, cuts internet access, and blocks USB/Bluetooth devices — enforcing discipline for those struggling with harmful digital habits such as pornography, gambling, or distracting content.

This tool aims to be the ultimate personal guardian, helping users regain control of their digital environment and maintain a focused, addiction-free lifestyle.

Why ImaanGuard?
In today’s digital age, temptations and distractions are everywhere — often leading to unhealthy habits that impact productivity, mental health, and spiritual well-being. Traditional parental controls or screen timers can be bypassed easily.

ImaanGuard goes deeper:

Real-time detection of varied keyword forms using fuzzy matching.

Full system lockdown with strict input and network controls.

Persistent lock that survives shutdowns and restarts.

Anti-bypass mechanisms to prevent circumvention.

Dynamic lock durations escalating with repeated violations.

Optional mercy mode to reduce penalties with positive actions.

ImaanGuard is not just software — it’s a disciplined lifestyle companion, empowering users to uphold their personal and spiritual commitments.

Features
Real-time Keystroke Monitoring with fuzzy keyword detection (e.g., “p0rn”, “pornography”).

Full Lockdown Mode: Disables keyboard, touchpad, USB devices (except registered wired mouse), internet, Bluetooth, taskbar, and notifications.

Persistent Lock: Lockout continues through shutdowns and restarts, reapplying remaining lock duration on boot.

Dynamic Lock Duration: Starts at 2 hours, doubles with each violation, capped at 24 hours; decreases after violation-free periods.

Anti-Bypass: Detects and penalizes uninstall attempts, process kills, time manipulation, and file tampering.

Encrypted Logs & Session Data: All data stored securely using AES encryption.

Stealth Operation: Hidden process name, auto-restart on kill, admin-level protection on uninstall.

Mercy Mode: User can reduce lock duration by interacting with on-screen positive content once per lock.

Safe Mode & Shutdown Protection: Locks apply even in Safe Mode, blocks shutdown/restart attempts during lockdown.

Installation
Clone the repository:

git clone https://github.com/yourusername/ImaanGuard.git
cd ImaanGuard
Install dependencies:

pip install -r requirements.txt
Run the prototype:

python src/main.py
Build executable (optional):

python scripts/build.py
Usage
Run the executable or Python script.

The app runs silently in the background, monitoring keystrokes.

Upon detecting forbidden keywords, the lockdown activates automatically.

To unlock, follow the mercy mode prompts or wait out the lock duration.

Admin rights and a secret key are required for uninstallation.

Configuration
Keywords: Stored encrypted in data/keywords.json. Modify with care.

Lock durations and penalties: Defined in src/config.py.

Encryption keys: Securely managed within config (do not share).

Contributing
ImaanGuard welcomes contributions to improve detection, lockdown methods, or extend compatibility. Please fork the repo and submit pull requests.

Security & Privacy
All sensitive data is AES encrypted and protected by strict ACLs.

The tool runs with minimal permissions and respects user privacy aside from enforcing lockdown.

Intended for personal use; do not deploy without user consent.

License
MIT License © 2025 ImaanGuard Team

Contact
For questions or support, open an issue on GitHub or contact: support@imaanGuard.org

Stay strong. Stay focused. ImaanGuard is your silent sentinel.
