<div align="center">

# 🟣 Discord Twitch Status Selfbot

**Keep your Discord account online 24/7 with rotating Twitch streaming presence**

![Preview](https://github.com/sxkkpg/Discord-Twitch-Status/blob/cf92a4d844a378a002b1664768d5daa938b2cd13/ex.png)

[![PTI Shop](https://img.shields.io/badge/PTI%20Shop-Link%20Tree-blueviolet?style=for-the-badge&logo=discord)](https://YOUR_LINKTREE_URL_HERE)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![discord.py-self](https://img.shields.io/badge/discord.py--self-latest-5865F2?style=for-the-badge&logo=discord&logoColor=white)

</div>

---

## ✨ Features

- 🎮 **Rotating Twitch streaming status** — cycles through multiple stream titles automatically
- 🔁 **Runs 24/7** — designed to keep your account always online
- 🎙️ **Two versions available** — with or without auto voice channel join
- 🔐 **Token stored in `.env`** — safe and easy to configure

---

## 📁 Versions

| File | Description |
|------|-------------|
| `twitchnovoice.py` | Rotating Twitch status only — no voice channel |
| `twitchvoice.py` | Rotating Twitch status **+ auto joins a voice channel** |

---

## ⚙️ Setup

### 1. Clone the repo

```bash
git clone https://github.com/sxkkpg/Discord-Twitch-Status.git
cd Discord-Twitch-Status
```

### 2. Install dependencies

```bash
pip install discord.py-self python-dotenv
```

### 3. Configure `.env`

```env
TOKEN=your_discord_token_here
```

> ⚠️ **Warning:** Using a selfbot may violate Discord's Terms of Service. Use at your own risk.

### 4. Edit values in the script

Open your chosen `.py` file and adjust:
- Stream titles list
- Twitch username
- Rotation interval
- Voice channel ID *(twitchvoice.py only)*

### 5. Run

```bash
python twitchnovoice.py
# or
python twitchvoice.py
```

---

## 🔗 Links

- 🌐 [PTI Shop](https://YOUR_LINKTREE_URL_HERE)
- 💬 Discord: `sxkkp.d`

---

<div align="center">
Made with 💜 by <a href="https://YOUR_LINKTREE_URL_HERE">PTI Shop</a>
</div>
