import discord
from discord.components import SelectMenu, SelectOption, Button
from discord.ext import commands
import asyncio
from asyncio import run_coroutine_threadsafe
from urllib import parse, request
import re
import json
import os
from youtube_dl import YoutubeDL

class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.is_playing = {}
        self.is_paused = {}
        self.musicQueue = {}
        self.queueIndex = {}

        self.YTDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'False'}
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

        self.embedBlue = 0x2c76dd
        self.embedRed = 0xdf1141
        self.embedGreen = 0x0eaa51
        
        self.vc = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            id = int(guild.id)
            self.musicQueue[id] = []
            self.queueIndex[id] = 0
            self.vc[id] = None
            self.is_paused[id] = self.is_playing[id] = False

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        id = int(member.guild.id)
        if member.id != self.bot.user.id and before.channel != None and after.channel != before.channel:
            remainingChannelMembers = before.channel.members
            if len(remainingChannelMembers) == 1 and remainingChannelMembers[0].id == self.bot.user.id and self.vc[id].is_connected():
                self.is_playing[id] = self.is_paused[id] = False
                self.musicQueue[id] = []
                self.queueIndex[id] = 0
                await self.vc[id].disconnect()

    def now_playing_embed(self, ctx, song):
        title = song['title']
        link = song['link']
        thumbnail = song['thumbnail']
        author = ctx.author
        avatar = author.avatar_url

        embed = discord.Embed(title="Now Playing", description=f'[{title}]({link})', color=self.embedBlue)
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text=f'Requested by: {str(author)}', icon_url=avatar)
        return embed

    async def join_vc(self, ctx, channel):
        id = int(ctx.guild.id)
        if self.vc[id] == None or not self.vc[id].is_connected():
            self.vc[id] = await channel.connect()
            
            if self.vc[id] == None:
                await ctx.send("Unable to join voice channel.")
                return
        else:
            await self.vc[id].move_to(channel)
                
    def search_yt(self, search):
        queryString = parse.urlencode({'search_query': search})
        htmContent = request.urlopen('https://www.youtube.com/results?' + queryString)
        searchResults = re.findall('/watch\?v=(.{11})',htmContent.read().decode())
        return searchResults[0:10]
    
    def extract_yt(self, url):
        with YoutubeDL(self.YTDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(url, download=False)

            except:
                return False
        
        return {
            'link': 'https://www.youtube.com/watch?v=' + url,
            'thumbnail': 'https://i.ytimg.com/vi/' + url + '/hqdefault.jpg?sqp=-oaymwEcCOADEI4CSFXyq4qpAw4IARUAAIhCGAFwAcABBg==&rs=AOn4CLD5uL4xKN-IUfez6KIW_j5y70mlig',
            'source': info['formats'][0]['url'],
            'title': info['title']
        }   
    
    def play_next(self, ctx):
        id = int(ctx.guild.id)
        if not self.is_playing[id]:
            return
        if self.queueIndex[id] + 1 < len(self.musicQueue[id]):
            self.is_playing[id] = True
            self.queryIndex[id] += 1

            song = self.musicQueue[id][self.queueIndex[id]][0]
            message = self.now_playing_embed(ctx, song)
            coro = ctx.send(embed = message)
            fut = run_coroutine_threadsafe(coro, self.bot.loop) 
            try:
                fut.result()
            except:
                pass

            self.vc[id].play(discord.FFmpegPCMAudio(song['source'], **self.FFMPEG_OPTIONS), after=lambda e: self.play_next(ctx))
        else:
            self.queueIndex[id] += 1
            self.is_playing[id] = False

    async def play_music(self, ctx):
        id = int(ctx.guild.id)
        if self.queueIndex[id] < len(self.musicQueue[id]):
            self.is_playing = True
            self.is_paused = False

            await self.join_vc(ctx, self.musicQueue[id][self.queueIndex[id]][1])

            song = self.musicQueue[id][self.queueIndex[id][0]]
            message = self.now_playing_embed(ctx, song)
            await ctx.send(embed = message)

            self.vc[id].play(discord.FFmpegPCMAudio(song['source'], **self.FFMPEG_OPTIONS),after=lambda e: self.play_music(ctx))
        
        else:
            await ctx.send("There is no song in the queue.")
            self.queueIndex[id] += 1
            self.is_playing[id] = False

    @commands.command(name = 'join', aliases = ['j'], help = '')
    async def join_vc(self, ctx, channel=None):
        guild_id = ctx.guild.id

        # Ensure self.vc dictionary is initialized
        if not hasattr(self, "vc"):
            self.vc = {}

        # Get the user's voice channel if not provided
        if channel is None:
            if ctx.author.voice and ctx.author.voice.channel:
                channel = ctx.author.voice.channel
            else:
                await ctx.send("You need to be in a voice channel to use this command! ❌")
                return

        # Check if the bot is already connected
        if guild_id in self.vc and self.vc[guild_id] is not None and self.vc[guild_id].is_connected():
            await ctx.send("I'm already connected to a voice channel! ✅")
            return

        # Join the voice channel
        try:
            self.vc[guild_id] = await channel.connect()
            await ctx.send(f"Joined {channel.name}! 🎵")
        except Exception as e:
            await ctx.send(f"Error joining voice channel: {e}")

    @commands.command(name = 'leave', aliases = ['l'], help = '')
    async def leave(self, ctx):
        guild_id = ctx.guild.id

        # Ensure self.vc dictionary is initialized
        if not hasattr(self, "vc"):
            self.vc = {}

        # Check if the bot is in a voice channel before trying to leave
        if guild_id not in self.vc or self.vc[guild_id] is None:
            await ctx.send("I'm not currently in a voice channel! ❌")
            return

        await ctx.send("Melonie has left the voice channel. ✅")
        await self.vc[guild_id].disconnect()
        self.vc[guild_id] = None  # Reset after disconnecting
