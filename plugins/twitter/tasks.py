import urllib2,json,base64,datetime
from django.conf import settings
from celery.task.base import Task
from kral.models import *
from kral.views import push_data

class Twitter(Task):
    def run(self, querys, **kwargs):
        logger = self.get_logger(**kwargs)
        self.query_post = str("track="+",".join([q.text for q in querys]))
        self.request = urllib2.Request('http://stream.twitter.com/1/statuses/filter.json',self.query_post)
        self.auth = base64.b64encode('%s:%s' % (settings.TWITTER_USER, settings.TWITTER_PASS))
        self.request.add_header('Authorization', "basic %s" % self.auth)
        try:
            self.stream = urllib2.urlopen(self.request)
        except Exception,e:
            if e.code == 420:
                logger.info("Twitter connection closed")
            else:
                logger.error("Invalid/null response from server: %s" % (e))
            return False
        for tweet in self.stream:
            ProcessTweet.delay(tweet, querys)

class ProcessTweet(Task):
    def run(self, data, querys, **kwargs):
        logger = self.get_logger(**kwargs)
        content = json.loads(data)
        time_format = "%a %b %d %H:%M:%S +0000 %Y"
        if content["user"].get('id_str', None):
            post_info = { 
                'service' : 'twitter',
                'user' : {
                    'id' : content['user']['id_str'],
                    'utc' : content['user']['utc_offset'],
                    'name' : content['user']['screen_name'],
                    'description' : content['user']['description'],
                    'location' : content['user']['location'],
                    'avatar' : content['user']['profile_image_url'],
                    'subscribers': content['user']['followers_count'],
                    'subscriptions': content['user']['friends_count'],
                    'website': content['user']['url'],
                    'language' : content['user']['lang'],
                },
                'id' : content['id'],
                'application': content['source'],
                'date' : str(datetime.datetime.strptime(content['created_at'],time_format)),
                'text' : content['text'],
                'geo' : content['coordinates'],
            }
            for query in [q.text.lower() for q in querys]:
                if query in content['text'].lower():
                    push_data(post_info, queue=query)

#vim: ai ts=5 sts=4 et sw=4
