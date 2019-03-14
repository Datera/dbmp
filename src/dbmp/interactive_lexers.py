# -*- coding: utf-8 -*-
from __future__ import print_function, division
# Can't import unicode_literals because it breaks pygments for some reason
import re

from prompt_toolkit.styles import Style, merge_styles
from pygments.lexer import RegexLexer, words
from pygments.token import Text, Name

VOLS = {"volumes", "volume", "v", "vol", "vols"}
VOLS_D = {"volumes-detail", "volume-detail", "vd", "vol-d", "vols-d",
          "volumes_detail", "volume-detail", "vol_d", "vols_d"}
TMPS = {"template", "templates", "t", "tmp", "tmpl"}
TMPS_D = {"template-detail", "templates-detail", "td", "tmp-d", "tmpl-d",
          "template_detail", "templates_detail", "tmp_d", "tmpl_d"}
MOUNTS = {"mount", "mounts", "m", "mnt"}
ALERTS = {"alerts", "alert", "a"}
EVENTS_U = {"events-user", "events_user", "eu", "event_user", "event-user"}
EVENTS_S = {"events-system", "events_system", "es", "event_system",
            "event-system"}
EVENTS_ID = {"events-id", "events_id", "ei", "eid", "event-id", "events_id"}
PP = {"placement_policies", "placement_policy", "pp", "placement", "pl",
      "placement-policies", "placement-policy"}
MP = {"media_policies", "media_policy", "mp", "media", "md", "media-policies",
      "media-policy"}

COLORS = ["green", "red", "blue", "yellow",
          "purple", "pink", "cyan", "magenta",
          "brown", "grey", "orange"]


dbmp_style = merge_styles([
    # style_from_pygments_cls(TangoStyle),
    Style.from_dict({
        'pygments.name.attribute': 'green bold',
        'pygments.name.builtin': 'red bold',
        'pygments.name.class': 'blue bold',
        'pygments.name.constant': 'yellow bold',
        'pygments.name.decorator': 'purple bold',
        'pygments.name.entity': 'pink bold',
        'pygments.name.exception': 'cyan bold',
        'pygments.name.function': 'magenta bold',
        'pygments.name.property': 'brown bold',
        'pygments.name.label': 'grey bold',
        'pygments.name.namespace': 'orange bold',
    })
])


class WelcomeLexer(RegexLexer):
    flags = re.MULTILINE | re.UNICODE
    tokens = {
        'root': [
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),  # line continuations
            (words(('p',), prefix=r'\b', suffix=r'\b'), Name.Attribute),
            (words(('c',), prefix=r'\b', suffix=r'\b'), Name.Builtin),
            (words(('l',), prefix=r'\b', suffix=r'\b'), Name.Class),
        ]
    }


class TypeChooserLexer(RegexLexer):
    flags = re.MULTILINE | re.UNICODE
    tokens = {
        'root': [
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),  # line continuations
            (words(tuple(VOLS), prefix=r'\b', suffix=r'\b'), Name.Attribute),
            (words(tuple(VOLS_D), prefix=r'\b', suffix=r'\b'), Name.Builtin),
            (words(tuple(TMPS), prefix=r'\b', suffix=r'\b'), Name.Class),
            (words(tuple(TMPS_D), prefix=r'\b', suffix=r'\b'), Name.Constant),
            (words(tuple(MOUNTS), prefix=r'\b', suffix=r'\b'), Name.Decorator),
            (words(tuple(ALERTS), prefix=r'\b', suffix=r'\b'), Name.Entity),
            (words(tuple(EVENTS_U), prefix=r'\b', suffix=r'\b'),
                Name.Exception),
            (words(tuple(EVENTS_S), prefix=r'\b', suffix=r'\b'),
                Name.Function),
            (words(tuple(PP), prefix=r'\b', suffix=r'\b'), Name.Property),
            (words(tuple(MP), prefix=r'\b', suffix=r'\b'), Name.Label),
        ]
    }


class EditLexer(RegexLexer):
    flags = re.MULTILINE | re.UNICODE
    tokens = {
        'root': [
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),  # line continuations
            (r'.+: ', Name.Attribute),
        ]
    }
