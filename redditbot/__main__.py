import argparse
import asyncio
import yaml

from kombu.utils.debug import setup_logging

import redditbot

parser = argparse.ArgumentParser('parser for redditbot')

parser.add_argument('--worker', action='store_true', help='Run worker process')
parser.add_argument(
    '--workers', '-w', type=int, default=1,
    help='Number of workers to run'
)
parser.add_argument('--client', action='store_true', help='Run client process')
parser.add_argument(
    '--interval', '-i', type=int, default=30,
    help='Interval to check reddit at'
)
parser.add_argument(
    '--config', '-c', type=str, default='/etc/redditbot.yml',
    help='Path to YAML config file'
)
parser.add_argument(
    '--log', '-l', type=str, default='info',
    choices=('debug', 'info', 'warning'),
    help='Logging Level'
)

args = parser.parse_args()
setup_logging(loglevel=args.log.upper(), loggers=[''])

loop = asyncio.get_event_loop()
tasks = []

with open(args.config, 'r') as ymlfile:
    redditbot.config = yaml.load(ymlfile)

if args.client is True:
    from redditbot.client import UpdateSubreddit
    for subreddit in redditbot.config['subreddits'].keys():
        tasks.append(UpdateSubreddit(subreddit, args.interval))

if args.worker is True:
    from redditbot import bot  # noqa
    from redditbot import worker
    connection = 'redis://localhost:6379/'
    for w in [worker.Worker(connection, redditbot.config).run] * args.workers:
        tasks.append(asyncio.ensure_future(loop.run_in_executor(None, w)))

loop.run_forever()
