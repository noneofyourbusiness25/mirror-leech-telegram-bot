from asyncio import create_subprocess_exec
from sys import executable
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import send_message
from bot.helper.ext_utils.bot_utils import new_task

scraper_processes = {
    "autoscrape": None,
    "vegascrape": None
}

@new_task
async def manage_scrapers(_, message):
    args = message.text.split(maxsplit=1)

    if len(args) == 1:
        status_msg = "<b>Scraper Status:</b>\n"
        auto_status = "Running" if scraper_processes["autoscrape"] and scraper_processes["autoscrape"].returncode is None else "Stopped"
        vega_status = "Running" if scraper_processes["vegascrape"] and scraper_processes["vegascrape"].returncode is None else "Stopped"
        status_msg += f"Autoscrape (1TamilMV/Blasters): {auto_status}\n"
        status_msg += f"Vegascrape (Vegamovies): {vega_status}\n\n"
        status_msg += "<b>Usage:</b>\n"
        status_msg += f"/{BotCommands.ScraperCommand} start - Starts both scrapers\n"
        status_msg += f"/{BotCommands.ScraperCommand} stop - Stops both scrapers"
        await send_message(message, status_msg)
        return

    action = args[1].lower().strip()

    if action == "start":
        started = []
        if not scraper_processes["autoscrape"] or scraper_processes["autoscrape"].returncode is not None:
            scraper_processes["autoscrape"] = await create_subprocess_exec(executable, "bot/autoscrape.py")
            started.append("Autoscrape")

        if not scraper_processes["vegascrape"] or scraper_processes["vegascrape"].returncode is not None:
            scraper_processes["vegascrape"] = await create_subprocess_exec(executable, "bot/vegascrape.py")
            started.append("Vegascrape")

        if started:
            await send_message(message, f"Started scrapers: {', '.join(started)}")
        else:
            await send_message(message, "Scrapers are already running.")

    elif action == "stop":
        stopped = []
        if scraper_processes["autoscrape"] and scraper_processes["autoscrape"].returncode is None:
            scraper_processes["autoscrape"].kill()
            await scraper_processes["autoscrape"].wait()
            scraper_processes["autoscrape"] = None
            stopped.append("Autoscrape")

        if scraper_processes["vegascrape"] and scraper_processes["vegascrape"].returncode is None:
            scraper_processes["vegascrape"].kill()
            await scraper_processes["vegascrape"].wait()
            scraper_processes["vegascrape"] = None
            stopped.append("Vegascrape")

        if stopped:
            await send_message(message, f"Stopped scrapers: {', '.join(stopped)}")
        else:
            await send_message(message, "Scrapers are not running.")
    else:
        await send_message(message, "Invalid action. Use start or stop.")
