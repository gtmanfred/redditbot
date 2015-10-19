from kombu.connection import BrokerConnection
from kombu.mixins import ConsumerMixin
from blinker import signal
import logging

from redditbot.queues import task_queues

logger = logging.getLogger(__name__)


class Worker(ConsumerMixin):
    def __init__(self, connection, config):
        self.connection = BrokerConnection(connection)
        self.config = config

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=task_queues,
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task])]

    def process_task(self, body, message):
        post = body['post']
        logger.info('Got task: %s', post.id)
        try:
            logger.info(
                'New Post for %s: %s',
                post.subreddit.display_name, str(post)
            )
            for channel in \
                    self.config['subreddits'][post.subreddit.display_name]:
                signal('send-message').send(channel, message=post)
            message.ack()
        except Exception as exc:
            logger.error('Exception Raised: %r', exc)
