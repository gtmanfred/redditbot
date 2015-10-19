import itertools
import asyncio
from asyncirc import irc
from blinker import signal
import asyncirc.plugins.sasl

from redditbot import config

if hasattr(irc.asyncio, 'async') and hasattr(asyncio, 'ensure_future'):
    # remove deprecation warnings
    irc.asyncio.async = asyncio.ensure_future

conn = irc.connect(config['server'], 6697, use_ssl=True)
conn.register(config['botnick'], config['botnick'], config['botnick'])
if config.get('sasl', False) is True:
    asyncirc.plugins.sasl.auth(conn, config['username'], config['password'])
command_character_registry = []


def register_command_character(c):
    command_character_registry.append(c)


def handle_send_messages(channel, message):
    conn.say(
        channel, '{0} https://redd.it/{1}'.format(str(message), message.id)
    )

signal("send-message").connect(handle_send_messages)
signal("plugin-registered").send("asyncirc.plugins.custom")


@conn.on("sasl-auth-complete")
def autojoin_channels(message):
    print('JOINING')
    print(config['subreddits'])
    for channel in itertools.chain(config['subreddits'].values()):
        conn.join(channel)
