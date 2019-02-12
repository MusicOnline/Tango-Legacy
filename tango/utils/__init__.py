from typing import Union

import discord  # type: ignore

from .paginator import EmbedPaginator

__all__ = ["OptionalChannel", "EmbedPaginator"]

OptionalChannel = Union[
    discord.TextChannel,
    discord.VoiceChannel,
    discord.CategoryChannel,
    discord.DMChannel,
    discord.GroupChannel,
    None,
]
