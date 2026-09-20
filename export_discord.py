#!/usr/bin/env python3
"""Exporta todos los mensajes de un canal de Discord en orden cronologico.

Genera:
  - export/<canal>.json  (datos completos)
  - export/<canal>.html  (vista previa estilo Discord)

El token NUNCA se guarda: se lee de la variable DISCORD_TOKEN o se pide
por consola (sin mostrarlo).
"""
import argparse
import getpass
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

API = "https://discord.com/api/v10"


def api_get(path, token, params=None):
    url = API + path
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(
        url, headers={"Authorization": token, "User-Agent": "DiscordChatExporter/1.0"}
    )
    while True:
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code == 429:
                wait = json.loads(body).get("retry_after", 1) + 0.5
                print(f"  Rate limit, esperando {wait:.1f}s...")
                time.sleep(wait)
                continue
            if e.code == 401:
                sys.exit("Error 401: token invalido.")
            if e.code == 403:
                sys.exit("Error 403: sin permisos (Read Message History / View Channel).")
            if e.code == 404:
                sys.exit("Error 404: canal o servidor no encontrado (o sin acceso).")
            sys.exit(f"Error HTTP {e.code}: {body}")


def fetch_all(channel_id, token):
    messages, after = [], "0"
    while True:
        batch = api_get(
            f"/channels/{channel_id}/messages", token, {"limit": 100, "after": after}
        )
        if not batch:
            break
        batch.sort(key=lambda m: int(m["id"]))  # Discord devuelve el lote al reves
        messages.extend(batch)
        after = batch[-1]["id"]
        print(f"  {len(messages)} mensajes descargados...", end="\r")
        if len(batch) < 100:
            break
    print()
    messages.sort(key=lambda m: int(m["id"]))  # orden cronologico (snowflake)
    return messages


def fmt_ts(iso):
    return datetime.fromisoformat(iso).astimezone().strftime("%d/%m/%Y %H:%M:%S")


def render_content(text, mentions):
    names = {m["id"]: m.get("global_name") or m["username"] for m in mentions}
    out = html.escape(text)
    out = re.sub(
        r"&lt;@!?(\d+)&gt;",
        lambda m: f'<span class="mention">@{html.escape(names.get(m.group(1), m.group(1)))}</span>',
        out,
    )
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", out)
    return out.replace("\n", "<br>")


CSS = """
body{background:#313338;color:#dbdee1;font-family:'Segoe UI',Arial,sans-serif;margin:0}
header{background:#2b2d31;padding:16px 24px;position:sticky;top:0;border-bottom:1px solid #1e1f22}
header h1{margin:0;font-size:18px;color:#fff}header small{color:#949ba4}
main{max-width:900px;margin:0 auto;padding:16px}
.day{text-align:center;color:#949ba4;font-size:12px;margin:18px 0;border-top:1px solid #3f4147;line-height:0}
.day span{background:#313338;padding:0 10px}
.msg{display:flex;gap:14px;padding:6px 8px;border-radius:4px}.msg:hover{background:#2e3035}
.av{width:40px;height:40px;border-radius:50%;flex:none;background:#5865f2}
.name{color:#fff;font-weight:600}.ts{color:#949ba4;font-size:12px;margin-left:8px}
.reply{color:#949ba4;font-size:12px;margin-bottom:2px}
.mention{background:#3c4270;color:#c9cdfb;border-radius:3px;padding:0 2px}
code{background:#1e1f22;padding:1px 4px;border-radius:3px}
.att img{max-width:400px;max-height:300px;border-radius:6px;margin-top:4px;display:block}
.att a,.embed a{color:#00a8fc}
.embed{border-left:4px solid #5865f2;background:#2b2d31;padding:8px 12px;margin-top:4px;border-radius:4px;max-width:500px}
.embed b{display:block}.embed p{margin:4px 0 0;font-size:14px}
.react{display:inline-block;background:#2b2d31;border:1px solid #3f4147;border-radius:6px;padding:1px 6px;margin:4px 4px 0 0;font-size:13px}
"""


def build_html(messages, title, subtitle):
    parts = [
        f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>"
        f"<style>{CSS}</style></head><body><header><h1>{html.escape(title)}</h1>"
        f"<small>{html.escape(subtitle)} &middot; {len(messages)} mensajes</small></header><main>"
    ]
    last_day = None
    for m in messages:
        day = fmt_ts(m["timestamp"])[:10]
        if day != last_day:
            parts.append(f'<div class="day"><span>{day}</span></div>')
            last_day = day
        a = m["author"]
        name = html.escape(m.get("member", {}).get("nick") or a.get("global_name") or a["username"])
        avatar = ""
        if a.get("avatar"):
            avatar = f"https://cdn.discordapp.com/avatars/{a['id']}/{a['avatar']}.png?size=64"
        av = f'<img class="av" src="{avatar}">' if avatar else '<div class="av"></div>'
        body = ""
        ref = m.get("referenced_message")
        if ref:
            rn = ref["author"].get("global_name") or ref["author"]["username"]
            body += f'<div class="reply">&#8617; {html.escape(rn)}: {html.escape(ref.get("content", "")[:80])}</div>'
        body += f"<div>{render_content(m.get('content', ''), m.get('mentions', []))}</div>"
        for att in m.get("attachments", []):
            u = html.escape(att["url"])
            if (att.get("content_type") or "").startswith("image/"):
                body += f'<div class="att"><a href="{u}"><img src="{u}"></a></div>'
            else:
                body += f'<div class="att"><a href="{u}">{html.escape(att["filename"])}</a></div>'
        for e in m.get("embeds", []):
            t = html.escape(e.get("title", ""))
            link = e.get("url")
            t = f'<a href="{html.escape(link)}">{t}</a>' if link and t else t
            body += f'<div class="embed"><b>{t}</b><p>{html.escape(e.get("description", ""))}</p></div>'
        for r in m.get("reactions", []):
            body += f'<span class="react">{html.escape(r["emoji"].get("name") or "?")} {r["count"]}</span>'
        edited = " (editado)" if m.get("edited_timestamp") else ""
        parts.append(
            f'<div class="msg">{av}<div><span class="name">{name}</span>'
            f'<span class="ts">{fmt_ts(m["timestamp"])}{edited}</span>{body}</div></div>'
        )
    parts.append("</main></body></html>")
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser(description="Exporta un canal de Discord")
    ap.add_argument("--server", required=True, help="ID del servidor (guild)")
    ap.add_argument("--channel", required=True, help="ID del canal")
    ap.add_argument("--out", default="export", help="carpeta de salida")
    ap.add_argument("--user-token", action="store_true",
                    help="el token es de usuario (NO recomendado: infringe los TOS de Discord)")
    args = ap.parse_args()

    token = os.environ.get("DISCORD_TOKEN") or getpass.getpass("Token (oculto): ").strip()
    if not args.user_token and not token.startswith("Bot "):
        token = "Bot " + token

    channel = api_get(f"/channels/{args.channel}", token)
    if str(channel.get("guild_id")) != args.server:
        sys.exit("El canal no pertenece a ese servidor.")
    try:
        guild_name = api_get(f"/guilds/{args.server}", token)["name"]
    except SystemExit:
        guild_name = args.server
    cname = channel.get("name", args.channel)
    print(f"Exportando #{cname} de {guild_name}...")

    messages = fetch_all(args.channel, token)
    os.makedirs(args.out, exist_ok=True)
    base = os.path.join(args.out, re.sub(r"[^\w-]", "_", cname))
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(build_html(messages, f"#{cname}", guild_name))
    print(f"Listo: {len(messages)} mensajes.\n  {base}.json\n  {base}.html")


if __name__ == "__main__":
    main()
