# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division

import json

import dfs_sdk


def get_alerts(api):
    return api.alerts.list()


def list_alerts(api):
    for alert in get_alerts(api):
        print(json.dumps(json.loads(str(alert)), indent=4))


def clear_alerts(api):
    for alert in get_alerts(api):
        alert.set(cleared=True)


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
            except Exception:
                pass
    return events


def list_events(api, user):
    events = get_events(api, user)
    for event in events:
        print(json.dumps(json.loads(str(event)), indent=4))
