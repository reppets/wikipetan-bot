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

yahoo_ma = yahoo.YahooMA(setting.yahoo_app_key)

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
        content = random_tweet(args.p)
    elif args.type=="midnight":
        content = midnight_tweet(args.p)
    elif args.type=="noon":
        content = noon_tweet(args.p)
    else:
        raise Exception('unexpected type')

    if args.t:
        print(content)
    else:
        tweeter.tweet(content)

def summarize(content):
    first_sentence = content.split('。',1)[0]
    analyzed = yahoo_ma.analyze(first_sentence)
    if verbose:
        print("YahooMA:"+str(analyzed))
    last_word = analyzed[-1]
    skeleton = [word.surface for word in analyzed]
    done = False
    if last_word.detail=='括弧閉':
        for word in reversed(analyzed[:-1]):
            if word.detail=='括弧開':
                done = True
                continue
            if done:
                last_word = word
                break
    if last_word.pos=='名詞':
        return first_sentence+'です。'
    elif last_word.detail=='助動詞だ':
        return first_sentence[:-1]+'です。'
    elif last_word.detail=='助動詞ある' and analyzed[-2]:
        return first_sentence[:-3]+'です。'
    elif last_word.detail=='助動詞一段':
        return first_sentence[:-1]+'ます。'
    elif last_word.detail=='助動詞する':
        return first_sentence[:-2]+'します。'
    elif last_word.detail=='助動詞た':
        return first_sentence[:-1]+'ました。'
    elif last_word.detail=='助数':
        return first_sentence+'です。'
    elif last_word.pos=='動詞' and last_word.conjugation=='基本形':
        if last_word.detail=='ラ五ある':
            return first_sentence[:-2]+'す。'
        if last_word.detail=='ワ五':
            return first_sentence[:-1]+'います。'
    elif last_word.pos=='接尾辞':
        return first_sentence+'です。'
    
    return first_sentence



def summarize_today(event, year=None):
    paren_match = re.search(r'[(（][^(]*[)）]$',event)
    if paren_match:
        event = event[:paren_match.start()]
    word_list = yahoo_ma.analyze(event)
    if verbose:
        print("YahooMA:"+str(word_list))
    last_detail = word_list[-1].detail
    skeleton = None
    if last_detail=='名サ他':
        skeleton = [word.surface for word in word_list]
        if word_list[-2].pos == '名詞':
            skeleton.insert(-1, 'が')
            skeleton.append('された日です。')
        for word in reversed(word_list[:-1]):
            if word.detail == '格助詞':
                if word.surface in ['を','に','へ']:
                    skeleton.append('した日です。')
                    break
                elif word.surface=='が':
                    skeleton.append('された日です。')
                    break
    elif last_detail=='名サ自':
        skeleton = [word.surface for word in word_list]
        skeleton.append('した日です。')
        if len(word_list) >= 2 and word_list[-2].pos=='名詞':
            skeleton.insert(-2,'が')
    elif last_detail=='名詞' or (word_list[-1].pos=='動詞' and word_list[-1].conjugation=='連用形'):
        skeleton = [word.surface for word in word_list]
        if year:
            skeleton.append('があった日です。')
        else:
            skeleton.append('です!')
    elif word_list[-1].pos=='動詞' and word_list[-1].conjugation=='基本形':
        skeleton = [word.surface for word in word_list]
        if word_list[-1].detail=='一段':
            skeleton[-1] = skeleton[-1][:-1]+'た日です。'
        elif word_list[-1].detail[1]=='五':
            #五段活用
            gyou = word_list[-1].detail[0]
            if word_list[-1].detail=='ワ五う':
                skeleton[-1] = skeleton[-1][:-1]+'うた日です。'
            elif word_list[-1].detail=='カ五いく' or gyou=='タ' or gyou=='ラ' or gyou=='ワ':
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

def random_tweet(param):
    if param:
        item, content = (param, wikipedia.get_content_wiki(param))
    else:
        item, content = wikipedia.get_random_content_wiki()
    return Template('「${item}」 ${url} ${summary}' ).substitute({
        'item':item,
        'url':wikipedia.get_article_url(item),
        'summary':summarize(wikipedia.strip_wiki_notation(content))})

def midnight_tweet(param):
    if param and '/' in param:
        splitted = param.split('/')
        month = splitted[0]
        day = splitted[1].split('#')[0]
    else:
        now = datetime.now(timezone(timedelta(hours=9))) # JST current time
        month = str(now.month)
        day = str(now.day)
    month_day_str = month+'月'+day+'日'
    content = wikipedia.get_content_wiki('Wikipedia:今日は何の日_'+month+'月')
    content = content[re.search(r'^==\s*\[\['+month_day_str+'\]\]\s*==$', content, re.MULTILINE).end():]
    next_header = re.search(r'^==[^=]', content, re.MULTILINE)
    if next_header:
        content = content[:next_header.start()]
    items = re.findall(r'^\*.*$', content, re.MULTILINE)
    choice = wikipedia.strip_wiki_notation(items[random.randint(0, len(items)-1) if not param or '#' not in param else int(param.split('#')[1])])
    year_match = re.search(r'(\(|（)([0-9０-９]*?年).*(\)|）)\s*$',choice)
    if year_match:
        year = year_match.group(2)
        event = choice[:year_match.start()]
    else:
        year = None
        event = choice
    
    summary = summarize_today(event, year)
    return Template('よるほー。明けて本日${date}は、${year}${summary} ${url}' ).substitute({
        'date':month_day_str,
        'year':year+'に' if year else '',
        'url':wikipedia.get_article_url(month_day_str),
        'summary':summary})

def noon_tweet(param):
    wiki_link_pattern = re.compile(r'\[\[(.*?)\]\]')

    featured_wiki = wikipedia.get_content_wiki('Wikipedia:秀逸な記事')
    articles = wiki_link_pattern.findall(featured_wiki[featured_wiki.find('== 秀逸な記事 =='):featured_wiki.rfind('== 関連項目 ==')])
    good_beginning = len(articles)
    good_wiki = wikipedia.get_content_wiki('Wikipedia:良質な記事/リスト')
    articles.extend(wiki_link_pattern.findall(good_wiki[good_wiki.find('=== 総記 ==='):]))
    if param:
        i = int(param.split('#')[1])
    else:
        i = random.randint(0, len(articles)-1)

    item = articles[i]
    return Template('お昼ですよー。${featured_or_good}な記事を紹介しますね。「${item}」 ${url} ${summary}').substitute({
        'featured_or_good': '秀逸' if i<good_beginning else '良質',
        'item': item,
        'url': wikipedia.get_article_url(item),
        'summary': summarize(wikipedia.strip_wiki_notation(wikipedia.get_content_wiki(item)))})
        
if __name__=="__main__":
    main()
