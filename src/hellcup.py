import enum
import hashlib
import os
import time
import traceback
from datetime import datetime
from typing import Optional

import aiohttp
import discord
from dotenv import load_dotenv
from easyDB import DB

import gspread_utilities as gu
import utils

load_dotenv()


class ButtonType(enum.Enum):
    READY = 1
    WAITING = 2
    PLAYING = 3


class MatchMakingButton(discord.ui.Button):
    def __init__(self, custom_id: str):
        super().__init__(
            custom_id=custom_id,
            label="🎮 Find a Match 🎮",
            style=discord.ButtonStyle.green,
            disabled=True,
        )


async def find_channel_id_for_team(teamName: str) -> int:
    inscriptionData = await utils.load_json("inscriptions.json")
    teamTextChannelIdFromTeamName = {
        teamName: teamData["teamTextChannelId"]
        for teamName, teamData in inscriptionData["teams"].items()
    }
    return teamTextChannelIdFromTeamName[teamName]


async def update_button(guild: discord.Guild, teamName: str, buttonType: ButtonType):
    """
    Update the match making button in a team's text channel based on its state.

    Parameters
    ----------
    guild : discord.Guild
        The guild where the team's text channel is located.
    teamName : str
        The name of the team.
    buttonType : ButtonType
        The state of the button.
    """

    channel = guild.get_channel(await find_channel_id_for_team(teamName))
    if channel is None:
        return
    firstMessage = [m async for m in channel.history(limit=1, oldest_first=True)][0]
    view = discord.ui.View().from_message(firstMessage)
    button = view.children[0]
    if buttonType == ButtonType.READY:
        button.disabled = False
        button.label = "🎮 Find a Match 🎮"
        button.style = discord.ButtonStyle.green
    elif buttonType == ButtonType.WAITING:
        button.disabled = False
        button.label = "⏳ Waiting for a Match ⏳"
        button.style = discord.ButtonStyle.gray
    elif buttonType == ButtonType.PLAYING:
        button.disabled = True
        button.label = "⚔️ In a Match ⚔️"
        button.style = discord.ButtonStyle.gray
    await firstMessage.edit(view=view)


def base62(num):
    """
    Convert a number to its base62 representation.

    The base62 representation of a number is a string of characters from the set
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz". The representation is computed by
    repeatedly dividing the number by 62 and taking the remainder as the index of the
    character in the set. The resulting string is then reversed and any leading zeros are
    removed.


    The result is a string of length 6, padded with leading zeros if necessary.

    :param num: The number to convert.
    :return: The base62 representation of the number as a string.
    """
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    res = ""
    while num > 0:
        num, i = divmod(num, 62)
        res = chars[i] + res
    return res.zfill(6)  # on force la longueur à 6


def generate_short_id(idList: list):
    """
    Generate a short id based on a list of ids.

    The function takes a list of ids, concatenates them into a string, computes the SHA1 hash of the string, takes the first 10 hexadecimal characters of the hash, converts them into an integer, and then converts this integer into a base 62 string of length 6.

    :param id_list: A list of ids to generate the short id from.
    :return: A short id based on the list of ids as a string of length 6.
    """
    concat = "".join(str(id) for id in idList)
    hashHex = hashlib.sha1(concat.encode()).hexdigest()
    hashInt = int(
        hashHex[:10], 16
    )  # on prend les 10 premiers hex chars → assez d'entropie
    return base62(hashInt)[:6]


async def get_geoguessr_flag_and_pro(geoguessrId: str):
    """
    Get the Geoguessr flag and pro status of a user.

    :param geooguessr_id: The Geoguessr ID of the user.
    :return: A tuple containing the Geoguessr flag and pro status of the user.
    :rtype: tuple[str, bool]
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://www.geoguessr.com/api/v3/users/{geoguessrId}"
        ) as response:
            if response.ok:
                data = await response.json()
                return (f":flag_{data['countryCode'].lower()}:", data["isProUser"])
            else:
                return False


def flag_to_emoji(flag: str):
    """
    Convert a country flag code to its emoji representation.

    The function takes a country flag code in the format ":flag_<ISO 3166-1 code>" and returns its emoji representation.

    The function uses a dictionary to map flag codes to their emoji representations.

    The dictionary contains the mappings for the flag codes of all countries in the ISO 3166-1 standard.

    The function returns the emoji representation of the given flag code, or None if the flag code is not recognized.

    :param flag: str
        The country flag code to convert.

    :return: str
        The emoji representation of the given flag code, or None if the flag code is not recognized.
    """
    flagShortcodesToEmojis = {
        ":flag_af:": "🇦🇫",  # Afghanistan
        ":flag_al:": "🇦🇱",  # Albanie
        ":flag_dz:": "🇩🇿",  # Algérie
        ":flag_ad:": "🇦🇩",  # Andorre
        ":flag_ao:": "🇦🇴",  # Angola
        ":flag_ag:": "🇦🇬",  # Antigua-et-Barbuda
        ":flag_ar:": "🇦🇷",  # Argentine
        ":flag_am:": "🇦🇲",  # Arménie
        ":flag_au:": "🇦🇺",  # Australie
        ":flag_at:": "🇦🇹",  # Autriche
        ":flag_az:": "🇦🇿",  # Azerbaïdjan
        ":flag_bs:": "🇧🇸",  # Bahamas
        ":flag_bh:": "🇧🇭",  # Bahreïn
        ":flag_bd:": "🇧🇩",  # Bangladesh
        ":flag_bb:": "🇧🇧",  # Barbade
        ":flag_by:": "🇧🇾",  # Bélarus
        ":flag_be:": "🇧🇪",  # Belgique
        ":flag_bz:": "🇧🇿",  # Belize
        ":flag_bj:": "🇧🇯",  # Bénin
        ":flag_bt:": "🇧🇹",  # Bhoutan
        ":flag_bo:": "🇧🇴",  # Bolivie
        ":flag_ba:": "🇧🇦",  # Bosnie-Herzégovine
        ":flag_bw:": "🇧🇼",  # Botswana
        ":flag_br:": "🇧🇷",  # Brésil
        ":flag_bn:": "🇧🇳",  # Brunéi
        ":flag_bg:": "🇧🇬",  # Bulgarie
        ":flag_bf:": "🇧🇫",  # Burkina Faso
        ":flag_bi:": "🇧🇮",  # Burundi
        ":flag_kh:": "🇰🇭",  # Cambodge
        ":flag_cm:": "🇨🇲",  # Cameroun
        ":flag_ca:": "🇨🇦",  # Canada
        ":flag_cv:": "🇨🇻",  # Cap-Vert
        ":flag_cf:": "🇨🇫",  # République centrafricaine
        ":flag_td:": "🇹🇩",  # Tchad
        ":flag_cl:": "🇨🇱",  # Chili
        ":flag_co:": "🇨🇴",  # Colombie
        ":flag_km:": "🇰🇲",  # Comores
        ":flag_cr:": "🇨🇷",  # Costa Rica
        ":flag_hr:": "🇭🇷",  # Croatie
        ":flag_cu:": "🇨🇺",  # Cuba
        ":flag_cy:": "🇨🇾",  # Chypre
        ":flag_cz:": "🇨🇿",  # Tchéquie
        ":flag_cd:": "🇨🇩",  # République démocratique du Congo
        ":flag_dk:": "🇩🇰",  # Danemark
        ":flag_dj:": "🇩🇯",  # Djibouti
        ":flag_dm:": "🇩🇲",  # Dominique
        ":flag_do:": "🇩🇴",  # République dominicaine
        ":flag_tl:": "🇹🇱",  # Timor oriental
        ":flag_ec:": "🇪🇨",  # Équateur
        ":flag_eg:": "🇪🇬",  # Égypte
        ":flag_sv:": "🇸🇻",  # Salvador
        ":flag_gq:": "🇬🇶",  # Guinée équatoriale
        ":flag_er:": "🇪🇷",  # Érythrée
        ":flag_ee:": "🇪🇪",  # Estonie
        ":flag_sz:": "🇸🇿",  # Eswatini
        ":flag_et:": "🇪🇹",  # Éthiopie
        ":flag_fj:": "🇫🇯",  # Fidji
        ":flag_fi:": "🇫🇮",  # Finlande
        ":flag_fr:": "🇫🇷",  # France
        ":flag_ga:": "🇬🇦",  # Gabon
        ":flag_ge:": "🇬🇪",  # Géorgie
        ":flag_de:": "🇩🇪",  # Allemagne
        ":flag_gh:": "🇬🇭",  # Ghana
        ":flag_gr:": "🇬🇷",  # Grèce
        ":flag_gd:": "🇬🇩",  # Grenade
        ":flag_gt:": "🇬🇹",  # Guatemala
        ":flag_gy:": "🇬🇾",  # Guyana
        ":flag_ht:": "🇭🇹",  # Haïti
        ":flag_hn:": "🇭🇳",  # Honduras
        ":flag_hu:": "🇭🇺",  # Hongrie
        ":flag_is:": "🇮🇸",  # Islande
        ":flag_in:": "🇮🇳",  # Inde
        ":flag_id:": "🇮🇩",  # Indonésie
        ":flag_ir:": "🇮🇷",  # Iran
        ":flag_iq:": "🇮🇶",  # Irak
        ":flag_ie:": "🇮🇪",  # Irlande
        ":flag_il:": "🇮🇱",  # Israël
        ":flag_it:": "🇮🇹",  # Italie
        ":flag_ci:": "🇨🇮",  # Côte d’Ivoire
        ":flag_jm:": "🇯🇲",  # Jamaïque
        ":flag_jp:": "🇯🇵",  # Japon
        ":flag_jo:": "🇯🇴",  # Jordanie
        ":flag_kz:": "🇰🇿",  # Kazakhstan
        ":flag_ke:": "🇰🇪",  # Kenya
        ":flag_ki:": "🇰🇮",  # Kiribati
        ":flag_kw:": "🇰🇼",  # Koweït
        ":flag_kg:": "🇰🇬",  # Kirghizistan
        ":flag_la:": "🇱🇦",  # Laos
        ":flag_lv:": "🇱🇻",  # Lettonie
        ":flag_lb:": "🇱🇧",  # Liban
        ":flag_ls:": "🇱🇸",  # Lesotho
        ":flag_lr:": "🇱🇷",  # Libéria
        ":flag_ly:": "🇱🇾",  # Libye
        ":flag_li:": "🇱🇮",  # Liechtenstein
        ":flag_lt:": "🇱🇹",  # Lituanie
        ":flag_lu:": "🇱🇺",  # Luxembourg
        ":flag_mg:": "🇲🇬",  # Madagascar
        ":flag_mw:": "🇲🇼",  # Malawi
        ":flag_my:": "🇲🇾",  # Malaisie
        ":flag_mv:": "🇲🇻",  # Maldives
        ":flag_ml:": "🇲🇱",  # Mali
        ":flag_mt:": "🇲🇹",  # Malte
        ":flag_mh:": "🇲🇭",  # Îles Marshall
        ":flag_mr:": "🇲🇷",  # Mauritanie
        ":flag_mu:": "🇲🇺",  # Maurice
        ":flag_mx:": "🇲🇽",  # Mexique
        ":flag_fm:": "🇫🇲",  # États fédérés de Micronésie
        ":flag_md:": "🇲🇩",  # Moldavie
        ":flag_mc:": "🇲🇨",  # Monaco
        ":flag_mn:": "🇲🇳",  # Mongolie
        ":flag_me:": "🇲🇪",  # Monténégro
        ":flag_ma:": "🇲🇦",  # Maroc
        ":flag_mz:": "🇲🇿",  # Mozambique
        ":flag_mm:": "🇲🇲",  # Myanmar
        ":flag_na:": "🇳🇦",  # Namibie
        ":flag_nr:": "🇳🇷",  # Nauru
        ":flag_np:": "🇳🇵",  # Népal
        ":flag_nl:": "🇳🇱",  # Pays-Bas
        ":flag_nz:": "🇳🇿",  # Nouvelle-Zélande
        ":flag_ni:": "🇳🇮",  # Nicaragua
        ":flag_ne:": "🇳🇪",  # Niger
        ":flag_ng:": "🇳🇬",  # Nigeria
        ":flag_kp:": "🇰🇵",  # Corée du Nord
        ":flag_mk:": "🇲🇰",  # Macédoine du Nord
        ":flag_no:": "🇳🇴",  # Norvège
        ":flag_om:": "🇴🇲",  # Oman
        ":flag_pk:": "🇵🇰",  # Pakistan
        ":flag_pw:": "🇵🇼",  # Palaos
        ":flag_pa:": "🇵🇦",  # Panama
        ":flag_pg:": "🇵🇬",  # Papouasie-Nouvelle-Guinée
        ":flag_ps:": "🇵🇸",  # Palestine
        ":flag_py:": "🇵🇾",  # Paraguay
        ":flag_pe:": "🇵🇪",  # Pérou
        ":flag_ph:": "🇵🇭",  # Philippines
        ":flag_pl:": "🇵🇱",  # Pologne
        ":flag_pt:": "🇵🇹",  # Portugal
        ":flag_qa:": "🇶🇦",  # Qatar
        ":flag_cg:": "🇨🇬",  # Congo
        ":flag_ro:": "🇷🇴",  # Roumanie
        ":flag_ru:": "🇷🇺",  # Russie
        ":flag_rw:": "🇷🇼",  # Rwanda
        ":flag_kn:": "🇰🇳",  # Saint-Kitts-et-Nevis
        ":flag_lc:": "🇱🇨",  # Sainte-Lucie
        ":flag_vc:": "🇻🇨",  # Saint-Vincent-et-les-Grenadines
        ":flag_sm:": "🇸🇲",  # Saint-Marin
        ":flag_st:": "🇸🇹",  # Sao Tomé-et-Principe
        ":flag_sa:": "🇸🇦",  # Arabie Saoudite
        ":flag_sn:": "🇸🇳",  # Sénégal
        ":flag_rs:": "🇷🇸",  # Serbie
        ":flag_sc:": "🇸🇨",  # Seychelles
        ":flag_sl:": "🇸🇱",  # Sierra Leone
        ":flag_sg:": "🇸🇬",  # Singapour
        ":flag_sk:": "🇸🇰",  # Slovaquie
        ":flag_si:": "🇸🇮",  # Slovénie
        ":flag_sb:": "🇸🇧",  # Îles Salomon
        ":flag_so:": "🇸🇴",  # Somalie
        ":flag_za:": "🇿🇦",  # Afrique du Sud
        ":flag_kr:": "🇰🇷",  # Corée du Sud
        ":flag_ss:": "🇸🇸",  # Soudan du Sud
        ":flag_es:": "🇪🇸",  # Espagne
        ":flag_lk:": "🇱🇰",  # Sri Lanka
        ":flag_sd:": "🇸🇩",  # Soudan
        ":flag_sr:": "🇸🇷",  # Suriname
        ":flag_se:": "🇸🇪",  # Suède
        ":flag_ch:": "🇨🇭",  # Suisse
        ":flag_sy:": "🇸🇾",  # Syrie
        ":flag_tj:": "🇹🇯",  # Tadjikistan
        ":flag_tz:": "🇹🇿",  # Tanzanie
        ":flag_th:": "🇹🇭",  # Thaïlande
        ":flag_gm:": "🇬🇲",  # Gambie
        ":flag_tg:": "🇹🇬",  # Togo
        ":flag_to:": "🇹🇴",  # Tonga
        ":flag_tt:": "🇹🇹",  # Trinité-et-Trinbago
        ":flag_tn:": "🇹🇳",  # Tunisie
        ":flag_tr:": "🇹🇷",  # Turquie
        ":flag_tm:": "🇹🇲",  # Turkménistan
        ":flag_tv:": "🇹🇻",  # Tuvalu
        ":flag_ug:": "🇺🇬",  # Ouganda
        ":flag_ua:": "🇺🇦",  # Ukraine
        ":flag_ae:": "🇦🇪",  # Émirats arabes unis
        ":flag_gb:": "🇬🇧",  # Royaume-Uni
        ":flag_us:": "🇺🇸",  # États-Unis d’Amérique
        ":flag_uy:": "🇺🇾",  # Uruguay
        ":flag_uz:": "🇺🇿",  # Ouzbékistan
        ":flag_vu:": "🇻🇺",  # Vanuatu
        ":flag_ve:": "🇻🇪",  # Venezuela
        ":flag_vn:": "🇻🇳",  # Vietnam
        ":flag_ye:": "🇾🇪",  # Yémen
        ":flag_zm:": "🇿🇲",  # Zambie
        ":flag_zw:": "🇿🇼",  # Zimbabwe
        ":flag_cn:": "🇨🇳",  # Chine
    }
    return flagShortcodesToEmojis[flag]


async def get_flag(discordId: int) -> str:
    """
    Get the flag of a player.

    Parameters
    ----------
    discordId : int
        The Discord ID of the player.

    Returns
    -------
    str
        The flag of the player as an emoji string.
    """
    inscriptionData = await utils.load_json("inscriptions.json")
    return flag_to_emoji(inscriptionData["players"][str(discordId)]["flag"])


async def inscription(member: dict):
    """
    Save a new player to the "inscriptions.json" file.

    Parameters
    ----------
    member : dict
        A dictionary containing information about the player.

    Returns
    -------
    None
    """
    inscriptionData = await utils.load_json("inscriptions.json")
    inscriptionData["players"][member["discordId"]] = member
    await utils.write_json(inscriptionData, "inscriptions.json")
    try:
        await gu.gspread_new_registration(member)
    except Exception:
        traceback.print_exc()


async def team_already_exists(member1: discord.Member, member2: discord.Member):
    """
    Check if a team with the given members already exists.

    Parameters
    ----------
    member1: discord.Member
        The first member of the team.
    member2: discord.Member
        The second member of the team.

    Returns
    -------
    bool
        True if the team already exists, False otherwise.
    """
    inscriptionData = await utils.load_json("inscriptions.json")
    return (
        f"{member1.id}_{member2.id}" in inscriptionData["teams"]
        or f"{member2.id}_{member1.id}" in inscriptionData["teams"]
    )


async def create_team(member1: discord.Member, member2: discord.Member):
    """
    Create a new team with the given members.

    Parameters
    ----------
    member1 : discord.Member
        The first member of the team.
    member2 : discord.Member
        The second member of the team.

    Returns
    -------
    tuple
        A tuple containing the surnames of the two members.
    """
    inscriptionData = await utils.load_json("inscriptions.json")
    member1Data = inscriptionData["players"][str(member1.id)]
    member2Data = inscriptionData["players"][str(member2.id)]

    for channel in member1.guild.channels:
        if (
            isinstance(channel, discord.CategoryChannel)
            and "TEAM TEXTS CHANNELS" in channel.name
            and len(channel.text_channels) < 50
        ):
            teamTextsChannelCategory = channel
            break
    else:
        teamTextsChannelCategory = await member1.guild.create_category_channel(
            "TEAM TEXTS CHANNELS"
        )

    overwrites = {
        member1.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member1: discord.PermissionOverwrite(view_channel=True),
        member2: discord.PermissionOverwrite(view_channel=True),
    }

    teamTextChannel = await teamTextsChannelCategory.create_text_channel(
        f"{member1Data['surname']}_{member2Data['surname']}", overwrites=overwrites
    )

    inscriptionData["teams"][
        f"{member1Data['discordId']}_{member2Data['discordId']}"
    ] = {
        "teamName": f"{member1Data['discordId']}_{member2Data['discordId']}",
        "member1": member1Data,
        "member2": member2Data,
        "score": [],
        "previousOpponents": [],
        "previousDuelIds": [],
        "lastGamemode": None,
        "teamTextChannelId": teamTextChannel.id,
    }
    await utils.write_json(inscriptionData, "inscriptions.json")

    view = discord.ui.View()
    view.add_item(
        MatchMakingButton(
            f"is_team_ready_{member1Data['discordId']}_{member2Data['discordId']}"
        )
    )

    teamWelcomeMessage = await teamTextChannel.send(
        "Welcome here ! This is your team text channel.\n\nWhenever you are ready to play, click on the button below to search for a match!\n\nIf ever you want to stop searching for a match, click again.\n\nYou'll receive messages from your opponents directly in this channel to communicate during a match.",
        view=view,
    )
    await teamWelcomeMessage.pin()

    try:
        await gu.gspread_new_team([member1Data, member2Data])
    except Exception:
        traceback.print_exc()
    return member1Data["surname"], member2Data["surname"]


async def refresh_invites_message(guild: discord.Guild, db: DB):
    """
    Refreshes the message containing the list of saved invites.

    Parameters
    ----------
    guild : discord.Guild
        The guild where the message is located.
    db : DB
        The database containing the information about the invites.

    Notes
    -----
    This function is used to refresh the message containing the list of saved invites.
    It fetches the message, gets the list of invites to check and the list of invites in the guild,
    and then edits the message with the new list of invites.

    """
    message = await guild.get_channel(db.get("registration_channel_id")).fetch_message(
        db.get("invit_message_id")
    )
    invitesToCheck = db.get("invit_to_check")
    guildInvites = await guild.invites()
    invites = {
        invite.code: invite.uses
        for invite in guildInvites
        if invite.code in invitesToCheck.keys()
    }
    content = "Liste des invitations sauvegardées actuelles :\n- "
    content += "\n- ".join(
        [
            f"{invitesToCheck[key]} ({key}) : {value} utilisation{'' if value == 1 else 's'}"
            for key, value in invites.items()
        ]
    )
    await message.edit(content=content)


def get_duel_score(team1: dict, team2: dict, gamemode: str) -> float:
    """
    Calculate the score of a duel between two teams.

    The score is based on whether any of the players are pros,
    whether the flags of the players are different, whether all
    players are unique, and whether the teams have previously
    played each other.

    If the teams have previously played each other, the score
    is decreased by 0.5 times the number of previous games.
    If the teams have previously played each other in the same
    gamemode, the score is decreased by an additional 0.01.

    If the teams have previously played each other 5 or more times,
    the score is decreased by 0.2 times the absolute difference
    in the average of their previous scores.

    Parameters:
    team1 (dict): The first team.
    team2 (dict): The second team.
    gamemode (str): The gamemode of the duel.

    Returns:
    float: The score of the duel.
    """
    allPros = [
        team1["member1"]["isPro"],
        team1["member2"]["isPro"],
        team2["member1"]["isPro"],
        team2["member2"]["isPro"],
    ]
    allFlags = [
        team1["member1"]["flag"],
        team1["member2"]["flag"],
        team2["member1"]["flag"],
        team2["member2"]["flag"],
    ]
    allPlayers = [
        team1["member1"]["discordId"],
        team1["member2"]["discordId"],
        team2["member1"]["discordId"],
        team2["member2"]["discordId"],
    ]
    if not (any(allPros) and len(set(allFlags)) > 1 and len(set(allPlayers)) == 4):
        return 0.0
    previousOpponentsScore = (
        0.5
        if team1["teamName"] not in team2["previousOpponents"]
        else min(
            0.1 * (team2["previousOpponents"][::-1].index(team1["teamName"]) + 1), 0.5
        )
    ) + (
        0.5
        if team2["teamName"] not in team1["previousOpponents"]
        else min(
            0.1 * (team1["previousOpponents"][::-1].index(team2["teamName"]) + 1), 0.5
        )
    )

    if len(team1["score"]) >= 5 and len(team2["score"]) >= 5:
        team1ScoreRatio = sum(team1["score"]) / len(team1["score"])
        team2ScoreRatio = sum(team2["score"]) / len(team2["score"])
        diff = abs(team1ScoreRatio - team2ScoreRatio)
        previousOpponentsScore -= diff * 0.2
    if team1["lastGamemode"] == gamemode:
        previousOpponentsScore -= 0.01
    if team2["lastGamemode"] == gamemode:
        previousOpponentsScore -= 0.01

    return previousOpponentsScore


async def watch_for_matches(
    matchmakingData: dict,
) -> list[tuple[tuple[str, str], float, str]]:
    """
    This function takes a matchmaking data dictionary as an argument and returns a list of tuples.
    Each tuple contains a pair of team names, a score for the pair, and a gamemode.
    The function first loads the registration data from the file "inscriptions.json".
    It then creates lists of available teams for each gamemode.
    For each available team pair, it calculates the score for the pair using the get_duel_score function.
    The function then sorts the available team pairs by score in descending order and filters out any pairs with a score of 0.
    Finally, it returns the list of available team pairs with scores and gamemodes.

    Parameters
    ----------
    matchmakingData: dict
        A dictionary containing the matchmaking data.

    Returns
    -------
    list[tuple[tuple[str, str], float, str]]
        A list of tuples, each containing a pair of team names, a score for the pair, and a gamemode.
    """
    inscriptionData = await utils.load_json("inscriptions.json")
    nmAvailableTeams = matchmakingData["pendingTeams"]["NM"]
    nmpzAvailableTeams = matchmakingData["pendingTeams"]["NMPZ"]

    nmAvailableTeamsPairs = [
        (nmAvailableTeams[i], nmAvailableTeams[j])
        for i in range(len(nmAvailableTeams))
        for j in range(i + 1, len(nmAvailableTeams))
        if i != j
    ]
    nmAvailableTeamsPairsScores = [
        get_duel_score(
            inscriptionData["teams"][team1], inscriptionData["teams"][team2], "NM 30s"
        )
        for team1, team2 in nmAvailableTeamsPairs
    ]
    nmpzAvailableTeamsPairs = [
        (nmpzAvailableTeams[i], nmpzAvailableTeams[j])
        for i in range(len(nmpzAvailableTeams))
        for j in range(i + 1, len(nmpzAvailableTeams))
        if i != j
    ]
    nmpzAvailableTeamsPairsScores = [
        get_duel_score(
            inscriptionData["teams"][team1], inscriptionData["teams"][team2], "NMPZ 15s"
        )
        for team1, team2 in nmpzAvailableTeamsPairs
    ]

    nmAvailableTeamsPairsScores = sorted(
        zip(nmAvailableTeamsPairs, nmAvailableTeamsPairsScores),
        key=lambda x: x[1],
        reverse=True,
    )
    nmpzAvailableTeamsPairsScores = sorted(
        zip(nmpzAvailableTeamsPairs, nmpzAvailableTeamsPairsScores),
        key=lambda x: x[1],
        reverse=True,
    )

    availableTeamsPairsScores = [
        (team[0], team[1], "NM 30s") for team in nmAvailableTeamsPairsScores
    ] + [(team[0], team[1], "NMPZ 15s") for team in nmpzAvailableTeamsPairsScores]

    availableTeamsPairsScores = sorted(
        availableTeamsPairsScores, key=lambda x: x[1], reverse=True
    )

    availableTeamsPairsScores = [
        match for match in availableTeamsPairsScores if match[1] > 0
    ]

    return availableTeamsPairsScores


async def is_team_connected(members: list[discord.Member]) -> Optional[str]:
    """
    Check if all members of a team are connected.

    Parameters
    ----------
    members : list[discord.Member]
        A list of discord members.

    Returns
    -------
    str
        The name of the team if all members are connected, None otherwise.
    """
    inscriptionData = await utils.load_json("inscriptions.json")
    membersIds = [member.id for member in members]
    for teamTemp in inscriptionData["teams"].values():
        if (
            int(teamTemp["member1"]["discordId"]) in membersIds
            and int(teamTemp["member2"]["discordId"]) in membersIds
        ):
            return teamTemp["teamName"]
    return None


async def create_match(
    match: tuple[tuple[str, str], float, str],
    matchmakingData: dict,
    allIds: list[int],
    guild: discord.Guild,
) -> dict:
    """
    Create a match between two teams.

    Parameters
    ----------
    match : tuple[tuple[str, str], float, str]
        A tuple containing the names of the two teams, their score, and the gamemode.
    matchmakingData : dict
        A dictionary containing the matchmaking data.
    channel : discord.VoiceChannel
        The voice channel of the server.

    Returns
    -------
    dict
        A dictionary containing the updated matchmaking data.
    """
    teams = match[0]
    matchType = match[2]

    matchData = {
        "teams": teams,
        "team1": teams[0],
        "team2": teams[1],
        "usersIds": allIds,
        "matchType": matchType,
        "startTime": time.time(),
    }

    inscriptionData = await utils.load_json("inscriptions.json")

    team1TextChannelId = inscriptionData["teams"][teams[0]]["teamTextChannelId"]
    team2TextChannelId = inscriptionData["teams"][teams[1]]["teamTextChannelId"]

    await guild.get_channel(team1TextChannelId).send(
        "New match found, you are playing against team <@"
        + teams[1].split("_")[0]
        + "> & <@"
        + teams[1].split("_")[1]
        + ">. Your match is in "
        + matchType
        + "."
    )
    await guild.get_channel(team2TextChannelId).send(
        "New match found, you are playing against team <@"
        + teams[0].split("_")[0]
        + "> & <@"
        + teams[0].split("_")[1]
        + ">. Your match is in "
        + matchType
        + "."
    )

    if teams[0] in matchmakingData["pendingTeams"]["NM"]:
        matchmakingData["pendingTeams"]["NM"].remove(teams[0])
    if teams[0] in matchmakingData["pendingTeams"]["NMPZ"]:
        matchmakingData["pendingTeams"]["NMPZ"].remove(teams[0])
    if teams[1] in matchmakingData["pendingTeams"]["NM"]:
        matchmakingData["pendingTeams"]["NM"].remove(teams[1])
    if teams[1] in matchmakingData["pendingTeams"]["NMPZ"]:
        matchmakingData["pendingTeams"]["NMPZ"].remove(teams[1])

    matchmakingData["currentMatches"].append(matchData)

    return matchmakingData


async def close_match(match: dict, guild: discord.Guild) -> None:
    """
    Close a match by deleting all the messages in the teams' text channels and updating the match making buttons of the teams.

    Parameters
    ----------
    match : dict
        A dictionary containing the match data.
    guild : discord.Guild
        The guild where the match is taking place.

    Returns
    -------
    None
    """
    channel1 = guild.get_channel(find_channel_id_for_team(match["team1"]))
    channel2 = guild.get_channel(find_channel_id_for_team(match["team2"]))

    timestampLimit = match["startTime"]

    timestampLimitDateTime = datetime.fromtimestamp(timestampLimit)
    await channel1.purge(limit=None, after=timestampLimitDateTime)
    await channel2.purge(limit=None, after=timestampLimitDateTime)

    await update_button(guild, match["team1"], ButtonType.READY)
    await update_button(guild, match["team2"], ButtonType.READY)


async def find_match_with_user_id(idTemp: int) -> Optional[dict]:
    """
    Find the match that a user is currently in.

    Parameters
    ----------
    id : int
        The user id to find the match for.

    Returns
    -------
    dict
        The match data if the user is in a match, None otherwise.
    """
    matchmakingData = await utils.load_json("matchmaking.json")
    for match in matchmakingData["currentMatches"]:
        if str(idTemp) in match["usersIds"]:
            return match
    return None


async def player_in_match(idTemp: int) -> Optional[int]:
    """
    Check if a player is currently in a match.

    Parameters
    ----------
    id : int
        The user id to check.

    Returns
    -------
    int
        The match text channel id if the user is in a match, None otherwise.
    """
    matchmakingData = await utils.load_json("matchmaking.json")
    for match in matchmakingData["currentMatches"]:
        if idTemp in match["usersIds"]:
            return match["matchTextChannelId"]
    return None


async def get_username_from_geoguessr_id(idTemp: str) -> str:
    """
    Get the username of a player from their Geoguessr ID.

    Parameters
    ----------
    id : str
        The Geoguessr ID of the player.

    Returns
    -------
    str
        The username of the player.
    """
    inscriptionData = await utils.load_json("inscriptions.json")
    inscriptionDataWithGeoguessrIdAsKey = {
        player["geoguessrId"]: player for player in inscriptionData["players"].values()
    }
    return inscriptionDataWithGeoguessrIdAsKey[idTemp]["surname"]


async def get_country_code_from_geoguessr_id(idTemp: str) -> str:
    """
    Get the country code of a player from their Geoguessr ID.

    Parameters
    ----------
    id : str
        The Geoguessr ID of the player.

    Returns
    -------
    str
        The country code of the player.

    """
    inscriptionData = await utils.load_json("inscriptions.json")
    inscriptionDataWithGeoguessrIdAsKey = {
        player["geoguessrId"]: player for player in inscriptionData["players"].values()
    }
    return inscriptionDataWithGeoguessrIdAsKey[idTemp]["flag"].split("_")[1][:-1]


async def process_duel_link(
    idTemp: str, match: dict, matchmakingData: dict
) -> tuple[str, str]:
    """
    Process a duel link and store the duel data in the Google Sheets API.

    Parameters
    ----------
    id : str
        The ID of the duel.
    match : dict
        The match data from the matchmaking system.
    matchmakingData : dict
        The matchmaking data from the matchmaking system.

    Returns
    -------
    tuple[str, str]
        A tuple containing the winning team and the other team.
    """
    inscriptionData = await utils.load_json("inscriptions.json")

    headers = {
        "Content-Type": "application/json",
        "cookie": f"_ncfa={os.getenv('GG_NCFA')}",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://game-server.geoguessr.com/api/duels/{idTemp}", headers=headers
        ) as r:
            js = await r.json()

    winningTeamId = js["result"]["winningTeamId"]

    duelData = {
        "link": f"https://www.geoguessr.com/duels/{idTemp}/summary",
        "mapName": js["options"]["map"]["name"],
        "mapLink": f"https://www.geoguessr.com/maps/{js['options']['map']['slug']}",
        "gamemode": (
            "No Move"
            if js["options"]["movementOptions"]["forbidMoving"]
            and not js["options"]["movementOptions"]["forbidRotating"]
            and not js["options"]["movementOptions"]["forbidZooming"]
            else (
                "NMPZ"
                if js["options"]["movementOptions"]["forbidMoving"]
                and js["options"]["movementOptions"]["forbidRotating"]
                and js["options"]["movementOptions"]["forbidZooming"]
                else "Unknown"
            )
        ),
        "initialHealth": js["options"]["initialHealth"],
        "numberOfRounds": js["currentRoundNumber"],
        "numberOfPlayers": sum(len(team["players"]) for team in js["teams"]),
        "allCountries": ",".join(
            [
                await get_country_code_from_geoguessr_id(player["playerId"])
                for team in js["teams"]
                for player in team["players"]
            ]
        ),
        "WnumberOfPlayers": sum(
            len(team["players"]) for team in js["teams"] if team["id"] == winningTeamId
        ),
        "WuserNames": ",".join(
            [
                await get_username_from_geoguessr_id(player["playerId"])
                for team in js["teams"]
                for player in team["players"]
                if team["id"] == winningTeamId
            ]
        ),
        "Wcountries": ",".join(
            [
                await get_country_code_from_geoguessr_id(player["playerId"])
                for team in js["teams"]
                for player in team["players"]
                if team["id"] == winningTeamId
            ]
        ),
        "LnumberOfPlayers": sum(
            len(team["players"]) for team in js["teams"] if team["id"] != winningTeamId
        ),
        "LuserNames": ",".join(
            [
                await get_username_from_geoguessr_id(player["playerId"])
                for team in js["teams"]
                for player in team["players"]
                if team["id"] != winningTeamId
            ]
        ),
        "Lcountries": ",".join(
            [
                await get_country_code_from_geoguessr_id(player["playerId"])
                for team in js["teams"]
                for player in team["players"]
                if team["id"] != winningTeamId
            ]
        ),
    }

    await gu.add_duels_infos(duelData)
    if match is not None:
        matchmakingData["currentMatches"].remove(match)
        winningPlayerId = [
            player["playerId"]
            for team in js["teams"]
            for player in team["players"]
            if team["id"] == winningTeamId
        ][0]

        ggIds = [
            inscriptionData["players"][str(discordId)]["geoguessrId"]
            for discordId in match["usersIds"]
        ]

        winningTeam = (
            match["teams"][0] if ggIds.index(winningPlayerId) > 2 else match["teams"][1]
        )
        otherTeam = (
            match["teams"][0]
            if ggIds.index(winningPlayerId) <= 2
            else match["teams"][1]
        )
    else:
        return (None, None)

    return (winningTeam, otherTeam)


async def reset_insc():
    """
    Resets the score, previous opponents, previous duel IDs and last gamemode for each team in the "inscriptions.json" file.

    This function is used to reset the data at the end of the tournament.
    """
    inscriptionData = await utils.load_json("inscriptions.json")
    for name in inscriptionData["teams"].keys():
        inscriptionData["teams"][name]["score"] = []
        inscriptionData["teams"][name]["previousOpponents"] = []
        inscriptionData["teams"][name]["previousDuelIds"] = []
        inscriptionData["teams"][name]["lastGamemode"] = None
    await utils.write_json(inscriptionData, "inscriptions.json")
