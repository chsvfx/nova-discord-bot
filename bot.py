import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
import asyncio
from collections import deque
import json
import os
import traceback
import yt_dlp
import imageio_ffmpeg

# ===================== CONFIG =====================
TOKEN = os.getenv("TOKEN")
GUILD_ID = 1351310078849847358
MEMBER_ROLE_ID = 1386784222781505619

SYSTEM_LOG_CHANNEL_ID = 1462412675295481971
VERIFY_LOG_CHANNEL_ID = 1462412645150752890
JOIN_LOG_CHANNEL_ID = 1462412615195164908
LEAVE_LOG_CHANNEL_ID = 1462412568747573422
BOT_STATUS_CHANNEL_ID = 1462406299936362516

STATUS_FILE = "status_data.json"

# ===================== INTENTS =====================
intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
BOT_START_TIME = datetime.now(timezone.utc)
RECENT_LEAVES = {}
guild_queues: dict[int, deque] = {}

# ===================== JSON HELPERS =====================
def load_status_data():
    if not os.path.exists(STATUS_FILE):
        return {"message_id": None}
    with open(STATUS_FILE, "r") as f:
        return json.load(f)

def save_status_data(data):
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ===================== LOGGING =====================
async def send_log(channel_id, title, description, color):
    channel = bot.get_channel(channel_id)
    if not channel:
        return
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    await channel.send(embed=embed)

# ===================== STATUS SYSTEM =====================
def build_status_embed(state: str):
    colors = {"online": discord.Color.green(), "offline": discord.Color.red(), "restart": discord.Color.orange()}
    texts = {"online": "🟢 Online", "offline": "🔴 Offline", "restart": "🟡 Restarting"}
    uptime = datetime.now(timezone.utc) - BOT_START_TIME
    embed = discord.Embed(
        title="🤖 𝙏𝙝𝙚 𝙇𝙤𝙪𝙣𝙜𝙚™ Status",
        color=colors[state],
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="> STATUS", value=f"```\n{texts[state]}\n```", inline=True)
    embed.add_field(name="> UPTIME", value=f"```\n{str(uptime).split('.')[0]}\n```", inline=True)
    embed.set_footer(text="Auto-updating status • Do not delete")
    return embed

async def send_or_edit_status(state: str):
    channel = bot.get_channel(BOT_STATUS_CHANNEL_ID)
    if not channel:
        return
    data = load_status_data()
    embed = build_status_embed(state)
    try:
        if data["message_id"]:
            msg = await channel.fetch_message(data["message_id"])
            await msg.edit(embed=embed)
        else:
            msg = await channel.send(embed=embed)
            data["message_id"] = msg.id
            save_status_data(data)
    except:
        msg = await channel.send(embed=embed)
        data["message_id"] = msg.id
        save_status_data(data)

@bot.tree.command(name="status", description="Show bot status")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def status_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(embed=build_status_embed("online"), ephemeral=True)

# ===================== VERIFY SYSTEM =====================
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
        await send_log(
            VERIFY_LOG_CHANNEL_ID,
            "✅ Member Verified",
            f"{interaction.user.mention} received **Member** role",
            discord.Color.green()
        )

@bot.tree.command(name="verify", description="Verify yourself")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def verify(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎉 𝙏𝙝𝙚 𝙇𝙤𝙪𝙣𝙜𝙚™ Verification",
        description="Click the button below to verify.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=VerifyView())

# ===================== MEMBER EVENTS =====================
@bot.event
async def on_member_join(member):
    await send_log(JOIN_LOG_CHANNEL_ID, "🟢 Member Joined", f"{member} (`{member.id}`)", discord.Color.green())

@bot.event
async def on_member_remove(member):
    RECENT_LEAVES[member.id] = datetime.now(timezone.utc)
    await send_log(LEAVE_LOG_CHANNEL_ID, "🔴 Member Left", f"{member} (`{member.id}`)", discord.Color.red())

# ===================== MUSIC SYSTEM =====================
YDL_OPTIONS = {"format": "bestaudio/best", "quiet": True, "noplaylist": True}
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()  # Static ffmpeg for Railway

async def play_next(guild_id):
    guild = bot.get_guild(guild_id)
    if not guild:
        return
    vc = guild.voice_client
    queue = guild_queues.get(guild_id)
    if not vc or not queue:
        return
    if len(queue) == 0:
        await vc.disconnect()
        return
    song = queue.popleft()
    source = await discord.FFmpegOpusAudio.from_probe(song["url"], executable=FFMPEG_PATH)
    vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop))

@bot.tree.command(name="play", description="Play music from YouTube")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def play(interaction: discord.Interaction, query: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Join a voice channel first.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    queue = guild_queues.setdefault(interaction.guild.id, deque())

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            if "youtube.com/watch" in query or "youtu.be/" in query:
                info = ydl.extract_info(query, download=False)
            else:
                search = ydl.extract_info(f"ytsearch:{query}", download=False)
                if "entries" not in search or len(search["entries"]) == 0:
                    await interaction.followup.send("❌ No results found.", ephemeral=True)
                    return
                info = search["entries"][0]
            queue.append({"title": info["title"], "url": info["url"]})
            if not vc.is_playing():
                await play_next(interaction.guild.id)
            await interaction.followup.send(f"▶️ Now playing **{info['title']}**")
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
    guild_queues.get(interaction.guild.id, deque()).clear()
    await interaction.response.send_message("⏹️ Stopped.", ephemeral=True)

# ===================== CORE EVENTS =====================
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    await send_or_edit_status("online")
    print(f"Logged in as {bot.user} | Commands synced in guild {GUILD_ID}")

@bot.event
async def on_disconnect():
    await send_or_edit_status("offline")

@bot.event
async def on_error(event, *args, **kwargs):
    err = traceback.format_exc(limit=4)
    await send_log(BOT_STATUS_CHANNEL_ID, "⚠️ Bot Error", f"```{err}```", discord.Color.red())

# ===================== START =====================
bot.run(TOKEN)