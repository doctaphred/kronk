import slackclient
import config

import pp


class Singleton(type):

    def __init__(self, *args, **kwargs):
        self.__instance = None
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        if self.__instance is None:
            self.__instance = super().__call__(*args, **kwargs)
        return self.__instance


class Kronk(metaclass=Singleton):

    def __init__(self, sc=None):
        sc = slackclient.SlackClient(config.token)
        print('Kronk is live:')
        pp(sc.auth)
        self.sc = sc
        self.channel = sc.channel(config.channel_name)
        self.event_stream = sc.monitor('channels', self.channel['id'])
        self.own_mention = '<@{}>'.format(sc.auth['user_id'])

    def say(self, *args, **kwargs):
        result = self.sc.post(self.channel['id'], *args, **kwargs)
        if not result['ok']:
            print('ERROR:', result)

    def handle_events(self):
        print('Checking for new events...')
        for event in next(self.event_stream):
            pp(event)
            self.handle(event)

    def is_own(self, event):
        return event.get('user') == self.sc.auth['user_id']

    def handle(self, event):
        if event['type'] == 'message':
            user = self.sc.look_up_user(event['user'])

            subtype = event.get('subtype')
            if subtype is None and not self.is_own(event):
                if event['text'].startswith(self.own_mention):
                    self.say("Can I help you, {}?".format(user['profile']['first_name']))
                else:
                    words = event['text'].split()
                    if self.own_mention in words:
                        self.say("I can hear you, but I have no idea what you're saying.")
                    elif 'Kronk' in words:
                        self.say('More... broccoli?')
            elif subtype == 'channel_join':
                if self.is_own(event):
                    self.say("Howdy folks!")
                else:
                    self.say("Hey there {}!".format(user['profile']['first_name']))
            elif subtype == 'channel_leave':
                self.say("Was it something I said?")

        else:
            self.say("Sorry, I don't know how to deal with {} events".format(event['type']))
