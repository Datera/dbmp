# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division

import argparse
import io
import os
import re
import subprocess
import sys

import prompt_toolkit as pt
# from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding.bindings.named_commands import get_by_name
from prompt_toolkit.key_binding.bindings.completion import generate_completions

from dbmp.interactive_lexers import TypeChooserLexer, WelcomeLexer, dbmp_style
from dbmp.interactive_lexers import EditLexer, VOLS, VOLS_D, PP, MP, COLORS
from dbmp.interactive_lexers import TMPS, TMPS_D, MOUNTS, ALERTS
from dbmp.interactive_lexers import EVENTS_U, EVENTS_S
from dbmp.interactive_lexers import dbmp_interactive_completer
from dbmp.interactive_lexers import dbmp_provision_completer
from dbmp.interactive_lexers import dbmp_chooser_completer
from dbmp.interactive_lexers import dbmp_list_completer

print = pt.print_formatted_text
HISTORY = os.path.expanduser("~/.dbmp_history")
# session = pt.PromptSession(history=pt.history.FileHistory(HISTORY))
session = pt.PromptSession()
bindings = pt.key_binding.KeyBindings()
VI = pt.enums.EditingMode.VI
EMACS = pt.enums.EditingMode.EMACS


def _process_re(raw_str):
    return list(map(re.compile, raw_str.splitlines()))


VPROMPT = r"""prefix: my-test
count: 1
size(GB): 1
replica: 3
template: None
object: False
placement_mode: hybrid
placement_policy: None
read_iops_max: 0
write_iops_max: 0
total_iops_max: 0
read_bandwidth_max: 0
write_bandwidth_max: 0
total_bandwidth_max: 0
login: False
mount: False
fio: False"""

VPROMPT_RE = list(map(re.compile, r"""prefix:\s*(?P<prefix>[\w\-]+)
count:\s*(?P<count>\d+)
size\(GB\):\s*(?P<size>\d+)
replica:\s*(?P<replica>\d+)
template:\s*(?P<template>\w+)
object:\s*(?P<object>([Tt]rue|[Ff]alse))
placement_mode:\s*(?P<placement_mode>[\w\-]+)
placement_policy:\s*(?P<placement_policy>[\w\-]+)
read_iops_max:\s*(?P<read_iops_max>\d+)
write_iops_max:\s*(?P<write_iops_max>\d+)
total_iops_max:\s*(?P<total_iops_max>\d+)
read_bandwidth_max:\s*(?P<read_bandwidth_max>\d+)
write_bandwidth_max:\s*(?P<write_bandwidth_max>\d+)
total_bandwidth_max:\s*(?P<total_bandwidth_max>\d+)
login:\s*(?P<login>[Tt]rue|[Ff]alse)
mount:\s*(?P<mount>[Tt]rue|[Ff]alse)
fio:\s*(?P<fio>[Tt]rue|[Ff]alse)""".splitlines()))

PPPROMPT = r"""name: my-placement-policy
max(';' separates): all-flash;hybrid
min(';' separates): hybrid
descr: This is my new policy"""

PPPROMPT_RE = _process_re(r"""name:\s*(?P<name>[\w\-]+)
max\(';' separates\):\s*(?P<max>[\w\-;]+)
min\(';' separates\):\s*(?P<min>[\w\-;]+)
descr:\s*(?P<descr>.*)""")

MPPROMPT = r"""name: my-media-policy
priority: 1
descr: This is my new policy"""

MPPROMPT_RE = _process_re(r"""name:\s*(?P<name>[\w\-]+)
priority:\s*(?P<priority>\d+)
descr:\s*(?P<descr>.*)""")

CVPROMPT = r"""prefix: my-test
count: 1"""

CVPROMPT_RE = _process_re(r"""prefix:\s*(?P<prefix>[\w\-]+)
count:\s*(?P<count>.+)""")

CPPPROMPT = r"""name: my-placement-policy"""

CPPPROMPT_RE = _process_re(r"""name:\s*(?P<name>.+)""")

CMPPROMPT = r"""name: my-media-policy"""

CMPPROMPT_RE = _process_re(r"""name:\s*(?P<name>.+)""")

REMOVES = {"None", "none", "", None}
QUIT = {"q", "quit", "exit", ":q"}
DRY_RUN = False


def app_exit(code):
    print("Thanks for playing!")
    sys.exit(code)


def convert_opts(opts):
    for k, v in opts.items():
        if v == "None" or v == "none" or v.strip() == "":
            v = None
            opts[k] = v
            continue
        if v in ("True", "true"):
            opts[k] = True
            continue
        if v in ("False", "false"):
            opts[k] = False
            continue
        if ';' in v:
            opts[k] = v.split(';')
            continue
        try:
            opts[k] = int(v)
        except ValueError:
            opts[k] = v


@bindings.add('s-down')
def _(event):
    "Accept input during multiline mode"
    get_by_name("accept-line")(event)


@bindings.add('tab')
def _(event):
    generate_completions(event)


def print_header(tp, color):
    print(pt.HTML(
        "<u><b>Please fill out the following <{}>{}</{}> attributes"
        "</b></u>".format(color, tp, color)))
    print(pt.HTML(
        "<u><i>Press <yellow>S-down</yellow> (Shift-&lt;down-arrow&gt;) "
        "when done</i></u>"))
    print()


def print_dict(d):
    for k, v in sorted(d.items()):
        print('{:<25} {:<15} '.format(k, str(v)))


def interactive(python):
    """ Main entrypoint into dbmp interactive mode """
    args = ''
    if not os.path.exists(HISTORY):
        io.open(HISTORY, 'w+').close()
    try:
        while True:
            pt.shortcuts.clear()
            pt.shortcuts.set_title("Datera Bare-Metal Provisioner")
            print("Welcome to the DBMP Interactive Session")
            print(
                pt.HTML("Would you like to <green>provison</green>, "
                        "or <red>clean</red> up or <blue>list</blue>?"))
            out = session.prompt(pt.HTML(
                "choices: [(<green>p</green>)rovision, "
                "(<red>c</red>)lean, "
                "(<blue>l</blue>)ist]> "),
                default="p", lexer=pt.lexers.PygmentsLexer(WelcomeLexer),
                style=dbmp_style, multiline=False, key_bindings=bindings,
                completer=dbmp_interactive_completer)
            out = out.strip().lower()
            print()
            if out in {"p", "provision"}:
                args = provision()
            if out in {"c", "clean"}:
                args = clean()
            if out in {"l", "list"}:
                args = dlist()
            if out in QUIT:
                if args:
                    print(args)
                app_exit(0)
            if not pt.shortcuts.confirm("Are you using multipath?"):
                args.append("--no-multipath")
            dbmp_exe(python, args)
    except KeyboardInterrupt:
        app_exit(1)


def type_chooser(tp, types, completer):
    pt.shortcuts.clear()
    print("Please type everything you'd like to {} "
          "(<space> separated)".format(tp))
    longs = []
    shorts = []
    for i, t in enumerate(types):
        long, short = t
        longs.append(
            "<{color}>{long}</{color}>".format(color=COLORS[i], long=long))
        shorts.append(
            "<{color}>{short}</{color}>".format(color=COLORS[i], short=short))
    print(pt.HTML("Options are: [" + " ".join(longs) + "]"))
    print(pt.HTML(
        "You can use abbreviations like [" + " ".join(shorts) + "]"))
    print("If you would like to {} multiple different types of the ".format(
        tp))
    print("same resource, enter it multiple times")
    print("Press ENTER when finished")
    out = session.prompt("> ", default="v ",
                         lexer=pt.lexers.PygmentsLexer(TypeChooserLexer),
                         multiline=False, key_bindings=bindings,
                         completer=completer)
    kwargs = {}
    if tp == "provision":
        kwargs = handle_provision_choice(out)
    elif tp == "clean":
        kwargs = handle_clean_choice(out)
    elif tp == "list":
        kwargs = handle_list_choice(out)
    else:
        print(pt.HTML("Unrecognized choice: [<b>{}</b>]".format(tp)))
    return create_dbmp_command(**kwargs)


def handle_provision_choice(out):
    volumes = []
    pp = []
    mp = []
    for choice in out.strip().split():
        if choice.lower() in VOLS:
            volumes.append(volume())
        elif choice.lower() in PP:
            pp.append(placement_policy())
        elif choice.lower() in MP:
            mp.append(media_policy())
        elif choice.lower() in QUIT:
            app_exit(0)
        else:
            print(pt.HTML("Unrecognized choice: [<b>{}</b>]".format(choice)))
    return dict(volumes=volumes, placement_policies=pp, media_policies=mp)


def handle_clean_choice(out):
    volumes = []
    pp = []
    mp = []
    for choice in out.strip().split():
        if choice.lower() in VOLS:
            volumes.append(clean_volume())
        elif choice.lower() in PP:
            pp.append(clean_placement_policy())
        elif choice.lower() in MP:
            mp.append(clean_media_policy())
        elif choice.lower() in QUIT:
            app_exit(0)
        else:
            print(pt.HTML("Unrecognized choice: [<b>{}</b>]".format(choice)))
    return dict(volumes=volumes, placement_policies=pp, media_policies=mp,
                clean=True)


def handle_list_choice(out):
    args = []
    for choice in out.strip().split():
        choice_lower = choice.lower()
        if choice_lower in VOLS:
            args.append("volumes")
        elif choice_lower in VOLS_D:
            args.append("volumes-detail")
        elif choice_lower in TMPS:
            args.append("templates")
        elif choice_lower in TMPS_D:
            args.append("templates-detail")
        elif choice_lower in MOUNTS:
            args.append("mounts")
        elif choice_lower in ALERTS:
            args.append("alerts")
        elif choice_lower in EVENTS_U:
            args.append("events-user")
        elif choice_lower in EVENTS_S:
            args.append("events-system")
        # elif choice_lower in EVENTS_ID:
        #     args.append("events-id")
        elif choice_lower in PP:
            args.append("placement-policy")
        elif choice_lower in MP:
            args.append("media-policy")
        elif choice_lower in QUIT:
            app_exit(0)
        else:
            print(pt.HTML("Unrecognized choice: [<b>{}</b>]".format(choice)))
    return dict(list=args)


def provision():
    return type_chooser("provision",
                        [("volumes", "v"),
                         ("placement_policies", "pp"),
                         ("media_policies", "mp")],
                        dbmp_chooser_completer)


def clean():
    return type_chooser("clean",
                        [("volumes", "v"),
                         ("placement_policies", "pp"),
                         ("media_policies", "mp")],
                        dbmp_chooser_completer)


def dlist():
    return type_chooser("list",
                        [("volumes", "v"),
                         ("volumes_detail", "vd"),
                         ("templates", "t"),
                         ("templates_detail", "td"),
                         ("mounts", "m"),
                         ("alerts", "a"),
                         ("events_user", "eu"),
                         ("events_system", "es"),
                         ("placement_policies", "pp"),
                         ("media_policies", "mp")],
                        dbmp_list_completer)


def _dprompt(tp, color, prompt, prompt_re):
    dprompt = prompt
    while True:
        pt.shortcuts.clear()
        print_header(tp, color)
        og_data = session.prompt("",
                                 default=dprompt,
                                 multiline=True,
                                 key_bindings=bindings,
                                 lexer=pt.lexers.PygmentsLexer(EditLexer),
                                 completer=dbmp_provision_completer)
        data = "\n".join(list(filter(bool, og_data.splitlines()))).strip()
        opts = {}
        fail = False
        for matcher in prompt_re:
            match = matcher.search(data)
            if not match:
                gi = matcher.groupindex.keys()[0]
                print(pt.HTML("<red><b>Invalid data for {}</b></red>".format(
                    gi)))
                dprompt = og_data

                session.prompt("Press Enter To Retry", multiline=False,
                               key_bindings=bindings)
                fail = True
                break
            opts.update(match.groupdict())
        if fail:
            continue
        convert_opts(opts)
        print()
        print("-----------------------------")
        print("Recieved the following config")
        print("-----------------------------")
        print_dict(opts)
        print()
        if pt.shortcuts.confirm("Is this correct?"):
            return opts
        dprompt = og_data


def volume():
    return _dprompt("VOLUME", "red", VPROMPT, VPROMPT_RE)


def placement_policy():
    return _dprompt("PLACEMENT_POLICY", "green", PPPROMPT, PPPROMPT_RE)


def media_policy():
    return _dprompt("MEDIA_POLICY", "blue", MPPROMPT, MPPROMPT_RE)


def clean_volume():
    return _dprompt("VOLUME", "red", CVPROMPT, CVPROMPT_RE)


def clean_placement_policy():
    return _dprompt("PLACEMENT_POLICY", "green", CPPPROMPT, CPPPROMPT_RE)


def clean_media_policy():
    return _dprompt("MEDIA_POLICY", "blue", CMPPROMPT, CMPPROMPT_RE)


def create_dbmp_command(**kwargs):
    args = []
    for vol in kwargs.get("volumes", []):
        if vol.pop('mount', ''):
            args.append('--mount')
        if vol.pop('login', ''):
            args.append('--login')
        if vol.pop('fio', ''):
            args.append('--fio')
        arg = ",".join(["=".join((k, str(v))) for k, v in vol.items()
                        if v not in REMOVES])
        args.append("--volume='{}'".format(arg))
    for pp in kwargs.get("placement_policies", []):
        mx = pp.get('max', [])
        pp['max'] = ";".join(mx) if type(mx) == list else mx
        mn = pp.get('min', [])
        pp['min'] = ";".join(mn) if type(mn) == list else mn
        arg = ",".join(["=".join((k, str(v))) for k, v in pp.items()])
        args.append("--placement-policy='{}'".format(arg))
    for mp in kwargs.get("media_policies", []):
        arg = ",".join(["=".join((k, str(v))) for k, v in mp.items()])
        args.append("--media-policy='{}'".format(arg))
    if kwargs.get('clean'):
        args.append("--clean")
    if kwargs.get('unmount'):
        args.append("--unmount")
    if kwargs.get('logout'):
        args.append("--logout")
    for larg in kwargs.get('list', []):
        args.append("--list={}".format(larg))
    return args


def dbmp_exe(python, args):
    if DRY_RUN:
        print("{} {}".format(python, "\n".join(args)))
        sys.exit(0)
    cmd = ["env", "DBMP_INTERACTIVE=true", python]
    cmd.extend(args)
    print(subprocess.check_output(" ".join(cmd), shell=True).decode('utf-8'))
    if pt.shortcuts.confirm("Would you like to restart?"):
        return
    sys.exit(0)


def main(args):
    interactive(args.python)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("python", help="Python executable to use")
    parser.add_argument("--dry-run", action='store_true',
                        help="Don't run any commands, just print them")
    args = parser.parse_args()
    DRY_RUN = args.dry_run
    main(args)
