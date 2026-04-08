import asyncio
import itertools
import logging
import os
import sys

import aiohttp
import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()

TOKEN           = os.getenv("TOKEN")
TWITCH_URL      = "https://www.twitch.tv/..."
ROTATE_INTERVAL = 60

APPLICATION_ID   = "..."
LARGE_IMAGE_NAME = "..."
SMALL_IMAGE_NAME = ""

BUTTONS = [
    {"label": "...",  "url": "..."},
    {"label": "...",   "url": "..."},
]

STREAMING_STATUSES = [
    "...",
    "...",
    "...",
    "...",
    "...",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("selfbot_novoice.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("selfbot_novoice")

client       = discord.Client(chunk_guilds_at_startup=False)
status_cycle = itertools.cycle(STREAMING_STATUSES)

_large_image_id = None
_small_image_id = None

async def fetch_asset_id(app_id: str, asset_name: str) -> str | None:
    if not asset_name:
        return None
    url     = f"https://discord.com/api/v10/oauth2/applications/{app_id}/assets"
    headers = {"Authorization": TOKEN}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    log.error(f"fetch assets HTTP {resp.status}")
                    return None
                for asset in await resp.json():
                    if asset.get("name") == asset_name:
                        log.info(f"Asset '{asset_name}' → ID {asset['id']}")
                        return asset["id"]
                log.warning(f"ไม่เจอ asset '{asset_name}' — เช็คชื่อใน Art Assets")
                return None
    except Exception as exc:
        log.error(f"fetch_asset_id error: {exc}")
        return None

async def set_next_presence() -> None:
    name = next(status_cycle)

    kwargs: dict = {
        "type": discord.ActivityType.streaming,
        "name": name,
        "url":  TWITCH_URL,
    }

    if APPLICATION_ID:
        kwargs["application_id"] = int(APPLICATION_ID)

    assets = {}
    if _large_image_id:
        assets["large_image"] = _large_image_id
        assets["large_text"]  = "PTIShop"
    if _small_image_id:
        assets["small_image"] = _small_image_id
        assets["small_text"]  = ""
    if assets:
        kwargs["assets"] = assets

    if BUTTONS:
        kwargs["buttons"]  = [b["label"] for b in BUTTONS]
        kwargs["metadata"] = {"button_urls": [b["url"] for b in BUTTONS]}

    try:
        await client.change_presence(activity=discord.Activity(**kwargs))
        log.info(f"Presence → {name}")
    except Exception as exc:
        log.error(f"change_presence error: {exc}")
        try:
            await client.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.streaming,
                    name=name,
                    url=TWITCH_URL,
                )
            )
            log.warning("fallback presence (ไม่มีรูป/ปุ่ม)")
        except Exception as e2:
            log.error(f"fallback error: {e2}")

@tasks.loop(seconds=ROTATE_INTERVAL)
async def rotate_presence() -> None:
    await set_next_presence()

@rotate_presence.before_loop
async def _before_rotate() -> None:
    await client.wait_until_ready()
    await asyncio.sleep(2)

@client.event
async def on_ready() -> None:
    global _large_image_id, _small_image_id
    log.info(f"Logged in as {client.user} (ID: {client.user.id})")

    if APPLICATION_ID:
        log.info("กำลังดึง Asset IDs...")
        _large_image_id = await fetch_asset_id(APPLICATION_ID, LARGE_IMAGE_NAME)
        _small_image_id = await fetch_asset_id(APPLICATION_ID, SMALL_IMAGE_NAME)
        if not _large_image_id:
            log.warning("ไม่ได้ large image ID — รูปจะไม่แสดง")
    else:
        log.warning("APPLICATION_ID ว่าง")

    await set_next_presence()

    if not rotate_presence.is_running():
        rotate_presence.start()

@client.event
async def on_disconnect() -> None:
    log.warning("Disconnected — รอ reconnect...")

@client.event
async def on_resumed() -> None:
    log.info("Session resumed — refresh presence")
    await set_next_presence()

def main() -> None:
    if not TOKEN:
        log.critical("TOKEN ไม่มีใน .env")
        sys.exit(1)

    log.info("Starting ... Selfbot ...")
    try:
        client.run(TOKEN)
    except discord.LoginFailure:
        log.critical("Token ผิดหรือหมดอายุ")
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("Stopped.")

if __name__ == "__main__":
    main()