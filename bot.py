import os
import re

import discord
import kadal


class TachiBoti(discord.Client):
    def __init__(self):
        super().__init__()
        self.manga_regex = re.compile(
            r"(?!`)<((?!https?:\/\/.*)(?!a?:.*:).*?)>(?!`)")
        self.anime_regex = re.compile(r"{((?!https?:\/\/.*)(?!a?:.*:).*?)}")
        self.tachi_id = 349436576037732353
        self.klient = kadal.Klient(loop=self.loop)

    async def format_embed(self, name, anime=False):
        try:
            if anime:
                media = await self.klient.search_anime(name, popularity=True)
            else:
                media = await self.klient.search_manga(name, popularity=True)
        except kadal.MediaNotFound:
            return

        title = media.title.get('english') or media.title.get('romaji') or media.title.get('native')
        desc = "***" + ", ".join(media.genres) + "***\n"
        if media.description is not None:
            desc += media.description[:256 - len(desc)] + f"... [(more)]({media.site_url})"
        # dirty half-fix until i figure something better out
        desc = desc.replace("<br>", "").replace("<i>", "").replace("</i>", "")
        e = discord.Embed(title=title, description=desc, color=0x4286f4)
        e.set_thumbnail(url=media.cover_image)
        e.url = media.site_url
        return e

    async def on_ready(self):
        print("Ready!")
        print(self.user.name)
        print(self.user.id)
        print("~-~-~-~-~")

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
            """)
        except discord.errors.Forbidden:  # Can't DM member, give up.
            pass

    async def on_message(self, message):
        if message.author == self.user:  # Ignore own messages
            return
        m = self.manga_regex.findall(message.clean_content)
        if m:
            if len(m) > 1:
                fmt = ""
                for name in m:
                    try:
                        manga = await self.klient.search_manga(name, popularity=True)
                        fmt += "<" + manga.site_url + ">\n"
                    except kadal.MediaNotFound:
                        pass
                await message.channel.send(fmt)
            else:
                embed = await self.format_embed(m[0])
                if not embed:
                    return
                await message.channel.send(embed=embed)

        a = self.anime_regex.findall(message.clean_content)
        if a:
            if len(a) > 1:
                fmt = ""
                for name in a:
                    try:
                        anime = await self.klient.search_anime(name, popularity=True)
                        fmt += "<" + anime.site_url + ">\n"
                    except kadal.MediaNotFound:
                        pass
                await message.channel.send(fmt)
            else:
                embed = await self.format_embed(a[0], anime=True)
                if not embed:
                    return
                await message.channel.send(embed=embed)


bot = TachiBoti()
token = os.environ.get('TOKEN')
if token is None:
    with open("token") as f:
        token = f.readline()
bot.run(token)
