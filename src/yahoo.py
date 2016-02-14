# coding: utf-8

import httplib2
import re
from urllib.parse import urlencode
from xml.parsers import expat

class YahooMA(object):

    def __init__(self, appKey):
        self.appKey = appKey

    def analyze(self, string):
        http = httplib2.Http()
        xmlParser = _YahooMAParser()
        options = {'appid': self.appKey, 'sentence': string, 'response': 'feature', 'results': 'ma'}
        headers, body = http.request('http://jlp.yahooapis.jp/MAService/V1/parse?'+urlencode(options))
        return xmlParser.getWordList(body.decode('utf-8'))

class _YahooMAParser(object):

    def __init__(self):
        self._clear()

    def _clear(self):
        self.result = []
        self.currentWord = None
        self.currentText = ''
        self.currentTag = None


    #for xml parser call back
    def _startElement(self, name, attr):
        if name=='word':
            self.currentWord = ''
        self.currentTag = name

    #for xml parser call back
    def _endElement(self, name):
        if name=='word':
            word = Word()
            word.setData(self.currentWord)  #TODO currentWord>currentWordFeature
            self.result.append(word)
            self.currentWord = None
            
    #for xml parser call back
    def _charData(self, data):
        if self.currentWord!=None:
            if self.currentTag=='feature':
                self.currentWord += data
        return

    def getWordList(self, xml):
        self.body=''
        parser = expat.ParserCreate('utf-8')
        parser.buffer_text = True
        parser.StartElementHandler = self._startElement
        parser.EndElementHandler = self._endElement
        parser.CharacterDataHandler = self._charData
        parser.Parse(xml, True)
        ret = self.result
        self._clear()
        return ret


class Word(object):
    _commaSplitPattern = re.compile(',')
    
    def __init__(self):
        self.pos = ''          #品詞
        self.detail = ''       #品詞の詳細
        self.conjugation = ''  #活用
        self.surface = ''      #文中での表記
        self.reading = ''      #読み
        self.baseform = ''     #基本形
        return

    def __repr__(self):
        return '('+'/'.join([self.pos, self.detail, self.conjugation, self.surface, self.reading, self.baseform])+')'

    def clean(self):
        #たぶん'*'が入るのはconjugationだけなんだけど
        self.pos=None if self.pos=='*' else self.pos
        self.detail=None if self.detail=='*' else self.detail
        self.conjugation=None if self.conjugation=='*' else self.conjugation
        self.surface=None if self.surface=='*' else self.surface
        self.reading=None if self.reading=='*' else self.reading
        self.baseform=None if self.baseform=='*' else self.baseform
        return

    def setData(self, feature):
        features = Word._commaSplitPattern.split(feature)
        self.pos = features[0]
        self.detail = features[1]
        self.conjugation = features[2]
        self.surface = features[3]
        self.reading = features[4]
        self.baseform = features[5]
        return
