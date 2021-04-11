import os
import re
import textwrap

import discord
import kadal

from dateutil.parser import parse


class TachiBoti(discord.Client):
    def __init__(self):
        super().__init__()
        # Note: this uses an OR regex hack.
        # Full match will match anything, but group 1 will match
        # the proper regex.
        self.regex = {
            "anime": re.compile(r"`[\s\S]*?`|{(.*?)}"),
            "manga": re.compile(r"<.*?https?:\/\/.*?>|<a?:.+?:\d*>|`[\s\S]*?`|<(.*?)>")
        }
        self.tachi_id = 349436576037732353
        self.klient = kadal.Klient(loop=self.loop)
        self.anilist_cover_url = "https://img.anili.st/media/"

    @staticmethod
    def get_title(media):
        return (media.title.get("english")
                or media.title.get("romaji")
                or media.title.get("native"))

    async def format_embed(self, name, media, method, *, allow_adult):
        try:
            media = await method(name, popularity=True, allow_adult=allow_adult)
        except kadal.MediaNotFound:
            return

        desc = "***" + ", ".join(media.genres) + "***\n"
        if media.description is not None:
            short_desc = textwrap.shorten(media.description, width=256 - len(desc), placeholder="")
            desc += f"{short_desc}... [(more)]({media.site_url})"
        # dirty half-fix until i figure something better out
        replacements = [
            (r"</?i/?>", ""),
            (r"</?br/?>", "\n")
        ]
        for regex, regex_replace in replacements:
            desc = re.sub(regex, regex_replace, desc, flags=re.I | re.M)
        footer = re.sub(r".*\.", "", str(media.format))

        color_hex = media.cover_color or "2F3136"
        embed_color = int(color_hex.lstrip('#'), 16)
        title = self.get_title(media)
        e = discord.Embed(title=title, description=desc, color=embed_color)
        e.set_footer(text=footer.replace("TV", "ANIME").capitalize(),
                     icon_url="https://anilist.co/img/logo_al.png")
        e.set_image(url=f"{self.anilist_cover_url}{media.id}")
        if any(media.start_date.values()):
            e.timestamp = parse(str(media.start_date), fuzzy=True)
        e.url = media.site_url
        return e

    async def search(self, message, regex, media, search_method, *, allow_adult):
        m = regex.findall(message.clean_content)
        m_clean = list(filter(bool, m))
        if m_clean:
            async with message.channel.typing():
                embed = discord.Embed()
                if len(m_clean) > 1:
                    fmt = ""
                    for name in m_clean:
                        try:
                            media = await search_method(name, popularity=True, allow_adult=allow_adult)
                            title = self.get_title(media)
                            fmt += f"[**{title}**]({media.site_url})\n"
                        except kadal.MediaNotFound:
                            pass
                    embed.description = fmt
                    embed.color = discord.Color(0x2f3136)
                else:
                    embed = await self.format_embed(m_clean[0], media, search_method, allow_adult=allow_adult)
                    if not embed:
                        return
                await message.channel.send(embed=embed)

    async def on_message(self, message):
        if message.author == self.user:  # Ignore own messages
            return
        for media, regex in self.regex.items():
            method = self.klient.search_anime if media == "anime" else self.klient.search_manga
            await self.search(message, regex, media, method, allow_adult=message.channel.is_nsfw())

    async def on_ready(self):
        print("~-~-~-~-~-~-~-~-~-~-~")
        print(f"Bot: {self.user.name}")
        print(f"ID: {self.user.id}")
        print("~-~-~-~-~-~-~-~-~-~-~")
        print("Ready!")

    async def on_member_join(self, member):
        if member.guild.id != self.tachi_id:
            return
        try:
            await member.send("""
Welcome to Tachiyomi!\n
Before asking anything in <#349436576037732355>, please make sure to check the <#403520500443119619> channel, \
there's a very high chance you won't even have to ask.
Most if not all entries in <#403520500443119619> are up to date, \
and the channel is updated regularly to reflect the status of extensions and the app in general.
            """)  # noqa
        except discord.errors.Forbidden:  # Can't DM member, give up.
            pass


bot = TachiBoti()
token = os.environ.get('TOKEN')
if token is None:
    with open("token") as f:
        token = f.readline()
bot.run(token)
