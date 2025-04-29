#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import code
import builtins
from pathlib import Path
import importlib.resources as resources

from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.history import FileHistory
from pygments.lexers.python import PythonLexer

from . import __version__
from .aipy import TaskManager
from .aipy.i18n import T, set_lang
from .aipy.config import ConfigManager

__PACKAGE_NAME__ = "aipyapp"

class PythonCompleter(WordCompleter):
    def __init__(self, ai):
        names = ['exit()']
        names += [name for name in dir(builtins)]
        names += [f"ai.{attr}" for attr in dir(ai) if not attr.startswith('_')]
        super().__init__(names, ignore_case=True)
    
def get_default_config():
    lang = os.getenv('LANG')[:2] if os.getenv('LANG') else "en"
    conf_file = lang=="zh" and "default.toml" or "default_en.toml"
    default_config_path = resources.files(__PACKAGE_NAME__) / conf_file
    return str(default_config_path)

def main(args):
    console = Console(record=True)
    console.print(f"[bold cyan]🚀 [AIPyApp ({__version__}) on [green]QPython[/green]][/bold cyan] ")
    console.print(f"[bold cyan]🌐 github.com/qpython-android/aipyapp[/bold cyan] ")
    conf = ConfigManager(get_default_config(), args.config_dir)
    conf.check_config()
    settings = conf.get_config()

    lang = settings.get('lang') or or (os.getenv('LANG')[:2] if os.getenv('LANG') else "en")
    if lang: set_lang(lang)
    
    try:
        ai = TaskManager(settings, console=console)
    except Exception as e:
        console.print_exception(e)
        return

    if not ai.llm:
        console.print(f"[bold red]{T('no_available_llm')}")
        return
    
    names = ai.llm.names
    console.print(f"{T('banner1_python')}", style="green")
    console.print(f"[cyan]{T('default')}: [green]{names['default']}，[cyan]{T('enabled')}: [yellow]{' '.join(names['enabled'])}")

    interp = code.InteractiveConsole({'ai': ai})

    completer = PythonCompleter(ai)
    lexer = PygmentsLexer(PythonLexer)
    auto_suggest = AutoSuggestFromHistory()
    history = FileHistory(str(Path.cwd() / settings.history))
    session = PromptSession(history=history, completer=completer, lexer=lexer, auto_suggest=auto_suggest)
    while True:
        try:
            user_input = session.prompt(HTML('<ansiblue>>> </ansiblue>'))
            if user_input.strip() in {"exit()", "quit()"}:
                break
            interp.push(user_input)
        except EOFError:
            console.print("[bold yellow]Exiting...")
            break
        except Exception as e:
            console.print(f"[bold red]Error: {e}")
