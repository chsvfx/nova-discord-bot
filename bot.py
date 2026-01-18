import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
import os
import traceback
import json

# ===================== CONFIG =====================

GUILD_ID = 1351310078849847358
MEMBER_ROLE_ID = 1386784222781505619

SYSTEM_LOG_CHANNEL_ID = 1461313337089331323
VERIFY_LOG_CHANNEL_ID = 1461313803156328563
JOIN_LOG_CHANNEL_ID = 1461313859368390841
LEAVE_LOG_CHANNEL_ID = 1461313906076291084
BOT_STATUS_CHANNEL_ID = 1462406299936362516  # Status + Errors

STATUS_FILE = "status_data.json"

# ===================== INTENTS =====================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===================== MEMORY =====================

RECENT_LEAVES = {}
BOT_START_TIME = datetime.now(timezone.utc)

# Load persistent status message
try:
    with open(STATUS_FILE, "r") as f:
        status_data = json.load(f)
except:
    status_data = {"status_message_id": None}

STATUS_MESSAGE_ID = status_data.get("status_message_id")
LAST_ERROR_MESSAGE_ID = None

# ===================== HELPERS =====================

def save_status_data(data):
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f)

def get_channel(cid):
    return bot.get_channel(cid)

def account_age(created_at):
    now = datetime.now(timezone.utc)
    days = (now - created_at).days
    years = days // 365
    months = (days % 365) // 30
    days = (days % 365) % 30
    return f"{years}y {months}m {days}d"

async def send_log(channel_id, title, user, color, extra_fields=None):
    channel = get_channel(channel_id)
    if not channel:
        return

    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(
        name="👤 User",
        value=f"{user.mention}\n`{user.id}`",
        inline=False
    )
    if extra_fields:
        for name, value, inline in extra_fields:
            embed.add_field(name=name, value=value, inline=inline)
    await channel.send(embed=embed)

async def log_system(message, color=discord.Color.blurple()):
    await send_log(SYSTEM_LOG_CHANNEL_ID, "🟢 System Log", bot.user, color=color, extra_fields=[("", message, False)])

def shorten_error(error: str, max_length=900):
    return error if len(error) <= max_length else error[:max_length] + "\n... (truncated)"

# ===================== STATUS EMBED =====================

STATUS_CONFIG = {
    "online": {"text": "🟢 Online", "color": discord.Color.green()},
    "offline": {"text": "🔴 Offline", "color": discord.Color.red()},
    "partial": {"text": "🔄 Restarting", "color": discord.Color.orange()}
}

def format_uptime():
    delta = datetime.now(timezone.utc) - BOT_START_TIME
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, _ = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m"

def build_status_embed(status_key: str):
    cfg = STATUS_CONFIG[status_key]
    embed = discord.Embed(
        title="Vibe Lounge Bot",
        description="Live bot status monitor",
        color=cfg["color"],
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="> STATUS", value=f"```\n{cfg['text']}\n```", inline=True)
    embed.add_field(name="> UPTIME", value=f"```\n{format_uptime()}\n```", inline=True)
    embed.add_field(name="> LAST START", value=f"```\n<t:{int(BOT_START_TIME.timestamp())}:R>\n```", inline=False)
    embed.set_footer(text="Auto-updating • Do not delete")
    return embed

async def send_or_edit_status(status_key: str):
    global STATUS_MESSAGE_ID, status_data
    channel = bot.get_channel(BOT_STATUS_CHANNEL_ID)
    if not channel:
        return
    embed = build_status_embed(status_key)
    if STATUS_MESSAGE_ID:
        try:
            msg = await channel.fetch_message(STATUS_MESSAGE_ID)
            await msg.edit(embed=embed)
            return
        except discord.NotFound:
            STATUS_MESSAGE_ID = None
    msg = await channel.send(embed=embed)
    STATUS_MESSAGE_ID = msg.id
    status_data["status_message_id"] = STATUS_MESSAGE_ID
    save_status_data(status_data)

# ===================== VERIFY =====================

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.success)
    async def verify(self, interaction: discord.Interaction, _):
        role = interaction.guild.get_role(MEMBER_ROLE_ID)
        if not role:
            await interaction.response.send_message("❌ Member role not found.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message("ℹ️ Already verified.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await interaction.user.add_roles(role, reason="Server verification")
        await interaction.followup.send("✅ You have been verified!", ephemeral=True)
        await send_log(
            VERIFY_LOG_CHANNEL_ID,
            "✅ Member Verified",
            interaction.user,
            discord.Color.green(),
            extra_fields=[
                ("📅 Account Age", account_age(interaction.user.created_at), False),
                ("🏷️ Role", role.mention, False)
            ]
        )

@bot.tree.command(name="verify", description="Verify yourself to access the server")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def verify(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎉 Verification",
        description="Click the button below to receive the **Member** role.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=VerifyView())

# ===================== STATUS COMMAND =====================

@bot.tree.command(name="status", description="Show live bot status")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def status(interaction: discord.Interaction):
    await send_or_edit_status("online")
    await interaction.response.send_message("✅ Status displayed/updated.", ephemeral=True)

# ===================== EVENTS =====================

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    await send_or_edit_status("online")
    print(f"Bot online: {bot.user}")

@bot.event
async def on_disconnect():
    await send_or_edit_status("offline")

@bot.event
async def on_resumed():
    await send_or_edit_status("partial")

@bot.event
async def on_error(event, *args, **kwargs):
    global LAST_ERROR_MESSAGE_ID
    channel = bot.get_channel(BOT_STATUS_CHANNEL_ID)
    if not channel:
        return
    if LAST_ERROR_MESSAGE_ID:
        try:
            old_msg = await channel.fetch_message(LAST_ERROR_MESSAGE_ID)
            await old_msg.delete()
        except (discord.NotFound, discord.Forbidden):
            pass
    error = shorten_error(traceback.format_exc())
    embed = discord.Embed(
        title="🔴 Bot Error",
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="📌 Event", value=f"`{event}`", inline=False)
    embed.add_field(name="🧨 Error Details", value=f"```py\n{error}\n```", inline=False)
    embed.set_footer(text="Latest error only • Previous errors removed")
    msg = await channel.send(embed=embed)
    LAST_ERROR_MESSAGE_ID = msg.id
    print(error)

# ===================== MEMBER EVENTS =====================

@bot.event
async def on_member_join(member):
    rejoin_time = RECENT_LEAVES.get(member.id)
    risk = "🟢 Low"
    rejoin = "No"
    if rejoin_time:
        minutes = int((datetime.now(timezone.utc) - rejoin_time).total_seconds() / 60)
        rejoin = f"Yes ({minutes} min)"
        risk = "🔴 High" if minutes < 10 else "🟡 Medium"
    await send_log(
        JOIN_LOG_CHANNEL_ID,
        "🟢 Member Joined",
        member,
        discord.Color.green(),
        [
            ("📅 Account Age", account_age(member.created_at), False),
            ("🕒 Account Created", f"<t:{int(member.created_at.timestamp())}:F>", False),
            ("🔁 Rejoin", rejoin, False),
            ("🧬 Risk Level", risk, False)
        ]
    )

@bot.event
async def on_member_remove(member):
    RECENT_LEAVES[member.id] = datetime.now(timezone.utc)
    await send_log(
        LEAVE_LOG_CHANNEL_ID,
        "🔴 Member Left",
        member,
        discord.Color.red(),
        [
            ("📅 Account Age", account_age(member.created_at), False),
            ("🕒 Joined Server", f"<t:{int(member.joined_at.timestamp())}:F>" if member.joined_at else "Unknown", False)
        ]
    )

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # Nickname changes
    if before.nick != after.nick:
        old = before.nick or before.name
        new = after.nick or after.name
        moderator = None
        async for entry in after.guild.audit_logs(limit=5):
            if entry.target and entry.target.id == after.id:
                moderator = entry.user
                break
        changed_by = "Self" if not moderator or moderator.id == after.id else moderator.mention
        await send_log(
            SYSTEM_LOG_CHANNEL_ID,
            "✏️ Nickname Changed",
            after,
            discord.Color.blurple(),
            [
                ("🔤 Old Nickname", old, False),
                ("🔠 New Nickname", new, False),
                ("🛡️ Changed By", changed_by, False)
            ]
        )
    # Role changes
    before_roles = set(before.roles)
    after_roles = set(after.roles)
    added = after_roles - before_roles
    removed = before_roles - after_roles
    if added or removed:
        moderator = None
        async for entry in after.guild.audit_logs(limit=5):
            if entry.target and entry.target.id == after.id:
                moderator = entry.user
                break
    for role in added:
        await send_log(
            SYSTEM_LOG_CHANNEL_ID,
            "➕ Role Added",
            after,
            discord.Color.green(),
            [
                ("🏷️ Role", role.mention, False),
                ("🛡️ Added By", moderator.mention if moderator else "Unknown", False)
            ]
        )
    for role in removed:
        await send_log(
            SYSTEM_LOG_CHANNEL_ID,
            "➖ Role Removed",
            after,
            discord.Color.red(),
            [
                ("🏷️ Role", role.mention, False),
                ("🛡️ Removed By", moderator.mention if moderator else "Unknown", False)
            ]
        )

@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot:
        return
    deleter = None
    async for entry in message.guild.audit_logs(limit=5):
        if entry.target and entry.target.id == message.author.id:
            deleter = entry.user
            break
    content = message.content[:1000] if message.content else "*No text*"
    await send_log(
        SYSTEM_LOG_CHANNEL_ID,
        "🗑️ Message Deleted",
        message.author,
        discord.Color.orange(),
        [
            ("📍 Channel", message.channel.mention, False),
            ("📝 Content", f"```{content}```", False),
            ("🛡️ Deleted By", deleter.mention if deleter else "Unknown", False)
        ]
    )

# ===================== START =====================

bot.run(os.getenv("TOKEN"))
