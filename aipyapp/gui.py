#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import subprocess
from enum import Enum, auto
from pathlib import Path
import importlib.resources as resources
import traceback
from typing import Any, Optional, Union
import threading
try:
    import tkinter as tk
    from tkinter import ttk
    import tkinter.font as tkFont
    import tkinter.scrolledtext as scrolledtext
except ImportError:
    import sys
    print("Python Tkinter package is not installed. Please install python-tk.")
    if sys.platform == "darwin":
        print("You can use brew to install it: brew install python-tk")
    else:
        raise
    sys.exit(1)

from dynaconf import Dynaconf
from rich.console import Console,JustifyMethod, OverflowMethod
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import WordCompleter

from . import __version__
from .aipy.config import ConfigManager
from .aipy import TaskManager
from .aipy.i18n import T,set_lang
#
__PACKAGE_NAME__ = "aipyapp"

def strip_rich_text_tags(text: str) -> str:
    """
    Removes common Rich text formatting tags from a string without using regex.

    Args:
        text: The input string containing Rich tags.

    Returns:
        The string with Rich tags removed.
    """
    # List of common colors and styles
    colors = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
    styles = ["bold", "italic", "underline", "blink", "reverse", "strike", "dim", "b", "i", "u", "s"]

    tags_to_remove = []

    # Simple color tags
    for color in colors:
        tags_to_remove.append(f"[{color}]")
        tags_to_remove.append(f"[/{color}]")

    # Simple style tags
    for style in styles:
        tags_to_remove.append(f"[{style}]")
        tags_to_remove.append(f"[/{style}]")

    # Combined style and color tags (e.g., [bold red])
    for style in styles:
        for color in colors:
            tags_to_remove.append(f"[{style} {color}]")
            tags_to_remove.append(f"[/{style} {color}]") # Although [/style color] is not standard, include for safety
            tags_to_remove.append(f"[{color} {style}]") # Handle swapped order if necessary
            tags_to_remove.append(f"[/{color} {style}]")

    # Generic closing tag
    tags_to_remove.append("[/]")

    # Add specific known tags if needed
    # tags_to_remove.extend(["[link]", "[/link]"]) # Example

    cleaned_text = text
    for tag in tags_to_remove:
        cleaned_text = cleaned_text.replace(tag, "")

    # Handle potential edge cases like incomplete tags or variations if necessary
    # This simple replacement might leave artifacts if tags are nested complexly
    # or if there are tags not covered in the lists.

    return cleaned_text

class GUIConsole(Console):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gui = None

    def set_gui(self, gui):
        self.gui = gui


    def print(
        self,
        *objects: Any,
        sep: str = " ",
        end: str = "\n",
        style: Optional[Union[str, Style]] = None,
        justify: Optional[JustifyMethod] = None,
        overflow: Optional[OverflowMethod] = None,
        no_wrap: Optional[bool] = None,
        emoji: Optional[bool] = None,
        markup: Optional[bool] = None,
        highlight: Optional[bool] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        crop: bool = True,
        soft_wrap: Optional[bool] = None,
        new_line_start: bool = False,
    ) -> None:
        """Print to the console and send the output to a GUI handler."""
        message = ""
        # if the first argument is a string, use it as the message
        if len(objects) == 1 and isinstance(objects[0], str):
            message = objects[0]
        else:
            # Otherwise, join all objects into a single string
            #message = sep.join(str(_object) for _object in objects)
            pass
        # If the message is empty, return
        if not message:
            return
        #print("message", message)

        if self.gui:
            message = strip_rich_text_tags(message)
            self.gui.handle_ai_output(message)


    def print_exception(self, *args, **kwargs):
        super().print_exception(*args, **kwargs)
        # Optionally, capture the formatted exception and display in the text_widget
        # This requires capturing the output of super().print_exception
        # and redirecting it to the text_widget.  A full implementation is
                # beyond the scope of this example.

class CommandType(Enum):
    CMD_DONE = auto()
    CMD_USE = auto()
    CMD_EXIT = auto()
    CMD_INVALID = auto()
    CMD_TEXT = auto()

def parse_command(input_str, llms=set()):
    lower = input_str.strip().lower()

    if lower in ("/done", "done"):
        return CommandType.CMD_DONE, None
    if lower in ("/exit", "exit"):
        return CommandType.CMD_EXIT, None
    if lower in llms:
        return CommandType.CMD_USE, input_str
    
    if lower.startswith("/use "):
        arg = input_str[5:].strip()
        if arg in llms:
            return CommandType.CMD_USE, arg
        else:
            return CommandType.CMD_INVALID, arg

    if lower.startswith("use "):
        arg = input_str[4:].strip()
        if arg in llms:
            return CommandType.CMD_USE, arg
               
    return CommandType.CMD_TEXT, input_str

class AIAppGUI:
    def __init__(self, tm, settings):
        self.tm = tm
        self.settings = settings

        # init llm
        self.names = tm.llm.names
        self.task = None
        completer = WordCompleter(['/use', 'use', '/done','done'] + list(self.names['enabled']), ignore_case=True)
        self.history = FileHistory(str(Path.cwd() / settings.history))
        self.session = PromptSession(history=self.history, completer=completer)
        self.style_main = Style.from_dict({"prompt": "green"})
        self.style_ai = Style.from_dict({"prompt": "cyan"})
        # EOF
        
        # GUI staff
        self.root = tk.Tk()
        self.root.title("aipyapp GUI")
        # Maximize the window on startup
        try:
            # This works on Windows and some Linux environments
            self.root.state('zoomed')
        except tk.TclError:
            # Fallback for macOS and other environments
            # Get screen width and height
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            # Set geometry to fill the screen (may include taskbar/menu bar space)
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")

        # AI输出结果：
        self.output_label = ttk.Label(self.root, text="AI 输出:")
        self.output_label.grid(row=0, column=0, sticky="w")
        self.output_text = scrolledtext.ScrolledText(self.root, width=60, height=20)
        self.output_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # 程序执行结果：
        self.code_label = ttk.Label(self.root, text="代码执行结果:")
        self.code_label.grid(row=0, column=1, sticky="w")
        self.code_text = scrolledtext.ScrolledText(self.root, width=60, height=20)
        self.code_text.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")



        self.input_label = ttk.Label(self.root, text="输入你的需求，然后点击提交:")
        self.input_label.grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.input_entry = tk.Text(self.root, width=60, height=5)
        self.input_entry.grid(row=3, column=0, padx=5, pady=2, sticky="ew")

        button_font = tkFont.Font(family="Arial", size=16)  # 调整 size 以改变字体大小
        style = ttk.Style()
        style.configure("Submit.TButton", font=button_font, padding=(10, 20, 10, 20))  # 使用 TButton 样式
        self.submit_button = ttk.Button(self.root, text="提交", command=self.submit_prompt, style="Submit.TButton")
        self.submit_button.grid(row=3, column=1, padx=5, pady=5, ipady=10, sticky="w")

        self.continue_button = ttk.Button(self.root, text="结束会话并继续", command=self.continue_session)
        self.continue_button.grid(row=4, column=1, padx=5, pady=2, sticky="w")
        self.end_button = ttk.Button(self.root, text="结束会话并退出", command=self.end_session)
        self.end_button.grid(row=4, column=1, padx=60, pady=2, sticky="e")


        self.open_work_button = ttk.Button(self.root, text="打开工作目录", command=self.open_work_dir)
        self.open_work_button.grid(row=4, column=0, padx=5, pady=2, sticky="w")

        #self.open_config_button = ttk.Button(self.root, text="打开配置文件", command=self.open_config_file)
        #self.open_config_button.grid(row=4, column=0, padx=10, pady=2, sticky="e")

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        console.print(f"[bold cyan]🚀 [AIPyApp ({__version__}) on [[green]QPython[/green]][/bold cyan] ")
        console.print(f"[bold cyan]🌐 http://github.com/qpython-android/aipyapp[/bold cyan]")
        self.print_output(f"{T('default')}: {self.names['default']}，{T('enabled')}: {' '.join(self.names['enabled'])}\n")

    def open_work_dir(self):
        #path = self.settings.workdir
        path = Path.cwd()
        if os.path.exists(path):
            if os.name == 'nt':  # Windows
                os.startfile(path)
            elif os.name == 'posix':  # macOS or Linux
                subprocess.Popen(['open', path])  # macOS
                # For Linux, you might want to use 'xdg-open' instead of 'open'
                # subprocess.Popen(['xdg-open', path])
        else:
            print(f"Directory not found: {path}")

    def open_config_file(self):
        path = self.settings.user_config_path
        if os.path.exists(path):
            if os.name == 'nt':  # Windows
                os.startfile(path)
            elif os.name == 'posix':  # macOS or Linux
                subprocess.Popen(['open', path])
        else:
            print(f"File not found: {path}")


    def handle_ai_output(self, output):
        if output[0] == '{' and output[-1] == '}':
            # output is json
            self.print_code("\n" + output)
        else:
            self.print_output(output)

    def print_code(self, code):
        self.code_text.insert(tk.END, code)
        self.code_text.see(tk.END)
        self.code_text.update_idletasks()  # 添加此行以强制刷新 GUI
        self.code_text.update()  # Force the GUI to refresh
    
    def print_output(self, output):
        self.output_text.insert(tk.END, output)
        self.output_text.see(tk.END)
        self.output_text.update_idletasks()  # 添加此行以强制刷新 GUI
        self.output_text.update()  # Force the GUI to refresh

    def parse_use_command(self, user_input, llms):
        words = user_input.split()
        if len(words) > 2:
            return None
        if words[0] in ('/use', 'use'):
            return words[1] if len(words) > 1 else ''
        return words[0] if len(words) == 1 and words[0] in llms else None
    
    def submit_prompt(self):
        user_input = self.input_entry.get("1.0", tk.END)

        # check use command
        if len(user_input) < 2:
            return

        cmd, arg = parse_command(user_input, self.names['enabled'])
        if cmd == CommandType.CMD_TEXT:
            if self.task:
                # in task
                self.run_task(self.task, arg)
            else:
                print("new task", arg)
                task = self.tm.new_task(arg)
                self.run_task(task)
                self.task = task
        elif cmd == CommandType.CMD_DONE:
            self.continue_session()
            self.print_output("\n task Done\n")
        elif cmd == CommandType.CMD_USE:
            ret = self.tm.llm.use(arg)
            self.print_output(f'\nUsing {arg} ok\n' if ret else '\nUsing {arg} failed\n')
        elif cmd == CommandType.CMD_INVALID:
            self.print_output(f"\nInvalid command: {arg}")
        elif cmd == CommandType.CMD_EXIT:
            self.end_session()

        # clear
        self.input_entry.delete("1.0", tk.END)

    def _run_task(self, task, instruction=None):
        try:
            task.run(instruction=instruction)
        except (EOFError, KeyboardInterrupt):
            pass
        except Exception as e:
            #self.console.print_exception()
            pass

    def run_task(self, task, instruction=None):
        thread = threading.Thread(target=self._run_task, args=(task, instruction))
        thread.start()


    def end_session(self):
        #try:
        #    self.tm.publish(verbose=False)
        #except Exception as e:
        #    pass

        try:
            if self.task:
                self.task.done()
                self.task = None
        except Exception as e:
            #self.console.print_exception()
            pass
        self.root.destroy()

    def continue_session(self):
        #try:
        #    self.tm.publish(verbose=False)
        #except Exception as e:
        #    pass

        try:
            if self.task:
                self.task.done()
                self.task = None
        except Exception as e:
            traceback.print_exc()
            #self.console.print_exception()
            pass
        self.input_entry.delete("1.0", tk.END)
        self.code_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)

    def run(self):
        self.root.mainloop()

def main(args):

    path = args.config if args.config else 'aipython.toml'
    user_config_path = Path(path).resolve()
    default_config_path = resources.files(__PACKAGE_NAME__) / "default.toml"
    conf = ConfigManager(default_config_path, args.config)
    conf.check_config()
    settings = conf.get_config()

    settings.user_config_path = user_config_path
    # auto install package.
    settings.auto_install = True
    settings.auto_getenv = True
    settings.lang="zh"
    console = GUIConsole()

    lang = settings.get('lang') or or (os.getenv('LANG')[:2] if os.getenv('LANG') else "en")
    if lang: set_lang(lang)

    try:
        tm = TaskManager(settings, console=console)
    except Exception as e:
        #console.print_exception(e)
        #console.print(f"[bold red]Error: {e}")
        print(e)
        return
   
    gui = AIAppGUI(tm, settings)  # Replace None with actual AI instance
    console.set_gui(gui)
    gui.run()
