import os
import sys
import json
import time
import signal
import random
import asyncio
import aiohttp

from urllib.parse import parse_qs, unquote, quote

from utils.banner import show_banner

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

MY_PROJECT = "Notbux Miniapp"
BASE_URL = "https://notbux.click/api"
REF_CODE = "6004380466"

CALL_ATTEMPTS = 3
CALL_RETRY_SECONDS = 4
ROUND_PAUSE_SECONDS = 3
RATE_LIMIT_PAUSE_SECONDS = 8

TASK_LIMIT = 120
TASK_TITLE_LIMIT = 24
NAME_LIMIT = 18

AD_UNVERIFIED_LIMIT = 3
AD_MAX_ROUNDS = 24
AD_COOLDOWN_SECONDS = 4
ADSGRAM_BLOCK_MARKER = "adsgram"

BUSY_STATUS = (429, 500, 502, 503, 504)

JOIN_WORDS = (
    "not completed yet",
    "join",
    "subscribe",
)

DONE_WORDS = (
    "already completed",
    "already claimed",
    "come back tomorrow",
)

COOLDOWN_WORDS = (
    "cooldown",
    "please wait",
)

BANNED_CODES = (
    91, 93, 124, 35, 33, 64, 36, 37, 94, 38, 42, 40, 41,
    45, 44, 58, 59, 39, 34, 96, 126, 43, 61, 60, 62, 63, 47, 92,
)
BANNED_CHARS = tuple(chr(code) for code in BANNED_CODES)

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36"
)


def log_green(msg):
    print(f"{GREEN}{BOLD}{msg}{RESET}", flush=True)


def log_yellow(msg):
    print(f"{YELLOW}{BOLD}{msg}{RESET}", flush=True)


def log_red(msg):
    print(f"{RED}{BOLD}{msg}{RESET}", flush=True)


def signal_handler(sig, frame):
    print(flush=True)
    log_red("Script stopped by user")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def clean_text(value, fallback):
    if value is None:
        return str(fallback)
    text = str(value)
    for symbol in BANNED_CHARS:
        text = text.replace(symbol, " ")
    text = "".join(char for char in text if ord(char) < 128)
    text = " ".join(text.split())
    return text if text else str(fallback)


def shorten(value, fallback, limit):
    text = clean_text(value, fallback)
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    space = cut.rfind(" ")
    return cut[:space].rstrip() if space > 0 else text[:limit].rstrip()


def plural(count, noun="task"):
    return noun if int(count) == 1 else f"{noun}s"


def format_amount(value):
    try:
        number = float(value)
    except Exception:
        return "0"
    if number != number or number == 0:
        return "0"
    text = f"{number:.8f}" if abs(number) < 1 else f"{number:.2f}"
    text = text.rstrip("0").rstrip(".")
    return text or "0"


def display_name(account):
    for value in (account.get("firstName"), account.get("username")):
        name = clean_text(value, "")
        if name:
            return name
    return "Unknown"


def load_config():
    defaults = {"settings": {"sleep_seconds": 3600}}
    if not os.path.exists("config.json"):
        return defaults
    try:
        with open("config.json") as handle:
            loaded = json.load(handle)
    except Exception:
        return defaults
    settings = loaded.get("settings")
    if not isinstance(settings, dict):
        return defaults
    merged = dict(defaults["settings"])
    merged.update(settings)
    return {"settings": merged}


def load_lines(filename, required):
    if not os.path.exists(filename):
        if required:
            log_red(f"File {clean_text(filename, 'data.txt')} was not found")
            sys.exit(1)
        return []
    lines = [line.strip() for line in open(filename).readlines() if line.strip()]
    if required and not lines:
        log_red("File data.txt is empty and holds no initData string")
        sys.exit(1)
    return lines


def parse_init_data(line):
    value = line.strip()
    address = ""
    if "|" in value:
        value, address = value.rsplit("|", 1)
        value = value.strip()
        address = address.strip()
    if "tgWebAppData=" in value:
        value = value.split("tgWebAppData=", 1)[1]
        value = value.split("&tgWebAppVersion")[0]
        value = value.split("&tgWebAppPlatform")[0]
        value = unquote(value)
    fields = parse_qs(value, keep_blank_values=True)
    raw_user = (fields.get("user") or [""])[0]
    if not raw_user:
        return None
    try:
        profile = json.loads(raw_user)
    except Exception:
        try:
            profile = json.loads(unquote(raw_user))
        except Exception:
            return None
    if not isinstance(profile, dict) or not profile.get("id"):
        return None
    return {
        "initData": value,
        "id": str(profile.get("id")),
        "username": str(profile.get("username") or ""),
        "firstName": str(profile.get("first_name") or ""),
        "lastName": str(profile.get("last_name") or ""),
        "startParam": str((fields.get("start_param") or [""])[0] or ""),
        "coins": 0.0,
        "ton": 0.0,
        "streak": 0,
        "friends": 0,
    }


def referrer_id_of(account):
    value = clean_text(account.get("startParam") or REF_CODE, "")
    return "".join(char for char in value if char.isdigit())


def normalize_proxy(proxy_line):
    if not proxy_line:
        return None
    value = proxy_line.strip()
    if "://" in value:
        return value
    parts = value.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{user}:{password}@{host}:{port}"
    if len(parts) == 3:
        host, port, user = parts
        return f"http://{user}@{host}:{port}"
    return f"http://{value}"


def mask_proxy(proxy_url):
    try:
        value = proxy_url.split("://")[-1]
        after_at = value.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        elif len(host_part) > 4:
            masked_host = f"{host_part[:2]}*****{host_part[-2:]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"


def error_message(payload):
    if isinstance(payload, dict):
        message = payload.get("error") or payload.get("message")
        if message:
            return str(message)
    return ""


def busy_error(status, payload):
    if status in BUSY_STATUS:
        return True
    message = error_message(payload).lower()
    return "busy" in message or "timeout" in message or "too many" in message


def number_float(mapping, key, fallback=0.0):
    if not isinstance(mapping, dict):
        return fallback
    value = mapping.get(key)
    if value is None or value == "":
        return fallback
    try:
        return float(value)
    except Exception:
        return fallback


def number_of(mapping, key, fallback=0):
    return int(number_float(mapping, key, fallback))


def countdown(seconds, label):
    total = int(seconds)
    if total < 1:
        return
    line = ""
    for remaining in range(total, 0, -1):
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        rest = remaining % 60
        line = f"{label} {hours:02d}:{minutes:02d}:{rest:02d}"
        print(f"\r{YELLOW}{BOLD}{line}{RESET}", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * (len(line) + 6) + "\r", end="", flush=True)


def build_headers(account):
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "origin": "https://notbux.click",
        "referer": "https://notbux.click/",
        "user-agent": USER_AGENT,
        "authorization": f"tma {account['initData']}",
    }


async def api_call(session, account, path, body=None, proxy=None, method="GET"):
    url = f"{BASE_URL}{path}"
    last_status = 0
    last_payload = None
    for attempt in range(1, CALL_ATTEMPTS + 1):
        pause = CALL_RETRY_SECONDS * attempt
        try:
            request = session.request(
                method,
                url,
                headers=build_headers(account),
                json=body,
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=30),
            )
            async with request as response:
                last_status = response.status
                text = await response.text()
                try:
                    last_payload = json.loads(text)
                except Exception:
                    last_payload = None
                if response.status < 400 or not busy_error(response.status, last_payload):
                    return last_status, last_payload
                if response.status == 429:
                    pause = RATE_LIMIT_PAUSE_SECONDS * attempt
        except Exception:
            last_status = 0
            last_payload = None
        if attempt < CALL_ATTEMPTS:
            countdown(pause, "Retry in")
    return last_status, last_payload


def ok_payload(status, payload):
    return status == 200 and isinstance(payload, dict) and payload.get("status") == "success"


def store_user(account, payload):
    user = payload.get("user") if isinstance(payload, dict) else None
    if not isinstance(user, dict):
        return {}
    account["coins"] = number_float(user, "balance_coins")
    account["ton"] = number_float(user, "balance_ton")
    return user


async def read_state(session, account, proxy):
    status, payload = await api_call(session, account, "/me", None, proxy, "GET")
    if ok_payload(status, payload):
        return store_user(account, payload)
    return {}


async def run_auth(session, account, proxy):
    query = f"/me?start_param={quote(referrer_id_of(account), safe='')}"
    status, payload = await api_call(session, account, query, None, proxy, "GET")
    if ok_payload(status, payload):
        return store_user(account, payload)
    return {}


async def run_earn_status(session, account, proxy):
    status, payload = await api_call(session, account, "/earn/status", None, proxy, "GET")
    if not ok_payload(status, payload):
        log_yellow("The rewards board was not returned by the server")
        return {}, [], []
    account["streak"] = number_of(payload, "streak")
    quests = payload.get("quests") or []
    achievements = payload.get("achievements") or []
    return payload, quests, achievements


async def run_checkin(session, account, proxy, board):
    if not isinstance(board, dict):
        return 0.0
    before = account["coins"]
    status, payload = await api_call(session, account, "/earn/checkin", {}, proxy, "POST")
    if not ok_payload(status, payload):
        message = error_message(payload).lower()
        if any(word in message for word in DONE_WORDS):
            log_yellow("The daily check in was already claimed for this account")
        else:
            log_yellow("The daily check in could not be claimed on this run")
        return 0.0
    fresh = await read_state(session, account, proxy)
    after = number_float(fresh, "balance_coins", account["coins"])
    gain = round(after - before, 6)
    account["coins"] = after
    if gain <= 0:
        log_yellow("The daily check in was accepted without a confirmed credit")
        return 0.0
    log_green(
        f"Daily check in credited {clean_text(format_amount(gain), 0)} coins "
        f"on streak day {clean_text(account['streak'], 1)}"
    )
    return gain


async def run_item_claim(session, account, proxy, path, item_id, label, kind):
    before = account["coins"]
    status, payload = await api_call(
        session, account, path, {"item_id": item_id}, proxy, "POST"
    )
    if not ok_payload(status, payload):
        return 0.0
    fresh = await read_state(session, account, proxy)
    after = number_float(fresh, "balance_coins", account["coins"])
    gain = round(after - before, 6)
    account["coins"] = after
    if gain <= 0:
        return 0.0
    log_green(
        f"{clean_text(kind, 'Reward')} {clean_text(label, 'item')} credited "
        f"{clean_text(format_amount(gain), 0)} coins"
    )
    return gain


async def run_quests(session, account, proxy, quests):
    if not quests:
        log_green("The rewards board holds no daily quest for this account")
        return 0.0
    earned = 0.0
    paid = 0
    reachable = 0
    for item in quests:
        item_id = clean_text(item.get("id"), "")
        if not item_id or item.get("is_claimed"):
            continue
        progress = number_float(item, "progress")
        target = number_float(item, "target", 1) or 1
        if progress < target:
            continue
        reachable += 1
        label = shorten(item.get("title"), "quest", TASK_TITLE_LIMIT)
        await api_call(
            session, account, "/earn/start", {"item_id": item_id}, proxy, "POST"
        )
        gain = await run_item_claim(
            session, account, proxy, "/earn/daily_quest", item_id, label, "Daily quest"
        )
        if gain > 0:
            earned += gain
            paid += 1
        countdown(ROUND_PAUSE_SECONDS, "Next task in")
    if paid:
        log_green(
            f"{clean_text(paid, 0)} {clean_text(plural(paid, 'quest'), 'quests')} "
            f"paid on this account"
        )
    elif reachable:
        log_yellow("A daily quest within reach was not paid on this run")
    return earned


async def run_achievements(session, account, proxy, achievements):
    if not achievements:
        log_green("The achievement board is empty for this account")
        return 0.0
    earned = 0.0
    paid = 0
    reachable = 0
    for item in achievements:
        item_id = clean_text(item.get("id"), "")
        if not item_id or item.get("is_claimed"):
            continue
        progress = number_float(item, "progress")
        target = number_float(item, "target", 1) or 1
        if progress < target:
            continue
        reachable += 1
        label = shorten(item.get("title"), "achievement", TASK_TITLE_LIMIT)
        gain = await run_item_claim(
            session, account, proxy, "/earn/achievement", item_id, label, "Achievement"
        )
        if gain > 0:
            earned += gain
            paid += 1
        countdown(ROUND_PAUSE_SECONDS, "Next task in")
    if paid:
        log_green(
            f"{clean_text(paid, 0)} "
            f"{clean_text(plural(paid, 'achievement'), 'achievements')} "
            f"paid on this account"
        )
    elif reachable:
        log_yellow("An achievement within reach was not paid on this run")
    else:
        log_green("No achievement has reached its target for this account yet")
    return earned


async def verify_task(session, account, proxy, task_id):
    status, payload = await api_call(
        session, account, f"/tasks/{task_id}/verify", {}, proxy, "POST"
    )
    if ok_payload(status, payload):
        return "paid", number_float(payload, "reward")
    message = error_message(payload).lower()
    if any(word in message for word in DONE_WORDS):
        return "done", 0.0
    if any(word in message for word in JOIN_WORDS):
        return "join", 0.0
    return "failed", 0.0


async def run_tasks(session, account, proxy):
    status, payload = await api_call(session, account, "/tasks", None, proxy, "GET")
    if not ok_payload(status, payload):
        log_yellow("The task list was not returned by the server")
        return 0.0, {}
    tasks = payload.get("tasks") or []
    counters = payload.get("ads") or {}
    if not tasks:
        log_yellow("The task list came back empty for this account")
        return 0.0, counters
    before = account["coins"]
    paid = 0
    done = 0
    joins = 0
    failed = 0
    for task in tasks[:TASK_LIMIT]:
        task_id = clean_text(task.get("id"), "")
        if not task_id:
            continue
        label = shorten(task.get("title"), "task", TASK_TITLE_LIMIT)
        kind = clean_text(task.get("task_type"), "task")
        if kind not in ("channel", "bot", "group"):
            continue
        await api_call(
            session, account, f"/tasks/{task_id}/start", {}, proxy, "POST"
        )
        result, reward = await verify_task(session, account, proxy, task_id)
        if result == "paid":
            gained = await read_state(session, account, proxy)
            after = number_float(gained, "balance_coins", account["coins"])
            delta = round(after - account["coins"], 6)
            account["coins"] = after
            if delta > 0:
                log_green(
                    f"Task {clean_text(label, 'task')} credited "
                    f"{clean_text(format_amount(delta), 0)} coins"
                )
            paid += 1
        elif result == "done":
            done += 1
        elif result == "join":
            joins += 1
        else:
            failed += 1
        countdown(ROUND_PAUSE_SECONDS, "Next task in")
    total = round(account["coins"] - before, 6)
    if paid:
        log_green(
            f"{clean_text(paid, 0)} {clean_text(plural(paid), 'tasks')} "
            f"verified and paid on this account"
        )
    elif done and not joins and not failed:
        log_green("Every available task was already claimed for this account")
    if joins:
        log_yellow(
            f"{clean_text(joins, 0)} {clean_text(plural(joins), 'tasks')} "
            f"skipped because a channel join is required"
        )
    if failed:
        log_yellow(
            f"{clean_text(failed, 0)} {clean_text(plural(failed), 'tasks')} "
            f"refused by the server on this run"
        )
    return max(0.0, total), counters


async def run_ads(session, account, proxy):
    status, payload = await api_call(session, account, "/tasks", None, proxy, "GET")
    if not ok_payload(status, payload):
        return 0.0
    config = payload.get("ads_config") or {}
    rewards = config.get("rewards") or {}
    limit = number_of(config, "limit", AD_MAX_ROUNDS) or AD_MAX_ROUNDS
    fresh = payload.get("ads") or counters
    earned = 0.0
    credited = 0
    unverified = 0
    for provider, ad_type in (
        (ADSGRAM_BLOCK_MARKER, "task_adsgram"),
        ("monetag", "task_monetag"),
        ("onclicka", "earn_onclicka"),
        ("adexium", "earn_adexium"),
    ):
        watched = number_of(fresh, provider)
        if watched >= limit:
            continue
        rounds = 0
        while rounds < AD_MAX_ROUNDS and watched < limit:
            rounds += 1
            before = account["coins"]
            status, payload = await api_call(
                session, account, "/earn/watch_ad", {"ad_type": ad_type}, proxy, "POST"
            )
            if not ok_payload(status, payload):
                message = error_message(payload).lower()
                if any(word in message for word in COOLDOWN_WORDS):
                    countdown(AD_COOLDOWN_SECONDS, "Wait for next ad")
                    continue
                break
            await asyncio.sleep(AD_COOLDOWN_SECONDS)
            status, payload = await api_call(
                session, account, "/tasks", None, proxy, "GET"
            )
            if not ok_payload(status, payload):
                break
            fresh = payload.get("ads") or fresh
            account["coins"] = number_float(
                (await read_state(session, account, proxy)),
                "balance_coins",
                account["coins"],
            )
            moved = number_of(fresh, provider) - watched
            if moved > 0:
                rate = number_float(rewards, provider)
                gain = round(rate * moved, 6)
                earned += gain
                credited += moved
                watched = number_of(fresh, provider)
                log_green(
                    f"Ad view {clean_text(watched, 0)} of {clean_text(limit, 0)} on "
                    f"{clean_text(provider, 'provider')} was rewarded "
                    f"{clean_text(format_amount(gain), 0)} coins"
                )
            else:
                account["coins"] = before
                unverified += 1
                if unverified >= AD_UNVERIFIED_LIMIT:
                    break
            countdown(AD_COOLDOWN_SECONDS, "Wait for next ad")
        if unverified >= AD_UNVERIFIED_LIMIT:
            break
    if credited:
        log_green(
            f"{clean_text(credited, 0)} "
            f"{clean_text(plural(credited, 'ad view'), 'ad views')} "
            f"credited on this account"
        )
    elif not unverified:
        log_green("Every rewarded ad slot was already filled for this account")
    else:
        log_yellow("No ad reward could be verified from the ad network")
    return earned


async def run_friends(session, account, proxy):
    status, payload = await api_call(session, account, "/friends", None, proxy, "GET")
    if not ok_payload(status, payload):
        return 0.0
    friends = len(payload.get("friends") or [])
    earned = number_float(payload, "total_earnings")
    account["friends"] = friends
    if friends <= 0:
        log_yellow("This account has no invited friends yet")
        return 0.0
    log_green(
        f"Referral team holds {clean_text(friends, 0)} friends and "
        f"{clean_text(format_amount(earned), 0)} coins earned"
    )
    return earned


async def process_account(line, proxy, index):
    account = parse_init_data(line)
    if not account:
        log_red(f"Credential line {clean_text(index, 1)} is not valid initData")
        return

    connector = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        user = await run_auth(session, account, proxy)
        if not user:
            log_red(f"Sign in failed for account number {clean_text(index, 1)}")
            return

        name = display_name(account)
        log_green(
            f"Signed in {clean_text(shorten(name, 'account', NAME_LIMIT), 'account')} "
            f"with {clean_text(format_amount(account['coins']), 0)} coins and "
            f"{clean_text(format_amount(account['ton']), 0)} TON"
        )

        binding = clean_text(account.get("startParam"), "")
        if binding and binding == clean_text(REF_CODE, ""):
            log_green(
                f"Referral code {clean_text(binding, 'code')} is carried by this sign in"
            )
        elif binding:
            log_yellow(
                f"Credential already carries referral code {clean_text(binding, 'code')}"
            )
        else:
            log_green(
                f"Referral code {clean_text(REF_CODE, 'code')} is attached to this sign in"
            )

        start_coins = account["coins"]
        board, quests, achievements = await run_earn_status(session, account, proxy)
        await run_checkin(session, account, proxy, board)
        await run_quests(session, account, proxy, quests)
        await run_achievements(session, account, proxy, achievements)
        await run_tasks(session, account, proxy)
        await run_ads(session, account, proxy)
        await run_friends(session, account, proxy)

        end_coins = account["coins"]
        if abs(round(end_coins - start_coins, 6)) > 0.000001:
            log_green(
                f"Cycle credited {clean_text(format_amount(end_coins - start_coins), 0)} "
                f"coins on this account"
            )
        log_red(
            f"Cycle closed with {clean_text(format_amount(account['coins']), 0)} coins and "
            f"{clean_text(format_amount(account['ton']), 0)} TON"
        )


async def main_async(accounts, proxies, sleep_secs):
    cycle = 1
    while True:
        log_yellow(f"Starting automation cycle number {clean_text(cycle, 0)}")

        for index, line in enumerate(accounts):
            if index > 0:
                print()

            proxy_line = proxies[index % len(proxies)] if proxies else None
            proxy_url = normalize_proxy(proxy_line) if proxy_line else None
            if proxy_url:
                log_yellow(f"Using proxy {mask_proxy(proxy_url)}")

            await process_account(line, proxy_url, index + 1)
            countdown(ROUND_PAUSE_SECONDS, "Next account in")

        log_yellow(f"Automation cycle number {clean_text(cycle, 0)} is complete")
        cycle += 1
        countdown(sleep_secs, "Next cycle starts in")
        show_banner(MY_PROJECT)


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    show_banner(MY_PROJECT)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    settings = load_config().get("settings", {})
    accounts = load_lines("data.txt", True)
    proxies = load_lines("proxy.txt", False)
    asyncio.run(main_async(accounts, proxies, settings["sleep_seconds"]))


if __name__ == "__main__":
    main()
