import asyncio
import logging
import traceback
from typing import List

import discord  # type: ignore
from discord.ext import commands  # type: ignore

import tango


logger = logging.getLogger(__name__)


class Events:
    def __init__(self, bot: tango.Tango) -> None:
        self.bot: tango.Tango = bot

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.content:
            return

        mentions: List[str] = [f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"]
        if message.content in mentions:
            try:
                await message.channel.send(
                    f"Hello! My command prefixes are {self.bot.user.mention} "
                    f"and `tango`. Commands can be viewed with the help command."
                )
            except discord.Forbidden:
                pass

    async def on_guild_join(self, guild: discord.Guild) -> None:
        logger.info("Joined guild named '%s' (ID: %s).", guild, guild.id)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        logger.info("Removed from guild named '%s' (ID: %s).", guild, guild.id)

    async def on_command(self, ctx: tango.Context) -> None:
        logger.info("Command '%s' was called by %s.", ctx.command, ctx.author)

    async def on_command_error(self, ctx: tango.Context, error: Exception) -> None:
        # error is not typehinted as commands.CommandError
        # because error.original is not one

        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, tango.BotMissingFundamentalPermissions):
            if error.send_messages:
                await ctx.send(error)
            return

        if isinstance(error, asyncio.TimeoutError):
            await ctx.send("Tick tock. You took too long.")
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"You missed the `{error.param.name}` argument. "
                f"Here's the correct usage for the command.\n"
                f"```\n{ctx.prefix}{ctx.command.signature}\n```"
            )
            return

        if isinstance(error, commands.CheckFailure):
            message: str = str(error)
            if message and not message.startswith("The check functions for command"):
                await ctx.send(message)
            return

        ignored = (commands.CommandNotFound,)

        if isinstance(error, ignored):
            return

        logger.error(
            "Unhandled exception in '%s' command. (%s: %s)",
            ctx.command,
            error.__class__.__name__,
            error,
        )

        exc_info: List[str] = traceback.format_exception(
            type(error), error, error.__traceback__
        )
        logger.error("\n".join(exc_info))

        embed: discord.Embed = discord.Embed(
            colour=discord.Colour.red(),
            description=(
                f"The developer has been notified regarding this error.\n"
                f"Here's an apology cookie. \N{COOKIE}\n"
                f"```\n{type(error).__name__}"
            ),
        )
        if str(error):
            embed.description += f":\n{error}"
        embed.description += "\n```"
        embed.set_author(name="Beep boop. Unhandled exception.")
        await ctx.send(embed=embed)


def setup(bot: tango.Tango) -> None:
    bot.add_cog(Events(bot))
