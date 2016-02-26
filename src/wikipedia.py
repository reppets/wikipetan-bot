import httplib2
import re
from urllib.parse import quote,unquote
from xml.parsers import expat

_HTML_TAG_PATTERN = re.compile(r'<.*?>')
_HTML_SINGLE_REF_TAG_PATTERN = re.compile(r'<[Rr][Ee][Ff][^/>]*/>')
_HTML_REF_TAG_PATTERN = re.compile(r'<[Rr][Ee][Ff](\s+[^>]*|\s*)[^/]?>.*?</[Rr][Ee][Ff]\s*>',re.MULTILINE)
_HTML_GALLERY_TAG_PATTERN = re.compile(r'<[Gg][Aa][Ll][Ll][Ee][Rr][Yy]\s*>.*?</[Gg][Aa][Ll][Ll][Ee][Rr][Yy]\s*>',re.MULTILINE)
_LINE_HEAD_PATTERN = re.compile(r'^(:| |----+|\*(\*|#)*|#(\*|#)*|;+|=[^=]+=|==[^=]+==|===[^=]+===|====[^=]+====)',re.MULTILINE)
_WIKI_FILE_PATTERN = re.compile(r'\[\[(ファイル|画像|[Ff][Ii][Ll][Ee]|[Ii][Mm][Aa][Gg][Ee]):([^\|]*?)\]\]')
_WIKI_FILE_OPTION_PATTERN = re.compile(r'\[\[(ファイル|画像|[Ff][Ii][Ll][Ee]|[Ii][Mm][Aa][Gg][Ee]):([^\|]*?)\|(([^\[]|\[[^\[])*?)\]\]')
_WIKI_LINK_PATTERN = re.compile(r'\[\[(?!ファイル|画像|[Ff][Ii][Ll][Ee]|[Ii][Mm][Aa][Gg][Ee])([^|]*?)\]\]')
_WIKI_LINK_ALIAS_PATTERN = re.compile(r'\[\[(?!ファイル|画像|[Ff][Ii][Ll][Ee]|[Ii][Mm][Aa][Gg][Ee]).*?\|(([^\|]|[^\[]|\[[^\[])*?)\]\]')
_OUTER_LINK_PATTERN = re.compile(r'\[(.*?)\]')
_OUTER_LINK_ALIAS_PATTERN = re.compile(r'\[\S*?[ \t]+(.*?)\]')
_TEMPLATE_LANG_PATTERN = re.compile(r'\{\{\s*([Rr]tl-)?[Ll]ang\s*\|[^|]+\|(([^\{]|\{[^\{])*?)([^\{]\{)?\}\}',re.MULTILINE)
_TEMPLATE_LANG_LABEL_PATTERN = re.compile(r'\{\{\s*([Ll]ang-[^|]+|[Aa]r|[Cc]s|[Dd]e|[Ee]l|[Ee]n|[Ee]s|[Ff]r|[Hh]u|[Ii]t|[Kk]o|[Ll]a|[Mm]y|[Nn]l|[Pp]t|[Rr]u|[Zz]h(-tw)?|[Ss]namei?)\s*\|(([^\{]|\{[^\{])*?)([^\{]\{)?\}\}',re.MULTILINE)
_TEMPLATE_YOMIGANA_PATTERN = re.compile(r'\{\{\s*読み仮名\s*\|([^|]*)\|[^}]*\}\}')
_TEMPLATE_PATTERN = re.compile(r'\{\{([^\{]|\{[^\{])*?([^\{]\{)?\}\}',re.MULTILINE)
_TABLE_PATTERN = re.compile(r'^\{\|.*?^\|\}',re.MULTILINE|re.DOTALL)
_BOLD_PATTERN = re.compile(r"'''(.+?)'''")
_ITALIC_PATTERN = re.compile(r"''(.+?)''")
_STRAY_BOLD_PATTERN = re.compile(r"'''")
_STRAY_ITALIC_PATTERN = re.compile(r"''")

def _get_content_wiki(url):
    http = httplib2.Http()
    content = http.request(url)[1];
    return _XmlParser().derive_wiki(content.decode('utf-8'))
    
def get_content_wiki(item_name):
    return _get_content_wiki('http:' + quote('//ja.wikipedia.org/wiki/特別:データ書き出し/') + quote(item_name, ''))

def get_random_content_wiki():
    http = httplib2.Http()
    http.follow_redirects = False
    random_url = 'https:' + quote('//ja.wikipedia.org/wiki/特別:おまかせ表示/')
    article_url = http.request(random_url)[0]['location'] # status:302 should be returned.
    item_name = unquote(article_url.split('/')[-1])
    return (item_name, get_content_wiki(item_name))

def get_article_url(item_name):
    return 'https://ja.wikipedia.org/wiki/' + quote(item_name)
    
def strip_wiki_notation(data):
    tmp = _strip_html_tags(data)
    tmp = _strip_head_pattern(tmp)
    tmp = _strip_link(tmp)
    tmp = _strip_template(tmp)
    tmp = _strip_table(tmp)
    tmp = _strip_italic_bold(tmp)
    tmp = _strip_new_line(tmp)
    return tmp

def _strip_html_tags(data):
    data = _HTML_SINGLE_REF_TAG_PATTERN.sub('', data)
    data = _HTML_REF_TAG_PATTERN.sub('', data)
    data = _HTML_GALLERY_TAG_PATTERN.sub('', data)
    return _HTML_TAG_PATTERN.sub('', data)    #簡易タグ除去

def _strip_head_pattern(data):
    return _LINE_HEAD_PATTERN.sub('', data)

def _strip_link(data):
    tmp = data
    while True:
        prev = tmp
        tmp = _WIKI_FILE_PATTERN.sub('', tmp)
        tmp = _WIKI_FILE_OPTION_PATTERN.sub('', tmp)
        tmp = _WIKI_LINK_PATTERN.sub(r'\1', tmp)
        tmp = _WIKI_LINK_ALIAS_PATTERN.sub(r'\1', tmp)
        if prev == tmp:
            break
    tmp = _OUTER_LINK_ALIAS_PATTERN.sub(r'\1', tmp)
    tmp = _OUTER_LINK_PATTERN.sub(r'\1', tmp)
    return tmp

def _strip_template(data):
    stripped = _TEMPLATE_LANG_PATTERN.sub(r'\2', data)
    stripped = _TEMPLATE_LANG_LABEL_PATTERN.sub(r'\3', stripped)
    stripped = _TEMPLATE_YOMIGANA_PATTERN.sub(r'\1', stripped)
    while True:
        raw = stripped
        stripped = _TEMPLATE_PATTERN.sub('', raw)
        if raw == stripped:
            break
    return stripped

def _strip_table(data):
    return _TABLE_PATTERN.sub('', data)

def _strip_italic_bold(data):
    tmp = _BOLD_PATTERN.sub(r'\1', data)
    tmp = _ITALIC_PATTERN.sub(r'\1', tmp)
    tmp = _STRAY_BOLD_PATTERN.sub(r'', tmp)
    tmp = _STRAY_ITALIC_PATTERN.sub(r'', tmp)
    return tmp

def _strip_new_line(data):
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
    def _start_element(self, name, attr):
        if name=='text':
            self.body_started = True

    #for xml parser call back
    def _end_element(self, name):
        if name=='text':
            self.body_started = False
            
    #for xml parser call back
    def _charData(self, data):
        if self.body_started:
            self.body+=data

    def derive_wiki(self, xml):
        self.body=''
        self.body_started = False
        parser = expat.ParserCreate()
        parser.buffer_text = True
        parser.StartElementHandler = self._start_element
        parser.EndElementHandler = self._end_element
        parser.CharacterDataHandler = self._charData
        parser.Parse(xml, True)
        return self.body
