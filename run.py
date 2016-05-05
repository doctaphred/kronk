#!/usr/bin/env python3
import time
from importlib import import_module

import config
import kronk
from filewatch import autoreload

autoreload_modules = [
    'config',
    'kronk',
    'slackclient',
    ]

for name in autoreload_modules:
    autoreload(import_module(name))

while True:
    try:
        kronk.Kronk().handle_events()
    except Exception as e:
        print('{e.__class__}: {e}'.format(e=e))
        print('Retrying in 3 seconds...')
        time.sleep(3)
    else:
        time.sleep(config.delay)
