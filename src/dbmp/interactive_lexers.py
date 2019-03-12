import re

from prompt_toolkit.styles import Style, merge_styles
from pygments.lexer import RegexLexer, words
from pygments.token import Text, Keyword

VOLS = {"volumes", "volume", "v", "vol", "vols"}
PP = {"placement_policies", "placement_policy", "pp", "placement", "pl",
      "placement-policies", "placement-policy"}
MP = {"media_policies", "media_policy", "mp", "media", "md", "media-policies",
      "media-policy"}

dbmp_style = merge_styles([
    # style_from_pygments_cls(TangoStyle),
    Style.from_dict({
        'pygments.keyword.namespace': 'green bold',
        'pygments.keyword.constant': 'red bold',
        'pygments.keyword.type': 'blue bold',
    })
])


class WelcomeLexer(RegexLexer):
    flags = re.MULTILINE | re.UNICODE
    tokens = {
        'root': [
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),  # line continuations
            (words(('p',), suffix=r'\b'), Keyword.Namespace),
            (words(('c',), suffix=r'\b'), Keyword.Constant)
        ]
    }


class TypeChooserLexer(RegexLexer):
    flags = re.MULTILINE | re.UNICODE
    tokens = {
        'root': [
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),  # line continuations
            (words(tuple(VOLS), suffix=r'\b'), Keyword.Constant),
            (words(tuple(PP), suffix=r'\b'), Keyword.Namespace),
            (words(tuple(MP), suffix=r'\b'), Keyword.Type)
        ]
    }


class EditLexer(RegexLexer):
    flags = re.MULTILINE | re.UNICODE
    tokens = {
        'root': [
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),  # line continuations
            (r'.+: ', Keyword.Namespace),
        ]
    }
