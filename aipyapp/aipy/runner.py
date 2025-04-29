#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import traceback
from io import StringIO
from importlib.util import find_spec

from term_image.image import from_file, from_url

from . import utils
from .qpython import qpy_is_webapp, qpy_exec
from .i18n import T
from .plugin import event_bus
from .interface import Runtime

INIT_IMPORTS = """
import os
import re
import sys
import json
import time
import random
import traceback
"""

import signal

# 定义处理 Ctrl+C 的函数
def signal_handler(sig, frame):
    raise KeyboardInterrupt

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)


def is_json_serializable(obj):
    try:
        json.dumps(obj)  # 尝试序列化对象
        return True
    except (TypeError, OverflowError):
        return False

def diff_dicts(dict1, dict2):
    diff = {}
    for key, value in dict1.items():
        if key not in dict2 or dict2[key] != value:
            diff[key] = value
    return diff

class Runner(Runtime):
    def __init__(self, settings, console, *, envs=None):
        self._console = console
        self._settings = settings
        self.env = envs or {}
        self._auto_install = settings.get('auto_install')
        self._auto_getenv = settings.get('auto_getenv')
        self.clear()

    def clear(self):
        self.history = [{'env': self.env}]
        self._globals = {'runtime': self, '__session__': {}, '__name__': '__main__', 'input': self.input, '__history__': self.history}
        exec(INIT_IMPORTS, self._globals)

    def __repr__(self):
        return f"<Runner history={len(self.history)}, env={len(self.env)}>"
    
    @property
    def globals(self):
        return self._globals
    
    def __call__(self, code_str, blocks):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        captured_stdout = StringIO()
        captured_stderr = StringIO()
        sys.stdout, sys.stderr = captured_stdout, captured_stderr
        result = {}
        env = self.env.copy()
        session = self._globals['__session__'].copy()
        gs = self._globals.copy()
        gs['__result__'] = {}
        gs['__code_blocks__'] = blocks
        try:
            if qpy_is_webapp(code_str): #如果是QPY的WEB APP
                qpy_exec(code_str, gs)
            else: # 否则正常运行
                exec(code_str, gs)

            if not gs['__result__']:
                result['message'] = T("The operation completed successfully")
        except (SystemExit, Exception) as e:
            result['errstr'] = str(e)
            result['traceback'] = traceback.format_exc()

        except KeyboardInterrupt:
            result['message'] = T("Execution was interrupted by the user")

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        s = captured_stdout.getvalue().strip()
        if s: result['stdout'] = s if is_json_serializable(s) else '<filtered: cannot json-serialize>'
        s = captured_stderr.getvalue().strip()
        if s: result['stderr'] = s if is_json_serializable(s) else '<filtered: cannot json-serialize>'        

        vars = gs.get('__result__')
        if vars:
            result['__result__'] = self.filter_result(vars)

        history = {'code': code_str, 'result': result}

        diff = diff_dicts(env, self.env)
        if diff:
            history['env'] = diff
        diff = diff_dicts(gs['__session__'], session)
        if diff:
            history['session'] = diff

        self.history.append(history)
        return result
    
    @utils.restore_output
    def install_packages(self, packages):
        self._console.print(f"\n⚠️ LLM {T('ask_for_packages')}: {packages}")
        need_install = []
        for package in packages:
            if not find_spec(package):
                need_install.append(package)
        if not need_install:
            self._console.print(f"✅ {T('packages_exist')}")
            return True
        ok = utils.confirm(self._console, f"💬 {T('agree_packages')} 'y'> ", auto=self._auto_install)
        if ok:
            return utils.install_packages(self._console, need_install)
        
    @utils.restore_output
    def getenv(self, name, default=None, *, desc=None):
        self._console.print(f"\n⚠️ LLM {T('ask_for_env', name)}: {desc}")
        try:
            value = self.env[name][0]
            self._console.print(f"✅ {T('env_exist', name)}")
        except KeyError:
            if self._auto_getenv:
                self._console.print(f"✅ {T('auto_confirm')}")
                value = None
            else:
                value = self._console.input(f"💬 {T('input_env', name)}: ")
                value = value.strip()
            if value:
                self.setenv(name, value, desc)
        return value or default
    
    @utils.restore_output
    def display(self, path=None, url=None):
        quiet = self._console.quiet
        image = {'path': path, 'url': url}
        event_bus.broadcast('display', image)
        if not quiet:
            image = from_file(path) if path else from_url(url)
            image.draw()

    @utils.restore_output
    def input(self, prompt=''):
        return self._console.input(prompt)
      
    def setenv(self, name, value, desc):
        self.env[name] = (value, desc)

    def filter_result(self, vars):
        if isinstance(vars, dict):
            for key in vars.keys():
                if key in self.env:
                    vars[key] = '<masked>'
                else:
                    vars[key] = self.filter_result(vars[key])
        elif isinstance(vars, list):
            vars = [self.filter_result(v) for v in vars]
        else:
            vars = vars if is_json_serializable(vars) else '<filtered>'
        return vars
