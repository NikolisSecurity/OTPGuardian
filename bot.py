import discord
import random
import asyncio
import logging
import json
import time
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

with open("config.json", "r") as config_file:
    config = json.load(config_file)

TOKEN = config["bot_token"]
OTP_LENGTH = config["otp_length"]
OTP_EXPIRATION_SECONDS = config["otp_expiration_seconds"]
RATE_LIMIT_SECONDS = config["rate_limit_seconds"]
COMMAND_PREFIX = config["command_prefix"]
ROLE_ID = int(config["role_id"])
OTP_CHARACTERS = config.get("otp_characters", "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required for role management

class MyBot(commands.Bot):
    async def setup_hook(self):
        self.loop.create_task(otp_cleanup_task())

client = MyBot(command_prefix=COMMAND_PREFIX, intents=intents)

otp_store = {}

class OTPView(View):
    def __init__(self, timeout):
        super().__init__(timeout=timeout)
        self.message = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                logging.warning("OTP message already deleted")

def generate_otp(length=OTP_LENGTH):
    return ''.join(random.choices(OTP_CHARACTERS, k=length))

@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')

@client.command(name='otp')
@commands.cooldown(1, RATE_LIMIT_SECONDS, commands.BucketType.user)
async def otp_command(ctx: commands.Context):
    user_id = ctx.author.id
    otp_code = generate_otp()
    otp_store[user_id] = {'otp': otp_code, 'time': time.time()}

    logging.info(f"Generated OTP for {ctx.author} (ID: {user_id})")

    embed = discord.Embed(
        title="Your OTP",
        description="Click a button below to proceed:",
        color=discord.Color.green()
    )
    
    view = OTPView(timeout=OTP_EXPIRATION_SECONDS)
    
    send_otp_button = Button(label="Send OTP Code", style=discord.ButtonStyle.primary)
    enter_otp_button = Button(label="Enter OTP Code", style=discord.ButtonStyle.secondary)

    async def send_otp_callback(interaction: discord.Interaction):
        try:
            await interaction.user.send(
                embed=discord.Embed(
                    title="Your OTP",
                    description=f"**{otp_code}**\nExpires <t:{int(time.time())+OTP_EXPIRATION_SECONDS}:R>",
                    color=discord.Color.green()
                )
            )
            await interaction.response.send_message(
                f"{interaction.user.mention}, OTP has been sent to your DM.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"{interaction.user.mention}, I cannot send you a DM. Please enable DMs and try again.",
                ephemeral=True
            )

    async def enter_otp_callback(interaction: discord.Interaction):
        modal = OTPInputModal()
        await interaction.response.send_modal(modal)

    send_otp_button.callback = send_otp_callback
    enter_otp_button.callback = enter_otp_callback

    view.add_item(send_otp_button)
    view.add_item(enter_otp_button)
    
    msg = await ctx.send(embed=embed, view=view)
    view.message = msg

class OTPInputModal(Modal, title="Enter Your OTP"):
    otp_input = TextInput(label="OTP Code", placeholder="Enter your OTP here", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await verify_otp(interaction, self.otp_input.value.strip())

async def verify_otp(interaction: discord.Interaction, user_input: str):
    user_id = interaction.user.id
    embed = discord.Embed(color=discord.Color.green())
    
    if user_id not in otp_store:
        embed.description = "No OTP found. Please generate one using `!otp`."
        embed.color = discord.Color.red()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    stored_otp = otp_store[user_id]
    elapsed_time = time.time() - stored_otp['time']

    if elapsed_time > OTP_EXPIRATION_SECONDS:
        del otp_store[user_id]
        embed.description = "OTP has expired. Please generate a new one using `!otp`."
        embed.color = discord.Color.red()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if user_input.upper() != stored_otp['otp']:
        embed.description = "Invalid OTP. Please try again."
        embed.color = discord.Color.red()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    del otp_store[user_id]
    role = interaction.guild.get_role(ROLE_ID)
    
    if not role:
        embed.description = "Error: Configured role not found. Please contact an administrator."
        embed.color = discord.Color.red()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        await interaction.user.add_roles(role)
        embed.description = f"Success! You've been granted the {role.name} role."
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logging.info(f"Assigned role {role.name} to {interaction.user} (ID: {user_id})")
    except discord.Forbidden:
        embed.description = "Error: I don't have permission to assign roles."
        embed.color = discord.Color.red()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logging.error(f"Missing permissions to assign role to {interaction.user}")
    except Exception as e:
        embed.description = "An unexpected error occurred. Please contact an administrator."
        embed.color = discord.Color.red()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logging.error(f"Error assigning role: {e}", exc_info=True)

@client.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandOnCooldown):
        embed = discord.Embed(
            title="Slow Down!",
            description=f"Please wait {error.retry_after:.1f} seconds before generating a new OTP.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=10)
    else:
        logging.error(f"Command error: {error}", exc_info=True)
        embed = discord.Embed(
            title="Error",
            description="An unexpected error occurred. Please try again later.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=10)

async def otp_cleanup_task():
    await client.wait_until_ready()
    while not client.is_closed():
        current_time = time.time()
        expired_users = [uid for uid, data in otp_store.items() if current_time - data['time'] > OTP_EXPIRATION_SECONDS]
        
        for user_id in expired_users:
            del otp_store[user_id]
        
        if expired_users:
            logging.info(f"Cleaned up {len(expired_users)} expired OTPs")
        await asyncio.sleep(60)

async def main():
    async with client:
        await client.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
