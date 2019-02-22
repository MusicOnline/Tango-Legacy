import logging
import sys

from . import config
from .core import Tango

# Logging
dpy_logger: logging.Logger = logging.getLogger("discord")
dpy_logger.setLevel(logging.WARNING)
logger: logging.Logger = logging.getLogger("tango")
logger.setLevel(logging.INFO)

formatter: logging.Formatter = logging.Formatter(
    "[{asctime}] [{levelname:>8}] {name}: {message}", style="{"
)

stream_hdlr: logging.StreamHandler = logging.StreamHandler(sys.stdout)
file_hdlr: logging.FileHandler = logging.FileHandler(
    filename="tango.log", encoding="utf-8", mode="w"
)

stream_hdlr.setFormatter(formatter)
file_hdlr.setFormatter(formatter)

dpy_logger.addHandler(stream_hdlr)
dpy_logger.addHandler(file_hdlr)
logger.addHandler(stream_hdlr)
logger.addHandler(file_hdlr)

# Bot
bot: Tango = Tango()

bot.loop.run_until_complete(bot.db.set_bind(config.DATABASE_URI))
bot.load_extension("jishaku")
bot.load_extension("tango.modules.events")
bot.load_extension("tango.modules.owner")
bot.load_extension("tango.modules.meta")
bot.load_extension("tango.modules.jisho")
bot.load_extension("tango.modules.kanji")
bot.load_extension("tango.modules.shiritori")

try:
    bot.run(config.BOT_TOKEN)
except KeyboardInterrupt:
    logger.info("Received KeyboardInterrupt signal to shutdown.")
    bot.loop.run_until_complete(bot.shutdown())
