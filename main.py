import discord
from discord.ext import commands
from music_cog import music_cog

# ✅ Explicitly enable all required intents
intents = discord.Intents.default()
intents.message_content = True  # Already enabled in Discord Developer Portal
intents.guilds = True  # Required for bot to work in servers
intents.voice_states = True  # Required for music bots

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.add_cog(music_cog(bot))

# Read bot token
with open("token.txt", "r") as f:
    TOKEN = f.read().strip()

bot.run(TOKEN)
