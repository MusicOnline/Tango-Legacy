from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Union

import discord  # type: ignore
from discord.ext import commands  # type: ignore

import tango


class Meta:
    """Meta commands related to the bot."""

    def __init__(self, bot: tango.Tango) -> None:
        self.bot: tango.Tango = bot
        self.owner_show_hidden: bool = False

    def get_statistics_embed(self) -> discord.Embed:
        total_members: int = sum(1 for m in self.bot.get_all_members())
        total_users: int = self.bot.user_count
        total_online: int = len(
            {
                m
                for m in self.bot.get_all_members()
                if m.status is not discord.Status.offline
            }
        )

        text_channels: int = sum(
            1
            for channel in self.bot.get_all_channels()
            if isinstance(channel, discord.TextChannel)
        )
        voice_channels: int = sum(
            1
            for channel in self.bot.get_all_channels()
            if isinstance(channel, discord.VoiceChannel)
        )
        total_channels: int = text_channels + voice_channels

        total_guilds: int = self.bot.guild_count
        assert self.bot.ready_time is not None
        up_since: str = self.bot.ready_time.strftime("%d %b %y")
        ping: int = self.bot.ping
        cpu_usage: float = self.bot.process.cpu_percent()
        ram_usage: float = self.bot.process.memory_full_info().uss / 2 ** 20

        embed: discord.Embed = discord.Embed(colour=tango.config.TANGO_COLOUR)
        embed.add_field(
            name="Member Stats",
            value=(
                f"{total_members} total members\n"
                f"{total_users} unqiue users\n"
                f"{total_online} users online"
            ),
        )
        embed.add_field(
            name="Channel Stats",
            value=(
                f"{total_channels} total\n"
                f"{text_channels} text channels\n"
                f"{voice_channels} voice channels"
            ),
        )
        embed.add_field(name="Other Stats", value=f"{total_guilds} guilds")
        embed.add_field(
            name="Uptime",
            value=(
                f"{self.bot.humanise_uptime(brief=True)}\n" f"(Since {up_since} UTC)"
            ),
        )
        embed.add_field(name="Connection", value=f"{ping} ms current")
        embed.add_field(name="Process", value=f"{cpu_usage}% CPU\n{ram_usage:.2f} MiB")

        return embed

    @tango.command(name="help", aliases=["ヘルプ"])
    async def _help(self, ctx: tango.Context, *command: str) -> None:
        if command:
            cmd: Optional[tango.Command] = self.bot.get_command(" ".join(command))
            if cmd is None:
                await ctx.send("I don't have that command.")
            elif cmd == self._help:  # pylint: disable=comparison-with-callable
                await ctx.send("Help help help help help help help help help help hel-")
            elif cmd._help_embed_coro:
                embed: discord.Embed = await cmd.get_help_embed()
                await ctx.send(embed=embed)
            else:
                await ctx.send(
                    "Additonal help information for that command is not available."
                )
            return

        embed = discord.Embed(colour=tango.config.TANGO_COLOUR)
        embed.set_author(name="How to use Tango?")
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.description = (
            "Tango is a simplistic bot here to help you learn and have fun with "
            "Japanese!\n"
            "To learn more about a command, type `tango help command_name`."
        )
        cmd_names: List[str] = [
            "jisho",
            "kanji",
            "strokeorder",
            "shiritori",
            "shiritori check",
            "invite",
        ]

        for cmd_name in cmd_names:
            cmd = self.bot.get_command(cmd_name)
            if cmd is not None:
                embed.add_field(
                    name=f"Command: tango {cmd.signature_without_aliases}",
                    value=cmd.short_doc or "TBA.",
                    inline=False,
                )
        embed.add_field(
            name="Bug Reports and Suggestions",
            value="All bug reports and suggestions should be DM'd to Music#9755.",
        )
        embed.set_footer(
            text="Prefixes: @Tango, tango, tg, t (followed with spaces) or たんご, タンゴ "
        )

        await ctx.send(embed=embed)

    @tango.command()
    async def botstats(self, ctx: tango.Context) -> None:
        """Show general statistics of the bot."""
        embed: discord.Embed = self.get_statistics_embed()
        await ctx.send(embed=embed)

    @tango.command()
    async def ping(self, ctx: tango.Context) -> None:
        """Show connection statistics of the bot."""
        await ctx.send(f"ws pong: **{self.bot.ping} ms**")

    @tango.command()
    async def uptime(self, ctx: tango.Context) -> None:
        """Show uptime of the bot."""
        await ctx.send(f"Online since **{self.bot.humanise_uptime()}** ago.")

    @tango.command()
    async def invite(self, ctx: tango.Context) -> None:
        """Show invite link of the bot."""
        await ctx.send(f"<{discord.utils.oauth_url(ctx.me.id)}>")

    @tango.command()
    async def source(self, ctx: tango.Context) -> None:
        """Show GitHub link to source code."""
        await ctx.send("https://github.com/MusicOnline/Tango")


def setup(bot: tango.Tango) -> None:
    bot.add_cog(Meta(bot))
