#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import uuid
import platform
from pathlib import Path
from datetime import date
from enum import Enum, auto

import requests
from rich.panel import Panel
from rich.align import Align
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown

from .i18n import T
from .plugin import event_bus
from .templates import CONSOLE_HTML_FORMAT
from .utils import get_safe_filename

CERT_PATH = Path('/tmp/aipy_client.crt')

class MsgType(Enum):
    CODE = auto()
    TEXT = auto()

class Task:
    MAX_ROUNDS = 16

    def __init__(self, instruction, *, system_prompt=None, max_rounds=None):
        self.task_id = uuid.uuid4().hex
        self.instruction = instruction
        self.console = None
        self.llm = None
        self.runner = None
        self.max_rounds = max_rounds
        self.system_prompt = system_prompt
        self.pattern = re.compile(
            r"^(`{3,4})(\w+)\s+([\w\-\.]+)\n(.*?)^\1\s*$",
            re.DOTALL | re.MULTILINE
        )

    def save(self, path):
       self._console.save_html(path, clear=False, code_format=CONSOLE_HTML_FORMAT)

    def save_html(self, path, task):
        # 获取当前代码所在目录下的template.html作为模版文件
        # 读取模版文件
        # 将模版文件中的{{code}}替换为task转换为json
        # 保存为新的html文件
        template_path = Path(__file__).resolve().parent / 'template.html'
        try:
            with open(template_path, 'r') as f:
                template_content = f.read()
        except FileNotFoundError:
            self.console.print(f"[red]Error: template.html not found at {template_path}[/red]")
            return
        except Exception as e:
            self.console.print_exception()
            return

        if 'llm' in task and isinstance(task['llm'], list) and len(task['llm']) > 0:
            if task['llm'][0]['role'] == 'system':
                task['llm'].pop(0)

        task_json = json.dumps(task, ensure_ascii=False)
        html_content = template_content.replace('{{code}}', task_json)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                self.console.print(f"[green]Task saved to {path}[/green]")
        except Exception as e:
            self.console.print_exception()
            return

    def done(self):
        #import pdb;pdb.set_trace()
        instruction = self.instruction
        task = {'instruction': instruction}
        task['llm'] = self.llm.history.json()
        task['runner'] = self.runner.history
        filename = get_safe_filename(instruction, extension='.json') or f"{self.task_id}.json"
        try:
            json.dump(task, open(filename, 'w'), ensure_ascii=False, indent=4)
        except Exception as e:
            self.console.print_exception()

        filename = get_safe_filename(instruction) or f"{self.task_id}.html"
        if hasattr(self.console, 'gui'):
            # Only save new html in gui mode for now.
            self.save_html(filename, task)
        else:
            self.console.save_html(filename, clear=True, code_format=CONSOLE_HTML_FORMAT)

        self.llm.clear()
        self.runner.clear()
        self.task_id = None
        self.instruction = None

    def parse_reply(self, markdown):
        """
        从LLM回复中匹配出需要执行的代码
        """
        code_blocks = {}
        for match in self.pattern.finditer(markdown):
            _, _, name, content = match.groups()
            code_blocks[name] = content.rstrip('\n')

        return code_blocks

    def process_code_reply(self, blocks, llm=None):
        """
        执行从LLM回复中匹配出的代码
        """

        event_bus('exec', blocks)
        code_block = blocks['main']
        self.box(f"[white] 🚀 {T('start_execute')} ", code_block, lang='python')
        result = self.runner(code_block, blocks)
        event_bus('result', result)
        result = json.dumps(result, ensure_ascii=False, indent=4)
        self.box(f"[green] ✅ {T('execute_result')} ", result, lang="json")
        status = self.console.status(f"[dim white]{T('start_feedback')}...")
        self.console.print(status)
        feed_back = f"# {T('Initial mission')}\n{self.instruction}\n\n# {T('Code execution result feedback')}\n{result}"
        feedback_response = self.llm(feed_back, name=llm)
        return feedback_response

    def box(self, title, content, align=None, lang=None):
        if hasattr(self.console, 'gui'):
            # Using Mocked console. Dont use Panel

            if lang == 'json':
                # Only print execute result.
                self.console.print(f"\n{title}")
                self.console.print(content)
            return

        if lang:
            content = Syntax(content, lang, line_numbers=True, word_wrap=True)
        if align:
            content = Align(content, align=align)
        
        self.console.print(Panel(content, title=title))

    def print_summary(self):
        history = self.llm.history
        """
        table = Table(title=T("Task Summary"), show_lines=True)

        table.add_column(T("Round"), justify="center", style="bold cyan", no_wrap=True)
        table.add_column(T("Time(s)"), justify="right")
        table.add_column(T("In Tokens"), justify="right")
        table.add_column(T("Out Tokens"), justify="right")
        table.add_column(T("Total Tokens"), justify="right", style="bold magenta")

        round = 1
        for row in history.get_usage():
            table.add_row(
                str(round),
                str(row["time"]),
                str(row["input_tokens"]),
                str(row["output_tokens"]),
                str(row["total_tokens"]),
            )
            round += 1
        self._console.print("\n")
        self._console.print(table)
        """
        summary = history.get_summary()
        if 'time' in summary:
            summary = "| {rounds} | {time:.3f}s | Tokens: {input_tokens}/{output_tokens}/{total_tokens}".format(**summary)
        else:
            summary = ''
        event_bus.broadcast('summary', summary)
        self.console.print(f"\n⏹ [cyan]{T('end_instruction')} {summary}")

    def build_user_prompt(self):
        prompt = {'task': self.instruction}
        prompt['python_version'] = platform.python_version()
        prompt['platform'] = platform.platform()
        prompt['today'] = date.today().isoformat()
        prompt['work_dir'] = '工作目录为qpy.tmp，默认在qpy.tmp下创建文件'
        if self.console.quiet:
            prompt['matplotlib'] = "我现在用的是 matplotlib 的 Agg 后端，请默认用 plt.savefig() 保存图片后用 runtime.display() 显示，禁止使用 plt.show()"
            prompt['wxPython'] = "你回复的Markdown 消息中，可以用 ![图片](图片路径) 的格式引用之前创建的图片，会显示在 wx.html2 的 WebView 中"
        else:
            prompt['TERM'] = os.environ.get('TERM')
            prompt['LC_TERMINAL'] = os.environ.get('LC_TERMINAL')
        return prompt

    def run(self, instruction=None, *, llm=None, max_rounds=None):
        """
        执行自动处理循环，直到 LLM 不再返回代码消息
        """
        self.box(f"[yellow] 💁 {T('start_instruction')} ", f'[red]{instruction or self.instruction}', align="center")
        if not instruction:
            prompt = self.build_user_prompt()
            event_bus('task_start', prompt)
            instruction = json.dumps(prompt, ensure_ascii=False)
            system_prompt = self.system_prompt
        else:
            system_prompt = None
        rounds = 1
        max_rounds = max_rounds or self.max_rounds
        if not max_rounds or max_rounds < 1:
            max_rounds = self.MAX_ROUNDS
        response = self.llm(instruction, system_prompt=system_prompt, name=llm)
        while response and rounds <= max_rounds:
            blocks = self.parse_reply(response)
            if 'main' not in blocks:
                break
            rounds += 1
            response = self.process_code_reply(blocks, llm)
            if event_bus.is_stopped():
                break
        self.print_summary()
        os.write(1, b'\a\a\a')

    def chat(self, prompt):
        system_prompt = None if self.llm.history else self.system_prompt
        response, ok = self.llm(prompt, system_prompt=system_prompt)
        self.console.print(Markdown(response))

    def step(self):
        response = self.llm.get_last_message()
        if not response:
            self.console.print(f"❌ {T('no_context')}")
            return
        self.process_reply(response)

    def publish(self, title=None, author=None, verbose=True):
        url = self.settings.get('publish.url')
        cert = self.settings.get('publish.cert')
        if not (url and cert) or self.settings.get('publish.disable'):
            if verbose: self.console.print(f"[red]{T('publish_disabled')}")
            return False
        title = title or self.instruction
        author = author or os.getlogin()
        meta = {'author': author}
        files = {'content': self.console.export_html(clear=False)}
        data = {'title': title, 'metadata': json.dumps(meta)}

        if not (CERT_PATH.exists() and CERT_PATH.stat().st_size  > 0):
            CERT_PATH.write_text(cert)

        try:
            response = requests.post(url, files=files, data=data, cert=str(CERT_PATH), verify=True)
        except Exception as e:
            self.console.print_exception(e)
            return
        
        status_code = response.status_code
        if status_code in (200, 201):
            if verbose: self.console.print(f"[green]{T('upload_success')}:", response.json())
            return response.json()
        else:
            if verbose: self.console.print(f"[red]{T('upload_failed', status_code)}:", response.text)
            return False
