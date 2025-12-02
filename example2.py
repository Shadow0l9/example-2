import os
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
import aiohttp
from datetime import datetime
from typing import Optional, Dict, Any

#Configuration 

DISCORD_BOT_TOKEN = "BOT_TOKEN"

# Bot setup
# set up the default intents
intents = discord.Intents.default()
# we dont need message content for slash commands so turn it off
intents.message_content = False

# custom bot class to handle setup stuff
class RobloxBot(commands.Bot):
    def __init__(self):
        # init the bot with a prefix
        super().__init__(command_prefix="!", intents=intents)

    async def on_ready(self):
        """confirms the bot is logged in and ready."""
        print(f'Logged in as {self.user}')
        #sync the application commands
        try:
            # sync the slash commands to discord
            synced = await self.tree.sync()
            print(f"synced {len(synced)} command/s")
        except Exception as e:
            print(f"failed to sync commands: {e}")

bot = RobloxBot()

#Utility views

class LinkButton(View):
    """A simple view to display a single link button"""
    def __init__(self, url: str):
        super().__init__(timeout=180)
        # this view just holds one button that links to a URL
        self.add_item(discord.ui.Button(label="🔗 View Item", style=discord.ButtonStyle.link, url=url))

class ProfileButton(View):
    """A simple view to display a single profile link button"""
    def __init__(self, url: str):
        super().__init__(timeout=180)
        # same as LinkButton, but for a profile link
        self.add_item(discord.ui.Button(label="Go to Profile", url=url, style=discord.ButtonStyle.link))

# Slash commands
#/check gamepass or asset command
# what command do.? -> so uhh lets say now you cant go in roblox and you want to make sure the user has bought the shirt, gamepass, ect you can use the command
# with the username and the gamepass/shirt id and it will use api to check and sends result.
@bot.tree.command(name="check-asset", description="check if a user owns a asset or gamepass")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    username="the Roblox username",
    asset_id="the ID of the asset or gamepass"
)
async def check_asset(interaction: discord.Interaction, username: str, asset_id: int):
    """handles the /check-asset slash command."""
    # defer the response so we have time to talk to the roblox API
    await interaction.response.defer()
    
    #send loading message
    # send a temporary message so the user knows we are working
    loading_msg = await interaction.followup.send("Loading...⏳", ephemeral=False)

    try:
        # start a session for making web requests
        async with aiohttp.ClientSession() as session:
            #get user ID from Username
            url = "https://users.roblox.com/v1/usernames/users"
            headers = {'Content-Type': 'application/json'}
            body = {"usernames": [username], "excludeBannedUsers": True}

            # first API call: get the user ID from their username
            async with session.post(url, headers=headers, json=body) as response:
                data = await response.json()

                # check if the username was valid
                if not data.get('data'):
                    embed = discord.Embed(
                        title="❌ Invalid Roblox User",
                        description="⚠️ Please make sure to input your username correctly.",
                        color=discord.Color.red()
                    )
                    # edit the loading message to show the error
                    await loading_msg.edit(content=None, embed=embed)
                    return

                user_info = data['data'][0]
                user_id = user_info['id']
                display_name = user_info.get('displayName', username)

                link = None
                status = None

                #checking asset ownership
                # second API call: check if they own the asset (shirt, item, etc.)
                asset_url = f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{asset_id}"
                async with session.get(asset_url) as asset_response:
                    asset_data = await asset_response.json()

                    if asset_data.get('data'):
                        # they own the asset
                        link = f"https://www.roblox.com/catalog/{asset_id}"
                        status = "✅ Owns the asset"
                    else:
                        #checking gamepass ownership
                        # third API call: if not an asset, check if its a gamepass
                        gamepass_url = f"https://inventory.roblox.com/v1/users/{user_id}/items/GamePass/{asset_id}"
                        async with session.get(gamepass_url) as gamepass_response:
                            gamepass_data = await gamepass_response.json()
                            
                            if gamepass_data.get('data'):
                                # they own the gamepass
                                link = f"https://www.roblox.com/game-pass/{asset_id}"
                                status = "✅ Owns the gamepass"
                            else:
                                # they dont own it or the ID is wrong
                                status = "❌ Does not Own / The ID does not exist\n-# Please make sure to input a valid ID"

                # the final embed message
                embed = discord.Embed(title="🔍 Ownership Verification", color=discord.Color.blue())
                embed.description = (
                    f"**Display :** {display_name}\n"
                    f"**Username :** {username}\n"
                    f"**Status :** {status}"
                )
                
                #button link
                if link:
                    # if we have a link send the embed with the button
                    await loading_msg.edit(content=None, embed=embed, view=LinkButton(link))
                else:
                    # no link just send the embed
                    await loading_msg.edit(content=None, embed=embed)

    except Exception as e:
        print(f"ERROR in /check-asset command: {e}")
        # if something is wrong
        embed = discord.Embed(
            title="❌ error occurred",
            description=f"⚠️ an error occurred: `{str(e)}`",
            color=discord.Color.red()
        )
        # show the error to the user
        await loading_msg.edit(content=None, embed=embed)


#/get info of roblox user command
@bot.tree.command(name="getinfo-roblox", description="check roblox user information")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(username="The roblox username to look up")
async def roblox_info(interaction: discord.Interaction, username: str):
    """handles the /getinfo-roblox slash command."""
    # defer the response
    await interaction.response.defer()
    # send a temporary message
    loading_msg = await interaction.followup.send("Looking for user...⏳", ephemeral=False)
    
    try:
        # start a web session
        async with aiohttp.ClientSession() as session:
            #get user ID from username
            # API call 1: get user ID
            async with session.post(
                "https://users.roblox.com/v1/usernames/users",
                json={"usernames": [username], "excludeBannedUsers": False}
            ) as resp:
                data = await resp.json()
                # if no data the user doesn't exist
                if not data.get("data"):
                    return await loading_msg.edit(content="❌ nah, couldn`t find that user. check the spelling.")
                user = data["data"][0]

            user_id = user["id"]

            #get full user info by ID
            # API call 2: get full profile data
            async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as user_resp:
                user_data = await user_resp.json()

            # get avatar image
            # API call 3: get the user's avatar headshot URL
            async with session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false") as thumb_resp:
                thumb_data = await thumb_resp.json()
                avatar_url = thumb_data['data'][0]['imageUrl']

            # pull out the info we need
            display_name = user_data.get("displayName", "Unknown")
            description = user_data.get("description", "No description set.")
            verified = "✅ Verified" if user_data.get("hasVerifiedBadge") else "❌ Not Verified"
            roblox_profile = f"https://www.roblox.com/users/{user_id}/profile"

            created_at = user_data.get("created")
            creation_date_text = "Unknown"
            if created_at:
                # convert roblox time string to a discord timestamp
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                # format it nicely with a relative timestamp
                creation_date_text = f"<t:{int(dt.timestamp())}:F> (<t:{int(dt.timestamp())}:R>)"
            
            # start building the embed
            embed = discord.Embed(
                title=f"👤 Roblox Profile: {display_name}",
                description=f"**Username:** `{user_data['name']}`\n**User ID:** `{user_id}`\n**Verified Status:** {verified}",
                color=discord.Color.from_rgb(237, 28, 36)
            )
            
            embed.add_field(name="Account Created", value=creation_date_text, inline=False)
            
            # only add the bio field if there is one
            if description and description != "No description set.":
                # make sure the bio isn't too long for an embed field
                if len(description) > 1024:
                    description = description[:1021] + "..."
                embed.add_field(name="Bio", value=f"```{description}```", inline=False)
            
            # set the avatar as the thumbnail
            embed.set_thumbnail(url=avatar_url)
            embed.set_footer(text="Roblox Info Lookup")

            #add the profile link button
            await loading_msg.edit(content=None, embed=embed, view=ProfileButton(roblox_profile))

    except Exception as e:
        print(f"ERROR in /getinfo-roblox command: {e}")
        # if something is wrong
        error_embed = discord.Embed(
            title="❌ oops, something broke",
            description=f"⚠️ couldn't get the info. error: `{str(e)}`",
            color=discord.Color.red()
        )
        # show the error to the user
        await loading_msg.edit(content=None, embed=error_embed)

#run the bot
if __name__ == "__main__":
    # check if the token is still the placeholder
    if DISCORD_BOT_TOKEN == "BOT_TOKEN":
        print("please replace the DISCORD_BOT_TOKEN with your bot token")
    
    else:
        #run the bot
        bot.run(DISCORD_BOT_TOKEN)
