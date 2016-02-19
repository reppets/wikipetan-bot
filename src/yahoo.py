# coding: utf-8

import httplib2
import re
from urllib.parse import urlencode
from xml.parsers import expat

class YahooMA(object):

    def __init__(self, app_key):
        self.app_key = app_key

    def analyze(self, string):
        http = httplib2.Http()
        xml_parser = _YahooMAParser()
        options = {'appid': self.app_key, 'sentence': string, 'response': 'feature', 'results': 'ma'}
        headers, body = http.request('http://jlp.yahooapis.jp/MAService/V1/parse?'+urlencode(options))
        return xml_parser.get_word_list(body.decode('utf-8'))

class _YahooMAParser(object):

    def __init__(self):
        self._clear()

    def _clear(self):
        self.result = []
        self.currentWord = None
        self.currentText = ''
        self.currentTag = None


    #for xml parser call back
    def _start_element(self, name, attr):
        if name=='word':
            self.currentWord = ''
        self.currentTag = name

    #for xml parser call back
    def _end_element(self, name):
        if name=='word':
            word = Word()
            word.set_data(self.currentWord)  #TODO currentWord>currentWordFeature
            self.result.append(word)
            self.currentWord = None
            
    #for xml parser call back
    def _char_data(self, data):
        if self.currentWord!=None:
            if self.currentTag=='feature':
                self.currentWord += data
        return

    def get_word_list(self, xml):
        self.body=''
        parser = expat.ParserCreate('utf-8')
        parser.buffer_text = True
        parser.StartElementHandler = self._start_element
        parser.EndElementHandler = self._end_element
        parser.CharacterDataHandler = self._char_data
        parser.Parse(xml, True)
        ret = self.result
        self._clear()
        return ret


class Word(object):
    comma_pattern = re.compile(',')
    
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

    def set_data(self, feature):
        features = Word.comma_pattern.split(feature)
        self.pos = features[0]
        self.detail = features[1]
        self.conjugation = features[2]
        self.surface = features[3]
        self.reading = features[4]
        self.baseform = features[5]
        return
