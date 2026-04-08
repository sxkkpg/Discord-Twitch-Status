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

TOKEN            = os.getenv("TOKEN")
TWITCH_URL       = "https://www.twitch.tv/..."
VOICE_CHANNEL_ID = 
ROTATE_INTERVAL  = 60

APPLICATION_ID   = "..."
LARGE_IMAGE_NAME = "..."
SMALL_IMAGE_NAME = ""

BUTTONS = [
    {"label": "PTIShop",  "url": "..."},
    {"label": "PTIShop",  "url": "..."},
]

STREAMING_STATUSES = [
    "PTI Shop",
    "...",
    "...",
    "...",
    "...",
    "Online",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("selfbot_voice.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("selfbot_voice")

_e2ee_failed = False

class PatchedVoiceClient(discord.VoiceClient):
    async def connect(self, *, reconnect=True, timeout=60.0,
                      self_deaf=False, self_mute=False):
        global _e2ee_failed
        try:
            await super().connect(reconnect=reconnect, timeout=timeout,
                                  self_deaf=self_deaf, self_mute=self_mute)
        except discord.errors.ConnectionClosed as exc:
            if "4017" in str(exc) or getattr(exc, "code", 0) == 4017:
                _e2ee_failed = True
                log.error("4017 E2EE: เปลี่ยนห้องเสียงที่ไม่ได้เปิด E2EE")
                voice_watchdog.stop()
            raise

client       = discord.Client(chunk_guilds_at_startup=False)
status_cycle = itertools.cycle(STREAMING_STATUSES)

_voice_client   = None
_joining        = False
_just_joined    = False
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

async def _force_disconnect() -> None:
    global _voice_client
    if _voice_client is not None:
        try:
            await _voice_client.disconnect(force=True)
        except Exception:
            pass
        _voice_client = None
    for vc in list(client.voice_clients):
        try:
            await vc.disconnect(force=True)
        except Exception:
            pass

async def join_voice() -> None:
    global _voice_client, _joining, _just_joined

    if _e2ee_failed or _joining:
        return
    _joining = True

    try:
        if not VOICE_CHANNEL_ID:
            log.warning("VOICE_CHANNEL_ID ยังไม่ได้ตั้ง — ข้าม")
            return

        if _voice_client and _voice_client.is_connected():
            log.info("Already in voice")
            return

        if _voice_client or client.voice_clients:
            log.warning("มี voice client ค้าง — force disconnect ก่อน")
            await _force_disconnect()
            await asyncio.sleep(2)

        channel = client.get_channel(VOICE_CHANNEL_ID)
        if channel is None:
            try:
                channel = await client.fetch_channel(VOICE_CHANNEL_ID)
            except discord.NotFound:
                log.error(f"ไม่เจอ channel ID {VOICE_CHANNEL_ID}")
                return
            except discord.Forbidden:
                log.error("ไม่มีสิทธิ์เข้า channel นี้")
                return

        if not isinstance(channel, discord.VoiceChannel):
            log.error(f"Channel {VOICE_CHANNEL_ID} ไม่ใช่ VoiceChannel")
            return

        log.info(f"กำลัง join #{channel.name}...")
        _just_joined  = True
        _voice_client = await channel.connect(cls=PatchedVoiceClient)
        log.info(f"Joined voice: #{channel.name}")
        await asyncio.sleep(10)
        _just_joined = False

    except discord.errors.ConnectionClosed as exc:
        if not _e2ee_failed:
            log.error(f"ConnectionClosed: {exc}")
        await _force_disconnect()
        _just_joined = False

    except Exception as exc:
        log.error(f"Voice join failed: {exc}")
        await _force_disconnect()
        _just_joined = False

    finally:
        _joining = False

@tasks.loop(seconds=30)
async def voice_watchdog() -> None:
    if _e2ee_failed or not VOICE_CHANNEL_ID or _just_joined:
        return
    if _voice_client is None or not _voice_client.is_connected():
        log.warning("Voice watchdog: หลุด voice — rejoin...")
        await join_voice()

@voice_watchdog.before_loop
async def _before_watchdog() -> None:
    await client.wait_until_ready()
    await asyncio.sleep(15)

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
    if not voice_watchdog.is_running():
        voice_watchdog.start()

    await join_voice()

@client.event
async def on_disconnect() -> None:
    log.warning("Disconnected — รอ reconnect...")

@client.event
async def on_resumed() -> None:
    log.info("Session resumed — refresh presence")
    await set_next_presence()

@client.event
async def on_voice_state_update(member, before, after) -> None:
    if member.id != client.user.id:
        return
    if _e2ee_failed or _just_joined:
        return
    if before.channel is not None and after.channel is None:
        log.warning("หลุดออกจาก voice — rejoin ใน 5 วิ")
        await asyncio.sleep(5)
        await join_voice()

def main() -> None:
    if not TOKEN:
        log.critical("TOKEN ไม่มีใน .env")
        sys.exit(1)
    if VOICE_CHANNEL_ID == 0:
        log.warning("VOICE_CHANNEL_ID = 0 อย่าลืมใส่ ID ห้องเสียง")

    log.info("Starting ... Selfbot...")
    try:
        client.run(TOKEN)
    except discord.LoginFailure:
        log.critical("Token ผิดหรือหมดอายุ")
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("Stopped.")

if __name__ == "__main__":
    main()