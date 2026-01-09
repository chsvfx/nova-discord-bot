import discord
from discord.ext import commands
from discord import app_commands
import os

# -------------------- CONFIG --------------------
VERIFY_ROLE_NAME = "Inwoner"

MONITORING_CHANNEL = "discord-monitoring"
VERIFY_LOG_CHANNEL = "discord-verify-logs"
ANTI_NUKE_CHANNEL = "discord-anti-nuke"
JOIN_LOG_CHANNEL = "discord-join-logs"
LEAVE_LOG_CHANNEL = "discord-leave-logs"

GUILD_ID = 1437438257972379870  # <-- JOUW SERVER ID

# -------------------- INTENTS --------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------- VERIFY VIEW (PERSISTENT) --------------------
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
        logs = discord.utils.get(interaction.guild.text_channels, name=VERIFY_LOG_CHANNEL)

        if not role:
            await interaction.response.send_message(
                "❌ Rol **Inwoner** bestaat niet. Contacteer staff.",
                ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                "ℹ️ Je hebt deze rol al.",
                ephemeral=True
            )
            return

        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            "🎉 Je bent nu **Inwoner**!",
            ephemeral=True
        )

        if logs:
            await logs.send(f"✅ {interaction.user} kreeg de rol **Inwoner**")

# -------------------- EVENTS --------------------
@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    bot.add_view(VerifyView())

    print(f"🟢 Bot online als {bot.user}")

    monitoring = discord.utils.get(bot.get_all_channels(), name=MONITORING_CHANNEL)
    if monitoring:
        await monitoring.send("🟢 Bot is succesvol opgestart")

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name=JOIN_LOG_CHANNEL)
    if channel:
        await channel.send(f"🟢 **{member}** is gejoined")

@bot.event
async def on_member_remove(member):
    channel = discord.utils.get(member.guild.text_channels, name=LEAVE_LOG_CHANNEL)
    if channel:
        await channel.send(f"🔴 **{member}** heeft de server verlaten")

@bot.event
async def on_guild_channel_delete(channel):
    logs = discord.utils.get(channel.guild.text_channels, name=ANTI_NUKE_CHANNEL)
    if logs:
        await logs.send(f"⚠️ Kanaal verwijderd: **{channel.name}**")

# -------------------- SLASH COMMAND --------------------
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

    await interaction.channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message(
        "✅ Verificatiebericht geplaatst!",
        ephemeral=True
    )

# -------------------- START BOT --------------------
bot.run(os.getenv("TOKEN"))
