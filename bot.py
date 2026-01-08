import discord
from discord.ext import commands
from discord import app_commands
import os

VERIFY_ROLE_NAME = "Inwoner"

MONITORING_CHANNEL = "discord-monitoring"
VERIFY_LOG_CHANNEL = "discord-verify-logs"
ANTI_NUKE_CHANNEL = "discord-anti-nuke"
JOIN_LOG_CHANNEL = "discord-join-logs"
LEAVE_LOG_CHANNEL = "discord-leave-logs"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot online als {bot.user}")

    monitoring = discord.utils.get(bot.get_all_channels(), name=MONITORING_CHANNEL)
    if monitoring:
        await monitoring.send("🟢 Bot is succesvol opgestart")

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Klik Hier Om je Rollen te ontvangen",
        style=discord.ButtonStyle.success
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=VERIFY_ROLE_NAME)
        logs = discord.utils.get(interaction.guild.text_channels, name=VERIFY_LOG_CHANNEL)

        if role in interaction.user.roles:
            await interaction.response.send_message("Je hebt deze rol al.", ephemeral=True)
            return

        await interaction.user.add_roles(role)
        await interaction.response.send_message("🎉 Je bent nu inwoner!", ephemeral=True)

        if logs:
            await logs.send(f"✅ {interaction.user} kreeg rol Inwoner")

@bot.tree.command(name="verifysetup")
@app_commands.checks.has_permissions(administrator=True)
async def verifysetup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 Server Regels & Verificatie",
        description=(
            "**Welkom bij Nova District! 🎮**\n\n"
            "📜 Regels:\n"
            "1️⃣ Respecteer iedereen\n"
            "2️⃣ Geen spam\n"
            "3️⃣ Geen NSFW\n"
            "4️⃣ Geen discriminatie\n"
            "5️⃣ Luister naar staff\n"
            "6️⃣ Geen alts\n"
            "7️⃣ Gebruik juiste kanalen\n\n"
            "**Klik op de knop hieronder om je rollen te ontvangen.**"
        ),
        color=discord.Color.green()
    )

    await interaction.channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message("Verificatie geplaatst", ephemeral=True)

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name=JOIN_LOG_CHANNEL)
    if channel:
        await channel.send(f"🟢 {member} is gejoined")

@bot.event
async def on_member_remove(member):
    channel = discord.utils.get(member.guild.text_channels, name=LEAVE_LOG_CHANNEL)
    if channel:
        await channel.send(f"🔴 {member} heeft verlaten")

@bot.event
async def on_guild_channel_delete(channel):
    logs = discord.utils.get(channel.guild.text_channels, name=ANTI_NUKE_CHANNEL)
    if logs:
        await logs.send(f"⚠️ Kanaal verwijderd: {channel.name}")

bot.run(os.getenv("TOKEN"))
