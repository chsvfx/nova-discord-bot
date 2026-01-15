import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
import os
import traceback

# ===================== CONFIG =====================

GUILD_ID = 1351310078849847358
MEMBER_ROLE_NAME = "Member"

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
    return years, months, days

async def log_system(message: str, color=discord.Color.blurple()):
    """Send a system log embed"""
    channel = get_channel(SYSTEM_LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🟢 System Log",
            description=message,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        await channel.send(embed=embed)

# ===================== VERIFY VIEW =====================

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verify", style=discord.ButtonStyle.success)
    async def verify(self, interaction: discord.Interaction, _):
        role = discord.utils.get(interaction.guild.roles, name=MEMBER_ROLE_NAME)

        if not role:
            await interaction.response.send_message("❌ Member role not found.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("ℹ️ You are already verified.", ephemeral=True)
            return

        await interaction.user.add_roles(role, reason="Vibe Lounge Verification")
        await interaction.response.send_message(
            "✅ You are now verified. Welcome to **Vibe Lounge**!",
            ephemeral=True
        )

        # Verify log
        years, months, days = account_age(interaction.user.created_at)
        log = get_channel(VERIFY_LOG_CHANNEL_ID)

        if log:
            embed = discord.Embed(
                title="✅ Member Verified",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👤 User", value=f"{interaction.user}\n`{interaction.user.id}`", inline=False)
            embed.add_field(name="📅 Account Age", value=f"{years}y {months}m {days}d", inline=False)
            embed.add_field(name="🏷️ Role", value=MEMBER_ROLE_NAME, inline=False)
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="Vibe Lounge • Verify Logs")
            await log.send(embed=embed)

# ===================== /VERIFY COMMAND =====================

@bot.tree.command(name="verify", description="Verify yourself to access the server")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def verify(interaction: discord.Interaction):
    embed = discord.Embed(
        title="‼️ Server Rules",
        description=(
            "**1. Be respectful**\n"
            "Treat everyone with respect.\n\n"
            "**2. No discrimination**\n"
            "Hate or discrimination is not tolerated.\n\n"
            "**3. No spamming**\n"
            "No spam, ads or excessive tagging.\n\n"
            "**4. No join/leave abuse**\n"
            "This results in a permanent ban.\n\n"
            "**5. Stay on topic**\n"
            "Use the correct channels.\n\n"
            "**6. No impersonation**\n"
            "Be yourself.\n\n"
            "**7. No self-promotion**\n"
            "Only with staff permission.\n\n"
            "**8. Appropriate content**\n"
            "No NSFW or offensive content.\n\n"
            "**9. No spoilers**\n"
            "Use spoiler tags."
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Vibe Lounge • Verification")
    await interaction.response.send_message(embed=embed, view=VerifyView())

# ===================== EVENTS =====================

@bot.event
async def on_ready():
    # No bot.add_view() here, non-persistent view is enough
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
    log = get_channel(JOIN_LOG_CHANNEL_ID)
    if not log:
        return

    years, months, days = account_age(member.created_at)
    rejoin = RECENT_LEAVES.get(member.id)
    risk = "🟢 Low"
    rejoin_text = "No"

    if rejoin:
        minutes = int((datetime.now(timezone.utc) - rejoin).total_seconds() / 60)
        rejoin_text = f"Yes ({minutes} min)"
        risk = "🔴 High" if minutes < 10 else "🟡 Medium"

    embed = discord.Embed(
        title="🟢 Member Joined",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(name="👤 User", value=f"{member}\n`{member.id}`", inline=False)
    embed.add_field(name="🌍 Type", value="🤖 Bot" if member.bot else "👤 User", inline=False)
    embed.add_field(name="📅 Account Age", value=f"{years}y {months}m {days}d", inline=False)
    embed.add_field(name="🕒 Account Created", value=f"<t:{int(member.created_at.timestamp())}:F>", inline=False)
    embed.add_field(name="🟡 Rejoin", value=rejoin_text, inline=False)
    embed.add_field(name="🧬 Risk", value=risk, inline=False)

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Vibe Lounge • Join Logs")

    await log.send(embed=embed)

@bot.event
async def on_member_remove(member):
    log = get_channel(LEAVE_LOG_CHANNEL_ID)
    if not log:
        return

    years, months, days = account_age(member.created_at)
    roles = [r.mention for r in member.roles if r != member.guild.default_role]
    reason = "Left voluntarily"

    async for entry in member.guild.audit_logs(limit=5):
        if entry.target and entry.target.id == member.id:
            if entry.action == discord.AuditLogAction.kick:
                reason = f"Kicked by {entry.user}"
            elif entry.action == discord.AuditLogAction.ban:
                reason = f"Banned by {entry.user}"
            break

    embed = discord.Embed(
        title="🔴 Member Left",
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(name="👤 User", value=f"{member}\n`{member.id}`", inline=False)
    embed.add_field(name="🌍 Type", value="🤖 Bot" if member.bot else "👤 User", inline=False)
    embed.add_field(name="📅 Account Age", value=f"{years}y {months}m {days}d", inline=False)
    embed.add_field(
        name="🕒 Joined Server",
        value=f"<t:{int(member.joined_at.timestamp())}:F>" if member.joined_at else "Unknown",
        inline=False
    )
    embed.add_field(name="🧾 Role Count", value=str(len(roles)), inline=False)
    embed.add_field(name="🏷️ Roles", value=", ".join(roles) if roles else "None", inline=False)
    embed.add_field(name="📥 Reason", value=reason, inline=False)

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Vibe Lounge • Leave Logs")

    await log.send(embed=embed)
    RECENT_LEAVES[member.id] = datetime.now(timezone.utc)

# ===================== START =====================

bot.run(os.getenv("TOKEN"))
