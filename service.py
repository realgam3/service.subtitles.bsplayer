# -*- coding: utf-8 -*-

import sys
import shutil
from os import path
from urllib import parse

import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
import xbmcplugin

from resources.lib.bsplayer import BSPlayer, OpenSubtitles, GetSubtitle
from resources.lib.utils import log, notify, get_params, get_video_path, get_languages_dict

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo("author")
__scriptid__ = __addon__.getAddonInfo("id")
__scriptname__ = __addon__.getAddonInfo("name")
__version__ = __addon__.getAddonInfo("version")
__language__ = __addon__.getLocalizedString

__cwd__ = xbmcvfs.translatePath(__addon__.getAddonInfo("path"))
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo("profile"))
__resource__ = xbmcvfs.translatePath(path.join(__cwd__, "resources", "lib"))
__temp__ = xbmcvfs.translatePath(path.join(__profile__, "temp", ""))

engines = {
    "BSPlayer": BSPlayer,
    "OpenSubtitles": OpenSubtitles,
    "GetSubtitle": GetSubtitle
}
params = get_params()
log(f"Service.params", f"Current Action: {params['action']}.")
if params["action"] == "search":
    video_path = get_video_path()
    if video_path.startswith("http://") or video_path.startswith("https://"):
        notify(__scriptname__, __language__, 32001)
        log("Service.get_video_path", "Streaming not supported.")

    log("Service.video_path", f"Current Video Path: {video_path}.")
    languages = get_languages_dict(params["languages"])
    log("Service.languages", f"Current Languages: {languages}.")

    for engine_name, engine in engines.items():
        kwargs = {}
        if engine_name == "OpenSubtitles":
            username = __addon__.getSetting("OSuser")
            password = __addon__.getSetting("OSpass")
            kwargs.update({"username": username, "password": password})
            if not all([username, password]):
                notify(__scriptname__, __language__, 32005)
                log("Service.subtitles", "OpenSubtitles username or password is empty.")
                continue

        try:
            with engine(**kwargs) as sub:
                subtitles = sub.search_subtitles(video_path, language_ids=list(languages.keys()))
                log("Service.subtitles", f"Subtitles found: {subtitles}.")
                for subtitle in sorted(subtitles, key=lambda s: s["subLang"]):
                    list_item = xbmcgui.ListItem(
                        label=engine_name,
                        label2=subtitle["subName"],
                    )
                    list_item.setArt({
                        "icon": f"{float(subtitle['subRating']) / 2}",
                        "thumb": xbmc.convertLanguage(subtitle["subLang"], xbmc.ISO_639_1)
                    })

                    query = parse.urlencode(dict(
                        action="download",
                        engine=engine_name,
                        link=subtitle["subDownloadLink"],
                        file_name=subtitle["subName"],
                        format=subtitle["subFormat"]
                    ))
                    plugin_url = f"plugin://{__scriptid__}/?{query}"
                    log("Service.plugin_url", f"Plugin Url Created: {plugin_url}.")
                    xbmcplugin.addDirectoryItem(
                        handle=int(sys.argv[1]),
                        url=plugin_url, listitem=list_item,
                        isFolder=False
                    )
        except Exception as ex:
            log("Service.search", f"{engine_name} Error: {ex}.")

elif params["action"] == "manualsearch":
    notify(__scriptname__, __language__, 32002)
    log("Service.manualsearch", "Manual search not supported.")

elif params["action"] == "download":
    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    if params["format"] in ["srt", "sub", "txt", "smi", "ssa", "ass"]:
        subtitle_path = path.join(__temp__, params["file_name"])
        engine = engines[params["engine"]]()
        if engine.download_subtitles(download_url=params["link"], dest_path=subtitle_path):
            log("Service.download_subtitles", f"Subtitles Download Successfully From: {params['link']}")
            list_item = xbmcgui.ListItem(label=subtitle_path)
            log("Service.download", f"Downloaded Subtitle Path: {subtitle_path}")
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=subtitle_path, listitem=list_item, isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
