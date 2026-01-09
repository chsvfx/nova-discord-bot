import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
import os

# ===================== CONFIG =====================

GUILD_ID = 1437438257972379870
VERIFY_ROLE_NAME = "Inwoner"

MONITORING_CHANNEL_ID = 1445758222408614049
VERIFY_LOG_CHANNEL_ID = 1445605544017531072
ANTI_NUKE_CHANNEL_ID = 1445772067877294211
JOIN_LOG_CHANNEL_ID = 1445606304138792980
LEAVE_LOG_CHANNEL_ID = 1445606375102349312

# ===================== INTENTS =====================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===================== VERIFY VIEW =====================

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Klik Hier Om je Rollen te ontvangen",
        style=discord.ButtonStyle.success,
        custom_id="verify_button"
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):

        role = discord.utils.get(interaction.guild.roles, name=VERIFY_ROLE_NAME)
        log_channel = interaction.guild.get_channel(VERIFY_LOG_CHANNEL_ID)

        if not role:
            await interaction.response.send_message("❌ Rol niet gevonden.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("ℹ️ Je bent al geverifieerd.", ephemeral=True)
            return

        await interaction.user.add_roles(role)
        await interaction.response.send_message("✅ Je bent nu geverifieerd!", ephemeral=True)

        now = datetime.now(timezone.utc)
        account_age = (now - interaction.user.created_at).days

        embed = discord.Embed(
            title="✅ Verificatie Voltooid",
            color=discord.Color.green(),
            timestamp=now
        )

        embed.add_field(
            name="👤 Gebruiker",
            value=f"{interaction.user}\n{interaction.user.id}",
            inline=False
        )

        embed.add_field(
            name="📅 Account Leeftijd",
            value=f"{account_age} dagen",
            inline=False
        )

        embed.add_field(
            name="🛡️ Status",
            value="Goedgekeurd",
            inline=False
        )

        embed.set_footer(text="Nova District • Security System")

        if log_channel:
            await log_channel.send(embed=embed)

# ===================== EVENTS =====================

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    bot.add_view(VerifyView())
    print(f"🟢 Bot online als {bot.user}")

    monitoring = bot.get_channel(MONITORING_CHANNEL_ID)
    if monitoring:
        await monitoring.send("🟢 Bot is succesvol opgestart")

@bot.event
async def on_member_join(member):
    channel = member.guild.get_channel(JOIN_LOG_CHANNEL_ID)
    if channel:
        await channel.send(f"🟢 **{member}** is gejoined")

@bot.event
async def on_member_remove(member):
    channel = member.guild.get_channel(LEAVE_LOG_CHANNEL_ID)
    if channel:
        await channel.send(f"🔴 **{member}** heeft de server verlaten")

@bot.event
async def on_guild_channel_delete(channel):
    log_channel = channel.guild.get_channel(ANTI_NUKE_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"⚠️ Kanaal verwijderd: **{channel.name}**")

# ===================== SLASH COMMANDS =====================

@bot.tree.command(
    name="verifysetup",
    description="Plaats het verificatiebericht"
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
async def verifysetup(interaction: discord.Interaction):

    embed = discord.Embed(
        title="📋 Server Regels & Verificatie",
        description=(
            "**Welkom bij Nova District! 🎮**\n\n"
            "📜 **Serverregels:**\n"
            "1️⃣ Respecteer alle leden en staff\n"
            "2️⃣ Geen spam of reclame\n"
            "3️⃣ Geen NSFW\n"
            "4️⃣ Geen discriminatie\n"
            "5️⃣ Luister naar staff\n"
            "6️⃣ Geen alts / ban evasion\n"
            "7️⃣ Juiste kanalen gebruiken\n\n"
            "🔐 **Klik op de knop hieronder om je rollen te ontvangen.**"
        ),
        color=discord.Color.green()
    )

    await interaction.channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message("✅ Verificatie geplaatst.", ephemeral=True)

# ===================== SERVER STATUS COMMAND =====================

@bot.tree.command(
    name="serverstatus",
    description="Plaats status van externe servers met links"
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
async def serverstatus(
    interaction: discord.Interaction,
    server1_name: str,
    server1_status: str,
    server1_link: str = None,
    server2_name: str = None,
    server2_status: str = None,
    server2_link: str = None,
    server3_name: str = None,
    server3_status: str = None,
    server3_link: str = None,
):
    def format_status(name, status, link):
        emoji_map = {
            "online": "🟢",
            "offline": "🔴",
            "onderhoud": "🟠"
        }
        emoji = emoji_map.get(status.lower(), "🟠")
        display = f"{emoji} {name}"
        if link:
            display = f"[{display}]({link})"
        return display

    embed = discord.Embed(
        title="🌐 Nova District • Server Status",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(name=format_status(server1_name, server1_status, server1_link), value="Status weergegeven", inline=False)
    if server2_name and server2_status:
        embed.add_field(name=format_status(server2_name, server2_status, server2_link), value="Status weergegeven", inline=False)
    if server3_name and server3_status:
        embed.add_field(name=format_status(server3_name, server3_status, server3_link), value="Status weergegeven", inline=False)

    embed.set_footer(text="Laatste update")

    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Server status geplaatst.", ephemeral=True)

# ===================== DISCORD LINKS COMMAND =====================

@bot.tree.command(
    name="discordlinks",
    description="Toon belangrijke Discord links"
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
async def discordlinks(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌐 Nova District • Belangrijke Discords",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(
        name="💬 Support Discord",
        value="[Join hier](https://discord.gg/66UMrE8psM)",
        inline=False
    )
    embed.add_field(
        name="🏛️ Overheid Discord",
        value="[Join hier](https://discord.gg/QBkYEfQDkV)",
        inline=False
    )
    embed.add_field(
        name="🕵️ Onderwereld Discord",
        value="[Join hier](https://discord.gg/nZHCH68QvG)",
        inline=False
    )

    embed.set_footer(text="Nova District • Discord Links")
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Discord links geplaatst!", ephemeral=True)

# ===================== START BOT =====================

bot.run(os.getenv("TOKEN"))
