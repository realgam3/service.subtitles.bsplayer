import gzip
import socket
import random
from time import sleep
from xml.etree import ElementTree
from urllib.request import Request

from .utils import movie_size_and_hash, get_session, log


class BSPlayer(object):
    VERSION = "2.67"
    DOMAIN = "api.bsplayer-subtitles.com"
    SUB_DOMAINS = [
        's1', 's2', 's3', 's4', 's5', 's6', 's7', 's8',
        's101', 's102', 's103', 's104', 's105', 's106', 's107', 's108', 's109'
    ]

    def __init__(self, search_url=None, proxies=None):
        self.session = get_session(proxies=proxies)
        self.search_url = search_url or self.get_sub_domain()
        self.token = None

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.logout()

    def get_sub_domain(self, tries=5):
        for t in range(tries):
            domain = f"{random.choice(self.SUB_DOMAINS)}.{self.DOMAIN}"
            try:
                socket.gethostbyname(domain)
                return f"http://{domain}/v1.php"
            except socket.gaierror:
                continue
        raise Exception("API Domain not found")

    def api_request(self, func_name='logIn', params='', tries=5):
        headers = {
            'User-Agent': 'BSPlayer/2.x (1022.12360)',
            'Content-Type': 'text/xml; charset=utf-8',
            'Connection': 'close',
            'SOAPAction': f'"http://{self.DOMAIN}/v1.php#{func_name}"'
        }
        data = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            f'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:ns1="{self.search_url}">'
            '<SOAP-ENV:Body SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f'<ns1:{func_name}>{params}</ns1:{func_name}></SOAP-ENV:Body></SOAP-ENV:Envelope>'
        )

        log('BSPlayer.api_request', 'Sending request: %s.' % func_name)
        for i in range(tries):
            try:
                req = Request(self.search_url, data=data.encode(), headers=headers, method="POST")
                res = self.session.open(req)
                return ElementTree.fromstring(res.read())
            except Exception as ex:
                log("BSPlayer.api_request", "ERROR: %s." % ex)
                if func_name == 'logIn':
                    self.search_url = self.get_sub_domain()
                sleep(1)
        log('BSPlayer.api_request', 'ERROR: Too many tries (%d)...' % tries)
        raise Exception('Too many tries...')

    def login(self):
        # If already logged in
        if self.token:
            return True

        root = self.api_request(
            func_name='logIn',
            params=(
                '<username></username>'
                '<password></password>'
                f'<AppID>BSPlayer v{self.VERSION}</AppID>'
            )
        )
        res = root.find('.//return')
        if res.find('status').text == 'OK':
            self.token = res.find('data').text
            log("BSPlayer.login", "Logged In Successfully.")
            return True
        return False

    def logout(self):
        # If already logged out / not logged in
        if not self.token:
            return True

        root = self.api_request(
            func_name='logOut',
            params=f'<handle>{self.token}</handle>'
        )
        res = root.find('.//return')
        self.token = None
        if res.find('status').text == 'OK':
            log("BSPlayer.logout", "Logged Out Successfully.")
            return True
        return False

    def search_subtitles(self, movie_path, language_ids='heb,eng', logout=False):
        if not self.login():
            return None

        if isinstance(language_ids, (tuple, list, set)):
            language_ids = ",".join(language_ids)

        try:
            movie_size, movie_hash = movie_size_and_hash(movie_path)
        except Exception as ex:
            print(ex)
            exit(1)
        log('BSPlayer.search_subtitles', f'Movie Size: {movie_size}, Movie Hash: {movie_hash}.')
        root = self.api_request(
            func_name='searchSubtitles',
            params=(
                f'<handle>{self.token}</handle>'
                f'<movieHash>{movie_hash}</movieHash>'
                f'<movieSize>{movie_size}</movieSize>'
                f'<languageId>{language_ids}</languageId>'
                '<imdbId>*</imdbId>'
            )
        )
        res = root.find('.//return/result')
        if res.find('status').text != 'OK':
            return []

        items = root.findall('.//return/data/item')
        subtitles = []
        if items:
            log("BSPlayer.search_subtitles", "Subtitles Found.")
            for item in items:
                subtitles.append(dict(
                    subID=item.find('subID').text,
                    subDownloadLink=item.find('subDownloadLink').text,
                    subLang=item.find('subLang').text,
                    subName=item.find('subName').text,
                    subFormat=item.find('subFormat').text,
                    subRating=item.find('subRating').text or '0'
                ))

        if logout:
            self.logout()

        return subtitles

    @staticmethod
    def download_subtitles(download_url, dest_path, proxies=None):
        session = get_session(proxies=proxies, http_10=True)
        session.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; Synapse)'),
                              ('Content-Length', 0)]
        res = session.open(download_url)
        if res:
            gf = gzip.GzipFile(fileobj=res)
            with open(dest_path, 'wb') as f:
                f.write(gf.read())
                f.flush()
            gf.close()
            return True
        return False
