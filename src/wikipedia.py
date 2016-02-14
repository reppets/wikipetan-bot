# coding: utf-8
import httplib2
import re
from urllib.parse import quote,unquote
from xml.parsers import expat

_htmlTagPattern = re.compile(r'<.*?>')
_htmlRefTagPattern = re.compile(r'<[Rr][Ee][Ff](\s+[^>]*|\s*)[^/]>.*?</[Rr][Ee][Ff]\s*>')
_htmlGalleryTagPattern = re.compile(r'<[Gg][Aa][Ll][Ll][Ee][Rr][Yy]\s*>.*?</[Gg][Aa][Ll][Ll][Ee][Rr][Yy]\s*>')
_lineheadPattern = re.compile(r'^(:| |----+|\*(\*|#)*|#(\*|#)*|;+|=[^=]+=|==[^=]+==|===[^=]+===|====[^=]+====)',re.MULTILINE)
_wikiFilePattern = re.compile(r'\[\[(ファイル|画像|[Ff][Ii][Ll][Ee]|[Ii][Mm][Aa][Gg][Ee]):([^\|]*?)\]\]')
_wikiFileOptionPattern = re.compile(r'\[\[(ファイル|画像|[Ff][Ii][Ll][Ee]|[Ii][Mm][Aa][Gg][Ee]):([^\|]*?)\|(([^\[]|\[[^\[])*?)\]\]')
_wikilinkPattern = re.compile(r'\[\[(?!ファイル|画像|[Ff][Ii][Ll][Ee]|[Ii][Mm][Aa][Gg][Ee])([^|]*?)\]\]')
_wikilinkAliasPattern = re.compile(r'\[\[(?!ファイル|画像|[Ff][Ii][Ll][Ee]|[Ii][Mm][Aa][Gg][Ee]).*?\|(([^\|]|[^\[]|\[[^\[])*?)\]\]')
_outerlinkPattern = re.compile(r'\[(.*?)\]')
_outerlinkAliasPattern = re.compile(r'\[\S*?[ \t]+(.*?)\]')
_templateLangPattern = re.compile(r'\{\{\s*([Rr]tl-)?[Ll]ang\s*\|[^|]+\|(([^\{]|\{[^\{])*?)([^\{]\{)?\}\}',re.MULTILINE)
_templateLangLabelPattern = re.compile(r'\{\{\s*?([Ll]ang-[^|]+|[Aa]r|[Cc]s|[Dd]e|[Ee]l|[Ee]n|[Ee]s|[Ff]r|[Hh]u|[Ii]t|[Kk]o|[Ll]a|[Mm]y|[Nn]l|[Pp]t|[Rr]u|[Zz]h(-tw)?|[Ss]namei?)\s*\|(([^\{]|\{[^\{])*?)([^\{]\{)?\}\}',re.MULTILINE)
_templatePattern = re.compile(r'\{\{([^\{]|\{[^\{])*?([^\{]\{)?\}\}',re.MULTILINE)
_tablePattern = re.compile(r'^\{\|.*?^\|\}',re.MULTILINE|re.DOTALL)
_boldPattern = re.compile(r"'''(.+?)'''")
_italicPattern = re.compile(r"''(.+?)''")
_strayBoldPattern = re.compile(r"'''")
_strayItalicPattern = re.compile(r"''")

def _getContentWiki(url):
    http = httplib2.Http()
    content = http.request(url)[1];
    return _XmlParser().deriveWiki(content.decode('utf-8'))
    
def getContentWiki(itemName):
    return _getContentWiki('http:' + quote('//ja.wikipedia.org/wiki/特別:データ書き出し/') + quote(itemName, ''))

def getRandomContentWiki():
    http = httplib2.Http()
    http.follow_redirects = False
    randomUrl = 'https:' + quote('//ja.wikipedia.org/wiki/特別:おまかせ表示/')
    articleUrl = http.request(randomUrl)[0]['location'] # status:302 should be returned.
    itemName = unquote(articleUrl.split('/')[-1])
    return (itemName, getContentWiki(itemName))

def getArticleUrl(itemName):
    return 'https://ja.wikipedia.org/wiki/' + quote(itemName)
    
def stripWikiNotation(data):
    tmp = _stripHtmlTags(data)
    tmp = _stripHeadPattern(tmp)
    tmp = _stripLink(tmp)
    tmp = _stripTemplate(tmp)
    tmp = _stripTable(tmp)
    tmp = _stripItalicBold(tmp)
    tmp = _stripNewline(tmp)
    return tmp

def _stripHtmlTags(data):
    data = _htmlRefTagPattern.sub('', data)
    data = _htmlGalleryTagPattern.sub('', data)
    return _htmlTagPattern.sub('', data)    #簡易タグ除去

def _stripHeadPattern(data):
    return _lineheadPattern.sub('', data)

def _stripLink(data):
    tmp = data
    while True:
        prev = tmp
        tmp = _wikiFilePattern.sub('', tmp)
        tmp = _wikiFileOptionPattern.sub('', tmp)
        tmp = _wikilinkPattern.sub(r'\1', tmp)
        tmp = _wikilinkAliasPattern.sub(r'\1', tmp)
        if prev == tmp:
            break
    tmp = _outerlinkAliasPattern.sub(r'\1', tmp)
    tmp = _outerlinkPattern.sub(r'\1', tmp)
    return tmp

def _stripTemplate(data):
    stripped = _templateLangPattern.sub(r'\2', data)
    stripped = _templateLangLabelPattern.sub(r'\3', stripped)
    while True:
        raw = stripped
        stripped = _templatePattern.sub('', raw)
        if raw == stripped:
            break
    return stripped

def _stripTable(data):
    return _tablePattern.sub('', data)

def _stripItalicBold(data):
    tmp = _boldPattern.sub(r'\1', data)
    tmp = _italicPattern.sub(r'\1', tmp)
    tmp = _strayBoldPattern.sub(r'', tmp)
    tmp = _strayItalicPattern.sub(r'', tmp)
    return tmp

def _stripNewline(data):
    data = data.replace('\n','')
    data = data.replace('\r','')
    return data


'''
XML Parser to derive the Wiki body from a retrieved XML.
'''
class _XmlParser(object):
    
    def __init__(self):
        pass
    
    #for xml parser call back
    def _startElement(self, name, attr):
        if name=='text':
            self.bodyStarted = True

    #for xml parser call back
    def _endElement(self, name):
        if name=='text':
            self.bodyStarted = False
            
    #for xml parser call back
    def _charData(self, data):
        if self.bodyStarted:
            self.body+=data

    def deriveWiki(self, xml):
        self.body=''
        self.bodyStarted = False
        parser = expat.ParserCreate()
        parser.buffer_text = True
        parser.StartElementHandler = self._startElement
        parser.EndElementHandler = self._endElement
        parser.CharacterDataHandler = self._charData
        parser.Parse(xml, True)
        return self.body
