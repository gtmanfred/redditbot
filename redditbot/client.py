from kombu.pools import producers
from kombu import Connection
from redis import StrictRedis
from praw import Reddit
import asyncio
import logging

from redditbot.queues import task_exchange

log = logging.getLogger(__name__)


class UpdateSubreddit(dict):
    def __init__(self, subreddit, interval=None):
        self._conn = None
        self._rconn = None
        self._loop = None
        self['place_holder'] = None
        self['recent_posts'] = []
        if interval is not None:
            self.interval = interval
            self._set()
        else:
            self.interval = 10
        self.subreddit = subreddit

    def _set(self):
        self._handler = self.loop.call_later(self.interval, self._run)

    def _run(self):
        self.process_new_posts()
        self._set()

    @property
    def loop(self):
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        return self._loop

    @property
    def rconn(self):
        if self._rconn is None:
            self._rconn = StrictRedis('localhost', 6379)
        return self._rconn

    @property
    def conn(self):
        if self._conn is None:
            self._conn = Connection('redis://localhost:6379//')
        return self._conn

    @property
    def subreddit(self):
        return self.get('subreddit')

    @subreddit.setter
    def subreddit(self, value):
        reddit = Reddit('gtmanfred/1.0', cache_timeout=self.interval)
        self['subreddit'] = reddit.get_subreddit(value)

    @property
    def place_holder(self):
        if self.get('place_holder', None) is None:
            self['place_holder'] = self.rconn.get('place_holder:{0}'.format(self.subreddit.display_name))
            if isinstance(self['place_holder'], bytes):
                self['place_holder'] = self['place_holder'].decode('utf-8')
        return self['place_holder']

    @place_holder.setter
    def place_holder(self, value):
        if value == self['place_holder']:
            log.debug('place_holder:{0} already set'.format(self.subreddit.display_name, value))
            return
        log.debug('Setting place_holder:{0} {1}'.format(self.subreddit.display_name, value))
        self['place_holder'] = value
        self.rconn.set('place_holder:{0}'.format(self.subreddit.display_name), value)

    @property
    def recent_posts(self):
        if not self['recent_posts']:
            self['recent_posts'] = self.rconn.lrange('recent_posts:{0}'.format(self.subreddit.display_name), 0, -1)
            if isinstance(self['recent_posts'], list):
                self['recent_posts'] = list(map(lambda x: x.decode('utf-8'), self['recent_posts']))
        return self['recent_posts']
        
    @recent_posts.setter
    def recent_posts(self, value):
        if not value:
            return
        self['recent_posts'].extend(value)
        if len(self['recent_posts']) > 25:
            self['recent_posts'] = self['recent_posts'][-25:]
        self.rconn.lpush('recent_posts:{0}'.format(self.subreddit.display_name), *value)
        self.rconn.ltrim('recent_posts:{0}'.format(self.subreddit.display_name), 0, 24)

    def send_as_task(self, post):
        payload = {'post': post}

        with producers[self.conn].acquire(block=True) as producer:
            producer.publish(payload,
                             serializer='pickle',
                             compression='bzip2',
                             exchange=task_exchange,
                             declare=[task_exchange],
                             routing_key='posts')

    def process_new_posts(self):
        first_post = None
        recent_posts = []
        for post in self.subreddit.get_new(place_holder=self.place_holder):
            if first_post is None:
                first_post = post.id
            if post.id == self.place_holder or post.id in self.recent_posts:
                continue
            log.debug('New post for {0}: {1}'.format(self.subreddit.display_name, post.id))
            recent_posts.append(post.id)
            self.send_as_task(post)
        self.recent_posts = recent_posts
        self.place_holder = first_post

if __name__ == '__main__':
    u = UpdateSubreddit('linux')
    u.process_new_posts()
