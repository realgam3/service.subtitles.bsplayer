import re
import gzip
import zlib
import json
import socket
import random
from time import sleep
from base64 import b64decode
from xml.etree import ElementTree
from urllib.request import Request
from abc import ABC, abstractmethod
from urllib.parse import urlencode, urlparse, parse_qsl

from .utils import movie_size_and_hash, get_session, log


class BSPlayerSubtitleEngine(ABC):
    def __init__(self, search_url, proxies=None, username="", password="",
                 app_id="BSPlayer v2.7", user_agent="BSPlayer/2.x (1106.12378)"):
        self.proxies = proxies
        self.username = username
        self.password = password
        self.app_id = app_id
        self.user_agent = user_agent
        self.session = get_session(proxies=self.proxies)
        self.search_url = search_url
        self.token = None

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.logout()

    @abstractmethod
    def login(self):
        pass

    @abstractmethod
    def logout(self):
        pass

    @abstractmethod
    def search_subtitles(self, movie_path, language_ids="heb,eng", logout=False):
        pass

    def download_subtitles(self, download_url, dest_path):
        session = get_session(proxies=self.proxies, http_10=True)
        session.addheaders = [("User-Agent", "Mozilla/4.0 (compatible; Synapse)"),
                              ("Content-Length", 0)]
        res = session.open(download_url)
        if res:
            gf = gzip.GzipFile(fileobj=res)
            with open(dest_path, "wb") as f:
                f.write(gf.read())
                f.flush()
            gf.close()
            log("BSPlayerSubtitleEngine.download_subtitles", f"File {repr(download_url)} Download Successfully.")
            return True
        log("BSPlayerSubtitleEngine.download_subtitles", f"File {repr(download_url)} Download Failed.")
        return False


class BSPlayer(BSPlayerSubtitleEngine):
    DOMAIN = "api.bsplayer-subtitles.com"
    SUB_DOMAINS = [
        "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8",
        "s101", "s102", "s103", "s104", "s105", "s106", "s107", "s108", "s109"
    ]

    def __init__(self, search_url=None, proxies=None, username="", password="",
                 app_id="BSPlayer v2.7", user_agent="BSPlayer/2.x (1106.12378)"):
        search_url = search_url or self.get_sub_domain()
        super().__init__(
            search_url=search_url, proxies=proxies,
            username=username, password=password,
            app_id=app_id, user_agent=user_agent
        )

    def get_sub_domain(self, tries=5):
        for t in range(tries):
            domain = f"{random.choice(self.SUB_DOMAINS)}.{self.DOMAIN}"
            try:
                socket.gethostbyname(domain)
                return f"http://{domain}/v1.php"
            except socket.gaierror:
                continue
        raise Exception("API Domain not found")

    def api_request(self, func_name, params="", tries=5, delay=1):
        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "text/xml; charset=utf-8",
            "Connection": "close",
            "SOAPAction": f'"http://{self.DOMAIN}/v1.php#{func_name}"'
        }

        log("BSPlayer.api_request", f"Sending request: {func_name}.")
        for i in range(tries):
            data = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" '
                'xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                f'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:ns1="{self.search_url}">'
                '<SOAP-ENV:Body SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
                f'<ns1:{func_name}>{params}</ns1:{func_name}></SOAP-ENV:Body></SOAP-ENV:Envelope>'
            )
            try:
                req = Request(self.search_url, data=data.encode(), headers=headers, method="POST")
                res = self.session.open(req)
                return ElementTree.fromstring(res.read())
            except Exception as ex:
                log("BSPlayer.api_request", f"ERROR: {ex}.")
                if func_name == "logIn":
                    self.search_url = self.get_sub_domain()
                sleep(delay)
        log("BSPlayer.api_request", f"ERROR: Too many tries ({tries})...")
        raise Exception("Too many tries...")

    def login(self):
        # If already logged in
        if self.token:
            return True

        root = self.api_request(
            func_name="logIn",
            params=(
                f"<username>{self.username}</username>"
                f"<password>{self.password}</password>"
                f"<AppID>{self.app_id}</AppID>"
            )
        )
        res = root.find(".//return")
        if res.find("status").text.upper() == "OK":
            self.token = res.find("data").text
            log("BSPlayer.login", "Logged In Successfully.")
            return True
        log("BSPlayer.login", "Logged In Failed.")
        return False

    def logout(self):
        # If already logged out / not logged in
        if not self.token:
            return True

        root = self.api_request(
            func_name="logOut",
            params=f"<handle>{self.token}</handle>"
        )
        res = root.find(".//return")
        self.token = None
        if res.find("status").text.upper() == "OK":
            log("BSPlayer.logout", "Logged Out Successfully.")
            return True
        return False

    def search_subtitles(self, movie_path, language_ids="heb,eng", logout=False):
        if not self.login():
            return None

        if isinstance(language_ids, (tuple, list, set)):
            language_ids = ",".join(language_ids)

        try:
            movie_size, movie_hash = movie_size_and_hash(movie_path)
        except Exception as ex:
            log("BSPlayer.search_subtitles", f"Error Calculating Movie Size / Hash: {ex}.")
            return []

        log("BSPlayer.search_subtitles", f"Movie Size: {movie_size}, Movie Hash: {movie_hash}.")
        root = self.api_request(
            func_name="searchSubtitles",
            params=(
                f"<handle>{self.token}</handle>"
                f"<movieHash>{movie_hash}</movieHash>"
                f"<movieSize>{movie_size}</movieSize>"
                f"<languageId>{language_ids}</languageId>"
                "<imdbId>*</imdbId>"
            )
        )
        res = root.find(".//return/result")
        status = res.find("status").text.upper()
        if status != "OK":
            log("BSPlayer.search_subtitles", f"Status: {status}.")
            return []

        items = root.findall(".//return/data/item")
        subtitles = []
        if items:
            for item in items:
                subtitle = dict(
                    subID=item.find("subID").text,
                    subDownloadLink=item.find("subDownloadLink").text,
                    subLang=item.find("subLang").text,
                    subName=item.find("subName").text,
                    subFormat=item.find("subFormat").text,
                    subRating=item.find("subRating").text or "0"
                )
                subtitles.append(subtitle)
            log("BSPlayer.search_subtitles", f"Subtitles Found: {json.dumps(subtitles)}.")

        if logout:
            self.logout()

        return subtitles


class OpenSubtitles(BSPlayerSubtitleEngine):
    DOMAIN = "bsplayer.api.opensubtitles.org"

    def __init__(self, username, password, search_url=None, proxies=None,
                 app_id="BSPlayer v2.78", user_agent="XmlRpc"):
        search_url = search_url or f"http://{self.DOMAIN}/xml-rpc"
        super().__init__(
            search_url=search_url, proxies=proxies,
            username=username, password=password,
            app_id=app_id, user_agent=user_agent
        )

    def api_request(self, func_name, params="", tries=5, delay=1):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/*",
            "Content-Type": "text/xml",
            "Pragma": "no-cache",
            "Connection": "close",
        }

        log("OpenSubtitles.api_request", f"Sending request: {func_name}.")
        for i in range(tries):
            data = (
                '<?xml version="1.0"?>\n'
                f'<methodCall><methodName>{func_name}</methodName>\n'
                f'<params>{params}</params>'
                '</methodCall>'
            )
            try:
                req = Request(self.search_url, data=data.encode(), headers=headers, method="POST")
                res = self.session.open(req)
                return ElementTree.fromstring(res.read())
            except Exception as ex:
                log("OpenSubtitles.api_request", f"ERROR: {ex}.")
                sleep(delay)
        log("OpenSubtitles.api_request", f"ERROR: Too many tries ({tries})...")
        raise Exception("Too many tries...")

    def login(self):
        # If already logged in
        if self.token:
            return True

        root = self.api_request(
            func_name="LogIn",
            params=(
                f'<param><value>{self.username}</value></param>'
                f'<param><value>{self.password}</value></param>'
                f'<param><value>en</value></param><param><value>{self.app_id}</value></param>'
            )
        )

        res = {
            member.find("name").text: member.find("value/*").text
            for member in root.findall(".//struct//member")
        }
        if res.get("status", "").upper() == "200 OK":
            self.token = res["token"]
            log("OpenSubtitles.login", "Logged In Successfully.")
            return True
        log("OpenSubtitles.login", "Logged In Failed.")
        return False

    def logout(self):
        # If already logged out / not logged in
        if not self.token:
            return True

        root = self.api_request(
            func_name="LogOut",
            params=f"<param><value>{self.token}</value></param>"
        )
        res = {
            member.find("name").text: member.find("value/*").text
            for member in root.findall(".//struct//member")
        }
        if res.get("status", "").upper() == "200 OK":
            self.token = None
            log("OpenSubtitles.logout", "Logged Out Successfully.")
            return True
        return False

    def search_subtitles(self, movie_path, language_ids="heb,eng", logout=False):
        if not self.login():
            return None

        if isinstance(language_ids, (tuple, list, set)):
            language_ids = ",".join(language_ids)

        try:
            movie_size, movie_hash = movie_size_and_hash(movie_path)
        except Exception as ex:
            log("OpenSubtitles.search_subtitles", f"Error Calculating Movie Size / Hash: {ex}.")
            return []

        log("OpenSubtitles.search_subtitles", f"Movie Size: {movie_size}, Movie Hash: {movie_hash}.")
        root = self.api_request(
            func_name="SearchSubtitles",
            params=(
                f"<param><value>{self.token}</value></param>"
                "<param><value><array><data><value><struct>"
                "<member><name>imdbid</name><value><string/></value></member>"
                f"<member><name>moviebytesize</name><value><double>{movie_size}.000000</double></value></member>"
                f"<member><name>moviehash</name><value>{movie_hash}</value></member>"
                f"<member><name>sublanguageid</name><value>{language_ids}</value></member>"
                "</struct></value></data></array></value></param>"
            )
        )
        res = {
            member.find("name").text: member.find("value/*").text
            for member in root.findall(".//struct//member")
        }
        status = res.get("status", "").upper()
        if status != "200 OK":
            log("OpenSubtitles.search_subtitles", f"Status: {status}.")
            return []

        items = [
            {
                member.find("name").text: member.find("value/*").text
                for member in item.findall(".//struct//member")
            } for item in root.findall(".//member/value/array/data/value")
        ]
        subtitles = []
        if items:
            for item in items:
                subtitle = dict(
                    subID=item.get("IDSubtitle"),
                    subDownloadLink=item.get("SubDownloadLink"),
                    subLang=item.get("sublanguageid"),
                    subName=item.get("SubFileName"),
                    subFormat=item.get("subFormat"),
                    subRating=item.get("SubRating") or "0"
                )
                subtitles.append(subtitle)
            log("OpenSubtitles.search_subtitles", f"Subtitles Found: {json.dumps(subtitles)}.")

        if logout:
            self.logout()

        return subtitles


class GetSubtitle(BSPlayerSubtitleEngine):
    DOMAIN = "api.getsubtitle.com"

    def __init__(self, search_url=None, proxies=None, username="", password="",
                 app_id="", user_agent="gSOAP/2.7"):
        search_url = search_url or f"http://{self.DOMAIN}/server.php"
        super().__init__(
            search_url=search_url, proxies=proxies,
            username=username, password=password,
            app_id=app_id, user_agent=user_agent
        )

    def login(self):
        log("GetSubtitle.login", "Logged In Successfully.")
        return True

    def logout(self):
        log("GetSubtitle.logout", "Logged Out Successfully.")
        return True

    def api_request(self, func_name, params="", tries=5, delay=1):
        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "text/xml; charset=utf-8",
            "Connection": "close",
            "SOAPAction": f'"{func_name}_wsdl#{func_name}"',
        }
        soap_env = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
            'xmlns:ns1="http://173.242.116.50/~admin/nusoap" '
            'xmlns:ns2="searchSubtitles_wsdl" '
            'xmlns:ns3="searchSubtitlesByHash_wsdl" '
            'xmlns:ns4="findSubtitlesByHash_wsdl" '
            'xmlns:ns5="downloadSubtitles_wsdl" '
            'xmlns:ns6="getLanguages_wsdl" '
            'xmlns:ns7="getFilesName_wsdl" '
            'xmlns:ns8="uploadSubtitle_wsdl" '
            'xmlns:ns9="uploadSubtitle2_wsdl">'
        )
        log("GetSubtitle.api_request", f"Sending request: {func_name}.")
        for i in range(tries):
            namespace = re.search(fr'xmlns:(?P<ns>ns\d+)="{func_name}_wsdl"', soap_env).group('ns')
            data = soap_env + (
                f'<SOAP-ENV:Body SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
                f'<{namespace}:{func_name}>{params}</{namespace}:{func_name}></SOAP-ENV:Body></SOAP-ENV:Envelope>'
            )
            try:
                req = Request(self.search_url, data=data.encode(), headers=headers, method="POST")
                res = self.session.open(req)
                return ElementTree.fromstring(res.read())
            except Exception as ex:
                log("GetSubtitle.api_request", f"ERROR: {ex}.")
                sleep(delay)
        log("GetSubtitle.api_request", f"ERROR: Too many tries ({tries})...")
        raise Exception("Too many tries...")

    def search_subtitles(self, movie_path, language_ids="heb,eng", logout=False):
        if isinstance(language_ids, (tuple, list, set)):
            language_ids = ",".join(language_ids)

        try:
            movie_size, movie_hash = movie_size_and_hash(movie_path)
        except Exception as ex:
            log("GetSubtitle.search_subtitles", f"Error Calculating Movie Size / Hash: {ex}.")
            return []

        log("GetSubtitle.search_subtitles", f"Movie Size: {movie_size}, Movie Hash: {movie_hash}.")
        root = self.api_request(
            func_name="searchSubtitlesByHash",
            params=(
                f"<hash>{movie_hash}</hash>"
                f"<language>{language_ids}</language>"
                "<index>0</index>"
                "<count>100</count>"
            )
        )
        subtitles = []
        for item in root.findall(".//return/item") or []:
            filename = item.find("file_name").text
            cod_subtitle_file = item.find("cod_subtitle_file").text
            query_string = urlencode(dict(
                cod_subtitle_file=cod_subtitle_file,
                movie_hash=movie_hash
            ))
            subtitle = dict(
                subID=cod_subtitle_file,
                subDownloadLink=f"http://api.getsubtitle.com/?{query_string}",
                subLang=item.find("desc_reduzido").text,
                subName=filename,
                subFormat=filename.split(".")[-1],
                subRating="0"
            )
            subtitles.append(subtitle)
        log("GetSubtitle.search_subtitles", f"Subtitles Found: {json.dumps(subtitles)}.")

        if logout:
            self.logout()

        return subtitles

    def download_subtitles(self, download_url, dest_path):
        url = urlparse(download_url)
        params = dict(parse_qsl(url.query))
        root = self.api_request(
            func_name="downloadSubtitles",
            params=(
                '<subtitles xsi:type="SOAP-ENC:Array" SOAP-ENC:arrayType="ns1:SubtitleDownload[1]"><item>'
                f'<movie_hash>{params["movie_hash"]}</movie_hash>'
                f'<cod_subtitle_file>{params["cod_subtitle_file"]}</cod_subtitle_file>'
                '</item></subtitles>'
            )
        )
        res = root.find(".//return/item/data")
        if res is not None:
            with open(dest_path, "wb") as f:
                f.write(zlib.decompress(b64decode(res.text)))
                f.flush()
            log("GetSubtitle.download_subtitles", f"File {repr(download_url)} Download Successfully.")
            return True
        log("GetSubtitle.download_subtitles", f"File {repr(download_url)} Download Failed.")
        return False
