import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
import os
import traceback

# ===================== CONFIG =====================

GUILD_ID = 1351310078849847358
MEMBER_ROLE_ID = 1386784222781505619

SYSTEM_LOG_CHANNEL_ID = 1461313337089331323
VERIFY_LOG_CHANNEL_ID = 1461313803156328563
JOIN_LOG_CHANNEL_ID = 1461313859368390841
LEAVE_LOG_CHANNEL_ID = 1461313906076291084

# ===================== INTENTS =====================

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===================== MEMORY =====================

RECENT_LEAVES = {}

# ===================== HELPERS =====================

def get_channel(cid):
    return bot.get_channel(cid)

def account_age(created_at):
    now = datetime.now(timezone.utc)
    days = (now - created_at).days
    years = days // 365
    months = (days % 365) // 30
    days = (days % 365) % 30
    return f"{years}y {months}m {days}d"

async def send_log(channel_id, title, user, color=discord.Color.green(), extra_fields=None, thumbnail=True):
    channel = get_channel(channel_id)
    if not channel:
        return
    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="👤 User", value=f"{user}\n`{user.id}`", inline=False)
    if extra_fields:
        for name, value, inline in extra_fields:
            embed.add_field(name=name, value=value, inline=inline)
    if thumbnail:
        embed.set_thumbnail(url=user.display_avatar.url)
    await channel.send(embed=embed)

async def log_system(message: str, color=discord.Color.blurple()):
    await send_log(SYSTEM_LOG_CHANNEL_ID, "🟢 System Log", bot.user, color=color, extra_fields=[("", message, False)], thumbnail=False)

# ===================== COMMANDS =====================

@bot.tree.command(name="rules", description="View the server rules")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def rules(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 Server Rules",
        description=(
            "1️⃣ **Be respectful** – Treat everyone with respect.\n"
            "2️⃣ **No discrimination** – Hate or discrimination is not tolerated.\n"
            "3️⃣ **No spamming** – No spam, ads or excessive tagging.\n"
            "4️⃣ **No join/leave abuse** – This results in a permanent ban.\n"
            "5️⃣ **Stay on topic** – Use the correct channels.\n"
            "6️⃣ **No impersonation** – Be yourself.\n"
            "7️⃣ **No self-promotion** – Only with staff permission.\n"
            "8️⃣ **Appropriate content** – No NSFW or offensive content.\n"
            "9️⃣ **No spoilers** – Use spoiler tags."
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Vibe Lounge • Server Rules")
    await interaction.response.send_message(embed=embed)

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
            await interaction.response.send_message("ℹ️ You already have the Member role.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await interaction.user.add_roles(role, reason="Vibe Lounge Verification")
        await interaction.followup.send("✅ Verify - You received the **Member** role!", ephemeral=True)

        age = account_age(interaction.user.created_at)
        await send_log(
            VERIFY_LOG_CHANNEL_ID,
            "✅ Member Verified",
            interaction.user,
            color=discord.Color.green(),
            extra_fields=[
                ("📅 Account Age", age, False),
                ("🏷️ Role", role.mention, False)
            ]
        )

@bot.tree.command(name="verify", description="Verify yourself to access the server")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def verify(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎉 Verify to Join!",
        description=(
            "Welcome to **Vibe Lounge!**\n\n"
            "Click the button below to receive the **Member** role and gain access to the server.\n\n"
            "💡 Make sure to read the server rules"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="Vibe Lounge • Verification")
    await interaction.response.send_message(embed=embed, view=VerifyView())

# ===================== EVENTS =====================

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    await log_system(f"Bot **{bot.user}** is now online ✅")
    print(f"🟢 Logged in as {bot.user}")

@bot.event
async def on_disconnect():
    await log_system(f"Bot **{bot.user}** disconnected ⚠️", color=discord.Color.orange())
    print(f"⚠️ {bot.user} disconnected")

@bot.event
async def on_resumed():
    await log_system(f"Bot **{bot.user}** resumed connection ✅", color=discord.Color.green())
    print(f"🟢 {bot.user} resumed")

@bot.event
async def on_error(event, *args, **kwargs):
    err = traceback.format_exc()
    await log_system(f"⚠️ Error in `{event}`:\n```{err}```", color=discord.Color.red())
    print(f"⚠️ Error in {event}:\n{err}")

@bot.event
async def on_member_join(member):
    rejoin = RECENT_LEAVES.get(member.id)
    risk = "🟢 Low"
    rejoin_text = "No"
    if rejoin:
        minutes = int((datetime.now(timezone.utc) - rejoin).total_seconds() / 60)
        rejoin_text = f"Yes ({minutes} min)"
        risk = "🔴 High" if minutes < 10 else "🟡 Medium"

    age = account_age(member.created_at)
    extra_fields = [
        ("🌍 Type", "🤖 Bot" if member.bot else "👤 User", False),
        ("📅 Account Age", age, False),
        ("🕒 Account Created", f"<t:{int(member.created_at.timestamp())}:F>", False),
        ("🟡 Rejoin", rejoin_text, False),
        ("🧬 Risk", risk, False)
    ]
    await send_log(JOIN_LOG_CHANNEL_ID, "🟢 Member Joined", member, color=discord.Color.green(), extra_fields=extra_fields)

@bot.event
async def on_member_remove(member):
    roles = [r.mention for r in member.roles if r != member.guild.default_role]
    reason = "Left voluntarily"
    async for entry in member.guild.audit_logs(limit=5):
        if entry.target and entry.target.id == member.id:
            if entry.action == discord.AuditLogAction.kick:
                reason = f"Kicked by {entry.user}"
            elif entry.action == discord.AuditLogAction.ban:
                reason = f"Banned by {entry.user}"
            break
    age = account_age(member.created_at)
    extra_fields = [
        ("🌍 Type", "🤖 Bot" if member.bot else "👤 User", False),
        ("📅 Account Age", age, False),
        ("🕒 Joined Server", f"<t:{int(member.joined_at.timestamp())}:F>" if member.joined_at else "Unknown", False),
        ("🧾 Role Count", str(len(roles)), False),
        ("🏷️ Roles", ", ".join(roles) if roles else "None", False),
        ("📥 Reason", reason, False)
    ]
    await send_log(LEAVE_LOG_CHANNEL_ID, "🔴 Member Left", member, color=discord.Color.red(), extra_fields=extra_fields)
    RECENT_LEAVES[member.id] = datetime.now(timezone.utc)

# ===================== START =====================

bot.run(os.getenv("TOKEN"))