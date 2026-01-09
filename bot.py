import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
import os

# ===================== CONFIG =====================

GUILD_ID = 1437438257972379870  # JOUW SERVER ID
VERIFY_ROLE_NAME = "Inwoner"

# 🔽 ECHTE CHANNEL ID'S
MONITORING_CHANNEL_ID = 1459132474276974735
VERIFY_LOG_CHANNEL_ID = 1459132382098620501
ANTI_NUKE_CHANNEL_ID = 1459132519290245196
JOIN_LOG_CHANNEL_ID = 1459132310719955172
LEAVE_LOG_CHANNEL_ID = 1459132249202233479

# Minimum account leeftijd (dagen)
MIN_ACCOUNT_AGE_DAYS = 7
ENABLE_MIN_AGE_CHECK = True

# ===================== INTENTS =====================

intents = discord.Intents.default()
intents.members = True  # NODIG VOOR JOIN/LEAVE EVENTS
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===================== VERIFY VIEW =====================

class VerifyView(discord.ui.View):
    def __init__(self, use_website=False, website_url=None):
        super().__init__(timeout=None)
        self.use_website = use_website
        self.website_url = website_url

        if self.use_website and self.website_url:
            self.add_item(discord.ui.Button(
                label="Klik hier om te verifiëren via website",
                url=self.website_url,
                style=discord.ButtonStyle.link
            ))

    @discord.ui.button(
        label="Klik Hier Om je Rollen te ontvangen",
        style=discord.ButtonStyle.success,
        custom_id="verify_button"
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=VERIFY_ROLE_NAME)
        log_channel = bot.get_channel(VERIFY_LOG_CHANNEL_ID)

        if not role:
            await interaction.response.send_message(
                "❌ Verificatie mislukt: rol niet gevonden.",
                ephemeral=True
            )
            return

        # Minimum account leeftijd check
        now = datetime.now(timezone.utc)
        account_age_days = (now - interaction.user.created_at).days
        if ENABLE_MIN_AGE_CHECK and account_age_days < MIN_ACCOUNT_AGE_DAYS:
            await interaction.response.send_message(
                f"⚠️ Je account is te jong ({account_age_days} dagen). Je kunt nog niet verifiëren.",
                ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                "ℹ️ Je bent al geverifieerd.",
                ephemeral=True
            )
            return

        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            "✅ **Verificatie voltooid!** Je hebt nu toegang.",
            ephemeral=True
        )

        # ------------------- SECURITY LOG -------------------
        embed = discord.Embed(
            title="✅ Verificatie Voltooid",
            color=discord.Color.green(),
            timestamp=now
        )
        embed.add_field(name="👤 Gebruiker", value=f"{interaction.user}\n{interaction.user.id}", inline=False)
        embed.add_field(name="📅 Account Leeftijd", value=f"{account_age_days} dagen", inline=False)
        embed.add_field(name="🏷️ Rol Toegekend", value=VERIFY_ROLE_NAME, inline=False)
        embed.add_field(name="🛡️ Status", value="Goedgekeurd", inline=False)
        embed.set_footer(text="Nova District • Security System")

        if log_channel:
            await log_channel.send(embed=embed)

# ===================== EVENTS =====================

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    bot.add_view(VerifyView())  # Persistent view voor verify knop
    print(f"🟢 Bot online als {bot.user}")

    monitoring = bot.get_channel(MONITORING_CHANNEL_ID)
    if monitoring:
        await monitoring.send("🟢 Nova District is succesvol opgestart")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(JOIN_LOG_CHANNEL_ID)
    if channel:
        await channel.send(f"🟢 **{member}** is gejoined")

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVE_LOG_CHANNEL_ID)
    if channel:
        await channel.send(f"🔴 **{member}** heeft de server verlaten")

@bot.event
async def on_guild_channel_delete(channel):
    log_channel = bot.get_channel(ANTI_NUKE_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"⚠️ Kanaal verwijderd: **{channel.name}**")

# ===================== SLASH COMMAND =====================

@bot.tree.command(
    name="verifysetup",
    description="Plaats het verificatiebericht"
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def verifysetup(interaction: discord.Interaction):
    website_verify_url = "https://JOUW-WEBSITE-URL"  # vul dit in of laat None
    view = VerifyView(use_website=True, website_url=website_verify_url)

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
            "🔐 **Klik op de knop hieronder om je rollen te ontvangen.**\n"
            "Door te verifiëren ga je akkoord met onze regels."
        ),
        color=discord.Color.green()
    )

    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Verificatiebericht geplaatst!", ephemeral=True)

# ===================== START BOT =====================

bot.run(os.getenv("TOKEN"))
