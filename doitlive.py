#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
  doitlive
  ~~~~~~~~

  :copyright: (c) 2014 by Steven Loria.
  :license: MIT, see LICENSE for more details.
"""

from __future__ import unicode_literals
import os
import sys
import re
import getpass
import subprocess
from tempfile import NamedTemporaryFile

import click
from click import echo, style, getchar

__version__ = '0.1.0'
__author__ = 'Steven Loria'
__license__ = 'MIT'

env = os.environ
PY2 = int(sys.version[0]) == 2
if PY2:
    basestring = basestring
else:
    basestring = (str, bytes)

HERE = os.path.abspath(os.path.dirname(__file__))
ESC = u'\x1b'
RETURNS = {'\r', '\n'}
OPTION_RE = re.compile(r'^#\s?doitlive\s+'
            '(?P<option>prompt|shell|alias|env|speed):'
            '\s*(?P<arg>.+)$')

class PromptState(object):
    user = ''
    cwd = ''
    display_dir = ''

    def update(self):
        self.user = style(getpass.getuser(), fg='cyan', bold=True)
        self.cwd = os.getcwd()
        display_cwd_raw = '~' if self.cwd == env['HOME'] else os.path.split(self.cwd)[-1]
        self.display_cwd = style(display_cwd_raw, fg='green')

_prompt_state = PromptState()

def echof(text, *args, **kwargs):
    echo(style(text, *args, **kwargs))

def get_default_prompt():
    if env.get('DOITLIVE_PROMPT'):
        return env['DOITLIVE_PROMPT']
    _prompt_state.update()
    return '{user}@{dir}: $'.format(
        user=_prompt_state.user,
        dir=_prompt_state.display_cwd
    )

def ensure_utf(string):
    return string.encode('utf-8') if PY2 else string


def run_command(cmd, shell=None, check_output=False, aliases=None, envvars=None):
    shell = shell or env.get('DOITLIVE_INTERPRETER') or '/bin/bash'
    if cmd.startswith("cd "):
        directory = cmd.split()[1]
        os.chdir(os.path.expanduser(directory))
    else:
        # Need to make a temporary command file so that $ENV are used correctly
        # and that shell built-ins, e.g. "source" work
        with NamedTemporaryFile('w') as fp:
            fp.write('#!{0}\n'.format(shell))
            fp.write('# -*- coding: utf-8 -*-\n')
            # Make aliases work in bash:
            if 'bash' in shell:
                fp.write("shopt -s expand_aliases\n")

            if envvars:
                # Write envvars
                for envvar in envvars:
                    envvar_line = 'export {0}\n'.format(envvar)
                    fp.write(ensure_utf(envvar_line))

            if aliases:
                # Write aliases
                for alias in aliases:
                    alias_line = 'alias {0}\n'.format(alias)
                    fp.write(ensure_utf(alias_line))
            cmd_line = cmd + '\n'
            fp.write(ensure_utf(cmd_line))
            fp.flush()
            if check_output:
                return subprocess.check_output([shell, fp.name])
            else:
                return subprocess.call([shell, fp.name])

def wait_for(chars):
    while True:
        in_char = getchar()
        if in_char == ESC:
            echo()
            raise click.Abort()
        if in_char in chars:
            echo()
            return in_char

def magictype(text, shell, check_output,
        prompt=get_default_prompt, aliases=None, envvars=None, speed=1):
    if callable(prompt):
        prompt = prompt()
    echo(prompt + ' ', nl=False)
    i = 0
    while i < len(text):
        char = text[i:i + speed]
        in_char = getchar()
        if in_char == ESC:
            echo()
            raise click.Abort()
        echo(char, nl=False)
        i += speed
    wait_for(RETURNS)
    output = run_command(text, shell, check_output=check_output,
        aliases=aliases, envvars=envvars)
    if isinstance(output, basestring):
        echo(output)

def format_prompt(prompt):
    _prompt_state.update()
    return prompt.format(
        user=_prompt_state.user,
        cwd=_prompt_state.display_cwd,
        full_cwd=_prompt_state.cwd
    )

def run(commands, shell='/bin/bash',
        check_output=False, prompt=get_default_prompt, speed=1):
    echof("We'll do it live!", fg='red', bold=True)
    echof('STARTING SESSION: Press ESC at any time to exit.', fg='yellow', bold=True)

    click.pause()
    click.clear()
    aliases, envvars = [], []
    for line in commands:
        command = line.strip()
        if not command:
            continue
        if command.startswith('#'):
            # Parse comment magic
            match = OPTION_RE.match(command)
            if match:
                option, arg = match.group('option'), match.group('arg')
                if option == 'prompt':
                    prompt = format_prompt(arg)
                elif option == 'shell':
                    shell = arg
                elif option == 'alias':
                    aliases.append(arg)
                elif option == 'env':
                    envvars.append(arg)
                elif option == 'speed':
                    speed = int(arg)
            continue
        magictype(command, shell, check_output,
            prompt=prompt, aliases=aliases, envvars=envvars, speed=speed)
    if callable(prompt):
        prompt = prompt()
    echo(prompt + ' ', nl=False)
    wait_for(RETURNS)
    echof("FINISHED SESSION", fg='yellow', bold=True)

@click.option('--check-output', is_flag=True, default=False)
@click.option('--speed', '-S', default=1, help='Typing speed.')
@click.option('--shell', '-s', metavar='<shell>',
    default='/bin/bash', help='The shell to use.')
@click.argument('session_file', type=click.File('r', encoding='utf-8'))
@click.version_option(__version__, '--version', '-v')
@click.command(context_settings={'help_option_names': ('-h', '--help')})
def cli(session_file, shell, check_output, speed):
    """The doitlive CLI.

    \b
    How to use:
        1. Create a file called session.sh. Fill it with bash commands.
        2. Run "doitlive session.sh"
        3. Type like a madman.

    Press ESC or ^C at any time to exit the session.
    To see a demo session, run "doitlive-demo".
    """
    run(session_file.readlines(),
        shell=shell,
        check_output=check_output,
        speed=speed)

DEMO = [
    'echo "Greetings"',
    'echo "This is just a demo session"',
    'echo "For more info, check out the home page..."',
    'echo "http://doitlive.rtfd.org"'
]

@click.option('--check-output', is_flag=True, default=False)
@click.option('--speed', '-S', default=1, help='Typing speed.')
@click.option('--shell', '-i', default='/bin/bash')
@click.command()
def demo(shell, check_output, speed):
    """Run a demo doitlive session."""
    run(DEMO, shell=shell, check_output=check_output, speed=speed)


if __name__ == '__main__':
    cli()
