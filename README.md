# 🤖 OTP Discord Bot

A simple and secure Discord bot that generates and verifies One-Time Passwords (OTPs) for users. This bot helps manage user access and roles through OTP verification. 

## ✨ Features

- **🔑 Generate OTP**: Users can generate a One-Time Password via a command.
- **📬 Send OTP**: Users can receive their OTP in a private message.
- **✅ Verify OTP**: Users can enter their OTP to gain access to specific roles.
- **⏳ Rate Limiting**: Users are limited in how frequently they can generate OTPs.
- **🕒 Expiration**: OTPs expire after a set period for security.

## 📋 Requirements

- Python 3.8 or higher
- `discord.py` library (v2.0 or higher)
- Basic knowledge of Discord bot development

## 🚀 Installation

1. Clone the repository:
   ```bash
   
   git clone https://github.com/NikolisSecurity/OTPGuardian.git
   cd otp-discord-bot
   ```
2. Install the required dependencies:
  ``` bash
  pip install -r requirements.txt
  ```
3. Configure your config.json file:
  ```bash
  {
      "bot_token": "YOUR_BOT_TOKEN",
      "otp_length": 6,
      "otp_expiration_seconds": 300,
      "rate_limit_seconds": 60,
      "command_prefix": "!",
      "role_id": "YOUR_ROLE_ID"
  }
  ```

## ⚙️ Usage

- Start the bot:
``` bash
  python bot.py
```

- Use the command to generate an OTP:
```bash
  /otp
```

-Follow the prompts to receive and enter your OTP.

## 🤝 Contributing
Feel free to fork the repository, make changes, and submit pull requests. Contributions are welcome!

## 📜 License
This project is licensed under the MIT License. See the LICENSE file for more details.

## 💖 Acknowledgments
discord.py - The library used for creating the Discord bot.
