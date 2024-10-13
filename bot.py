import discord
import random
import asyncio
import logging
import json
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load configuration from config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)

# Bot configuration
TOKEN = config["bot_token"]
OTP_LENGTH = config["otp_length"]
OTP_EXPIRATION_SECONDS = config["otp_expiration_seconds"]
RATE_LIMIT_SECONDS = config["rate_limit_seconds"]
COMMAND_PREFIX = config["command_prefix"]
ROLE_ID = int(config["role_id"])

# Discord Intents
intents = discord.Intents.default()
intents.message_content = True

# Create the bot instance
client = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# In-memory storage for OTPs and last OTP generation time
otp_store = {}
last_otp_time = {}

# Function to generate OTP
def generate_otp(length=OTP_LENGTH):
    return ''.join(random.choices('0123456789', k=length))

@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')

# Command to generate OTP
@client.tree.command(name="otp", description="Generate a One-Time Password (OTP)")
async def otp(interaction: discord.Interaction):
    user_id = interaction.user.id
    current_time = asyncio.get_event_loop().time()

    # Rate limiting
    if user_id in last_otp_time:
        time_since_last = current_time - last_otp_time[user_id]
        if time_since_last < RATE_LIMIT_SECONDS:
            await interaction.response.send_message(f"{interaction.user.mention}, you are generating OTPs too fast. Please wait.", ephemeral=True)
            return

    otp_code = generate_otp()
    otp_store[user_id] = {'otp': otp_code, 'time': current_time}
    last_otp_time[user_id] = current_time

    embed = discord.Embed(title="Your OTP", description="Click a button below to proceed:", color=discord.Color.green())
    view = View()

    # Buttons for sending OTP and entering OTP
    send_otp_button = Button(label="Send OTP Code", style=discord.ButtonStyle.primary)
    enter_otp_button = Button(label="Enter OTP Code", style=discord.ButtonStyle.secondary)

    async def send_otp_callback(interaction: discord.Interaction):
        try:
            await interaction.user.send(embed=discord.Embed(title="Your OTP", description=f"**{otp_code}**", color=discord.Color.green()))
            await interaction.response.send_message(f"{interaction.user.mention}, OTP has been sent to your DM.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"{interaction.user.mention}, I cannot send you a DM. Please enable DMs and try again.", ephemeral=True)

    async def enter_otp_callback(interaction: discord.Interaction):
        modal = OTPInputModal(otp_code)
        await interaction.response.send_modal(modal)

    # Assign the callback functions to buttons
    send_otp_button.callback = send_otp_callback
    enter_otp_button.callback = enter_otp_callback

    # Add buttons to the view and send the message
    view.add_item(send_otp_button)
    view.add_item(enter_otp_button)
    await interaction.response.send_message(embed=embed, view=view)

# Modal for OTP input
class OTPInputModal(Modal):
    def __init__(self, otp):
        super().__init__(title="Enter Your OTP")
        self.otp = otp
        self.add_item(TextInput(label="OTP Code", placeholder="Enter your OTP here", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        user_otp_input = self.children[0].value.strip()  # Strip any whitespace
        await verify(interaction, user_otp_input)

# Function to verify the entered OTP
async def verify(interaction: discord.Interaction, otp_input: str):
    user_id = interaction.user.id
    if user_id in otp_store:
        stored_otp_info = otp_store[user_id]
        # Check if the OTP has expired
        if asyncio.get_event_loop().time() - stored_otp_info['time'] > OTP_EXPIRATION_SECONDS:
            await interaction.response.send_message(f"{interaction.user.mention}, your OTP has expired. Please generate a new one using `/otp`.", ephemeral=True)
            del otp_store[user_id]  # Remove expired OTP
        elif stored_otp_info['otp'] == otp_input:
            role = interaction.guild.get_role(ROLE_ID)
            if role:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"{interaction.user.mention}, OTP verified successfully! You have been given the role: {role.name}", ephemeral=True)
            else:
                await interaction.response.send_message(f"{interaction.user.mention}, OTP verified successfully! However, I could not find the role to assign.", ephemeral=True)
            del otp_store[user_id]  # Remove OTP after verification
        else:
            await interaction.response.send_message(f"{interaction.user.mention}, invalid OTP. Try again.", ephemeral=True)
    else:
        await interaction.response.send_message(f"{interaction.user.mention}, no OTP found. Please generate one using `/otp`.", ephemeral=True)

# Cleanup expired OTPs periodically
async def otp_cleanup():
    while True:
        await asyncio.sleep(60)  # Check every minute
        current_time = asyncio.get_event_loop().time()
        for user_id in list(otp_store.keys()):
            if current_time - otp_store[user_id]['time'] > OTP_EXPIRATION_SECONDS:
                del otp_store[user_id]
                logging.info(f"Deleted expired OTP for user ID {user_id}")

# Start the bot
async def main():
    asyncio.create_task(otp_cleanup())
    await client.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
