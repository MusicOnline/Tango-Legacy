import asyncio
import random
from typing import Dict, List, Optional

import asyncpg  # type: ignore
import discord  # type: ignore
from discord.ext import commands  # type: ignore

import botto

# pylint: disable=bad-whitespace
# fmt: off
HIRAGANA_SYLLABLES = [
    "あ", "い", "う", "え", "お",
    "か", "き", "く", "け", "こ", "きゃ", "きゅ", "きょ",
    "さ", "し", "す", "せ", "そ", "しゃ", "しゅ", "しょ",
    "た", "ち", "つ", "て", "と", "ちゃ", "ちゅ", "ちょ",
    "な", "に", "ぬ", "ね", "の", "にゃ", "にゅ", "にょ",
    "は", "ひ", "ふ", "へ", "ほ", "ひゃ", "ひゅ", "ひょ",
    "ま", "み", "む", "め", "も", "みゃ", "みゅ", "みょ",
    "や",      "ゆ",      "よ",
    "ら", "り", "る", "れ", "ろ", "りゃ", "りゅ", "りょ",
    "わ", "ゐ",      "ゑ", "を",
    "ん",
    "が", "ぎ", "ぐ", "げ", "ご", "ぎゃ", "ぎゅ", "ぎょ",
    "ざ", "じ", "ず", "ぜ", "ぞ", "じゃ", "じゅ", "じょ",
    "だ", "ぢ", "づ", "で", "ど", "ぢゃ", "ぢゅ", "ぢょ",
    "ば", "び", "ぶ", "べ", "ぼ", "びゃ", "びゅ", "びょ",
    "ぱ", "ぴ", "ぷ", "ぺ", "ぽ", "ぴゃ", "ぴゅ", "ぴょ",
    "ゔぁ", "ゔぃ", "ゔ", "ゔぇ", "ゔぉ",
    "うぃ", "うぇ", "うぉ",
    "ふぁ", "ふぃ", "ふぇ", "ふぉ",
    "てぃ", "とぅ",
    "でぃ", "どぅ",
    "ちぇ", "しぇ", "じぇ"
]

KATAKANA_SYLLABLES = [
    "ア", "イ", "ウ", "エ", "オ",
    "カ", "キ", "ク", "ケ", "コ", "キャ", "キュ", "キョ",
    "サ", "シ", "ス", "セ", "ソ", "シャ", "シュ", "ショ",
    "タ", "チ", "ツ", "テ", "ト", "チャ", "チュ", "チョ",
    "ナ", "ニ", "ヌ", "ネ", "ノ", "ニャ", "ニュ", "ニョ",
    "ハ", "ヒ", "フ", "ヘ", "ホ", "ヒャ", "ヒュ", "ヒョ",
    "マ", "ミ", "ム", "メ", "モ", "ミャ", "ミュ", "ミョ",
    "ヤ",      "ユ",      "ヨ",
    "ラ", "リ", "ル", "レ", "ロ", "リャ", "リュ", "リョ",
    "ワ", "ヰ",      "ヱ", "ヲ",
    "ン",
    "ガ", "ギ", "グ", "ゲ", "ゴ", "ギャ", "ギュ", "ギョ",
    "ザ", "ジ", "ズ", "ゼ", "ゾ", "ジャ", "ジュ", "ジョ",
    "ダ", "ヂ", "ヅ", "デ", "ド", "ヂャ", "ヂュ", "ヂョ",
    "バ", "ビ", "ブ", "ベ", "ボ", "ビャ", "ビュ", "ビョ",
    "パ", "ピ", "プ", "ペ", "ポ", "ピャ", "ピュ", "ピョ",
    "ヴァ", "ヴィ", "ヴ", "ヴェ", "ヴォ",
    "ウィ", "ウェ", "ウォ",
    "ファ", "フィ", "フェ", "フォ",
    "ティ", "トゥ",
    "ディ", "ドゥ",
    "チェ", "シェ", "ジェ"
]

NON_SYLLABLES = ["っ", "ッ", "ー"]
# fmt: on
# pylint: enable=bad-whitespace

to_hiragana = lambda kana: HIRAGANA_SYLLABLES[KATAKANA_SYLLABLES.index(kana)]
to_katakana = lambda kana: KATAKANA_SYLLABLES[HIRAGANA_SYLLABLES.index(kana)]


class Shiritori(commands.Cog):
    def __init__(self, bot: botto.Botto) -> None:
        self.bot: botto.Botto = bot
        self.sessions: Dict[discord.User, asyncio.Task] = {}

    def __unload(self) -> None:
        for task in self.sessions.values():
            task.cancel()

    async def check_is_noun(self, word: str) -> bool:
        try:
            return await self.bot.db.scalar(
                """
                SELECT EXISTS(
                    SELECT
                        1
                    FROM
                        "JMdict_ReadingSense" AS rs
                    INNER JOIN
                        "JMdict_Sense" AS s
                            ON rs.entry_id = s.entry_id
                            AND rs.sense_index = s.index
                    WHERE
                        rs.reading_literal = '{}'
                        AND 'noun (common) (futsuumeishi)' = ANY(s.parts_of_speech)
                );
                """.format(
                    word
                )
            )
        except asyncpg.PostgresSyntaxError:
            return False

    async def get_next_word(
        self, kana_a: str, kana_b: str, used_words: Optional[List[str]] = None
    ) -> Optional[str]:

        if used_words is None:
            used_words = []

        if len(kana_a) == 2:
            regex_strategy: str = f"^(?:(?:{kana_a})|(?:{kana_b})).*[^んン]$"
        else:
            regex_strategy = f"^[{kana_a}{kana_b}][^ゃゅょャュョ].*[^んン]$"

        return await self.bot.db.scalar(
            """
            SELECT
                rs.reading_literal
            FROM
                "JMdict_ReadingSense" AS rs
            INNER JOIN
                "JMdict_Sense" AS s
                    ON rs.entry_id = s.entry_id
                    AND rs.sense_index = s.index
            WHERE
                rs.entry_id > {}
                AND rs.reading_literal ~ '{}'
                AND NOT rs.reading_literal = ANY(ARRAY[{}]::text[])
                AND 'noun (common) (futsuumeishi)' = ANY(s.parts_of_speech);
            """.format(
                random.randint(1000000, 1500000),
                regex_strategy,
                ", ".join(repr(s) for s in used_words),
            )
        )

    @botto.group(aliases=["しりとり", "尻取り"], invoke_without_command=True)
    async def shiritori(self, ctx: botto.Context, time_limit: int = 20) -> None:
        """Play Shiritori with Tango!"""
        if ctx.author in self.sessions:
            self.sessions.pop(ctx.author).cancel()
        if time_limit < 5:
            await ctx.send("I don't support speedtyping! Try five seconds and above.")
            return
        elif time_limit > 60:
            await ctx.send("I can be benevolent, but isn't over 60 seconds too much?")
            return

        embed: discord.Embed = discord.Embed(colour=botto.config.MAIN_COLOUR)
        embed.set_author(name="A game of Shiritori is starting!")
        embed.set_thumbnail(url=ctx.author.avatar_url)
        embed.description = (
            f"The rules for my game are as follows:\n"
            f"1. Words must be written in hiragana or katakana accordingly.\n"
            f"2. Words must consist of at least two syllables/kana.\n"
            f"3. Words must be nouns only.\n"
            f"4. A word must not be repeated twice.\n"
            f"5. The time limit for each turn is {time_limit} seconds.\n\n"
            f"All messages following this will be considered as answers. If you want "
            f"the bot to ignore a message (like if you're replying to a friend in the "
            f"same channel), add a backslash (`\\`) before your message.\n\n"
            f"Get ready, the game will start in 5 seconds!"
        )
        await ctx.send(embed=embed)
        await asyncio.sleep(5)

        await ctx.send(f"{botto.BLOBFISTBUMP} {ctx.author.mention} Starting off, しりとり!")

        self.sessions[ctx.author] = self.bot.loop.create_task(
            self.continue_shiritori(ctx, time_limit)
        )

    @shiritori.help_embed
    async def shiritori_help_embed(self, help_command) -> discord.Embed:
        embed: discord.Embed = discord.Embed(colour=botto.config.MAIN_COLOUR)
        embed.set_author(name=self.shiritori.name + " " + self.shiritori.signature)
        embed.description = (
            f"{self.shiritori.short_doc}\n\n"  # pylint: disable=no-member
            f"Shiritori (しりとり) is a Japanese word game in which the players are "
            f"required to say a word which begins with the final kana of the previous "
            f"word.\n\n"
            f'"Shiritori" literally means "taking the end" or "taking the rear".\n'
            f"The most similar game in English is Word Chain.\n"
            f"[Read more on Wikipedia.](https://en.wikipedia.org/wiki/Shiritori)"
        )
        embed.add_field(
            name="Command Aliases",
            value=" / ".join(self.shiritori.aliases),  # pylint: disable=no-member
        )
        embed.add_field(
            name="Checking Your Words",
            value=(
                "Tango provides you with an easy way to check if your word is valid "
                "without starting a game. To learn more, type "
                "`tango help shiritori check`."
            ),
        )
        embed.add_field(
            name="Wordbase",
            value=(
                "Tango's wordbase is built with data from the "
                "[JMdict](https://www.edrdg.org/jmdict/j_jmdict.html) project. "
            ),
        )
        embed.set_image(url="http://www.619.io/assets/img/shiritori/shiritori.png")
        return embed

    async def continue_shiritori(self, ctx: botto.Context, timeout: int) -> None:
        used_words: List[str] = ["しりとり"]

        def check(message: discord.Message) -> bool:
            return (
                ctx.author == message.author
                and ctx.channel == message.channel
                and message.content is not None
                and not message.content.startswith("\\")
            )

        while not self.bot.is_closed():
            try:
                msg: discord.Message = await self.bot.wait_for(
                    "message", check=check, timeout=timeout
                )
            except asyncio.TimeoutError:
                score = len(used_words) // 2
                if score == 0:
                    await ctx.send(
                        f"{botto.aBLOBSHAKE} {ctx.author} You took too long to answer. "
                        f"Try increasing the time limit!"
                    )
                elif score >= 10:
                    await ctx.send(
                        f"{botto.aBLOBCHEER} {ctx.author} Tick tock, time's up! "
                        f"You scored {score} point(s) this time."
                    )
                else:
                    await ctx.send(
                        f"{botto.aBLOBSHAKE} {ctx.author} Tick tock, time's up! "
                        f"You scored {score} point(s) this time."
                    )
                return
            used_words = await self.process_turn(ctx, msg.content, used_words)

    async def process_turn(
        self, ctx: botto.Context, word: str, used_words: List[str]
    ) -> List[str]:
        score: int = len(used_words) // 2
        emoji: discord.PartialEmoji
        if score >= 10:
            emoji = botto.aBLOBCHEER
        else:
            emoji = botto.BLOBSADPATS

        word = word.replace(" ", "").replace("\N{IDEOGRAPHIC SPACE}", "")
        if word in used_words:
            await ctx.send(f"{emoji} {ctx.author} You repeated {word}! Score: {score}")
            raise asyncio.CancelledError
        used_words.append(word)

        prev_word: str = used_words[-2]
        prev_last_syllable: str
        prev_other_syllable: str

        for i, char in enumerate(prev_word):
            try:
                if prev_word[i + 1] in "ゃゅょャュョ":
                    continue
            except IndexError:
                pass

            if char in "ゃゅょャュョ" and i >= 1:
                char = prev_word[i - 1] + char
            elif char in "ゃゅょャュョ" and i == 0:
                break

            if char in HIRAGANA_SYLLABLES:
                prev_last_syllable = char
                prev_other_syllable = to_katakana(char)
            elif char in KATAKANA_SYLLABLES:
                prev_last_syllable = char
                prev_other_syllable = to_hiragana(char)

        number_of_syllables: int = 0
        last_syllable: Optional[str] = None
        other_syllable: str

        for i, char in enumerate(word):
            try:
                if word[i + 1] in "ゃゅょャュョ":
                    continue
            except IndexError:
                pass

            if char in "ゃゅょャュョ" and i >= 1:
                char = word[i - 1] + char
            elif char in "ゃゅょャュョ" and i == 0:
                break

            if char in HIRAGANA_SYLLABLES:
                last_syllable = char
                other_syllable = to_katakana(char)
                number_of_syllables += 1
            elif char in KATAKANA_SYLLABLES:
                last_syllable = char
                other_syllable = to_hiragana(char)
                number_of_syllables += 1
            elif char not in NON_SYLLABLES:
                await ctx.send(
                    f"{emoji} {ctx.author} Your word must be in hiragana or katakana. "
                    f"What's {char}? Score: {score}"
                )
                raise asyncio.CancelledError

        if last_syllable is None:
            await ctx.send(
                f"{emoji} {ctx.author} Sokuon, sokuon, dash dash dash? Score: {score}"
            )
            raise asyncio.CancelledError
        elif not word.startswith((prev_last_syllable, prev_other_syllable)):
            await ctx.send(
                f"{emoji} {word} does not start with {prev_last_syllable} or "
                f"{prev_other_syllable}! Score: {score}"
            )
            raise asyncio.CancelledError
        elif last_syllable == "ん" or last_syllable == "ン":
            await ctx.send(f"{emoji} {word} ends with ん or ン! Score: {score}")
            raise asyncio.CancelledError
        elif number_of_syllables < 2:
            await ctx.send(
                f"{emoji} {ctx.author} Your word needs at least two syllables/kana. "
                f"Score: {score}"
            )
            raise asyncio.CancelledError

        async with ctx.typing():
            is_noun = await self.check_is_noun(word)

        if not is_noun:
            await ctx.send(
                f"{emoji} {ctx.author} Seems like {word} is not a common noun used "
                f"the Japanese language. Score: {score}"
            )
            raise asyncio.CancelledError

        async with ctx.typing():
            answer = await self.get_next_word(last_syllable, other_syllable, used_words)

        if answer is None:
            await ctx.send(
                f"{botto.aBLOBSHAKE} {ctx.author} I'm lost for words..."
                f" Score: {score}\n\nYou exhausted my vocabulary! "
                f"*(If you actually see this, I'm probably broken.)*"
            )
            raise asyncio.CancelledError

        await ctx.send(f"{botto.BLOBFISTBUMP} {answer}")
        used_words.append(answer)
        return used_words

    @shiritori.command(name="check", aliases=["かくにん", "確認"])
    async def shiritori_check(self, ctx: botto.Context, word: str) -> None:
        """Check if your word is Shiritori-compliant."""
        word = word.replace(" ", "").replace("\N{IDEOGRAPHIC SPACE}", "")
        number_of_syllables: int = 0
        last_syllable: Optional[str] = None
        other_syllable: str

        for i, char in enumerate(word):
            try:
                if word[i + 1] in "ゃゅょャュョ":
                    continue
            except IndexError:
                pass

            if char in "ゃゅょャュョ" and i >= 1:
                char = word[i - 1] + char
            elif char in "ゃゅょャュョ" and i == 0:
                break

            if char in HIRAGANA_SYLLABLES:
                last_syllable = char
                other_syllable = to_katakana(char)
                number_of_syllables += 1
            elif char in KATAKANA_SYLLABLES:
                last_syllable = char
                other_syllable = to_hiragana(char)
                number_of_syllables += 1
            elif char not in NON_SYLLABLES:
                await ctx.send(
                    f"{botto.BLOBSADPATS} Your word must be in hiragana or katakana. "
                    f"What's {char}?"
                )
                return

        if last_syllable is None:
            await ctx.send(f"{botto.BLOBSADPATS} Sokuon, sokuon, dash dash dash?")
            return
        elif last_syllable == "ん" or last_syllable == "ン":
            await ctx.send(f"{botto.BLOBSADPATS} {word} ends with ん or ン!")
            return
        elif number_of_syllables < 2:
            await ctx.send(
                f"{botto.BLOBSADPATS} Your word needs at least two syllables/kana."
            )
            return

        async with ctx.typing():
            is_noun = await self.check_is_noun(word)

        if not is_noun:
            await ctx.send(
                f"{botto.BLOBSADPATS} Seems like {word} is not a common noun used in "
                f"the Japanese language."
            )
            return

        await ctx.send(
            f"{botto.aBLOBCHEER} Looks good! The last syllable was {last_syllable} "
            f"or {other_syllable}."
        )

    @shiritori_check.help_embed
    async def shiritori_check_help_embed(self, help_command) -> discord.Embed:
        embed: discord.Embed = discord.Embed(colour=botto.config.MAIN_COLOUR)
        embed.set_author(name=self.shiritori_check.name + " " + self.shiritori_check.signature)
        embed.description = (
            f"{self.shiritori_check.short_doc}\n\n"  # pylint: disable=no-member
            f"The current implementation of Tango's Shiritori only allows hiragana "
            f"and katakana to be used. Shiritori with kanji will be added in the "
            f"future, with kana-only Shiritori being a game option.\n\n"
            f"To learn how to play the game with Tango, type `tango help shiritori`."
        )
        embed.add_field(
            name="Command Aliases",
            value=" / ".join(self.shiritori_check.aliases),  # pylint: disable=no-member
        )
        embed.add_field(
            name="Check Conditions",
            value=(
                "1. The word is made up of valid hiragana or katakana syllables.\n"
                "2. Thee word does not end with with ん or ン.\n"
                "3. The word consists of at least two kana. (ああ but not アー)\n"
                "4. The word is a common noun in the Japanese language."
            ),
        )
        return embed


def setup(bot: botto.Botto) -> None:
    # Temporary solution to issue where commands in cog instances lose their help embed
    cog = Shiritori(bot)
    cog.shiritori.help_embed(cog.shiritori_help_embed)
    cog.shiritori_check.help_embed(cog.shiritori_check_help_embed)
    bot.add_cog(cog)
