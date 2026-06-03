#!/usr/bin/env python3
"""
WeChat ←→ Claude Code Bridge

Connects Claude Code to WeChat via Tencent's ilink Bot API directly.
No OpenClaw dependency required.

Usage:
  python scripts/wechat-claude-bridge.py login     # QR code login
  python scripts/wechat-claude-bridge.py run        # Start bridge
  python scripts/wechat-claude-bridge.py status     # Show status

Architecture:
  微信用户 ⇄ 腾讯 ilink Bot API ⇄ 本脚本 ⇄ Claude Code CLI
"""

import base64
import hashlib
import json
import os
import random
import secrets
import signal
import struct
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

# Fix Windows encoding for emoji/Chinese output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================
# Constants
# ============================================================
BASE_URL = "https://ilinkai.weixin.qq.com"
ILINK_APP_ID = "bot"
CHANNEL_VERSION = "2.4.3"
VERSION_CODE = (2 << 16) | (4 << 8) | 3  # 132099
BOT_TYPE = "3"
BOT_AGENT = f"ClaudeCode/{CHANNEL_VERSION}"

DATA_DIR = Path(__file__).resolve().parent.parent / "assets" / "user-data" / "wechat-bridge"
CONFIG_FILE = DATA_DIR / "config.json"
SESSION_FILE = DATA_DIR / "sessions.json"


# ============================================================
# Utilities
# ============================================================
def random_wechat_uin():
    u32 = struct.unpack(">I", secrets.token_bytes(4))[0]
    return base64.b64encode(str(u32).encode()).decode()


def build_headers(token=None):
    headers = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": random_wechat_uin(),
        "iLink-App-Id": ILINK_APP_ID,
        "iLink-App-ClientVersion": str(VERSION_CODE),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def api_post(endpoint, body=None, token=None, timeout=30):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(url, data=data, headers=build_headers(token), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            if not raw.strip():
                return {}  # Empty response is success for some endpoints
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"  API Error {e.code}: {body_text[:200]}")
        return None
    except json.JSONDecodeError:
        return {}  # Non-JSON response = treat as success
    except Exception as e:
        print(f"  Request failed: {e}")
        return None


def api_get(endpoint, token=None, timeout=35):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers=build_headers(token), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            if not raw.strip():
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"  API Error {e.code}: {body_text[:200]}")
        return None
    except json.JSONDecodeError:
        return None
    except Exception:
        return None  # Timeout is expected for long polling


def _safe_json_load(path):
    """Load JSON file safely, return {} on any error."""
    try:
        if path.exists():
            raw = path.read_text(encoding="utf-8").strip()
            if raw:
                return json.loads(raw)
    except Exception:
        pass
    return {}


def load_config():
    return _safe_json_load(CONFIG_FILE)


def save_config(cfg):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


def load_sessions():
    return _safe_json_load(SESSION_FILE)


def save_sessions(sessions):
    try:
        tmp = SESSION_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(SESSION_FILE)
    except Exception:
        pass  # Don't crash if can't save sessions


# ============================================================
# Login Flow
# ============================================================
def cmd_login():
    """QR code login to WeChat Bot."""
    print("=" * 50)
    print("WeChat Bot 登录")
    print("=" * 50)

    # Step 1: Get QR code
    print("\n[1/3] 获取登录二维码...")
    existing_tokens = []
    cfg = load_config()
    if cfg.get("bot_token"):
        existing_tokens.append(cfg["bot_token"])

    resp = api_post("/ilink/bot/get_bot_qrcode?bot_type=" + BOT_TYPE,
                    {"local_token_list": existing_tokens[:10]})
    if not resp:
        print("ERROR: 获取二维码失败")
        sys.exit(1)

    qrcode_token = resp.get("qrcode", "")
    qrcode_img = resp.get("qrcode_img_content", "")
    if not qrcode_token or not qrcode_img:
        print("ERROR: 响应中无二维码")
        sys.exit(1)

    # Save QR code as PNG image file
    qr_img_file = DATA_DIR / "qr-login.png"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(qrcode_img)
        img = qr.make_image()
        img.save(str(qr_img_file))
        print(f"\n[1/3] 二维码已保存 → {qr_img_file}")
        print(f"      请用微信扫一扫打开此图片文件")
        # Try to open the image automatically
        try:
            os.startfile(str(qr_img_file))
        except Exception:
            pass
    except Exception as e:
        print(f"\nQR生成失败 ({e}), 请打开链接扫码：{qrcode_img}")

    # Step 2: Poll for scan
    print("\n[2/3] 等待扫码确认...")
    poll_url = f"/ilink/bot/get_qrcode_status?qrcode={urllib.parse.quote(qrcode_token)}"
    started = time.time()
    max_wait = 480  # 8 minutes

    while time.time() - started < max_wait:
        result = api_get(poll_url, timeout=35)
        if not result:
            print(".", end="", flush=True)
            continue

        status = result.get("status", "")
        if status == "confirmed":
            print("\n✅ 扫码确认成功！")
            # DEBUG: print all keys
            print(f"  [DEBUG] Response keys: {list(result.keys())}")
            break
        elif status == "scaned":
            print("\n📱 已扫码，请在手机上确认...", end="", flush=True)
        elif status == "expired":
            print("\n❌ 二维码已过期，请重试")
            sys.exit(1)
        elif status == "need_verifycode":
            verify = input("\n🔐 请输入手机上的配对码: ").strip()
            poll_url += "&verify_code=" + urllib.parse.quote(verify)
        elif status == "wait":
            print(".", end="", flush=True)
        else:
            print(f"\n  Unknown status: {status}")
            print(".", end="", flush=True)
    else:
        print("\n❌ 登录超时")
        sys.exit(1)

    # Step 3: Save credentials
    # Try multiple possible key names
    bot_token = result.get("botToken") or result.get("bot_token") or result.get("token") or ""
    account_id = result.get("ilink_bot_id") or result.get("account_id") or ""
    user_id = result.get("ilink_user_id") or result.get("user_id") or ""
    base_url = result.get("baseurl") or result.get("base_url") or result.get("baseUrl") or BASE_URL
    if isinstance(base_url, str) and base_url:
        base_url = base_url.rstrip("/")

    cfg = {
        "bot_token": bot_token,
        "bot_type": BOT_TYPE,
        "account_id": account_id,
        "user_id": user_id,
        "base_url": base_url,
        "logged_in_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_config(cfg)

    print(f"\n[3/3] 凭证已保存")
    print(f"  Account ID: {account_id}")
    print(f"  User ID: {user_id}")
    print(f"\n✅ 登录成功！运行 'python scripts/wechat-claude-bridge.py run' 启动桥接")


# ============================================================
# Claude Code Integration
# ============================================================
def call_claude_code(message: str, session_id: str) -> str:
    """Send a message to Claude Code CLI and return the response."""
    # Load conversation history for this session
    sessions = load_sessions()
    if session_id not in sessions:
        sessions[session_id] = []

    history = sessions[session_id][-10:]

    # Use claude CLI in non-interactive mode (-p = print mode)
    cmd = ["claude", "-p", "--output-format", "text"]

    # Strip emoji from input to avoid encoding issues
    def strip_emoji(text):
        import re
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)

    if history:
        context_parts = ["[Previous conversation]"]
        for h in history:
            role = "User" if h["role"] == "user" else "Claude"
            context_parts.append(f"{role}: {strip_emoji(h['msg'])}")
        context_parts.append("---")
        context_parts.append(f"[New message] {message}")
        full_input = "\n".join(context_parts)
    else:
        full_input = (
            "You are a fitness & nutrition advisor connected via WeChat. "
            "Keep responses concise (under 500 characters when possible) since "
            "the user is on mobile. Use Chinese. Do NOT use emoji.\n\n"
            f"User message: {message}"
        )

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            cmd + [full_input],
            capture_output=True,
            timeout=120,
            env=env,
        )
        # Decode manually with error handling
        stdout = result.stdout.decode("utf-8", errors="replace").strip() if result.stdout else ""
        stderr = result.stderr.decode("utf-8", errors="replace").strip() if result.stderr else ""

        if result.returncode == 0:
            reply = stdout
        else:
            reply = f"Sorry, error: {stderr[:200]}"

        # Remove emoji from reply for Windows console + WeChat compatibility
        reply = strip_emoji(reply)

        # Save to history
        sessions[session_id].append({"role": "user", "msg": message, "ts": time.time()})
        sessions[session_id].append({"role": "assistant", "msg": reply, "ts": time.time()})
        sessions[session_id] = sessions[session_id][-50:]
        save_sessions(sessions)

        return reply
    except subprocess.TimeoutExpired:
        return "Sorry, response timed out. Please try again."
    except Exception as e:
        return f"Sorry, error: {str(e)[:200]}"


# ============================================================
# Message Bridge
# ============================================================
def run_bridge():
    """Main loop: poll messages → Claude Code → send reply."""
    global BASE_URL

    cfg = load_config()
    if not cfg.get("bot_token"):
        print("ERROR: 未登录。请先运行: python scripts/wechat-claude-bridge.py login")
        sys.exit(1)

    token = cfg["bot_token"]
    base_url = cfg.get("base_url", BASE_URL)
    print("=" * 50)
    print("WeChat ←→ Claude Code Bridge")
    print(f"Account: {cfg.get('account_id', 'unknown')}")
    print("=" * 50)
    print("\n✅ 桥接已启动，等待微信消息...")
    print("   (Ctrl+C 停止)\n")

    cursor = ""
    running = True

    def on_signal(sig, frame):
        nonlocal running
        print("\n⏸️  正在停止...")
        running = False

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    # Use base_url for API calls if different from default
    BASE_URL = base_url.rstrip("/")

    while running:
        try:
            # Long poll for messages
            body = {
                "get_updates_buf": cursor,
                "base_info": {
                    "channel_version": CHANNEL_VERSION,
                    "bot_agent": BOT_AGENT,
                },
            }
            resp = api_post("/ilink/bot/getupdates", body, token, timeout=40)

            if resp is None:
                time.sleep(2)
                continue

            # Update cursor
            cursor = resp.get("get_updates_buf", cursor)
            msgs = resp.get("msgs", [])

            for msg in msgs:
                if not msg:
                    continue

                msg_type = msg.get("message_type", 0)
                msg_state = msg.get("message_state", 0)

                # Only process non-bot, non-generating messages
                if msg_type == 2:  # BOT message (our own reply echo)
                    continue
                if msg_state == 1:  # GENERATING (typing)
                    # Send typing indicator
                    api_post("/ilink/bot/sendtyping", {
                        "ilink_user_id": msg.get("from_user_id"),
                        "typing_ticket": cfg.get("typing_ticket", ""),
                        "status": 1,
                        "base_info": {"channel_version": CHANNEL_VERSION, "bot_agent": BOT_AGENT},
                    }, token, timeout=5)
                    continue

                # Extract text
                text = extract_text(msg)
                if not text:
                    continue

                from_user = msg.get("from_user_id", "unknown")
                session_id = msg.get("session_id", from_user)
                context_token = msg.get("context_token", "")
                to_user_id = msg.get("to_user_id", "")

                print(f"\n📩 [{from_user[:12]}...] {text[:100]}")

                # Call Claude Code
                reply = call_claude_code(text, session_id)

                print(f"📤 {reply[:100]}...")

                # Send reply
                send_text_message(token, to_user_id, from_user, reply, context_token)

                # Cancel typing
                api_post("/ilink/bot/sendtyping", {
                    "ilink_user_id": from_user,
                    "typing_ticket": cfg.get("typing_ticket", ""),
                    "status": 2,
                    "base_info": {"channel_version": CHANNEL_VERSION, "bot_agent": BOT_AGENT},
                }, token, timeout=5)

        except Exception as e:
            import traceback
            print(f"Loop error: {e}")
            traceback.print_exc()
            time.sleep(3)


def extract_text(msg):
    """Extract text content from a WeChat message."""
    items = msg.get("item_list", [])
    for item in items:
        if item.get("type") == 1:  # TEXT
            ti = item.get("text_item", {})
            return ti.get("text", "")
    return None


def send_text_message(token, to_user_id, from_user_id, text, context_token):
    """Send a text message back to WeChat."""
    body = {
        "msg": {
            "to_user_id": from_user_id,  # Reply to the sender
            "context_token": context_token,
            "message_type": 2,  # BOT
            "message_state": 1,  # GENERATING initially...
            "item_list": [{
                "type": 1,  # TEXT
                "text_item": {"text": text},
            }],
        },
        "base_info": {
            "channel_version": CHANNEL_VERSION,
            "bot_agent": BOT_AGENT,
        },
    }
    resp = api_post("/ilink/bot/sendmessage", body, token, timeout=15)
    if resp is None:
        print("  ⚠️ Failed to send message")

    # Also send a FINISH state message
    body["msg"]["message_state"] = 2  # FINISH
    api_post("/ilink/bot/sendmessage", body, token, timeout=15)


def cmd_status():
    """Show bridge status."""
    cfg = load_config()
    if cfg.get("bot_token"):
        print("✅ 已登录")
        print(f"   Account: {cfg.get('account_id', '?')}")
        print(f"   User: {cfg.get('user_id', '?')}")
        print(f"   Login time: {cfg.get('logged_in_at', '?')}")
    else:
        print("❌ 未登录。运行: python scripts/wechat-claude-bridge.py login")

    sessions = load_sessions()
    print(f"\n📊 活跃会话: {len(sessions)}")


def cmd_run():
    """Run as daemon with auto-restart."""
    while True:
        try:
            run_bridge()
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n💥 Bridge crashed: {e}")
            print("Restarting in 10 seconds...")
            time.sleep(10)


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("Commands:")
        print("  login     QR code login to WeChat Bot")
        print("  run       Start the Claude Code bridge")
        print("  status    Show login status")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "login":
        cmd_login()
    elif cmd in ("run", "start"):
        cmd_run()
    elif cmd == "status":
        cmd_status()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
