import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import yt_dlp

TOKEN = os.getenv("TOKEN")
GUILD_ID = 1351310078849847358
MEMBER_ROLE_ID = 1386784222781505619

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= MUSIC =================
YDL_OPTIONS = {"format": "bestaudio[ext=m4a]/bestaudio/best", "quiet": True, "noplaylist": True}

async def play_next(guild_id):
    guild = bot.get_guild(guild_id)
    if not guild:
        return
    vc = guild.voice_client
    queue = guild_queues.get(guild_id)
    if not vc or not queue or len(queue) == 0:
        if vc:
            await vc.disconnect()
        return
    song = queue.pop(0)
    vc.play(discord.FFmpegPCMAudio(song["file"]), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop))

guild_queues = {}

@bot.tree.command(name="play", description="Play a YouTube link")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def play(interaction: discord.Interaction, url: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Join a voice channel first.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    queue = guild_queues.setdefault(interaction.guild.id, [])

    try:
        # Download the audio first
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            queue.append({"title": info["title"], "file": filename})

        if not vc.is_playing():
            await play_next(interaction.guild.id)

        await interaction.followup.send(f"▶️ Now playing: **{info['title']}**")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="skip", description="Skip current song")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭️ Skipped.", ephemeral=True)

@bot.tree.command(name="stop", description="Stop music and clear queue")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
    guild_queues.get(interaction.guild.id, []).clear()
    await interaction.response.send_message("⏹️ Stopped.", ephemeral=True)

# ================= VERIFY =================
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.success)
    async def verify(self, interaction: discord.Interaction, _):
        role = interaction.guild.get_role(MEMBER_ROLE_ID)
        if role in interaction.user.roles:
            await interaction.response.send_message("ℹ️ Already verified.", ephemeral=True)
            return
        await interaction.user.add_roles(role, reason="Verification")
        await interaction.response.send_message("✅ You are now verified!", ephemeral=True)

@bot.tree.command(name="verify", description="Verify yourself")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def verify(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎉 Verification",
        description="Click the button below to verify.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=VerifyView())

# ================= CORE =================
@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Logged in as {bot.user} | Commands synced")

bot.run(TOKEN)
