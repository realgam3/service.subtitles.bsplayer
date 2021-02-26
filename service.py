# -*- coding: utf-8 -*-
import shutil
import sys
import urllib.parse
import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib import log
from resources.lib.utils import notify, get_params, get_video_path, get_languages_dict
from resources.lib.bsplayer import BSPlayer

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
__resource__ = xbmcvfs.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
__temp__ = xbmcvfs.translatePath(os.path.join(__profile__, 'temp', ''))


params = get_params()
log.debug("BSPlayer.params", "Current Action: %s." % params['action'])
if params['action'] == 'search':
    video_path = get_video_path()
    if video_path.startswith('http://') or video_path.startswith('https://'):
        notify(__scriptname__, __language__, 32001)
        log.debug("BSPlayer.get_video_path", "Streaming not supported.")

    log.debug("BSPlayer.video_path", "Current Video Path: %s." % video_path)
    languages = get_languages_dict(params['languages'])
    log.debug("BSPlayer.languages", "Current Languages: %s." % languages)

    with BSPlayer() as bsp:
        subtitles = bsp.search_subtitles(video_path, language_ids=list(languages.keys()))
        for subtitle in sorted(subtitles, key=lambda s: s['subLang']):
            list_item = xbmcgui.ListItem(
                label=languages[subtitle['subLang']],
                label2=subtitle['subName'],
            )
            list_item.setArt({'thumb': xbmc.convertLanguage(subtitle["subLang"], xbmc.ISO_639_1)})

            plugin_url = "plugin://{path}/?{query}".format(
                path=__scriptid__,
                query=urllib.parse.urlencode(dict(
                    action='download',
                    link=subtitle['subDownloadLink'],
                    file_name=subtitle['subName'],
                    format=subtitle['subFormat']
                ))
            )
            log.debug("BSPlayer.plugin_url", "Plugin Url Created: %s." % plugin_url)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=plugin_url, listitem=list_item, isFolder=False)
elif params['action'] == 'manualsearch':
    notify(__scriptname__, __language__, 32002)
    log.debug("BSPlayer.manualsearch", "Manual search not supported.")
elif params['action'] == 'download':
    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    if params['format'] in ["srt", "sub", "txt", "smi", "ssa", "ass"]:
        subtitle_path = os.path.join(__temp__, params['file_name'])
        if BSPlayer.download_subtitles(params['link'], subtitle_path):
            log.debug("BSPlayer.download_subtitles", "Subtitles Download Successfully From: %s." % params['link'])
            list_item = xbmcgui.ListItem(label=subtitle_path)
            log.debug("BSPlayer.download", "Downloaded Subtitle Path: %s" % subtitle_path)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=subtitle_path, listitem=list_item, isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
