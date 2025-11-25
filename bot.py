import asyncio
import json
import os
import re
import traceback
from datetime import datetime
from datetime import time as d_time
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

import DB
import hellcup as hc
import modals as md

user_in_match = []

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Créer une instance du bot avec le préfixe '!'
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

db = DB.DB("hellbot_gg")

# Variable globale pour stocker les invitations
invites_before = {}
tzParis = ZoneInfo("Europe/Paris")


async def matchmaking_logs(content):
    logs_channel_id = db.get("matchmaking_logs_channel_id")
    if not logs_channel_id:
        return

    channel = bot.get_channel(logs_channel_id)
    if not channel:
        return

    await channel.send(f"[<t:{int(datetime.now().timestamp())}:T>] " + str(content))


@tasks.loop(time=d_time(19, 00, 00, tzinfo=tzParis))
async def update_flags():
    try:
        inscriptions = json.load(open("inscriptions.json", "r"))
        for player in inscriptions["players"].values():
            new_flag_str, _ = await hc.get_geoguessr_flag_and_pro(player["geoguessrId"])
            if new_flag_str != player["flag"]:
                old_flag = hc.flag_to_emoji(player["flag"])
                new_flag = hc.flag_to_emoji(new_flag_str)
                await log_message(
                    f"Flag mis à jour de {player['surname']} de {player['flag']} à {new_flag}"
                )
                player["flag"] = new_flag_str
                member = bot.get_guild(db.get("guess_and_give_server_id")).get_member(
                    int(player["discordId"])
                )
                await member.edit(nick=member.display_name.replace(old_flag, new_flag))
                for teams in inscriptions["teams"].values():
                    if teams["member1"]["discordId"] == player["discordId"]:
                        teams["member1"]["flag"] = new_flag_str
                    elif teams["member2"]["discordId"] == player["discordId"]:
                        teams["member2"]["flag"] = new_flag_str
        json.dump(inscriptions, open("inscriptions.json", "w"))
    except Exception as e:
        await log_error(e)


@bot.event
async def on_ready():
    print(f"{bot.user} est connecté à Discord!")
    update_flags.start()
    # Charger les invitations existantes pour chaque serveur
    for guild in bot.guilds:
        invites_before[guild.id] = await guild.invites()
        invites_before[guild.id] = {inv.code: inv for inv in invites_before[guild.id]}


async def log_error(error: Exception, ctx=None):
    """Envoie les erreurs dans le canal des super logs"""
    logs_channel_id = db.get("logs_channel_id")
    if not logs_channel_id:
        return  # Si pas de canal configuré, on ne fait rien

    channel = bot.get_channel(logs_channel_id)
    if not channel:
        return

    # Créer un embed pour l'erreur
    embed = discord.Embed(
        title="⚠️ Erreur Détectée",
        description="Une erreur s'est produite lors de l'exécution du bot",
        color=discord.Color.red(),
        timestamp=datetime.now(),
    )

    # Ajouter les détails de l'erreur
    error_details = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    if len(error_details) > 1024:  # Discord limite la taille des fields
        error_details = error_details[-1021:] + "..."

    embed.add_field(name="Type d'erreur", value=type(error).__name__, inline=False)
    # embed.add_field(name="Message d'erreur", value=str(error), inline=False)
    error_details = (
        error_details[-1000:] if len(error_details) > 1000 else error_details
    )
    embed.add_field(
        name="Traceback", value=f"```python\n{error_details}```", inline=False
    )

    # Ajouter le contexte si disponible
    if ctx:
        embed.add_field(
            name="Contexte",
            value=f"Commande: {ctx.command}\nAuteur: {ctx.author}\nCanal: {ctx.channel}\nMessage: {ctx.message.content}",
            inline=False,
        )

    await channel.send(embed=embed)


async def log_message(message: str):
    """Envoie les erreurs dans le canal des super logs"""
    logs_channel_id = db.get("logs_channel_id")
    if not logs_channel_id:
        return  # Si pas de canal configuré, on ne fait rien

    channel = bot.get_channel(logs_channel_id)
    if not channel:
        return

    # Créer un embed pour l'erreur
    embed = discord.Embed(
        title="⚠️ Log info",
        description="Info de log",
        color=discord.Color.yellow(),
        timestamp=datetime.now(),
    )

    embed.add_field(name="Message", value=message, inline=False)

    await channel.send(embed=embed)


@bot.event
async def on_error(event, *args, **kwargs):
    """Capture les erreurs d'événements"""
    error = traceback.format_exc()
    await log_error(Exception(f"Erreur dans l'événement {event}:\n{error}"))


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Capture les erreurs de commandes"""
    await log_error(error, ctx)


@bot.event
async def on_invite_create(invite: discord.Invite):
    logs_channel_id = db.get("logs_channel_id")
    if not logs_channel_id:
        return

    logs_channel = bot.get_channel(logs_channel_id)
    if logs_channel:
        embed = discord.Embed(
            title="Nouvelle Invitation Créée",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )
        embed.add_field(name="Créée par", value=invite.inviter.mention, inline=True)
        embed.add_field(name="Code", value=invite.code, inline=True)
        embed.add_field(name="Channel", value=invite.channel.mention, inline=True)
        if invite.max_uses:
            embed.add_field(name="Utilisations max", value=invite.max_uses, inline=True)
        if invite.expires_at:
            embed.add_field(
                name="Expire le",
                value=invite.expires_at.strftime("%d/%m/%Y à %H:%M"),
                inline=True,
            )
        embed.set_footer(text=f"ID: {invite.inviter.id}")
        await logs_channel.send(embed=embed)
    invites_before[invite.guild.id] = await invite.guild.invites()
    invites_before[invite.guild.id] = {
        inv.code: inv for inv in invites_before[invite.guild.id]
    }


@bot.event
async def on_message_delete(message: discord.Message):
    logs_channel_id = db.get("logs_channel_id")
    if not logs_channel_id:
        return

    # Ignorer les messages des bots
    if message.author.bot:
        return

    logs_channel = bot.get_channel(logs_channel_id)
    if logs_channel:
        embed = discord.Embed(
            title="Message Supprimé",
            description=f"Un message a été supprimé dans {message.channel.mention}",
            color=discord.Color.red(),
            timestamp=datetime.now(),
        )
        embed.add_field(name="Auteur", value=message.author.mention, inline=False)
        embed.add_field(
            name="Contenu",
            value=message.content or "Contenu non disponible",
            inline=False,
        )
        embed.set_footer(text=f"ID: {message.author.id}")
        await logs_channel.send(embed=embed)


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    logs_channel_id = db.get("logs_channel_id")
    if not logs_channel_id:
        return

    # Ignorer les messages des bots
    if before.author.bot:
        return

    # Ignorer si le contenu n'a pas changé (par exemple, uniquement un embed ajouté)
    if before.content == after.content:
        return

    logs_channel = bot.get_channel(logs_channel_id)
    if logs_channel:
        embed = discord.Embed(
            title="Message Modifié",
            description=f"Un message a été modifié dans {before.channel.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )
        embed.add_field(name="Auteur", value=before.author.mention, inline=False)
        embed.add_field(
            name="Avant", value=before.content or "Contenu non disponible", inline=False
        )
        embed.add_field(
            name="Après", value=after.content or "Contenu non disponible", inline=False
        )
        embed.add_field(
            name="Lien", value=f"[Aller au message]({after.jump_url})", inline=False
        )
        embed.set_footer(text=f"ID: {before.author.id}")
        await logs_channel.send(embed=embed)


@bot.event
async def on_member_join(member: discord.Member):
    logs_channel_id = db.get("logs_channel_id")
    if not logs_channel_id:
        return

    try:
        await hc.refresh_invites_message(member.guild, db)
    except:
        pass

    await bot.change_presence(
        activity=discord.Activity(
            name=f"{len(member.guild.members)} gens (trop) cools !",
            type=discord.ActivityType.watching,
        )
    )

    logs_channel = bot.get_channel(logs_channel_id)
    if logs_channel:
        # Récupérer les invitations après l'arrivée du membre
        invites_after = await member.guild.invites()
        invites_after = {inv.code: inv for inv in invites_after}

        # Trouver quelle invitation a été utilisée
        used_invite = None
        for invite_after_code, invite_after in invites_after.items():
            if (
                invite_after_code in invites_before[member.guild.id]
                and invite_after.uses
                > invites_before[member.guild.id][invite_after_code].uses
            ):
                used_invite = invite_after
                break

        # Mettre à jour la liste des invitations
        invites_before[member.guild.id] = await member.guild.invites()
        invites_before[member.guild.id] = {
            inv.code: inv for inv in invites_before[member.guild.id]
        }

        # Créer l'embed de base pour le nouveau membre
        embed = discord.Embed(
            title="Nouveau Membre",
            description=f"{member.mention} a rejoint le serveur!",
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(
            url=member.avatar.url if member.avatar else member.default_avatar.url
        )
        embed.add_field(
            name="Compte créé le",
            value=member.created_at.strftime("%d/%m/%Y à %H:%M"),
            inline=False,
        )

        # Ajouter les informations sur l'invitation si trouvée
        if used_invite:
            embed.add_field(
                name="Invité par", value=used_invite.inviter.mention, inline=True
            )
            embed.add_field(
                name="Code d'invitation", value=used_invite.code, inline=True
            )
            embed.add_field(
                name="Utilisations",
                value=f"{used_invite.uses}/{used_invite.max_uses if used_invite.max_uses else '∞'}",
                inline=True,
            )
        else:
            embed.add_field(name="Invitation", value="Non trouvée", inline=True)

        embed.set_footer(text=f"ID: {member.id}")
        await logs_channel.send(embed=embed)


@bot.event
async def on_member_remove(member: discord.Member):
    logs_channel_id = db.get("logs_channel_id")
    if not logs_channel_id:
        return

    logs_channel = bot.get_channel(logs_channel_id)
    if logs_channel:
        embed = discord.Embed(
            title="Membre Parti",
            description=f"{member.display_name} a quitté le serveur",
            color=discord.Color.red(),
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(
            url=member.avatar.url if member.avatar else member.default_avatar.url
        )
        embed.add_field(
            name="Avait rejoint le",
            value=member.joined_at.strftime("%d/%m/%Y à %H:%M"),
            inline=False,
        )
        embed.set_footer(text=f"ID: {member.id}")
        await logs_channel.send(embed=embed)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # Vérifier si le nom a changé
    if before.display_name != after.display_name:
        tempName = None

        try:
            flag = hc.get_flag(after.id)

            if not after.display_name.startswith(flag + " "):
                tempName = after.display_name
                try:
                    await after.edit(nick=f"{flag} {after.display_name}")
                except:
                    pass

        except KeyError:
            pass

        logs_channel_id = db.get("logs_channel_id")
        if not logs_channel_id:
            return

        logs_channel = bot.get_channel(logs_channel_id)
        if logs_channel:
            embed = discord.Embed(
                title="Changement de Pseudo",
                description=f"Un membre a changé son pseudo",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="Membre", value=after.mention, inline=False)
            embed.add_field(
                name="Ancien pseudo", value=before.display_name, inline=True
            )
            embed.add_field(
                name="Nouveau pseudo",
                value=(
                    (after.display_name + f" ({tempName})")
                    if tempName is not None
                    else after.display_name
                ),
                inline=True,
            )
            embed.set_thumbnail(
                url=after.avatar.url if after.avatar else after.default_avatar.url
            )
            embed.set_footer(text=f"ID: {after.id}")
            await logs_channel.send(embed=embed)


@bot.event
async def on_voice_state_update(
    member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
):
    if after.channel and after.channel.id == db.get("voc_create_channel_id"):
        createdVocal = await after.channel.category.create_voice_channel(
            f"{member.name}"
        )
        tempVocalsChannelsId = db.get("temp_vocals_channel_id")
        tempVocalsChannelsId.append(createdVocal.id)
        db.modify("temp_vocals_channel_id", tempVocalsChannelsId)
        await member.move_to(createdVocal)

    if (
        before.channel
        and before.channel.id in db.get("temp_vocals_channel_id")
        and len(before.channel.members) == 0
    ):
        tempVocalsChannelsId = db.get("temp_vocals_channel_id")
        tempVocalsChannelsId.remove(before.channel.id)
        db.modify("temp_vocals_channel_id", tempVocalsChannelsId)
        await before.channel.delete()

    if (
        before.channel
        and before.channel.id in db.get("temp_matchmaking_vocals_channel_id")
        and after.channel != before.channel
    ):
        await matchmaking_logs(
            f"**{member.name}** left the voice channel : `{before.channel.name}`"
        )
        matchmakingData = json.load(open("matchmaking.json", "r"))
        teamToRemove = None
        for team in matchmakingData["pendingTeams"]["NM"]:
            if str(member.id) in team:
                teamToRemove = team
                break
        if teamToRemove is not None:
            try:
                matchmakingData["pendingTeams"]["NM"].remove(teamToRemove)
            except:
                pass
        for team in matchmakingData["pendingTeams"]["NMPZ"]:
            if str(member.id) in team:
                teamToRemove = team
                break
        if teamToRemove is not None:
            try:
                matchmakingData["pendingTeams"]["NMPZ"].remove(teamToRemove)
            except:
                pass
        if "Team Ready - " in before.channel.name or len(before.channel.members) == 0:
            await matchmaking_logs(
                "Deleting voice channel : `"
                + before.channel.name
                + "` because at least one member left or the voice channel was empty"
            )
            try:
                await before.channel.delete()
            except:
                pass
        json.dump(matchmakingData, open("matchmaking.json", "w"))

    if after.channel and after.channel.id == db.get(
        "matchmaking_voc_create_channel_id"
    ):
        await matchmaking_logs(
            f"**{member.name}** joined the voice channel : `{after.channel.name}` - Creating waiting vocal"
        )
        createdVocal = await after.channel.category.create_voice_channel(
            f"Waiting for mate - {member.name}"
        )
        tempVocalsChannelsId = db.get("temp_matchmaking_vocals_channel_id")
        tempVocalsChannelsId.append(createdVocal.id)
        db.modify("temp_matchmaking_vocals_channel_id", tempVocalsChannelsId)
        await member.move_to(createdVocal)

    if (
        after.channel
        and after.channel.name.startswith("Waiting for mate")
        and before.channel != after.channel
    ):
        await matchmaking_logs(
            f"**{member.name}** joined the voice channel : `{after.channel.name}`"
        )
        teamName = hc.isTeamConnected(after.channel.members)
        if len(after.channel.members) == 2 and teamName is None:
            await matchmaking_logs(
                f"Both players are not in a team : **{member.name}** has been disconnected"
            )
            try:
                await member.send(
                    "You have to create a team with the other player before joining the voice channel"
                )
            except:
                pass
            await member.move_to(None)
            return
        if teamName is None:
            return
        await matchmaking_logs(f"Team **{teamName}** is ready")
        await after.channel.edit(name=f"Team Ready - {teamName}")
        matchmakingData = json.load(open("matchmaking.json", "r"))
        member1 = member.guild.get_member(int(teamName.split("_")[0]))
        member2 = member.guild.get_member(int(teamName.split("_")[1]))
        NMRole = member.guild.get_role(db.get("NM_role_id"))
        NMPZRole = member.guild.get_role(db.get("NMPZ_role_id"))
        check = False

        if NMRole in member1.roles and NMRole in member2.roles:
            matchmakingData["pendingTeams"]["NM"].append(teamName)
            await matchmaking_logs(f"**{teamName}** added to NM queue")
            check = True
        if NMPZRole in member1.roles and NMPZRole in member2.roles:
            matchmakingData["pendingTeams"]["NMPZ"].append(teamName)
            await matchmaking_logs(f"**{teamName}** added to NMPZ queue")
            check = True
        json.dump(matchmakingData, open("matchmaking.json", "w"))

        if not check:
            await matchmaking_logs(
                f"**{teamName}** not added to queue because neither both players are NM nor NMPZ"
            )
            try:
                await member1.send(
                    "Hello, you and your mate need to be both registered as NM or NMPZ players to join the queue in the sign-up channel."
                )
            except:
                pass

            try:
                await member2.send(
                    "Hello, you and your mate need to be both registered as NM or NMPZ players to join the queue in the sign-up channel."
                )
            except:
                pass
            return

        availableTeamsPairsScores = hc.watch_for_matches(matchmakingData)

        if len(availableTeamsPairsScores) == 0:
            await matchmaking_logs("No match available")
            return

        while len(availableTeamsPairsScores) > 0:
            ### Matches availables but score not good enough
            try:
                timeout = min((1.0 - availableTeamsPairsScores[0][1]) * 100, 60)
                await matchmaking_logs(
                    "Match seeking done, best score: "
                    + str(availableTeamsPairsScores[0][1])
                    + ", waiting for "
                    + str(timeout)
                    + " seconds to see if another match is available"
                )
                if timeout < 5:
                    raise (asyncio.TimeoutError)
                await bot.wait_for(
                    "on_voice_state_update",
                    check=lambda _, __, after: after.channel
                    and after.channel.name.startswith("Waiting for mate")
                    and (hc.isTeamConnected(after.channel.members)) is not None,
                    timeout=timeout,
                )

            except asyncio.TimeoutError:
                match = availableTeamsPairsScores.pop(0)
                await matchmaking_logs(f"User in match: {len(user_in_match)} {user_in_match}")
                print(match[0][0], match[0][1])
                if not any([match[0][0].split('_')[0] in user_in_match,match[0][0].split('_')[1] in user_in_match,match[0][1].split('_')[0] in user_in_match,match[0][1].split('_')[1] in user_in_match]):
                    await matchmaking_logs(
                        f"No better match found, launching a match between {match[0][0]} and {match[0][1]}"
                    )
                    user_in_match.extend([match[0][0].split('_')[0],match[0][0].split('_')[1],match[0][1].split('_')[0],match[0][1].split('_')[1],])
                    matchmakingData = await hc.create_match(
                        match, matchmakingData, after.channel
                    )

                availableTeamsPairsScores = hc.watch_for_matches(matchmakingData)

            json.dump(matchmakingData, open("matchmaking.json", "w"))

        await matchmaking_logs("No more match available")


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if "custom_id" in interaction.data:
        if interaction.data["custom_id"] == "init_spectator":
            if (
                interaction.guild.get_role(db.get("registered_role_id"))
                not in interaction.user.roles
            ):
                await interaction.response.send_message(
                    ":popcorn: Prepare your popcorns, you are now a spectator of the tourney !",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f":warning: {interaction.user.mention} :warning:\n\nYou are already registered, if you want to modify your registration, please contact an admin.",
                    ephemeral=True,
                )
        elif interaction.data["custom_id"] == "init_player":
            if (
                interaction.guild.get_role(db.get("registered_role_id"))
                in interaction.user.roles
            ):
                await interaction.response.send_message(
                    f":warning: {interaction.user.mention} :warning:\n\nYou are already registered, if you want to modify your registration, please contact an admin.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_modal(md.RegisterModal())
        elif interaction.data["custom_id"] == "team_select":
            userMentionned = interaction.guild.get_member(
                int(interaction.data["values"][0])
            )
            if userMentionned == interaction.user:
                await interaction.response.send_message(
                    f":warning: {interaction.user.mention} :warning:\n\nYou can't make a team with yourself !",
                    ephemeral=True,
                )
            elif (
                userMentionned
                not in interaction.guild.get_role(db.get("registered_role_id")).members
            ):
                await interaction.response.send_message(
                    f":warning: {interaction.user.mention} :warning:\n\nThe selected player is not yet registered, to remedy this, tell him to register as a player in the channel {interaction.guild.get_channel(db.get('sign_up_channel_id')).mention} !",
                    ephemeral=True,
                )
            else:
                await interaction.response.defer()
                if hc.team_already_exists(interaction.user, userMentionned):
                    await interaction.followup.send(
                        f":x: You are already in a team with {userMentionned.mention} !",
                        ephemeral=True,
                    )
                    return

                nicknames = await hc.create_team(interaction.user, userMentionned)

                try:
                    await interaction.followup.send(
                        f":tada: {interaction.user.mention} :tada:\n\nYou are now in a team with {userMentionned.mention} !",
                        ephemeral=True,
                    )
                except:
                    pass
                try:
                    await interaction.user.send(
                        f":tada: {interaction.user.mention} :tada:\n\nYou are now in a team with {userMentionned.mention} !"
                    )
                except:
                    pass
                await userMentionned.send(
                    f":tada: {userMentionned.mention} :tada:\n\nYou are now in a team with {interaction.user.mention} ! If this is an error, please contact an admin."
                )

                embed = discord.Embed(
                    title="New team",
                    description=f"A new team has appeared : {nicknames[0]} ({interaction.user.mention}) & {nicknames[1]} ({userMentionned.mention})",
                    color=discord.Color.green(),
                    timestamp=datetime.now(),
                )
                await interaction.guild.get_channel(
                    db.get("registration_channel_id")
                ).send(embed=embed)
                await interaction.guild.get_channel(
                    db.get("new_teams_channel_id")
                ).send(embed=embed)
        elif interaction.data["custom_id"] == "NM_button":
            role = interaction.guild.get_role(db.get("NM_role_id"))
            if role in interaction.user.roles:
                await interaction.response.send_message(
                    f":warning: {interaction.user.mention} :warning:\n\nYou are no longer in NM 30s duels",
                    ephemeral=True,
                )
                await interaction.user.remove_roles(role)
            else:
                await interaction.response.send_message(
                    f":tada: {interaction.user.mention} :tada:\n\nYou can now play NM 30s duels ! Don't forget to tell your mate to do so if not done yet !",
                    ephemeral=True,
                )
                await interaction.user.add_roles(role)
        elif interaction.data["custom_id"] == "NMPZ_button":
            role = interaction.guild.get_role(db.get("NMPZ_role_id"))
            if role in interaction.user.roles:
                await interaction.response.send_message(
                    f":warning: {interaction.user.mention} :warning:\n\nYou are no longer in NMPZ 15s duels !",
                    ephemeral=True,
                )
                await interaction.user.remove_roles(role)
            else:
                await interaction.response.send_message(
                    f":tada: {interaction.user.mention} :tada:\n\nYou can now play NMPZ 15s duels ! Don't forget to tell your mate to do so if not done yet !",
                    ephemeral=True,
                )
                await interaction.user.add_roles(role)


@bot.tree.command(name="team", description="Créer votre équipe !/Create your team !")
async def team(interaction: discord.Interaction):
    if (
        interaction.user
        not in interaction.guild.get_role(db.get("registered_role_id")).members
    ):
        await interaction.response.send_message(
            f":warning: {interaction.user.mention} :warning:\n\nYou aren't registered as a player, to do so, go to the channel {interaction.guild.get_channel(db.get('sign_up_channel_id')).mention} !",
            ephemeral=True,
        )
    else:
        view = discord.ui.View()
        view.add_item(
            discord.ui.UserSelect(
                custom_id="team_select",
                max_values=1,
                placeholder="Who will be your team mate ?",
                min_values=1,
            )
        )
        await interaction.response.send_message(
            "Indicate your team mate", view=view, ephemeral=True
        )
    return


@bot.event
async def on_message(message: discord.Message):
    # Ignorer les messages du bot
    if message.author.bot:
        return

    # Continuer le traitement des autres commandes
    await bot.process_commands(message)

    if message.author.guild_permissions.administrator:

        if message.content == "$sync":
            try:
                sync_message = await message.channel.send(
                    "🔄 Synchronisation des commandes en cours..."
                )
                syncRet = await bot.tree.sync()
                await sync_message.edit(
                    content="✅ Commandes synchronisées avec succès! " + str(syncRet),
                    delete_after=5,
                )
            except Exception as e:
                await sync_message.edit(
                    f"❌ Erreur lors de la synchronisation: {str(e)}"
                )
            await message.delete()

        elif message.content.startswith("$send"):
            try:
                message_content = message.content.split("$send ", 1)[1]
                await message.channel.send(message_content)
            except Exception as e:
                pass
            await message.delete()

        elif message.content.startswith("$initmessagebienvenue"):
            view = discord.ui.View(timeout=None)
            player = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="Player !",
                custom_id="init_player",
            )
            spectator = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="Spectator !",
                custom_id="init_spectator",
            )
            view.add_item(player)
            view.add_item(spectator)
            e = discord.Embed(
                title="Welcome on the server ! :wave:", color=discord.Color.green()
            )
            e.add_field(
                name="What are you doing on the server ?",
                value='If you are here to play, click on the "Player !" button, if you are here to spectate the tourney, click on the "Spectator !" button.',
                inline=False,
            )
            e.set_footer(text=f"©HellBot")
            signupMessage = await message.guild.get_channel(
                db.get("sign_up_channel_id")
            ).send(embed=e, view=view)
            db.modify("signup_message_id", signupMessage.id)

        elif message.content.startswith("$nmornmpz"):
            view = discord.ui.View(timeout=None)
            nm = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="NM 30s",
                custom_id="NM_button",
            )
            nmpz = discord.ui.Button(
                style=discord.ButtonStyle.primary,
                label="NMPZ 15s",
                custom_id="NMPZ_button",
            )
            view.add_item(nm)
            view.add_item(nmpz)
            e = discord.Embed(
                title="Configure your duels :right_fist::zap::left_fist:",
                color=discord.Color.green(),
            )
            e.add_field(
                name="What do you want to play as Duels ?",
                value='If you want to play only NM 30s, click on the "NM 30s" button, if you want to play only NMPZ 15s, click on the "NMPZ 15s" button. If you want to play both, click on both buttons. If you change your mind, click again on buttons',
                inline=False,
            )
            e.set_footer(text=f"©HellBot")
            signupMessage = await message.guild.get_channel(
                db.get("sign_up_channel_id")
            ).send(embed=e, view=view)

    if message.channel.id == db.get("summary_links_channel_id"):
        duelId = re.search(
            r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
            message.content,
        )
        await matchmaking_logs(
            f"**{message.author.name}** sent a summary link: `{message.content}`"
        )

        if not duelId:
            await message.delete()
            await matchmaking_logs(
                f"Can't find a duelId in the summary link: `{message.content}`"
            )
            return

        # match = hc.find_match_with_user_id(message.author.id)
        # if not match:
        #     await matchmaking_logs(
        #         f"Can't find a match with the user id: `{message.author.id}`"
        #     )
        # else:
        #     for id in match["usersIds"]:
        #         try:
        #             user_in_match.remove(str(id))
        #         except:
        #             pass

        match = None

        duelId = duelId.group()

        matchmakingData = json.load(open("matchmaking.json", "r"))

        # if match:
        #     matchmakingData = await hc.close_match(
        #         match, matchmakingData, message.channel
        #     )

        winningTeam, loosingTeam = await hc.process_duel_link(
            duelId, match, matchmakingData
        )
        if match:
            inscriptionData = json.load(open("inscriptions.json", "r"))
            if duelId not in inscriptionData["teams"][winningTeam]["previousDuelIds"]:
                inscriptionData["teams"][winningTeam]["score"].append("1")
                inscriptionData["teams"][winningTeam]["previousOpponents"].append(
                    loosingTeam
                )
                inscriptionData["teams"][winningTeam]["previousDuelIds"].append(duelId)
                inscriptionData["teams"][winningTeam]["lastGamemode"] = match[
                    "matchType"
                ]

                inscriptionData["teams"][loosingTeam]["score"].append("0")
                inscriptionData["teams"][loosingTeam]["previousOpponents"].append(
                    winningTeam
                )
                inscriptionData["teams"][loosingTeam]["previousDuelIds"].append(duelId)
                inscriptionData["teams"][loosingTeam]["lastGamemode"] = match[
                    "matchType"
                ]

                for playersId in match["usersIds"]:
                    try:
                        member = message.guild.get_member(playersId)
                        await member.send(
                            f"Thanks for your participation ! To play again, just recreate a new vocal by clicking on <#1392420336506503248> and tell your mate to rejoin !"
                        )
                    except:
                        pass

            json.dump(inscriptionData, open("inscriptions.json", "w"))
            json.dump(matchmakingData, open("matchmaking.json", "w"))

        await message.add_reaction("✅")


# Lancer le bot
if __name__ == "__main__":
    bot.run(TOKEN, log_handler=None)
