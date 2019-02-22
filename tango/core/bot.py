import asyncio
import datetime
import itertools
import logging
from typing import Any, Generator, Optional

import aiohttp  # type: ignore
import pkg_resources
import psutil  # type: ignore
from gino import Gino  # type: ignore

import discord  # type: ignore
from discord.ext import commands  # type: ignore

import tango
from .context import Context
from .errors import BotMissingFundamentalPermissions

try:
    import ujson as json
except ImportError:
    import json  # type: ignore

logger = logging.getLogger(__name__)


class Tango(commands.AutoShardedBot):

    db = Gino()

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(*tango.config.PREFIXES),
            pm_help=False,
            owner_id=tango.config.OWNER_ID,
            **kwargs,
        )
        self.ready_time: Optional[datetime.datetime] = None
        self.keep_alive_task: Optional[asyncio.Task] = None

        self.dpy_version: str = pkg_resources.get_distribution("discord.py").version

        self.process: psutil.Process = psutil.Process()

        self.session: aiohttp.ClientSession = aiohttp.ClientSession(
            loop=self.loop, json_serialize=json.dumps, raise_for_status=True
        )

        self.activity: discord.Activity = discord.Activity(
            name="@Tango", type=discord.ActivityType.listening
        )

        self.remove_command("help")
        self.add_check(self._check_fundamental_permissions)
        self.after_invoke(self.unlock_after_invoke)

    # ------ Properties ------

    @property
    def ping(self) -> int:
        """The Discord WebSocket Protocol latency rounded in milliseconds."""
        return round(self.latency * 1000)

    @property
    def uptime(self) -> datetime.timedelta:
        assert isinstance(self.ready_time, datetime.datetime)
        return datetime.datetime.utcnow() - self.ready_time

    def humanise_uptime(self, *, brief: bool = False) -> str:
        hours, remainder = divmod(int(self.uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if not brief:
            fmt = "{h} hours, {m} minutes, and {s} seconds"
            if days:
                fmt = "{d} days, " + fmt
        else:
            fmt = "{h}h {m}m {s}s"
            if days:
                fmt = "{d}d " + fmt

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

    # ------ Basic methods ------

    def _do_cleanup(self) -> None:
        logger.info("Cleaning up event loop.")
        if self.loop.is_closed():
            return  # we're already cleaning up

        task = self.loop.create_task(self.shutdown())

        def _silence_gathered(fut: asyncio.Future) -> None:
            try:
                fut.result()
            except Exception:
                pass
            finally:
                self.loop.stop()

        def when_future_is_done(fut: asyncio.Future) -> None:
            pending = asyncio.Task.all_tasks(loop=self.loop)
            if pending:
                logger.info("Cleaning up after %s tasks.", len(pending))
                gathered = asyncio.gather(*pending, loop=self.loop)
                gathered.cancel()
                gathered.add_done_callback(_silence_gathered)
            else:
                self.loop.stop()

        task.add_done_callback(when_future_is_done)
        if not self.loop.is_running():
            self.loop.run_forever()
        else:
            # on Linux, we're still running because we got triggered via
            # the signal handler rather than the natural KeyboardInterrupt
            # Since that's the case, we're going to return control after
            # registering the task for the event loop to handle later
            return

        try:
            task.result()  # suppress unused task warning
        except Exception:
            pass

    async def shutdown(self) -> None:
        if self.keep_alive_task is not None:
            self.keep_alive_task.cancel()

        for ext in tuple(self.extensions):
            self.unload_extension(ext)

        await self.db.pop_bind().close()
        logger.info("Gracefully closed database connection.")
        await self.session.close()
        logger.info("Gracefully closed asynchronous HTTP client session.")
        await self.logout()
        logger.info("Gracefully logged out from Discord.")

    async def process_commands(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        ctx = await self.get_context(message, cls=Context)
        if ctx.is_locked():
            return
        await self.invoke(ctx)

    # ------ Checks and invocation hooks ------

    async def _check_fundamental_permissions(self, ctx: Context) -> bool:
        # read_messages is an implicit requirement.
        # This check wouldn't run if it didn't read a command message. (duh)
        required_perms = discord.Permissions()
        required_perms.update(
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            external_emojis=True,
            add_reactions=True,
        )

        actual_perms = ctx.channel.permissions_for(ctx.me)

        missing = [
            perm
            for perm, value in required_perms
            if value is True and getattr(actual_perms, perm) is not True
        ]

        if not missing:
            return True

        raise BotMissingFundamentalPermissions(missing)

    async def unlock_after_invoke(self, ctx: Context) -> None:
        """Post invocation hook to unlock context."""
        ctx.unlock()

    # ------ Views ------

    def users_view(self) -> Generator[discord.User, None, None]:
        return self._connection._users.values()

    def guilds_view(self) -> Generator[discord.Guild, None, None]:
        return self._connection._guilds.values()

    @property
    def user_count(self) -> int:
        return len(self._connection._users)

    @property
    def guild_count(self) -> int:
        return len(self._connection._guilds)

    # ------ Event listeners ------

    async def on_ready(self) -> None:
        if self.keep_alive_task is not None:
            self.keep_alive_task.cancel()
        self.keep_alive_task = self.loop.create_task(self.keep_alive())

        self.ready_time = datetime.datetime.utcnow()
        logger.info("Bot has connected.")
        owner: Optional[discord.User] = self.get_user(self.owner_id)
        assert owner is not None
        embed: discord.Embed = self.cogs["Meta"].get_statistics_embed()
        await owner.send("Bot has connected.", embed=embed)

    # ------ Other ------

    async def keep_alive(self) -> None:
        """Background task for the bot not to enter a sleepish state when inactive."""
        channel: tango.utils.OptionalChannel = self.get_channel(
            tango.config.KEEP_ALIVE_CHANNEL
        )
        assert isinstance(channel, discord.TextChannel)

        for i in itertools.count():
            if not self.is_closed():
                await channel.send(f"Keeping alive, #{i}")
            await asyncio.sleep(5)
