#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

import openai
import requests
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown

from .i18n import T
from .plugin import event_bus

@dataclass
class ChatMessage:
    role: str
    content: str
    reason: str = None
    usage: Counter = field(default_factory=Counter)

class LineReceiver(list):
    def __init__(self):
        super().__init__()
        self.buffer = ""

    @property
    def content(self):
        return '\n'.join(self)
    
    def feed(self, data: str):
        self.buffer += data
        new_lines = []

        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            self.append(line)
            new_lines.append(line)

        return new_lines

class LiveManager:
    def __init__(self, console, name):
        self.live = None
        self.name = name
        self.console = console
        self.lr = LineReceiver()
        self.title = f"{self.name} {T('llm_response')}"
        self.response_panel = None
        self.full_response = None

    def __enter__(self):
        console = self.console if self.console.quiet else None
        self.live = Live(console=console, auto_refresh=False, vertical_overflow='visible', transient=True)
        self.live.__enter__()
        status = self.console.status(f"[dim white]{self.name} {T('thinking')}...", spinner='runner')
        response_panel = Panel(status, title=f"[blue] 🤖️ {self.title} ")
        self.live.update(response_panel, refresh=True)
        return self

    def process_chunk(self, content):
        if not content: return
        lines = self.lr.feed(content)
        if not lines: return
        
        content = '\n'.join(lines)
        event_bus.broadcast('response_stream', {'llm': self.name, 'content': content})
        if hasattr(self.console, 'gui'):
            self.console.print(content, end="", highlight=False)

        full_response = self.lr.content
        try:
            md = Markdown(full_response)
            response_panel = Panel(md, title=f"[green] 🤖️ {self.title} ")
        except Exception:
            text = Text(full_response)
            response_panel = Panel(text, title=f"[yellow] 🤖️ {self.title} ")
        self.live.update(response_panel, refresh=True)
        self.response_panel = response_panel
        self.full_response = full_response
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lr.buffer:
            self.process_chunk('\n')
        self.live.__exit__(exc_type, exc_val, exc_tb)

class ChatHistory:
    def __init__(self):
        self.messages = []
        self._total_tokens = Counter()

    def __len__(self):
        return len(self.messages)
    
    def json(self):
        return [msg.__dict__ for msg in self.messages]
    
    def add(self, role, content):
        self.add_message(ChatMessage(role=role, content=content))

    def add_message(self, message: ChatMessage):
        self.messages.append(message)
        self._total_tokens += message.usage

    def get_usage(self):
        return iter(row.usage for row in self.messages if row.role == "assistant")
    
    def get_summary(self):
        summary = {'time': 0, 'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
        summary.update(dict(self._total_tokens))
        summary['rounds'] = sum(1 for row in self.messages if row.role == "assistant")
        return summary

    def get_messages(self):
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]

class BaseClient(ABC):
    MODEL = None
    BASE_URL = None
    RPS = 2
    MAX_TOKENS = 8192
    PARAMS = {}

    def __init__(self, config):
        self.name = None
        self.console = None
        self.max_tokens = config.get("max_tokens") or self.MAX_TOKENS
        self._model = config.get("model") or self.MODEL
        self._timeout = config.get("timeout")
        self._api_key = config.get("api_key")
        self._base_url = config.get("base_url") or self.BASE_URL
        self._stream = config.get("stream", True)
        self._client = None
        self._params = {}
        if self.PARAMS:
            self._params.update(self.PARAMS)
        temperature = config.get("temperature")
        if temperature != None and temperature >= 0 and temperature <= 1:
            self._params['temperature'] = temperature

    def __repr__(self):
        return f"{self.__class__.__name__}<{self.name}>({self._model}, {self.max_tokens})"
    
    def is_stopped(self):
        return event_bus.is_stopped()

    def usable(self):
        return self._model
    
    def _get_client(self):
        return self._client
    
    @abstractmethod
    def get_completion(self, messages):
        pass
        
    def add_system_prompt(self, history, system_prompt):
        history.add("system", system_prompt)

    @abstractmethod
    def _parse_usage(self, response):
        pass

    @abstractmethod
    def _parse_stream_response(self, response):
        pass

    @abstractmethod
    def _parse_response(self, response):
        pass

    def parse_response(self, response):
        if self._stream:
            response = self._parse_stream_response(response)
        else:
            response = self._parse_response(response)
        return response
    
    def __call__(self, history, prompt, system_prompt=None):
        # We shall only send system prompt once
        if not history and system_prompt:
            self.add_system_prompt(history, system_prompt)
        history.add("user", prompt)

        start = time.time()
        self.console.record = False
        with self.console.status(f"[dim white]{T('sending_task', self.name)} ..."):
            response = self.get_completion(history.get_messages())
        self.console.record = True
        end = time.time()
        if response:
            msg = self.parse_response(response)
            msg.usage['time'] = round(end - start, 3)
            history.add_message(msg)
            response = msg.content
        return response

# https://platform.openai.com/docs/api-reference/chat/create
# https://api-docs.deepseek.com/api/create-chat-completion
class OpenAIBaseClient(BaseClient):
    def usable(self):
        return super().usable() and self._api_key
    
    def _get_client(self):
        return openai.Client(api_key=self._api_key, base_url=self._base_url, timeout=self._timeout)
    
    def add_system_prompt(self, history, system_prompt):
        history.add("system", system_prompt)

    def _parse_usage(self, usage):
        usage = Counter({'total_tokens': usage.total_tokens,
                'input_tokens': usage.prompt_tokens,
                'output_tokens': usage.completion_tokens})
        return usage
    
    def _parse_stream_response(self, response):
        usage = Counter()
        with LiveManager(self.console, self.name) as lm:
            for chunk in response:
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    usage = self._parse_usage(chunk.usage)

                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    lm.process_chunk(content)

                if self.is_stopped():
                    break
        response_panel = lm.response_panel
        full_response = lm.full_response
        if response_panel: self.console.print(response_panel)
        #segments = self.console.render(response_panel)
        #self.console._record_buffer.extend(segments)
        return ChatMessage(role="assistant", content=full_response, usage=usage)

    def _parse_response(self, response):
        message = response.choices[0].message
        reason = getattr(message, "reasoning_content", None)
        return ChatMessage(
            role=message.role,
            content=message.content,
            reason=reason,
            usage=self._parse_usage(response.usage)
        )

    def get_completion(self, messages):
        if not self._client:
            self._client = self._get_client()
        try:
            response = self._client.chat.completions.create(
                model = self._model,
                messages = messages,
                stream=self._stream,
                max_tokens = self.max_tokens,
                **self._params
            )
        except Exception as e:
            self.console.print(f"❌ [bold red]{self.name} API {T('call_failed')}: [yellow]{str(e)}")
            response = None
        return response

# https://github.com/ollama/ollama/blob/main/docs/api.md
class OllamaClient(BaseClient):
    def __init__(self, config):
        super().__init__(config)
        self._session = requests.Session()

    def usable(self):
        return super().usable() and self._base_url
    
    def _parse_usage(self, response):
        ret = {'input_tokens': response['prompt_eval_count'], 'output_tokens': response['eval_count']}
        ret['total_tokens'] = ret['input_tokens'] + ret['output_tokens']
        return ret

    def _parse_stream_response(self, response):
        with LiveManager(self.console, self.name) as lm:
            for chunk in response.iter_lines():
                chunk = chunk.decode(encoding='utf-8')
                msg = json.loads(chunk)
                if msg['done']:
                    usage = self._parse_usage(msg)
                    break

                if 'message' in msg and 'content' in msg['message'] and msg['message']['content']:
                    content = msg['message']['content']
                    lm.process_chunk(content)

                if self.is_stopped():
                    break
        response_panel = lm.response_panel
        full_response = lm.full_response        
        if response_panel: self.console.print(response_panel)
        return ChatMessage(role="assistant", content=full_response, usage=usage)

    def _parse_response(self, response):
        response = response.json()
        msg = response["message"]
        return ChatMessage(role=msg['role'], content=msg['content'], usage=self._parse_usage(response))
    
    def get_completion(self, messages):
        try:
            response = self._session.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": self._stream,
                    "options": {"num_predict": self.max_tokens}
                },
                timeout=self._timeout,
                **self._params
            )
            response.raise_for_status()
        except Exception as e:
            self.console.print(f"❌ [bold red]{self.name} API {T('call_failed')}: [yellow]{str(e)}")
            response = None
        return response

# https://docs.anthropic.com/en/api/messages
class ClaudeClient(BaseClient):
    MODEL = "claude-3-7-sonnet-20250219"
    
    def __init__(self, config):
        super().__init__(config)
        self._system_prompt = None

    def _get_client(self):
        import anthropic
        return anthropic.Anthropic(api_key=self._api_key, timeout=self._timeout)
    
    def usable(self):
        return super().usable() and self._api_key
    
    def _parse_usage(self, response):
        usage = response.usage
        ret = {'input_tokens': usage.input_tokens, 'output_tokens': usage.output_tokens}
        ret['total_tokens'] = ret['input_tokens'] + ret['output_tokens']
        return ret

    def _parse_stream_response(self, response):
        usage = Counter()    
        with LiveManager(self.console, self.name) as lm:
            for event in response:
                if hasattr(event, 'delta') and hasattr(event.delta, 'text') and event.delta.text:
                    content = event.delta.text
                    lm.process_chunk(content)
                elif hasattr(event, 'message') and hasattr(event.message, 'usage') and event.message.usage:
                    usage['input_tokens'] += getattr(event.message.usage, 'input_tokens', 0)
                    usage['output_tokens'] += getattr(event.message.usage, 'output_tokens', 0)
                elif hasattr(event, 'usage') and event.usage:
                    usage['input_tokens'] += getattr(event.usage, 'input_tokens', 0)
                    usage['output_tokens'] += getattr(event.usage, 'output_tokens', 0)

                if self.is_stopped():
                    break

        response_panel = lm.response_panel
        full_response = lm.full_response        
        usage['total_tokens'] = usage['input_tokens'] + usage['output_tokens']
        if response_panel: self.console.print(response_panel)      
        return ChatMessage(role="assistant", content=full_response, usage=usage)

    def _parse_response(self, response):
        content = response.content[0].text
        role = response.role
        return ChatMessage(role=role, content=content, usage=self._parse_usage(response))
    
    def add_system_prompt(self, history, system_prompt):
        self._system_prompt = system_prompt

    def get_completion(self, messages):
        if not self._client:
            self._client = self._get_client()
        try:
            message = self._client.messages.create(
                model = self._model,
                messages = messages,
                stream=self._stream,
                system=self._system_prompt,
                max_tokens = self.max_tokens,
                **self._params
            )
        except Exception as e:
            self.console.print(f"❌ [bold red]{self.name} API {T('call_failed')}: [yellow]{str(e)}")
            message = None
        return message

class OpenAIClient(OpenAIBaseClient): 
    MODEL = 'gpt-4o'
    PARAMS = {'stream_options': {'include_usage': True}}

class GeminiClient(OpenAIBaseClient): 
    BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/'
    MODEL = 'gemini-2.5-pro-exp-03-25'
    PARAMS = {'stream_options': {'include_usage': True}}

class DeepSeekClient(OpenAIBaseClient): 
    BASE_URL = 'https://api.deepseek.com'
    MODEL = 'deepseek-chat'

class GrokClient(OpenAIBaseClient): 
    BASE_URL = 'https://api.x.ai/v1/'
    MODEL = 'grok-3-mini'
    PARAMS = {'stream_options': {'include_usage': True}}

class TrustClient(OpenAIBaseClient): 
    BASE_URL = 'https://api.trustoken.ai/v1'
    MODEL = 'auto'
    PARAMS = {'stream_options': {'include_usage': True}}

class AzureOpenAIClient(OpenAIBaseClient): 
    MODEL = 'gpt-4o'

    def __init__(self, config):
        super().__init__(config)
        self._end_point = config.get('endpoint')

    def usable(self):
        return super().usable() and self._end_point
    
    def _get_client(self):
        from openai import AzureOpenAI
        return AzureOpenAI(azure_endpoint=self._end_point, api_key=self._api_key, api_version="2024-02-01")

class PGPTAIClient(OpenAIBaseClient):
    BASE_URL = "https://openai.pgpt.cloud/v1/"
    MODEL = "auto"

class LLM(object):
    CLIENTS = {
        "openai": OpenAIClient,
        "ollama": OllamaClient,
        "claude": ClaudeClient,
        "gemini": GeminiClient,
        "pgptai": PGPTAIClient,
        "deepseek": DeepSeekClient,
        'grok': GrokClient,
        'trust': TrustClient,
        'azure': AzureOpenAIClient
    }

    def __init__(self, settings, console,system_prompt=None):
        self.llms = {}
        self.console = console
        self.default = None
        self._last = None
        self.history = ChatHistory()
        self.system_prompt = system_prompt
        names = defaultdict(set)
        for name, config in settings.llm.items():
            if not config.get('enable', True):
                names['disabled'].add(name)
                continue

            try:
                client = self.get_client(config)
            except Exception as e:
                self.console.print_exception()
                names['error'].add(name)
                continue
            
            names['enabled'].add(name)
            client.name = name
            client.console = console
            self.llms[name] = client

            if config.get('default', False) and not self.default:
                self.default = client
                names['default'] = name

        if not self.default:
            name = list(self.llms.keys())[0]
            self.default = self.llms[name]
            names['default'] = name
        self.current = self.default
        self.names = names

    def __len__(self):
        return len(self.llms)
    
    def __repr__(self):
        return f"Current: {'default' if self.current == self.default else self.current}, Default: {self.default}"
    
    @property
    def enabled(self):
        return self.names['enabled']
    
    @property
    def last(self):
        return self._last.name if self._last else None
    
    def get_last_message(self, role='assistant'):
        return self.history.get_last_message(role)
    
    def clear(self):
        self.history = ChatHistory()

    def get_client(self, config):
        proto = config.get("type", "openai")

        client = self.CLIENTS.get(proto.lower())
        if not client:
            raise ValueError(f"Unsupported LLM provider: {proto}")
        return client(config)
    
    def __contains__(self, name):
        return name in self.llms
    
    def use(self, name):
        llm = self.llms.get(name)
        if llm and llm.usable():
            self.current = llm
            return True
        return False
    
    def __call__(self, instruction, *, system_prompt=None, name=None):
        """ LLM 选择规则
        1. 如果 name 为 None, 使用 current
        2. 如果 name 存在，使用 name 对应的
        3. 使用 default
        """
        if not name:
            llm = self.current
        else:
            llm = self.llms.get(name, self.default)

        if not llm.usable():
            self.console.print(f"[red]LLM: {name} {T('not usable')}")
            return None
        
        self._last = llm
        ret = llm(self.history, instruction, system_prompt=system_prompt)
        event_bus.broadcast('response_complete', {'llm': llm.name, 'content': ret})
        return ret
