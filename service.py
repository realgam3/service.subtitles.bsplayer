# -*- coding: utf-8 -*-

import os
import sys
import time
import glob
import shutil
import urlparse

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui, xbmcplugin

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode("utf-8")
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp', '')).decode("utf-8")

if xbmcvfs.exists(__temp__):
    shutil.rmtree(__temp__)
xbmcvfs.mkdirs(__temp__)

sys.path.append(__resource__)


def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg)).encode('utf-8'), level=xbmc.LOGDEBUG)


def get_params(params_str=""):
    params_str = params_str or sys.argv[2]
    return dict(urlparse.parse_qsl(params_str.lstrip('?')))


def get_video_path(xbmc_path=''):
    xbmc_path = xbmc_path or urlparse.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))

    if xbmc_path.startswith('rar://'):
        return os.path.dirname(xbmc_path.replace('rar://', ''))
    elif xbmc_path.startswith('stack://'):
        return xbmc_path.split(" , ")[0].replace('stack://', '')

    return xbmc_path


params = get_params()
if params['action'] == 'search':
    log(__name__, "action '%s' called" % params['action'])
    languages = map(
        lambda lang: xbmc.convertLanguage(lang, xbmc.ISO_639_2),
        params['languages'].split(',')
    )
