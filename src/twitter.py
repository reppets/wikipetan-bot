# coding: utf-8
from urllib.parse import urlencode
from oauth2 import Client,Consumer,Token

class Tweeter(object):
    def __init__(self, consumer_key, consumer_secret, user_key, user_secret):
        self._consumer = Consumer(consumer_key, consumer_secret)
        self._token = Token(user_key, user_secret)
        self._client = Client(self._consumer, self._token)
    
    def tweet(self, content):
        return self._client.request('https://api.twitter.com/1.1/statuses/update.json', 'POST', urlencode({'status': content}))
