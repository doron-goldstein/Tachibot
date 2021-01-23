import os
import re

import discord
import kadal

import aiohttp        
import aiofiles
import asyncio
import functools
import fast_colorthief

from dateutil.parser import parse

class TachiBoti(discord.Client):
    def __init__(self):
        super().__init__()
        # Note: this uses an OR regex hack.
        # Full match will match anything, but group 1 will match
        # the proper regex.
        self.manga_regex = re.compile(r"<.*?https?:\/\/.*?>|<a?:.+?:\d*>|`[\s\S]*?`|<(.*?)>")
        self.anime_regex = re.compile(r"`[\s\S]*?`|{(.*?)}")
        self.tachi_id = 349436576037732353
        self.klient = kadal.Klient(loop=self.loop)
        self.anilist_cover_url = "https://img.anili.st/media/"

    async def format_embed(self, name, anime=False):
        try:
            if anime:
                media = await self.klient.search_anime(name, popularity=True)
            else:
                media = await self.klient.search_manga(name, popularity=True)
        except kadal.MediaNotFound:
            return

        title = (media.title.get("english")
                 or media.title.get("romaji")
                 or media.title.get("native"))
        desc = "***" + ", ".join(media.genres) + "***\n"
        if media.description is not None:
            desc += media.description[:256 - len(desc)] + f"... [(more)]({media.site_url})"
        # dirty half-fix until i figure something better out
        desc = re.sub(r"<[bri/]{1,2}>", "", desc, flags=re.I|re.M)
        footer = re.sub(r".*\.", "", str(media.format))
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.anilist_cover_url}{media.id}") as resp:
                if resp.status == 200:
                    temp_img = "image.tmp"
                    async with aiofiles.open(temp_img, mode='wb') as f:
                        await f.write(await resp.read())
                    palette_partial = functools.partial(
                        fast_colorthief.get_palette,
                        temp_img,
                        color_count=2,
                        quality=100
                    )
                    palette_color = await self.loop.run_in_executor(
                        None,
                        palette_partial
                    )
                    embed_color = "%02x%02x%02x" % palette_color[1]
                else:
                    embed_color = "02A9FF"

        e = discord.Embed(title=title, description=desc, color=int(embed_color, 16))
        e.set_footer(text=footer.replace("TV", "ANIME").capitalize(), icon_url="https://anilist.co/img/logo_al.png")
        e.set_image(url=f"{self.anilist_cover_url}{media.id}")
        e.timestamp = parse(str(media.start_date), fuzzy=True)
        e.url = media.site_url
        return e

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
            """)
        except discord.errors.Forbidden:  # Can't DM member, give up.
            pass

    async def on_message(self, message):
        if message.author == self.user:  # Ignore own messages
            return
        m = self.manga_regex.findall(message.clean_content)
        m_clean = list(filter(bool, m))
        if m_clean:
            if len(m_clean) > 1:
                fmt = ""
                for name in m_clean:
                    try:
                        manga = await self.klient.search_manga(name, popularity=True)
                        fmt += "<" + manga.site_url + ">\n"
                    except kadal.MediaNotFound:
                        pass
                await message.channel.send(fmt)
            else:
                embed = await self.format_embed(m_clean[0])
                if not embed:
                    return
                await message.channel.send(embed=embed)

        a = self.anime_regex.findall(message.clean_content)
        a_clean = list(filter(bool, a))
        if a_clean:
            if len(a_clean) > 1:
                fmt = ""
                for name in a_clean:
                    try:
                        anime = await self.klient.search_anime(name, popularity=True)
                        fmt += "<" + anime.site_url + ">\n"
                    except kadal.MediaNotFound:
                        pass
                await message.channel.send(fmt)
            else:
                embed = await self.format_embed(a_clean[0], anime=True)
                if not embed:
                    return
                await message.channel.send(embed=embed)


bot = TachiBoti()
token = os.environ.get('TOKEN')
if token is None:
    with open("token") as f:
        token = f.readline()
bot.run(token)
