import cookielib
import gzip
import logging
import random
import struct
import urllib2
from StringIO import StringIO
from httplib import HTTPConnection
from os import path
from time import sleep
from xml.etree import ElementTree

import xbmcvfs

# s1-9, s101-109
SUB_DOMAINS = ['s1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9',
               's101', 's102', 's103', 's104', 's105', 's106', 's107', 's108', 's109']
API_URL_TEMPLATE = "http://{sub_domain}.api.bsplayer-subtitles.com/v1.php"


def get_sub_domain():
    sub_domains_end = len(SUB_DOMAINS) - 1
    return API_URL_TEMPLATE.format(sub_domain=SUB_DOMAINS[random.randint(0, sub_domains_end)])


def get_session(proxies=None):
    cj = cookielib.CookieJar()
    proxy_handler = urllib2.ProxyHandler(proxies)
    return urllib2.build_opener(urllib2.HTTPCookieProcessor(cj), proxy_handler)


def python_logger(module, msg):
    logger = logging.getLogger('BSPlayer')
    logger.log(logging.DEBUG, (u"### [%s] - %s" % (module, msg)))


def OpensubtitlesHashRar(firsrarfile):
    # log(__name__, "Hash Rar file")
    f = xbmcvfs.File(firsrarfile)
    a = f.read(4)
    if a != 'Rar!':
        raise Exception('ERROR: This is not rar file.')
    seek = 0
    for i in range(4):
        f.seek(max(0, seek), 0)
        a = f.read(100)
        type, flag, size = struct.unpack('<BHH', a[2:2 + 5])
        if 0x74 == type:
            if 0x30 != struct.unpack('<B', a[25:25 + 1])[0]:
                raise Exception('Bad compression method! Work only for "store".')
            s_partiizebodystart = seek + size
            s_partiizebody, s_unpacksize = struct.unpack('<II', a[7:7 + 2 * 4])
            if (flag & 0x0100):
                s_unpacksize = (struct.unpack('<I', a[36:36 + 4])[0] << 32) + s_unpacksize
                # log(__name__, 'Hash untested for files biger that 2gb. May work or may generate bad hash.')
            lastrarfile = getlastsplit(firsrarfile, (s_unpacksize - 1) / s_partiizebody)
            hash = addfilehash(firsrarfile, s_unpacksize, s_partiizebodystart)
            hash = addfilehash(lastrarfile, hash, (s_unpacksize % s_partiizebody) + s_partiizebodystart - 65536)
            f.close()
            return (s_unpacksize, "%016x" % hash)
        seek += size
    raise Exception('ERROR: Not Body part in rar file.')


def getlastsplit(firsrarfile, x):
    if firsrarfile[-3:] == '001':
        return firsrarfile[:-3] + ('%03d' % (x + 1))
    if firsrarfile[-11:-6] == '.part':
        return firsrarfile[0:-6] + ('%02d' % (x + 1)) + firsrarfile[-4:]
    if firsrarfile[-10:-5] == '.part':
        return firsrarfile[0:-5] + ('%1d' % (x + 1)) + firsrarfile[-4:]
    return firsrarfile[0:-2] + ('%02d' % (x - 1))


def addfilehash(name, hash, seek):
    f = xbmcvfs.File(name)
    f.seek(max(0, seek), 0)
    for i in range(8192):
        hash += struct.unpack('<q', f.read(8))[0]
        hash &= 0xffffffffffffffff
    f.close()
    return hash


def movie_size_and_hash(file_path):
    file_ext = path.splitext(file_path)[1]
    if file_ext == '.rar' or file_ext =='.001':
        return OpensubtitlesHashRar(file_path)

    longlong_format = '<q'  # little-endian long long
    byte_size = struct.calcsize(longlong_format)

    f = xbmcvfs.File(file_path)
    file_size = f.size()
    movie_hash = file_size

    if file_size < 65536 * 2:
        f.close()
        raise Exception("SizeError")

    for x in range(65536 / byte_size):
        buff = f.read(byte_size)
        (l_value,) = struct.unpack(longlong_format, buff)
        movie_hash += l_value
        movie_hash &= 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number

    f.seek(max(0, file_size - 65536), 0)
    for x in range(65536 / byte_size):
        buff = f.read(byte_size)
        (l_value,) = struct.unpack(longlong_format, buff)
        movie_hash += l_value
        movie_hash &= 0xFFFFFFFFFFFFFFFF
    returned_movie_hash = "%016x" % movie_hash
    f.close()

    return file_size, returned_movie_hash


class HTTP10Connection(HTTPConnection):
    _http_vsn = 10
    _http_vsn_str = "HTTP/1.0"


class HTTP10Handler(urllib2.HTTPHandler):
    def http_open(self, req):
        return self.do_open(HTTP10Connection, req)


class BSPlayer(object):
    def __init__(self, search_url=None, log=python_logger, proxies=None):
        self.session = get_session(proxies)
        self.search_url = search_url or get_sub_domain()
        self.token = None
        self.log = log
        if self.log.__name__ == 'python_logger':
            logging.basicConfig(
                format='%(asctime)s T:%(thread)d  %(levelname)s: %(message)s',
                datefmt='%H:%M:%S',
                level=logging.DEBUG
            )

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.logout()

    def api_request(self, func_name='logIn', params='', tries=5):
        headers = {
            'User-Agent': 'BSPlayer/2.x (1022.12360)',
            'Content-Type': 'text/xml; charset=utf-8',
            'Connection': 'close',
            'SOAPAction': '"http://api.bsplayer-subtitles.com/v1.php#{func_name}"'.format(func_name=func_name)
        }
        data = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:ns1="{search_url}">'
            '<SOAP-ENV:Body SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            '<ns1:{func_name}>{params}</ns1:{func_name}></SOAP-ENV:Body></SOAP-ENV:Envelope>'
        ).format(search_url=self.search_url, func_name=func_name, params=params)

        self.log("BSPlayer.api_request", 'Sending request: %s' % func_name)
        for i in xrange(tries):
            try:
                self.session.addheaders.extend(headers.items())
                res = self.session.open(self.search_url, data)
                return ElementTree.fromstring(res.read())
            except Exception, ex:
                self.log("BSPlayer.api_request", ex)
                if func_name == 'logIn':
                    self.search_url = get_sub_domain()
                sleep(1)

        raise Exception('Too many tries...')

    def login(self):
        # If already logged in
        if self.token:
            return True

        root = self.api_request(
            func_name='logIn',
            params=('<username></username>'
                    '<password></password>'
                    '<AppID>BSPlayer v2.67</AppID>')
        )
        res = root.find('.//return')
        if res.find('status').text == 'OK':
            self.token = res.find('data').text
            self.log("BSPlayer.login", "Logged In Successfully.")
            return True
        return False

    def logout(self):
        # If already logged out / not logged in
        if not self.token:
            return True

        root = self.api_request(
            func_name='logOut',
            params='<handle>{token}</handle>'.format(token=self.token)
        )
        res = root.find('.//return')
        self.token = None
        if res.find('status').text == 'OK':
            self.log("BSPlayer.logout", "Logged Out Successfully.")
            return True
        return False

    def search_subtitles(self, movie_path, language_ids='heb,eng', logout=False):
        if not self.login():
            return None

        if isinstance(language_ids, (tuple, list, set)):
            language_ids = ",".join(language_ids)

        movie_size, movie_hash = movie_size_and_hash(movie_path)
        self.log('BSPlayer.search_subtitles', 'Movie Size: %s, Movie Hash: %s' % (movie_size, movie_hash))
        root = self.api_request(
            func_name='searchSubtitles',
            params=(
                '<handle>{token}</handle>'
                '<movieHash>{movie_hash}</movieHash>'
                '<movieSize>{movie_size}</movieSize>'
                '<languageId>{language_ids}</languageId>'
                '<imdbId>*</imdbId>'
            ).format(token=self.token, movie_hash=movie_hash,
                     movie_size=movie_size, language_ids=language_ids)
        )
        res = root.find('.//return/result')
        if res.find('status').text != 'OK':
            return []

        items = root.findall('.//return/data/item')
        subtitles = []
        if items:
            self.log("BSPlayer.search_subtitles", "Subtitles Found.")
            for item in items:
                subtitles.append(dict(
                    subID=item.find('subID').text,
                    subDownloadLink=item.find('subDownloadLink').text,
                    subLang=item.find('subLang').text,
                    subName=item.find('subName').text,
                    subFormat=item.find('subFormat').text
                ))

        if logout:
            self.logout()

        return subtitles

    @staticmethod
    def download_subtitles(download_url, dest_path="Subtitle.srt", proxies=None):
        proxy_handler = urllib2.ProxyHandler(proxies)
        opener = urllib2.build_opener(HTTP10Handler, proxy_handler)
        opener.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; Synapse)'),
                             ('Content-Length', 0)]
        res = opener.open(download_url)
        if res:
            gf = gzip.GzipFile(fileobj=StringIO(res.read()))
            with open(dest_path, 'wb') as f:
                f.write(gf.read())
                f.flush()
            gf.close()
            return True
        return False


if __name__ == '__main__':
    bsp = BSPlayer(proxies={'http': '207.91.10.234:8080'})
    subs = bsp.search_subtitles(
        r'V:\Movies\Jackass.Presents.Bad.Grandpa.0.5.2014.720p.Bluray.x264.DTS-EVO\Jackass.Presents.Bad.Grandpa.0.5.2014.720p.Bluray.x264.DTS-EVO.mkv',
        logout=True
    )
    for sub in subs:
        print bsp.download_subtitles(sub['subDownloadLink'], proxies={'http': '207.91.10.234:8080'})
        break
