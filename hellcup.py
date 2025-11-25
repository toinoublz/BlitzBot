import asyncio
import json
import os

import aiohttp
import discord
from dotenv import load_dotenv

import gspread_utilities as gu
import hashlib

def base62(num):
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    res = ''
    while num > 0:
        num, i = divmod(num, 62)
        res = chars[i] + res
    return res.zfill(6)  # on force la longueur à 6

def generate_short_id(id_list):
    concat = ''.join(str(id) for id in id_list)
    hash_hex = hashlib.sha1(concat.encode()).hexdigest()
    hash_int = int(hash_hex[:10], 16)  # on prend les 10 premiers hex chars → assez d'entropie
    return base62(hash_int)[:6]

load_dotenv()


async def get_geoguessr_flag_and_pro(geoguessr_id: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://www.geoguessr.com/api/v3/users/{geoguessr_id}"
        ) as response:
            if response.ok:
                data = await response.json()
                return (f":flag_{data['countryCode'].lower()}:", data["isProUser"])
            else:
                return False


def flag_to_emoji(flag: str):
    flag_shortcodes_to_emojis = {
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
    return flag_shortcodes_to_emojis[flag]


def get_flag(discordId: int) -> str:
    inscriptionData = json.load(open("inscriptions.json", "r"))
    return flag_to_emoji(inscriptionData["players"][str(discordId)]["flag"])


async def inscription(member: dict):
    inscriptionData = json.load(open("inscriptions.json", "r"))
    inscriptionData["players"][member["discordId"]] = member
    json.dump(inscriptionData, open("inscriptions.json", "w"))
    try:
        await gu.gspread_new_registration(member)
    except Exception as e:
        print(e)


def team_already_exists(member1: discord.Member, member2: discord.Member):
    inscriptionData = json.load(open("inscriptions.json", "r"))
    return (
        f"{member1.id}_{member2.id}" in inscriptionData["teams"]
        or f"{member2.id}_{member1.id}" in inscriptionData["teams"]
    )


async def create_team(member1: discord.Member, member2: discord.Member):
    inscriptionData = json.load(open("inscriptions.json", "r"))
    member1 = inscriptionData["players"][str(member1.id)]
    member2 = inscriptionData["players"][str(member2.id)]
    inscriptionData["teams"][f"{member1['discordId']}_{member2['discordId']}"] = {
        "teamName": f"{member1['discordId']}_{member2['discordId']}",
        "member1": member1,
        "member2": member2,
        "score": [],
        "previousOpponents": [],
        "previousDuelIds": [],
        "lastGamemode": None,
    }
    json.dump(inscriptionData, open("inscriptions.json", "w"))
    try:
        await gu.gspread_new_team([member1, member2])
    except Exception as e:
        print(e)
    return member1["surname"], member2["surname"]


def get_duel_score(team1: dict, team2: dict, gamemode: str) -> float:
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


def watch_for_matches(
    matchmakingData: dict,
) -> list[tuple[tuple[str, str], float, str]]:
    inscriptionData = json.load(open("inscriptions.json", "r"))
    NMAvailableTeams = matchmakingData["pendingTeams"]["NM"]
    NMPZAvailableTeams = matchmakingData["pendingTeams"]["NMPZ"]

    NMAvailableTeamsPairs = [
        (NMAvailableTeams[i], NMAvailableTeams[j])
        for i in range(len(NMAvailableTeams))
        for j in range(i + 1, len(NMAvailableTeams))
        if i != j
    ]
    NMAvailableTeamsPairsScores = [
        get_duel_score(
            inscriptionData["teams"][team1], inscriptionData["teams"][team2], "NM 30s"
        )
        for team1, team2 in NMAvailableTeamsPairs
    ]
    NMPZAvailableTeamsPairs = [
        (NMPZAvailableTeams[i], NMPZAvailableTeams[j])
        for i in range(len(NMPZAvailableTeams))
        for j in range(i + 1, len(NMPZAvailableTeams))
        if i != j
    ]
    NMPZAvailableTeamsPairsScores = [
        get_duel_score(
            inscriptionData["teams"][team1], inscriptionData["teams"][team2], "NMPZ 15s"
        )
        for team1, team2 in NMPZAvailableTeamsPairs
    ]

    NMAvailableTeamsPairsScores = sorted(
        zip(NMAvailableTeamsPairs, NMAvailableTeamsPairsScores),
        key=lambda x: x[1],
        reverse=True,
    )
    NMPZAvailableTeamsPairsScores = sorted(
        zip(NMPZAvailableTeamsPairs, NMPZAvailableTeamsPairsScores),
        key=lambda x: x[1],
        reverse=True,
    )

    availableTeamsPairsScores = [
        (team[0], team[1], "NM 30s") for team in NMAvailableTeamsPairsScores
    ] + [(team[0], team[1], "NMPZ 15s") for team in NMPZAvailableTeamsPairsScores]

    availableTeamsPairsScores = sorted(
        availableTeamsPairsScores, key=lambda x: x[1], reverse=True
    )

    availableTeamsPairsScores = [
        match for match in availableTeamsPairsScores if match[1] > 0
    ]

    return availableTeamsPairsScores


def isTeamConnected(members: list[discord.Member]) -> str:
    inscriptionData = json.load(open("inscriptions.json", "r"))
    membersIds = [member.id for member in members]
    for team in inscriptionData["teams"].values():
        if (
            int(team["member1"]["discordId"]) in membersIds
            and int(team["member2"]["discordId"]) in membersIds
        ):
            return team["teamName"]
    return None


async def create_match(
    match: tuple[tuple[str, str], float, str],
    matchmakingData: dict,
    channel: discord.VoiceChannel,
) -> dict:
    teams = match[0]
    matchType = match[2]
    allIds = [
        int(teams[0].split("_")[0]),
        int(teams[0].split("_")[1]),
        int(teams[1].split("_")[0]),
        int(teams[1].split("_")[1]),
    ]
    users = [channel.guild.get_member(id) for id in allIds]
    flags = [get_flag(id) for id in allIds]

    overwrites = {
        channel.guild.default_role: discord.PermissionOverwrite(view_channel=False)
    }
    for user in users:
        overwrites[user] = discord.PermissionOverwrite(view_channel=True)

    short_id = generate_short_id(allIds)

    if not any([short_id in voc.name for voc in channel.category.voice_channels]):
        matchTextChannel = await channel.category.create_text_channel(
            f"Match-{flags[0]}&{flags[1]}-vs-{flags[2]}&{flags[3]} ({short_id})", overwrites=overwrites
        )
        await matchTextChannel.send(
            f"{users[0].mention} & {users[1].mention} vs {users[2].mention} & {users[3].mention}\n\nYou can chat here. Here are the rules for your duel :\n- Gamemode : {matchType}\n- Map : {'An Arbitrary World' if matchType == 'NM 30s' else 'An Arbitrary Rural World'}\n- Every player should guess at least once during the duel.\n- 6000hp at start\n- Multiplier 0.5\n- Round without multiplier : 0\n\n**At the end of your duel**\n- Don't forget to send the summary link in <#1384834903245590588>\n- Return to <#1392420336506503248> if you want to play again\n\nGL&HF !"
        )

        teamsVocsIds = []

        for voc in channel.category.voice_channels:
            if teams[0] in voc.name and "Team Ready - " in voc.name:
                await voc.edit(name=f"Pending Match - {teams[0]}")
                teamsVocsIds.append(voc.id)
            elif teams[1] in voc.name and "Team Ready - " in voc.name:
                await voc.edit(name=f"Pending Match - {teams[1]}")
                teamsVocsIds.append(voc.id)

        matchData = {
            "teams": teams,
            "usersIds": allIds,
            "matchType": matchType,
            "matchTextChannelId": matchTextChannel.id,
            "teamsVocsIds": teamsVocsIds,
        }

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


async def close_match(
    match: dict, matchmakingData: dict, channel: discord.abc.GuildChannel
) -> dict:

    try:
        await channel.guild.get_channel(match["matchTextChannelId"]).delete()
    except:
        pass

    return matchmakingData


def find_match_with_user_id(id: int) -> dict:
    matchmakingData = json.load(open("matchmaking.json", "r"))
    for match in matchmakingData["currentMatches"]:
        if id in match["usersIds"]:
            return match
    return None


def player_in_match(id: int) -> int:
    matchmakingData = json.load(open("matchmaking.json", "r"))
    for match in matchmakingData["currentMatches"]:
        if id in match["usersIds"]:
            return match["matchTextChannelId"]
    return None


def get_username_from_geoguessr_id(id: str) -> str:
    inscriptionData = json.load(open("inscriptions.json", "r"))
    inscriptionDataWithGeoguessrIdAsKey = {
        player["geoguessrId"]: player for player in inscriptionData["players"].values()
    }
    return inscriptionDataWithGeoguessrIdAsKey[id]["surname"]


def get_country_code_from_geoguessr_id(id: str) -> str:
    inscriptionData = json.load(open("inscriptions.json", "r"))
    inscriptionDataWithGeoguessrIdAsKey = {
        player["geoguessrId"]: player for player in inscriptionData["players"].values()
    }
    return inscriptionDataWithGeoguessrIdAsKey[id]["flag"].split("_")[1][:-1]


async def process_duel_link(
    id: str, match: dict, matchmakingData: dict
) -> tuple[str, str]:

    inscriptionData = json.load(open("inscriptions.json", "r"))

    headers = {
        "Content-Type": "application/json",
        "cookie": f"_ncfa={os.getenv('GG_NCFA')}",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://game-server.geoguessr.com/api/duels/{id}", headers=headers
        ) as r:
            js = await r.json()

    winningTeamId = js["result"]["winningTeamId"]

    duelData = {
        "link": f"https://www.geoguessr.com/duels/{id}/summary",
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
                get_country_code_from_geoguessr_id(player["playerId"])
                for team in js["teams"]
                for player in team["players"]
            ]
        ),
        "WnumberOfPlayers": sum(
            len(team["players"]) for team in js["teams"] if team["id"] == winningTeamId
        ),
        "WuserNames": ",".join(
            [
                get_username_from_geoguessr_id(player["playerId"])
                for team in js["teams"]
                for player in team["players"]
                if team["id"] == winningTeamId
            ]
        ),
        "Wcountries": ",".join(
            [
                get_country_code_from_geoguessr_id(player["playerId"])
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
                get_username_from_geoguessr_id(player["playerId"])
                for team in js["teams"]
                for player in team["players"]
                if team["id"] != winningTeamId
            ]
        ),
        "Lcountries": ",".join(
            [
                get_country_code_from_geoguessr_id(player["playerId"])
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


def reset_insc():
    inscriptionData = json.load(open("inscriptions.json", "r"))
    for name in inscriptionData["teams"].keys():
        inscriptionData["teams"][name]["score"] = []
        inscriptionData["teams"][name]["previousOpponents"] = []
        inscriptionData["teams"][name]["previousDuelIds"] = []
        inscriptionData["teams"][name]["lastGamemode"] = None
    json.dump(inscriptionData, open("inscriptions.json", "w"))


if __name__ == "__main__":
    reset_insc()
