import asyncio
import os
import re
import traceback
from datetime import datetime
from datetime import time as d_time
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from easyDB import DB

import hellcup as hc
import modals as md
import utils

user_in_match = []

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Créer une instance du bot avec le préfixe '!'
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

db = DB("hellbot_gg")

# Variable globale pour stocker les invitations
invitesBefore = {}
tzParis = ZoneInfo("Europe/Paris")


async def matchmaking_logs(content):
    """
    Envoie un message dans le canal des logs de matchmaking.

    Parameters
    ----------
    content : str
        Le contenu du message à envoyer.

    Returns
    -------
    None
    """
    logsChannelId = db.get("matchmaking_logs_channel_id")
    if not logsChannelId:
        return

    channel = bot.get_channel(logsChannelId)
    if not channel:
        return

    await channel.send(f"[<t:{int(datetime.now().timestamp())}:T>] " + str(content))


@tasks.loop(time=d_time(19, 00, 00, tzinfo=tzParis))
async def update_flags():
    """
    Met à jour les flags des joueurs chaque nuit à 19h00 (heure de Paris).

    Cette fonction est exécutée en boucle infinie par la tâche @tasks.loop,
    ce qui signifie qu'elle sera exécutée une fois par jour, à la même heure.

    Elle charge les informations des joueurs depuis le fichier "inscriptions.json",
    puis pour chaque joueur, elle vérifie si le flag a changé. Si c'est le cas,
    elle met à jour le flag du joueur, ainsi que le surnom du joueur
    sur le serveur de Discord. Enfin, elle sauvegarde les informations mises
    à jour dans le fichier "inscriptions.json".

    Si une erreur se produit pendant l'exécution de cette fonction, l'erreur
    est loggée par la fonction log_error.

    """
    try:
        inscriptions = await utils.load_json("inscriptions.json")
        for player in inscriptions["players"].values():
            newFlagStr, _ = await hc.get_geoguessr_flag_and_pro(player["geoguessrId"])
            if newFlagStr != player["flag"]:
                oldFlag = hc.flag_to_emoji(player["flag"])
                newFlag = hc.flag_to_emoji(newFlagStr)
                await log_message(
                    f"Flag mis à jour de {player['surname']} de {player['flag']} à {newFlag}"
                )
                player["flag"] = newFlagStr
                member = bot.get_guild(db.get("guess_and_give_server_id")).get_member(
                    int(player["discordId"])
                )
                await member.edit(nick=member.display_name.replace(oldFlag, newFlag))
                for teams in inscriptions["teams"].values():
                    if teams["member1"]["discordId"] == player["discordId"]:
                        teams["member1"]["flag"] = newFlagStr
                    elif teams["member2"]["discordId"] == player["discordId"]:
                        teams["member2"]["flag"] = newFlagStr
        await utils.write_json(inscriptions, "inscriptions.json")
    except Exception as e:
        await log_error(e)


@bot.event
async def on_ready():
    """
    Fonction exécutée lorsque le bot est prêt à recevoir des événements.
    Elle écrit un message indiquant que le bot est connecté, puis lance la tâche
    update_flags qui met à jour les flags des joueurs chaque nuit à 19h00 (heure de Paris).
    Ensuite, elle charge les invitations existantes pour chaque serveur.
    """
    print(f"{bot.user} est connecté à Discord!")
    update_flags.start()
    # Charger les invitations existantes pour chaque serveur
    for guild in bot.guilds:
        invitesBefore[guild.id] = await guild.invites()
        invitesBefore[guild.id] = {inv.code: inv for inv in invitesBefore[guild.id]}


async def log_error(error: Exception, ctx=None):
    """Envoie les erreurs dans le canal des super logs"""
    logsChannelId = db.get("logs_channel_id")
    if not logsChannelId:
        return  # Si pas de canal configuré, on ne fait rien

    channel = bot.get_channel(logsChannelId)
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
    errorDetails = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    if len(errorDetails) > 1024:  # Discord limite la taille des fields
        errorDetails = errorDetails[-1021:] + "..."

    embed.add_field(name="Type d'erreur", value=type(error).__name__, inline=False)
    # embed.add_field(name="Message d'erreur", value=str(error), inline=False)
    errorDetails = errorDetails[-1000:] if len(errorDetails) > 1000 else errorDetails
    embed.add_field(
        name="Traceback", value=f"```python\n{errorDetails}```", inline=False
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
    logsChannelId = db.get("logs_channel_id")
    if not logsChannelId:
        return  # Si pas de canal configuré, on ne fait rien

    channel = bot.get_channel(logsChannelId)
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
    await log_error(
        Exception(
            f"Erreur dans l'événement {event}:\n{error}, args: {args}, kwargs: {kwargs}"
        )
    )


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Capture les erreurs de commandes"""
    await log_error(error, ctx)


@bot.event
async def on_invite_create(invite: discord.Invite):
    """
    Logged when a new invitation is created.

    Parameters
    ----------
    invite : discord.Invite
        The created invite.

    """
    logsChannelId = db.get("logs_channel_id")
    if not logsChannelId:
        return

    logsChannel = bot.get_channel(logsChannelId)
    if logsChannel:
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
        await logsChannel.send(embed=embed)
    invitesBefore[invite.guild.id] = await invite.guild.invites()
    invitesBefore[invite.guild.id] = {
        inv.code: inv for inv in invitesBefore[invite.guild.id]
    }


@bot.event
async def on_message_delete(message: discord.Message):
    """
    Logged when a message is deleted.

    Parameters
    ----------
    message : discord.Message
        The deleted message.

    """
    logsChannelId = db.get("logs_channel_id")
    if not logsChannelId:
        return

    # Ignorer les messages des bots
    if message.author.bot:
        return

    logsChannel = bot.get_channel(logsChannelId)
    if logsChannel:
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
        await logsChannel.send(embed=embed)


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    """
    Logged when a message is edited.

    Parameters
    ----------
    before : discord.Message
        The original message.
    after : discord.Message
        The edited message.

    Notes
    -----
    This function ignores messages from bots and messages where the content has not changed.
    """
    logsChannelId = db.get("logs_channel_id")
    if not logsChannelId:
        return

    # Ignorer les messages des bots
    if before.author.bot:
        return

    # Ignorer si le contenu n'a pas changé (par exemple, uniquement un embed ajouté)
    if before.content == after.content:
        return

    logsChannel = bot.get_channel(logsChannelId)
    if logsChannel:
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
        await logsChannel.send(embed=embed)


@bot.event
async def on_member_join(member: discord.Member):
    """
    Logged when a member joins the server.

    Parameters
    ----------
    member : discord.Member
        The member who joined the server.

    Notes
    -----
    This function ignores messages from bots and messages where the content has not changed.
    """
    logsChannelId = db.get("logs_channel_id")
    if not logsChannelId:
        return

    await bot.change_presence(
        activity=discord.Activity(
            name=f"{len(member.guild.members)} gens (trop) cools !",
            type=discord.ActivityType.watching,
        )
    )

    logsChannel = bot.get_channel(logsChannelId)
    if logsChannel:
        # Récupérer les invitations après l'arrivée du membre
        invitesAfter = await member.guild.invites()
        invitesAfter = {inv.code: inv for inv in invitesAfter}

        # Trouver quelle invitation a été utilisée
        usedInvite = None
        for inviteAfterCode, inviteAfter in invitesAfter.items():
            if (
                inviteAfterCode in invitesBefore[member.guild.id]
                and inviteAfter.uses
                > invitesBefore[member.guild.id][inviteAfterCode].uses
            ):
                usedInvite = inviteAfter
                break

        # Mettre à jour la liste des invitations
        invitesBefore[member.guild.id] = await member.guild.invites()
        invitesBefore[member.guild.id] = {
            inv.code: inv for inv in invitesBefore[member.guild.id]
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
        if usedInvite:
            embed.add_field(
                name="Invité par", value=usedInvite.inviter.mention, inline=True
            )
            embed.add_field(
                name="Code d'invitation", value=usedInvite.code, inline=True
            )
            embed.add_field(
                name="Utilisations",
                value=f"{usedInvite.uses}/{usedInvite.max_uses if usedInvite.max_uses else '∞'}",
                inline=True,
            )
        else:
            embed.add_field(name="Invitation", value="Non trouvée", inline=True)

        embed.set_footer(text=f"ID: {member.id}")
        await logsChannel.send(embed=embed)


@bot.event
async def on_member_remove(member: discord.Member):
    """
    Logged when a member leaves the server.

    Parameters
    ----------
    member : discord.Member
        The member that left the server.
    """
    logsChannelId = db.get("logs_channel_id")
    if not logsChannelId:
        return

    logsChannel = bot.get_channel(logsChannelId)
    if logsChannel:
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
        await logsChannel.send(embed=embed)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # Vérifier si le nom a changé
    """
    Logged when a member's name changes.

    Parameters
    ----------
    before : discord.Member
        The member before the name change.
    after : discord.Member
        The member after the name change.

    Notes
    -----
    This function will try to normalize the member's name by adding their flag
    at the beginning of their nickname if it is not already present.
    """
    if before.display_name != after.display_name:
        tempName = None

        try:
            flag = await hc.get_flag(after.id)

            if not after.display_name.startswith(flag + " "):
                tempName = after.display_name
                try:
                    await after.edit(nick=f"{flag} {after.display_name}")
                except Exception:
                    pass

        except KeyError:
            pass

        logsChannelId = db.get("logs_channel_id")
        if not logsChannelId:
            return

        logsChannel = bot.get_channel(logsChannelId)
        if logsChannel:
            embed = discord.Embed(
                title="Changement de Pseudo",
                description="Un membre a changé son pseudo",
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
            await logsChannel.send(embed=embed)


@bot.event
async def on_voice_state_update(
    member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
):
    """
    Logged when a voice state of a member changes.

    Parameters
    ----------
    member: discord.Member
        The member whose voice state changed.
    before: discord.VoiceState
        The previous voice state of the member.
    after: discord.VoiceState
        The new voice state of the member.

    """
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


@bot.event
async def on_interaction(interaction: discord.Interaction):
    """
    This function is called every time a user interacts with a custom component.
    It will handle the different interactions depending on the custom_id of the interaction.
    If the custom_id is "init_spectator", it will send a message to the user explaining that they are now a spectator of the tourney.
    If the custom_id is "init_player", it will check if the user is already registered as a player and if not, it will send a modal to the user to register as a player.
    If the custom_id is "team_select", it will check if the user selected is not themselves and not already registered as a player, and if not, it will create a team with the selected user.
    If the custom_id is "NM_button", it will add or remove the NM 30s duels role to the user.
    If the custom_id is "NMPZ_button", it will add or remove the NMPZ 15s duels role to the user.
    """
    if "custom_id" in interaction.data.keys():
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
                    f":warning: {interaction.user.mention} :warning:\n\nThe selected player is not registered yet, to remedy this, tell him to register as a player in the channel {interaction.guild.get_channel(db.get('sign_up_channel_id')).mention} !",
                    ephemeral=True,
                )
            else:
                await interaction.response.defer(ephemeral=True)
                if await hc.team_already_exists(interaction.user, userMentionned):
                    await interaction.followup.send(
                        f":x: You are already in a team with {userMentionned.mention} !",
                        ephemeral=True,
                    )
                    return

                nicknames = await hc.create_team(interaction.user, userMentionned, db.get("is_on"))

                try:
                    await interaction.followup.send(
                        f":tada: {interaction.user.mention} :tada:\n\nYou are now in a team with {userMentionned.mention} !",
                        ephemeral=True,
                    )
                except Exception:
                    pass
                try:
                    await interaction.user.send(
                        f":tada: {interaction.user.mention} :tada:\n\nYou are now in a team with {userMentionned.mention} !"
                    )
                except Exception:
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
        elif interaction.data["custom_id"].startswith("is_team_ready"):
            await interaction.response.defer(ephemeral=True)
            teamName = interaction.data["custom_id"].split("_", 3)[-1]
            tempView = discord.ui.View().from_message(interaction.message)
            button = tempView.children[0]
            if button.label == "🎮 Find a Match 🎮":

                await hc.update_button(
                    interaction.guild, teamName, hc.ButtonType.WAITING
                )

                await matchmaking_logs(f"**{teamName}** is ready for matchmaking")

                matchmakingData = await utils.load_json("matchmaking.json")
                member1 = interaction.guild.get_member(int(teamName.split("_")[0]))
                member2 = interaction.guild.get_member(int(teamName.split("_")[1]))
                nmRole = interaction.guild.get_role(db.get("NM_role_id"))
                nmpzRole = interaction.guild.get_role(db.get("NMPZ_role_id"))
                check = False
                if nmRole in member1.roles and nmRole in member2.roles:
                    matchmakingData["pendingTeams"]["NM"].append(teamName)
                    await matchmaking_logs(f"**{teamName}** added to NM queue")
                    check = True
                if nmpzRole in member1.roles and nmpzRole in member2.roles:
                    matchmakingData["pendingTeams"]["NMPZ"].append(teamName)
                    await matchmaking_logs(f"**{teamName}** added to NMPZ queue")
                    check = True
                await utils.write_json(matchmakingData, "matchmaking.json")

                if not check:
                    await matchmaking_logs(
                        f"**{teamName}** not added to queue because neither both players are NM nor NMPZ"
                    )

                    await hc.update_button(
                        interaction.guild, teamName, hc.ButtonType.READY
                    )

                    try:
                        await member1.send(
                            "Hello, you and your mate need to be both registered as NM or NMPZ players to join the queue in the sign-up channel. Fix the issue and then try again !"
                        )
                    except Exception:
                        pass

                    try:
                        await member2.send(
                            "Hello, you and your mate need to be both registered as NM or NMPZ players to join the queue in the sign-up channel. Fix the issue and then try again !"
                        )

                    except Exception:
                        pass
                    return

                availableTeamsPairsScores = await hc.watch_for_matches(matchmakingData)

                if len(availableTeamsPairsScores) == 0:
                    await matchmaking_logs("No match available yet")
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
                            raise asyncio.TimeoutError
                        await bot.wait_for(
                            "on_interaction",
                            check=lambda interaction_: interaction_.data.get(
                                "custom_id", ""
                            ).startswith("is_team_ready")
                            and discord.ui.View()
                            .from_message(interaction.message)
                            .children[0]
                            .label
                            == "🎮 Find a Match 🎮",
                            timeout=timeout,
                        )

                    except asyncio.TimeoutError:
                        match = availableTeamsPairsScores.pop(0)
                        await matchmaking_logs(
                            f"User in match: {len(user_in_match)} {user_in_match}"
                        )
                        allIds = [
                            match[0][0].split("_")[0],
                            match[0][0].split("_")[1],
                            match[0][1].split("_")[0],
                            match[0][1].split("_")[1],
                        ]
                        if not any(id in user_in_match for id in allIds):
                            await matchmaking_logs(
                                f"No better match found, launching a match between {match[0][0]} and {match[0][1]}"
                            )
                            user_in_match.extend(
                                [
                                    match[0][0].split("_")[0],
                                    match[0][0].split("_")[1],
                                    match[0][1].split("_")[0],
                                    match[0][1].split("_")[1],
                                ]
                            )
                            matchmakingData = await hc.create_match(
                                match, matchmakingData, allIds, interaction.guild
                            )

                        availableTeamsPairsScores = await hc.watch_for_matches(
                            matchmakingData
                        )

                    await utils.write_json(matchmakingData, "matchmaking.json")

                await matchmaking_logs("No more match available")

            else:
                await hc.update_button(interaction.guild, teamName, hc.ButtonType.READY)
                await matchmaking_logs(
                    f"**{teamName}** not ready anymore for matchmaking"
                )
                matchmakingData = await utils.load_json("matchmaking.json")
                try:
                    matchmakingData["pendingTeams"]["NMPZ"].remove(teamName)
                    matchmakingData["pendingTeams"]["NM"].remove(teamName)
                except Exception:
                    pass
                await utils.write_json(matchmakingData, "matchmaking.json")


@bot.tree.command(name="team", description="Créer votre équipe !/Create your team !")
async def team(interaction: discord.Interaction):
    """
    This command allows a player to create a team with another player.
    Before using this command, the player must be registered as a player.
    The command will ask the player to select the user they want to be their team mate.
    If the selected user is not yet registered as a player, the command will send an error message.
    """

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
    """
    This event is triggered when a message is sent in any channel that the bot can see.
    If the message is from a bot, the event is ignored.
    If the message is from an administrator, the event will process the message accordingly.
    Otherwise, the event will process the message as a command.
    """
    if message.author.bot:
        return

    # Continuer le traitement des autres commandes
    await bot.process_commands(message)

    inscriptionData = await utils.load_json("inscriptions.json")
    teamNamesFromTeamTextChannelsIds = {
        teamData["teamTextChannelId"]: teamName
        for teamName, teamData in inscriptionData["teams"].items()
    }
    teamTextChannelIdFromTeamName = {
        v: k for k, v in teamNamesFromTeamTextChannelsIds.items()
    }

    if message.channel.id in teamNamesFromTeamTextChannelsIds:
        teamName = teamNamesFromTeamTextChannelsIds[message.channel.id]
        match = await hc.find_match_with_user_id(int(teamName.split("_")[0]))
        if message.content == "$UMM":
            async for messageTemp in message.channel.history(
                limit=1, oldest_first=True
            ):
                view = discord.ui.View().from_message(messageTemp)
                view.children[0].disabled = False
                await messageTemp.edit(view=view)
        if match:
            opponentTeamName = (
                match["team1"] if teamName == match["team2"] else match["team2"]
            )
            opponentTextChannelId = teamTextChannelIdFromTeamName[opponentTeamName]
            await message.guild.get_channel(opponentTextChannelId).send(
                f"[{message.author.mention}] {message.content}"
            )

    if message.author.guild_permissions.administrator:

        if message.content == "$sync":
            try:
                syncMessage = await message.channel.send(
                    "🔄 Synchronisation des commandes en cours..."
                )
                syncRet = await bot.tree.sync()
                await syncMessage.edit(
                    content="✅ Commandes synchronisées avec succès! " + str(syncRet),
                    delete_after=5,
                )
            except Exception:
                await syncMessage.edit(
                    content="❌ Erreur lors de la synchronisation: {str(e)}"
                )
            await message.delete()

        elif message.content.startswith("$send"):
            try:
                messageContent = message.content.split("$send ", 1)[1]
                await message.channel.send(messageContent)
            except Exception:
                pass
            await message.delete()

        elif message.content == "$start_mm":
            await hc.start_matchmaking(message.guild)
            await message.channel.send("Matchmaking started")
            db.modify("is_on", True)

        elif message.content == "$stop_mm":
            await hc.stop_matchmaking(message.guild)
            await message.channel.send("Matchmaking stopped")
            db.modify("is_on", False)

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
            e.set_footer(text="©HellBot")
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
            e.set_footer(text="©HellBot")
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

        match = await hc.find_match_with_user_id(message.author.id)
        if not match:
            await matchmaking_logs(
                f"Can't find a match with the user id: `{message.author.id}`"
            )
        else:
            for idTemp in match["usersIds"]:
                try:
                    user_in_match.remove(str(idTemp))
                except Exception:
                    pass

        duelId = duelId.group()

        matchmakingData = await utils.load_json("matchmaking.json")

        winningTeam, loosingTeam = await hc.process_duel_link(
            duelId, match, matchmakingData
        )
        if match:
            inscriptionData = await utils.load_json("inscriptions.json")
            await hc.close_match(match, message.guild)
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
                            "Thanks for your participation ! To play again, just recreate a new vocal by clicking on <#1392420336506503248> and tell your mate to rejoin !"
                        )
                    except Exception:
                        pass

            await utils.write_json(inscriptionData, "inscriptions.json")
            await utils.write_json(matchmakingData, "matchmaking.json")

        await message.add_reaction("✅")


# Lancer le bot
if __name__ == "__main__":
    bot.run(TOKEN, log_handler=None)
