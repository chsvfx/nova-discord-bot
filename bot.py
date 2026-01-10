import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
import os

# ===================== CONFIG =====================

GUILD_ID = 1437438257972379870  # JOUW SERVER ID

VERIFY_ROLE_NAME = "Inwoner"
SNEAKPEAKS_ROLE_NAME = "Sneakpeaks"

# 🔽 ECHTE CHANNEL ID'S
MONITORING_CHANNEL_ID = 1459132474276974735
VERIFY_LOG_CHANNEL_ID = 1459132382098620501
ANTI_NUKE_CHANNEL_ID = 1459132519290245196
JOIN_LOG_CHANNEL_ID = 1459132310719955172
LEAVE_LOG_CHANNEL_ID = 1459132249202233479

# Minimum account leeftijd
MIN_ACCOUNT_AGE_DAYS = 7
ENABLE_MIN_AGE_CHECK = True

# ===================== INTENTS =====================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===================== HELPER =====================

def get_log_channel(channel_id: int):
    channel = bot.get_channel(channel_id)
    if not channel:
        print(f"[WARN] Kanaal {channel_id} niet gevonden")
    return channel

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
        log_channel = get_log_channel(VERIFY_LOG_CHANNEL_ID)

        if not role:
            await interaction.response.send_message("❌ Rol niet gevonden.", ephemeral=True)
            return

        now = datetime.now(timezone.utc)
        account_age_days = (now - interaction.user.created_at).days

        if ENABLE_MIN_AGE_CHECK and account_age_days < MIN_ACCOUNT_AGE_DAYS:
            await interaction.response.send_message(
                f"⚠️ Je account is te jong ({account_age_days} dagen).",
                ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("ℹ️ Je bent al geverifieerd.", ephemeral=True)
            return

        await interaction.user.add_roles(role)
        await interaction.response.send_message("✅ Verificatie voltooid!", ephemeral=True)

        embed = discord.Embed(
            title="✅ Verificatie Voltooid",
            color=discord.Color.green(),
            timestamp=now
        )
        embed.add_field(name="👤 Gebruiker", value=f"{interaction.user}\n{interaction.user.id}", inline=False)
        embed.add_field(name="📅 Account Leeftijd", value=f"{account_age_days} dagen", inline=False)
        embed.add_field(name="🏷️ Rol", value=VERIFY_ROLE_NAME, inline=False)
        embed.set_footer(text="Nova District • Security System")

        if log_channel:
            await log_channel.send(embed=embed)

# ===================== SNEAKPEAKS VIEW =====================

class SneakpeaksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="👀 Ontvang Sneakpeaks Rol",
        style=discord.ButtonStyle.primary,
        custom_id="sneakpeaks_button"
    )
    async def sneakpeaks(self, interaction: discord.Interaction, button: discord.ui.Button):

        role = discord.utils.get(interaction.guild.roles, name=SNEAKPEAKS_ROLE_NAME)

        if not role:
            await interaction.response.send_message("❌ Sneakpeaks rol niet gevonden.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("ℹ️ Je hebt deze rol al.", ephemeral=True)
            return

        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            "✅ Je hebt nu toegang tot **Sneakpeaks**!",
            ephemeral=True
        )

# ===================== EVENTS =====================

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))

    bot.add_view(VerifyView())
    bot.add_view(SneakpeaksView())

    print(f"🟢 Bot online als {bot.user}")

    monitoring = get_log_channel(MONITORING_CHANNEL_ID)
    if monitoring:
        await monitoring.send("🟢 Nova District is succesvol opgestart")

@bot.event
async def on_member_join(member):
    channel = get_log_channel(JOIN_LOG_CHANNEL_ID)
    if channel:
        await channel.send(f"🟢 **{member}** is gejoined")

@bot.event
async def on_member_remove(member):
    channel = get_log_channel(LEAVE_LOG_CHANNEL_ID)
    if channel:
        await channel.send(f"🔴 **{member}** heeft de server verlaten")

@bot.event
async def on_guild_channel_delete(channel):
    log_channel = get_log_channel(ANTI_NUKE_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"⚠️ Kanaal verwijderd: **{channel.name}**")

# ===================== SLASH COMMANDS =====================

@bot.tree.command(name="verifysetup", description="Plaats het verificatiebericht")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def verifysetup(interaction: discord.Interaction):

    embed = discord.Embed(
        title="📋 Server Regels & Verificatie",
        description=(
            "**Welkom bij Nova District! 🎮**\n\n"
            "📜 **Serverregels:**\n"
            "1️⃣ Respecteer alle leden en staff\n"
            "2️⃣ Geen spam, reclame of zelfpromotie\n"
            "3️⃣ Geen NSFW content\n"
            "4️⃣ Geen discriminatie of haatdragende taal\n"
            "5️⃣ Luister naar staff\n"
            "6️⃣ Geen alts of ban evasion\n"
            "7️⃣ Houd discussies in de juiste kanalen\n\n"
            "🔐 Klik op de knop hieronder om je rollen te ontvangen."
        ),
        color=discord.Color.green()
    )

    await interaction.channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message("✅ Verificatiebericht geplaatst!", ephemeral=True)

# ===================== SNEAKPEAKS COMMAND =====================

@bot.tree.command(name="sneakpeaks", description="Ontvang toegang tot Sneakpeaks")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def sneakpeaks(interaction: discord.Interaction):

    embed = discord.Embed(
        title="👀 Sneakpeaks",
        description=(
            "Klik op de knop hieronder om toegang te krijgen tot "
            "sneakpeaks van aankomende content in ⁠┃👀ㆍsneakpeaks"
        ),
        color=discord.Color.purple()
    )

    await interaction.channel.send(embed=embed, view=SneakpeaksView())
    await interaction.response.send_message(
        "✅ Sneakpeaks bericht geplaatst!",
        ephemeral=True
    )

# ===================== DISCORD LINKS =====================

@bot.tree.command(name="discordlinks", description="Externe Discord servers")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def discordlinks(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🌐 Externe Discord Servers",
        description=(
            "**Support Discord**\n"
            "https://discord.gg/66UMrE8psM\n\n"
            "**Overheid Discord**\n"
            "https://discord.gg/QBkYEfQDkV\n\n"
            "**Onderwereld Discord**\n"
            "https://discord.gg/nZHCH68QvG"
        ),
        color=discord.Color.blue()
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ===================== APV COMMAND =====================

@bot.tree.command(name="apv", description="Bekijk de APV van Nova District")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def apv(interaction: discord.Interaction):

    embed = discord.Embed(
        title="📜 APV Nova District",
        description=(
            "**De APV van Nova District is nu beschikbaar!**\n\n"
            "Alle regels, voorschriften en richtlijnen voor Nova District.\n\n"
            "🔗 https://www.novadistrict.nl/apv"
        ),
        color=discord.Color.blue()
    )

    await interaction.response.send_message(embed=embed)

# ===================== START =====================

bot.run(os.getenv("TOKEN"))
