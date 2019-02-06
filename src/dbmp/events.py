# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division

import json

import dfs_sdk


def get_alerts(api):
    return api.alerts.list()


def get_events(api, user):
    if user.lower() == "system":
        return api.events.system.list()
    elif user.lower() == "user":
        return prettify_events(api.events.user.list())
    else:
        try:
            return prettify_events([api.events.get(user)])
        except dfs_sdk.exceptions.ApiNotFoundError:
            print("No event found with uuid:", user)
            return []


def prettify_events(events):
    # Just prettify them a bit
    for event in events:
        for k, v in event._data.items():
            try:
                event._data[k] = json.loads(v)
            except Exception as e:
                pass
    return events
