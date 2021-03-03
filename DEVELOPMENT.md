# Payloads

For request:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:ns1="{search_url}"><SOAP-ENV:Body SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><ns1:searchSubtitles>
<!-- Payload -->
<handle>0ec5ea0192b1c0000000000bf069a682</handle>
<movieHash>c7639000064241c1</movieHash>
<movieSize>366807916</movieSize>
<languageId>eng,fin,ell,ita</languageId>
<imdbId>*</imdbId>
<!-- Payload -->
</ns1:searchSubtitles></SOAP-ENV:Body></SOAP-ENV:Envelope>
```

Response looks like:
```xml
<ns0:Envelope xmlns:ns0="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="http://api.bsplayer-subtitles.com/v1.php" xmlns:ns3="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ns0:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
	<ns0:Body>
		<ns1:searchSubtitlesResponse>
			<return xsi:type="ns1:SearchResult">
				<result xsi:type="ns1:SubtitlesResult">
					<result xsi:type="xsd:string">200</result>
					<status xsi:type="xsd:string">OK</status>
					<data xsi:type="xsd:string">0</data>
				</result>
				<data ns3:arrayType="ns1:SubtitleData[94]" xsi:type="ns1:ArrayOfSubtitleData">
					<item xsi:type="ns1:SubtitleData">
						<subID xsi:type="xsd:int">6974000</subID>
						<subSize xsi:type="xsd:int">23237</subSize>
						<subDownloadLink xsi:type="xsd:string">http://download.bsplayer-subtitles.com/download/file/6974000/d0ec5ea0192b1c170ab9528ebf069a682</subDownloadLink>
						<subLang xsi:type="xsd:string">ita</subLang>
						<subName xsi:type="xsd:string">Movie-ita.srt</subName>
						<subFormat xsi:type="xsd:string">srt</subFormat>
						<subHash xsi:type="xsd:string">1d7f5a4ee85300000087ff788888d50f</subHash>
						<subRating xsi:type="xsd:int">5</subRating>
						<season xsi:nil="true" />
						<episode xsi:nil="true" />
						<encsubtitle xsi:nil="true" />
						<movieIMBDID xsi:type="xsd:string">0412142</movieIMBDID>
						<movieIMBDRating xsi:nil="true" />
						<movieYear xsi:nil="true" />
						<movieName xsi:nil="true" />
						<movieHash xsi:type="xsd:string">c7639dbbc64241c1</movieHash>
						<movieSize xsi:type="xsd:long">0</movieSize>
						<movieFPS xsi:type="xsd:float">0</movieFPS>
					</item>
					<!-- ... -->
				</data>
			</return>
		</ns1:searchSubtitlesResponse>
	</ns0:Body>
</ns0:Envelope>
```
```json
[{
	'subID': '6974000',
	'subDownloadLink': 'http://download.bsplayer-subtitles.com/download/file/6974000/d0ec5ea0192b1c170ab9528ebf069a682',
	'subLang': 'ita',
	'subName': 'Movie-ita.srt',
	'subFormat': 'srt'
}, ...]
```
