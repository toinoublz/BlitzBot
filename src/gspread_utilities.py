import os
from datetime import datetime

import gspread_asyncio
from google.oauth2.service_account import Credentials


def get_creds():
    """
    Returns a Credentials object with the necessary scopes to use the Google Sheets API.

    To obtain a service account JSON file, follow these steps:
    https://gspread.readthedocs.io/en/latest/oauth2.html#for-bots-using-service-account

    Returns:
        Credentials: A Credentials object with the necessary scopes.
    """
    creds = Credentials.from_service_account_file(
        os.path.join(os.path.dirname(__file__), "..", "json", "creds.json")
    )
    scoped = creds.with_scopes(
        [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive",
        ]
    )
    return scoped


async def connect_gsheet_api() -> gspread_asyncio.AsyncioGspreadClient:
    """
    Connects to the Google Sheets API using the credentials in the service account JSON file.

    Returns:
        gspread_asyncio.AsyncioGspreadClient: A client object to interact with the Google Sheets API.
    """
    agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
    clientg = await agcm.authorize()
    return clientg


async def gspread_new_registration(member: dict):
    """
    Registers a new player in the Google Sheets database.

    Parameters
    ----------
    member : dict
        A dictionary containing information about the player.

    Returns
    -------
    None
    """
    clientg = await connect_gsheet_api()
    spreadsheet = await clientg.open("[ORGA] Guess and Give Inscriptions S2")
    worksheet = await spreadsheet.worksheet("Inscrits")
    await worksheet.append_row(
        [member["discordId"], member["geoguessrId"], member["surname"], member["flag"]]
    )
    return


async def gspread_new_team(team: list[dict]):
    """
    Registers a new team in the Google Sheets database.

    Parameters
    ----------
    team : list[dict]
        A list of dictionaries, each containing information about a player in the team.

    Returns
    -------
    None
    """
    clientg = await connect_gsheet_api()
    spreadsheet = await clientg.open("[ORGA] Guess and Give Inscriptions S2")
    worksheet = await spreadsheet.worksheet("Teams")
    await worksheet.append_row(
        [
            team[0]["discordId"],
            team[0]["geoguessrId"],
            team[0]["surname"],
            team[0]["flag"],
            team[1]["discordId"],
            team[1]["geoguessrId"],
            team[1]["surname"],
            team[1]["flag"],
        ]
    )
    return


async def add_duels_infos(data: dict):
    """
    Adds the information of a duel to the Google Sheets database.

    Parameters
    ----------
    data : dict
        A dictionary containing information about the duel.

    Returns
    -------
    None
    """
    clientg = await connect_gsheet_api()
    spreadsheet = await clientg.open(
        "Guess & Give Winter 2025 - International Duels - Hellias Version"
    )
    worksheet = await spreadsheet.worksheet("raw_data")
    await worksheet.append_row(
        [
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "",
            "",
            "",
            data["link"],
            f"=HYPERLINK(\"{data['mapLink']}\", \"{data['mapName']}\")",
            data["gamemode"],
            data["initialHealth"],
            data["numberOfRounds"],
            data["numberOfPlayers"],
            data["allCountries"],
            data["WnumberOfPlayers"],
            data["WuserNames"],
            data["Wcountries"],
            data["LnumberOfPlayers"],
            data["LuserNames"],
            data["Lcountries"],
        ],
        value_input_option="USER_ENTERED",
    )
    return
