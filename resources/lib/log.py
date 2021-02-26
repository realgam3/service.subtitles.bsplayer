import xbmc


def _log(module, msg, level=xbmc.LOGINFO):
    xbmc.log("### [%s] - %s" % (module, msg), level=level)


def debug(module, msg):
    _log(module, msg, xbmc.LOGDEBUG)


def info(module, msg):
    _log(module, msg, xbmc.LOGINFO)


def warn(module, msg):
    _log(module, msg, xbmc.LOGWARNING)

