import os
import unicodedata

import discord  # type: ignore
from discord.ext import commands  # type: ignore

import botto
from botto.core.models.kanjidic2 import Kanji, KanjiMeaningsReadings
from botto.utils import kanjivg_gif, kanimaji


class KanjiSearch(commands.Cog):
    def __init__(self, bot: botto.Botto) -> None:
        self.bot: botto.Botto = bot

    async def get_stroke_diagram(self, character: str) -> discord.File:
        codepoint = f"{ord(character):05x}"
        # filename = f"resources/data/kanjivg_gif/{codepoint}.gif"
        # if os.path.isfile(filename):
        #     return discord.File(
        #         filename, f"{unicodedata.name(character)}.gif".replace(" ", "_")
        #     )
        # else:
        #     return await self.create_kanji_vg_gif(character)
        filename = f"resources/data/kanjivg_kanimaji_gif/{codepoint}_anim.gif"
        if os.path.isfile(filename):
            return discord.File(
                filename, f"{unicodedata.name(character)}.gif".replace(" ", "_")
            )
        else:
            return await self.create_kanimaji_gif(character)

    async def create_kanji_vg_gif(self, character: str) -> discord.File:
        codepoint = f"{ord(character):05x}"
        filename = f"resources/data/kanjivg_svg/{codepoint}.svg"
        if not os.path.isfile(filename):
            raise ValueError("No stroke diagram found.")
        output = f"resources/data/kanjivg_gif/{codepoint}.gif"
        await self.bot.loop.run_in_executor(
            None, kanjivg_gif.create_gif, filename, output
        )
        return discord.File(
            output, f"{unicodedata.name(character)}.gif".replace(" ", "_")
        )

    async def create_kanimaji_gif(self, character: str) -> discord.File:
        codepoint = f"{ord(character):05x}"
        filename = f"resources/data/kanjivg_svg/{codepoint}.svg"
        if not os.path.isfile(filename):
            raise ValueError("No stroke diagram found.")
        output = f"resources/data/kanjivg_kanimaji_gif/{codepoint}_anim.gif"
        await self.bot.loop.run_in_executor(None, kanimaji.create_gif, filename)
        return discord.File(
            output, f"{unicodedata.name(character)}.gif".replace(" ", "_")
        )

    @botto.command(name="kanji", aliases=["k", "かんじ", "漢字"])
    async def kanji_search(self, ctx: botto.Context, kanji: str) -> None:
        """Look up a kanji character."""
        if len(kanji) > 1:
            await ctx.send("Try doing one character at a time.")
            return

        legal_prefixes = ("CJK UNIFIED IDEOGRAPH", "CJK COMPATIBILITY IDEOGRAPH")
        if not unicodedata.name(kanji, "").startswith(legal_prefixes):
            await ctx.send(
                "Not found in the Japanese Industrial Standard (JIS) X kanji sets."
            )
            return

        _kanji = await Kanji.query.where(Kanji.character == kanji).gino.first()

        if _kanji is None:
            await ctx.send(
                "Not found in the Japanese Industrial Standard (JIS) X kanji sets."
            )
            return

        meanings_readings = await KanjiMeaningsReadings.query.where(
            KanjiMeaningsReadings.character == kanji
        ).gino.all()

        embed: discord.Embed = discord.Embed(colour=botto.config.MAIN_COLOUR)

        embed.set_author(name=f"Kanji Lookup - {_kanji}")

        embed.description = f"Stroke count: {_kanji.stroke_count}"
        if _kanji.grade:
            embed.description += f"\nGrade: {_kanji.grade}"
        if _kanji.frequency_rank:
            embed.description += f"\nFrequency rank: #{_kanji.frequency_rank}"
        if _kanji.old_jlpt_level:
            embed.description += f"\nFormer JLPT level: {_kanji.old_jlpt_level}"

        lines = []
        for i, mr_object in enumerate(meanings_readings):
            if mr_object.meanings:
                lines.append("__" + "/".join(mr_object.meanings) + "__")
            else:
                lines.append("*(miscellaneous readings)*")
            if mr_object.kun_readings:
                lines.append(
                    "**kun:** " + "\N{IDEOGRAPHIC COMMA}".join(mr_object.kun_readings)
                )
            if mr_object.on_readings:
                lines.append(
                    "**on:** " + "\N{IDEOGRAPHIC COMMA}".join(mr_object.on_readings)
                )
            if i + 1 != len(meanings_readings):
                lines.append("\n")

        if meanings_readings:
            embed.add_field(
                name="Meanings and Readings", value="\n".join(lines), inline=False
            )

        if _kanji.nanori:
            embed.add_field(
                name="Nanori (Pronunciation in names)",
                value="\N{IDEOGRAPHIC COMMA}".join(_kanji.nanori),
                inline=False,
            )

        other_kwargs = {}
        try:
            stroke_diagram = await self.get_stroke_diagram(kanji)
            embed.set_thumbnail(url=f"attachment://{stroke_diagram.filename}")
            other_kwargs["file"] = stroke_diagram
        except ValueError:
            pass

        await ctx.send(embed=embed, **other_kwargs)

    @kanji_search.help_embed
    async def kanji_help_embed(self, help_command) -> discord.Embed:
        embed: discord.Embed = discord.Embed(colour=botto.config.MAIN_COLOUR)
        embed.set_author(name=self.kanji_search.name + " " + self.kanji_search.signature)
        embed.description = (
            f"{self.kanji_search.short_doc}\n\n"  # pylint: disable=no-member
            f"Kanji are the adopted logographic Chinese characters that are used in "
            f"the Japanese writing system. They are used alongside the Japanese "
            f"syllabic scripts hiragana and katakana. "
            f"The Japanese term kanji for the Chinese characters literally means "
            f'"Han characters". It is written with the same characters in the Chinese '
            f"language to refer to the character writing system, hanzi (漢字).\n\n"
            f"Tango looks through "
            f"[KANJIDIC2](http://www.edrdg.org/wiki/index.php/KANJIDIC_Project) "
            f"to provide you information on a kanji character.\n\n"
            f"Animated stroke diagrams, when available, are generated using "
            f"data from [KanjiVG](https://kanjivg.tagaini.net/) and "
            f"[Yorwba's script](https://github.com/Yorwba/kanjivg-gif).\n\n"
            f"You can also use the Jisho command to look up more information regarding "
            f"a kanji character and its usages. To learn more, type "
            f"`tango help jisho`."
        )
        embed.add_field(
            name="Command Aliases",
            value=" / ".join(self.kanji_search.aliases),  # pylint: disable=no-member
        )
        return embed

    @botto.command(aliases=["so", "ひつじゅん", "筆順", "かきじゅん", "書き順"])
    async def strokeorder(self, ctx: botto.Context, kanji: str) -> None:
        """View an animated stroke diagram of a kanji."""
        if len(kanji) > 1:
            await ctx.send("Try doing one character at a time.")
            return

        legal_prefixes = ("CJK UNIFIED IDEOGRAPH", "CJK COMPATIBILITY IDEOGRAPH")
        if not unicodedata.name(kanji, "").startswith(legal_prefixes):
            await ctx.send(
                "Not found in the Japanese Industrial Standard (JIS) X kanji sets."
            )
            return

        async with ctx.typing():
            try:
                stroke_diagram = await self.get_stroke_diagram(kanji)
            except ValueError as exc:
                await ctx.send(exc)
                return

        await ctx.send(file=stroke_diagram)

    @strokeorder.help_embed
    async def strokeorder_help_embed(self, help_command) -> discord.Embed:
        embed: discord.Embed = discord.Embed(colour=botto.config.MAIN_COLOUR)
        embed.set_author(name=self.strokeorder.name + " " + self.strokeorder.signature)
        embed.description = (
            f"{self.strokeorder.short_doc}\n\n"  # pylint: disable=no-member
            f"Animated stroke diagrams are generated using data from "
            f"[KanjiVG](https://kanjivg.tagaini.net/) and "
            f"[Yorwba's script](https://github.com/Yorwba/kanjivg-gif)."
        )
        embed.add_field(
            name="Command Aliases",
            value=" / ".join(self.strokeorder.aliases),  # pylint: disable=no-member
        )
        return embed


def setup(bot: botto.Botto) -> None:
    # Temporary solution to issue where commands in cog instances lose their help embed
    cog = KanjiSearch(bot)
    cog.kanji_search.help_embed(cog.kanji_help_embed)
    cog.strokeorder.help_embed(cog.strokeorder_help_embed)
    bot.add_cog(cog)
