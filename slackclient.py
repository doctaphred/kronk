import time

import requests


class SlackClient(object):

    base_url = 'https://slack.com/api/'

    def __init__(self, token):
        self.token = token
        self.auth = self.call('auth.test')
        self.cache = {
            'users.list': None,
            'users.info': {},
            }

    def call(self, method, params=None, **kwarg_params):
        stuff = {'token': self.token}
        if params:
            stuff.update(params)
        stuff.update(kwarg_params)
        return requests.get(self. base_url + method, params=stuff).json()

    def post(self, to, message):
        return self.call('chat.postMessage', channel=to, text=message, as_user=True)

    def monitor(self, thing, id):
        def stream(timestamp):
            while True:
                result = self.call(
                    thing + '.history',
                    channel=id,
                    oldest=timestamp,
                    )
                if not result['ok']:
                    raise ValueError(result)
                new_messages = result['messages']
                if new_messages:
                    timestamp = new_messages[0]['ts']
                yield new_messages
        return stream(time.time())

    def monitor_channel_named(self, name):
        return self.monitor('channels', self.channel(name)['id'])

    def monitor_dms_with(self, username):
        return self.monitor('im', self.dm_channel(username)['id'])

    def list_users(self):
        if 'users.list' not in self.cache:
            self.cache['users.list'] = self.call('users.list')
        return self.cache['users.list']['members']

    def list_channels(self):
        return self.call('channels.list')['channels']

    def list_dm_channels(self):
        return self.call('im.list')['ims']

    def look_up_user(self, user_id):
        user_info = self.cache['users.info']
        if user_id not in user_info:
            user_info[user_id] = self.call('users.info', user=user_id)['user']
        return user_info[user_id]

    def user(self, username):
        return next(user for user in self.list_users()
                    if user['name'] == username)

    def channel(self, name):
        return next(channel for channel in self.list_channels()
                    if channel['name'] == name)

    def dm_channel(self, username):
        user_id = self.user(username)['id']
        return next(dm_channel for dm_channel in self.list_dm_channels()
                    if dm_channel['user'] == user_id)
