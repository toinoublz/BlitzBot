import json
import os

import aiofiles


async def load_json(filename: str, folder: str = "json") -> dict:
    """
    Charge un fichier JSON depuis un dossier donné (par défaut "json").

    :param filename: Nom du fichier JSON (ex: "notations.json")
    :param folder: Nom du dossier contenant le JSON (relatif à ce fichier)
    :return: Contenu du JSON sous forme de dictionnaire
    """
    basePath = os.path.dirname(__file__)
    jsonPath = os.path.join(basePath, "..", folder, filename)

    async with aiofiles.open(jsonPath, mode="r", encoding="utf-8") as f:
        return json.loads(await f.read())


async def write_json(data: dict, filename: str, folder: str = "json") -> None:
    """
    Écrit un dictionnaire Python dans un fichier JSON de manière asynchrone.

    :param data: Le contenu à écrire (dictionnaire)
    :param filename: Nom du fichier de sortie (ex: "notations.json")
    :param folder: Dossier où enregistrer le fichier (relatif à ce fichier)
    """
    basePath = os.path.dirname(__file__)
    jsonPath = os.path.join(basePath, "..", folder, filename)

    async with aiofiles.open(jsonPath, mode="w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=4))
