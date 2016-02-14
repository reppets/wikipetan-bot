# coding: utf-8
import argparse
import random
import re
import sys

from datetime import datetime, timezone, timedelta
from string import Template

import twitter
import wikipedia
import yahoo
import setting

tweeter = twitter.Tweeter(
    setting.twitter_consumer_key,
    setting.twitter_consumer_secret,
    setting.twitter_user_key,
    setting.twitter_user_secret)

yahooMA = yahoo.YahooMA(setting.yahoo_app_key)

verbose = False

def main():
    
    parser = argparse.ArgumentParser()
    parser.add_argument('type',choices=['midnight','noon','random'])
    parser.add_argument('-p')
    parser.add_argument('-v', action='store_true')
    parser.add_argument('-t', action='store_true')
    args = parser.parse_args()

    random.seed()
    global verbose
    verbose = args.v
    if args.type =="random":
        content = randomTweet(args.p)
    elif args.type=="midnight":
        content = midnightTweet(args.p)
    elif args.type=="noon":
        content = noonTweet(args.p)
    elif args.type=="featured":
        content = featuredTweet(args.p)
    else:
        raise Exception('unexpected type')

    if args.t:
        print(content)
    else:
        tweeter.tweet(content)

def summarize(content):
    firstSentence = content.split('。',1)[0]
    analyzed = yahooMA.analyze(firstSentence)
    if verbose:
        print("YahooMA:"+str(analyzed))
    lastWord = analyzed[-1]
    skeleton = [word.surface for word in analyzed]
    done = False
    if lastWord.detail=='括弧閉':
        for word in reversed(analyzed[:-1]):
            if word.detail=='括弧開':
                done = True
                continue
            if done:
                lastWord = word
                break
    if lastWord.pos=='名詞':
        return firstSentence+'です。'
    elif lastWord.detail=='助動詞だ':
        return firstSentence[:-1]+'です。'
    elif lastWord.detail=='助動詞ある' and analyzed[-2]:
        return firstSentence[:-3]+'です。'
    elif lastWord.detail=='助動詞一段':
        return firstSentence[:-1]+'ます。'
    elif lastWord.detail=='助動詞する':
        return firstSentence[:-2]+'します。'
    elif lastWord.detail=='助動詞た':
        return firstSentence[:-1]+'ました。'
    elif lastWord.detail=='助数':
        return firstSentence+'です。'
    
    return firstSentence



def summarizeToday(event, year=None):
    paren_match = re.search(r'[(（][^(]*[)）]$',event)
    if paren_match:
        event = event[:paren_match.start()]
    wordlist = yahooMA.analyze(event)
    if verbose:
        print("YahooMA:"+str(wordlist))
    lastDetail = wordlist[-1].detail
    skeleton = None
    if lastDetail=='名サ他':
        skeleton = [word.surface for word in wordlist]
        if wordlist[-2].pos == '名詞':
            skeleton.insert(-1, 'が')
            skeleton.append('された日です。')
        for word in reversed(wordlist[:-1]):
            if word.detail == '格助詞':
                if word.surface in ['を','に','へ']:
                    skeleton.append('した日です。')
                    break
                elif word.surface=='が':
                    skeleton.append('された日です。')
                    break
    elif lastDetail=='名サ自':
        skeleton = [word.surface for word in wordlist]
        skeleton.append('した日です。')
        if len(wordlist) >= 2 and wordlist[-2].pos=='名詞':
            skeleton.insert(-2,'が')
    elif lastDetail=='名詞' or (wordlist[-1].pos=='動詞' and wordlist[-1].conjugation=='連用形'):
        skeleton = [word.surface for word in wordlist]
        if year:
            skeleton.append('があった日です。')
        else:
            skeleton.append('です!')
    elif wordlist[-1].pos=='動詞' and wordlist[-1].conjugation=='基本形':
        skeleton = [word.surface for word in wordlist]
        if wordlist[-1].detail=='一段':
            skeleton[-1] = skeleton[-1][:-1]+'た日です。'
        elif wordlist[-1].detail[1]=='五':
            #五段活用
            gyou = wordlist[-1].detail[0]
            if wordlist[-1].detail=='ワ五う':
                skeleton[-1] = skeleton[-1][:-1]+'うた日です。'
            elif wordlist[-1].detail=='カ五いく' or gyou=='タ' or gyou=='ラ' or gyou=='ワ':
                skeleton[-1] = skeleton[-1][:-1]+'った日です。'
            elif gyou=='ガ' or gyou=='カ':
                skeleton[-1] = skeleton[-1][:-1]+'いた日です。'
            elif gyou=='サ':
                skeleton[-1] = skeleton[-1][:-1]+'した日です。'
            else:
                skeleton[-1] = skeleton[-1][:-1]+'んだ日です。'

    if skeleton:
        event = ''.join(skeleton)
    
    if paren_match:
        event = event + paren_match.group(0)

    return event

def randomTweet(param):
    if param:
        item, content = (param, wikipedia.getContentWiki(param))
    else:
        item, content = wikipedia.getRandomContentWiki()
    return Template('「${item}」 ${url} ${summary}' ).substitute({
        'item':item,
        'url':wikipedia.getArticleUrl(item),
        'summary':summarize(wikipedia.stripWikiNotation(content))})

def midnightTweet(param):
    if param and '/' in param:
        splitted = param.split('/')
        month = splitted[0]
        day = splitted[1].split('#')[0]
    else:
        now = datetime.now(timezone(timedelta(hours=9))) # JST current time
        month = str(now.month)
        day = str(now.day)
    month_day_str = month+'月'+day+'日'
    content = wikipedia.getContentWiki('Wikipedia:今日は何の日_'+month+'月')
    content = content[re.search(r'^==\s*\[\['+month_day_str+'\]\]\s*==$', content, re.MULTILINE).end():]
    nextHeader = re.search(r'^==[^=]', content, re.MULTILINE)
    if nextHeader:
        content = content[:nextHeader.start()]
    items = re.findall(r'^\*.*$', content, re.MULTILINE)
    choice = wikipedia.stripWikiNotation(items[random.randint(0, len(items)-1) if param and '#' not in param else int(param.split('#')[1])])
    year_match = re.search(r'(\(|（)([0-9０-９]*?年).*(\)|）)\s*$',choice)
    if year_match:
        year = year_match.group(2)
        event = choice[:year_match.start()]
    else:
        year = None
        event = choice
    
    summary = summarizeToday(event, year)
    return Template('よるほー。明けて本日${date}は、${year}${summary} ${url}' ).substitute({
        'date':month_day_str,
        'year':year+'に' if year else '',
        'url':wikipedia.getArticleUrl(month_day_str),
        'summary':summary})

def noonTweet(param):
    wikiLinkPattern = re.compile(r'\[\[(.*?)\]\]')

    featuredWiki = wikipedia.getContentWiki('Wikipedia:秀逸な記事')
    articles = wikiLinkPattern.findall(featuredWiki[featuredWiki.find('== 秀逸な記事 =='):featuredWiki.rfind('== 関連項目 ==')])
    good_beginning = len(articles)
    goodWiki = wikipedia.getContentWiki('Wikipedia:良質な記事/リスト')
    articles.extend(wikiLinkPattern.findall(goodWiki[goodWiki.find('=== 総記 ==='):]))
    if param:
        i = int(param.split('#')[1])
    else:
        i = random.randint(0, len(articles)-1)

    item = articles[i]
    return Template('お昼ですよー。${featuredOrGood}な記事を紹介しますね。「${item}」 ${url} ${summary}').substitute({
        'featuredOrGood': '秀逸' if i<good_beginning else '良質',
        'item': item,
        'url': wikipedia.getArticleUrl(item),
        'summary': summarize(wikipedia.stripWikiNotation(wikipedia.getContentWiki(item)))})
        
if __name__=="__main__":
    main()
