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
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"  API Error {e.code}: {body_text[:200]}")
        return None
    except Exception as e:
        print(f"  Request failed: {e}")
        return None


def api_get(endpoint, token=None, timeout=35):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers=build_headers(token), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"  API Error {e.code}: {body_text[:200]}")
        return None
    except Exception:
        return None  # Timeout is expected for long polling


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def save_config(cfg):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


def load_sessions():
    if SESSION_FILE.exists():
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    return {}


def save_sessions(sessions):
    SESSION_FILE.write_text(json.dumps(sessions, ensure_ascii=False, indent=2))


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

    # Print QR in terminal (ASCII)
    print("\n请用微信扫描以下二维码：\n")
    try:
        import qrcode
        import sys
        qr = qrcode.QRCode()
        qr.add_data(qrcode_img)
        # Handle Windows GBK encoding issue
        try:
            qr.print_ascii(invert=True)
        except UnicodeEncodeError:
            # Fallback: print the URL directly
            print(qrcode_img)
    except ImportError:
        print(qrcode_img)
        print("\n(tip: pip install qrcode[pil] for terminal QR)")
    except Exception:
        print(qrcode_img)

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
    bot_token = result.get("botToken", "")
    account_id = result.get("ilink_bot_id", "")
    user_id = result.get("ilink_user_id", "")
    base_url = result.get("baseurl", BASE_URL)

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

    # Build the prompt
    # For ongoing conversations, we pass the last few exchanges as context
    history = sessions[session_id][-10:]  # Keep last 5 exchanges (10 msgs)

    # Use claude CLI in non-interactive mode
    # --print: output only the response, no UI
    # --output-format text: plain text response
    cmd = ["claude", "--print", "--output-format", "text"]

    # Build the input. For conversation continuity, we can pass
    # the full context as a single prompt with history
    if history:
        context_parts = ["[Previous conversation]"]
        for h in history:
            role = "User" if h["role"] == "user" else "Claude"
            context_parts.append(f"{role}: {h['msg']}")
        context_parts.append("---")
        context_parts.append(f"[New message] {message}")
        full_input = "\n".join(context_parts)
    else:
        # First message: prepend the fitness advisor context
        full_input = (
            f"You are a fitness & nutrition advisor connected via WeChat. "
            f"Keep responses concise (under 500 characters when possible) since "
            f"the user is on mobile. Use Chinese.\n\n"
            f"User message: {message}"
        )

    try:
        result = subprocess.run(
            cmd,
            input=full_input,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
        )
        if result.returncode == 0:
            reply = result.stdout.strip()
        else:
            reply = f"抱歉，处理消息时出错: {result.stderr[:200]}"

        # Save to history
        sessions[session_id].append({"role": "user", "msg": message, "ts": time.time()})
        sessions[session_id].append({"role": "assistant", "msg": reply, "ts": time.time()})
        # Trim old history (keep last 50 exchanges)
        sessions[session_id] = sessions[session_id][-50:]
        save_sessions(sessions)

        return reply
    except subprocess.TimeoutExpired:
        return "抱歉，回复超时了，请稍后再试。"
    except Exception as e:
        return f"抱歉，出错了: {e}"


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
            print(f"Loop error: {e}")
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
