"""Check existing bot rights and optionally persist a channel; sends no messages."""

import argparse
import json
import re
import shlex

import paramiko

from scripts.release_vps import ROOT, load_local_env, run_remote
from scripts.vps_operation_lock import remote_operations_lock


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("channel")
    parser.add_argument("--configure", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"@[A-Za-z0-9_]{5,32}|-100\d{6,20}", args.channel):
        raise SystemExit("Use @channel_username or a numeric channel ID.")
    env = load_local_env(ROOT / ".env")
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(
        env["SERVER_HOST"],
        username=env["SERVER_USER"],
        password=env["SERVER_PASSWORD"],
        timeout=20,
    )
    code = """import asyncio,json
from aiogram import Bot
from k_loto.core.config import get_settings
async def main():
 b=Bot(get_settings().lottery_bot_token.get_secret_value())
 try:
  async with asyncio.timeout(20):
   me=await b.get_me()
   chat=await b.get_chat(CHANNEL)
   member=await b.get_chat_member(chat.id,me.id)
   print(json.dumps({
    "channel":CHANNEL,"channel_id":chat.id,"bot_username":me.username,
    "can_post":getattr(member,"can_post_messages",False),
    "can_edit":getattr(member,"can_edit_messages",False),
    "delivery_enabled":False}))
 except Exception as error:
  print(json.dumps({"error_type":type(error).__name__,"delivery_enabled":False}))
 finally: await b.session.close()
asyncio.run(main())""".replace("CHANNEL", repr(args.channel))
    try:
        with remote_operations_lock(client):
            output = run_remote(
                client,
                "Read-only Telegram channel permission check",
                "cd /opt/k-loto && docker compose --env-file .env.production "
                "-f docker-compose.prod.yml exec -T api python -c " + shlex.quote(code),
                timeout=40,
            )
            result = json.loads(output.strip().splitlines()[-1])
            print(json.dumps(result, ensure_ascii=False))
            if args.configure:
                if not result.get("can_post"):
                    raise SystemExit("No posting rights: channel was not configured.")
                with client.open_sftp() as sftp:
                    target = "/opt/k-loto/.env.production"
                    with sftp.open(target, "rb") as stream:
                        original = stream.read().decode("utf-8")
                    lines = [
                        line
                        for line in original.splitlines()
                        if not line.startswith("PUBLICATION_CHANNEL=")
                    ]
                    lines.append(f"PUBLICATION_CHANNEL={args.channel}")
                    with sftp.open(target, "w") as stream:
                        stream.write("\n".join(lines) + "\n")
                    sftp.chmod(target, 0o600)
                print(
                    "Channel stored. Delivery remains disabled; "
                    "API picks it up at release."
                )
    finally:
        client.close()


if __name__ == "__main__":
    main()
