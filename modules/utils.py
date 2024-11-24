from functools import lru_cache, wraps
import time
from copy import deepcopy
from enum import Enum, Flag
from itertools import zip_longest

def cache(maxsize: int = 128, typed: bool = False, copy: bool = False, ttl: int = 60):
    def decorator(func):
        @lru_cache(maxsize=maxsize, typed=typed)
        def cached_func(*args, ttl_hash, **kwargs):
            del ttl_hash
            return func(*args, **kwargs)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return cached_func(*args, ttl_hash=round(time.time() / ttl), **kwargs)

        @wraps(func)
        def wrapper_with_copy(*args, **kwargs):
            return deepcopy(cached_func(*args, ttl_hash=round(time.time() / ttl), **kwargs))
        
        if copy:
            return wrapper_with_copy
        else:
            return wrapper

    return decorator

class MessagePaneDirection(Enum):
    VERTICAL = 'vertical'
    HORIZONTAL = 'horizontal'

class MessageContentConstraint(Enum):
    PLAIN = 'plain'
    FILL = 'fill'

class MessageModifierFlag(Flag):
    NONE = 0
    BOLD = 1
    ITALIC = 2
    STRIKETHROUGH = 4

class MessageContent:
    def content_length(self) -> int:
        pass
    def render(self):
        pass

class TextMessageContent(MessageContent):
    def __init__(self, text: str, constraint: MessageContentConstraint = MessageContentConstraint.PLAIN, modifiers: MessageModifierFlag = MessageModifierFlag.NONE):
        self.text = text
        self.constraint = constraint
        self.modifiers = modifiers

    def content_length(self) -> int:
        return len(self.text)

    def render(self) -> str:
        text = self.text
        if MessageModifierFlag.BOLD in self.modifiers:
            text = '**' + text + '**'
        if MessageModifierFlag.ITALIC in self.modifiers:
            text = '__' + text + '__'
        if MessageModifierFlag.STRIKETHROUGH in self.modifiers:
            text = '~~' + text + '~~'
        return text

class MessagePane(MessageContent):
    def __init__(self, direction: MessagePaneDirection, size: int = 0, constraint: MessageContentConstraint = MessageContentConstraint.PLAIN):
        self.direction = direction
        self.__content = []
        self.size = size
        self.constraint = constraint
        self.modifiers = MessageModifierFlag.NONE

    def add(self, content: TextMessageContent):
        self.__content.append(content)

    def prepend(self, content: TextMessageContent):
        self.__content.insert(0, content)

    def insert(self, index: int, content: TextMessageContent):
        self.__content.insert(index, content)

    def remove(self, index: int):
        self.__content.pop(index)

    def clear(self):
        self.__content.clear()

    def __len__(self):
        return len(self.__content)

    def content_length(self) -> int:
        match self.direction:
            case MessagePaneDirection.VERTICAL:
                return len(self.__content)
            case MessagePaneDirection.HORIZONTAL:
                return sum([content.content_length() for content in self.__content])

    def render(self) -> str:
        message = ''
        fill_content_count = 0
        for content in self.__content:
            if content.constraint == MessageContentConstraint.FILL:
                fill_content_count += 1

        spacings = []
        if fill_content_count != 0:
            space, mod = divmod(self.size - self.content_length(), fill_content_count)
            spacings = [s + r for s, r in zip_longest([space for _ in range(fill_content_count)], [1 for _ in range(mod)], fillvalue=0)]

        for content in self.__content:
            spacer = ''
            match self.direction:
                case MessagePaneDirection.VERTICAL:
                    spacer = '\n'
                case MessagePaneDirection.HORIZONTAL:
                    spacer = '⠀'

            match content.constraint:
                case MessageContentConstraint.PLAIN:
                    message += content.render()
                case MessageContentConstraint.FILL:
                    spacing = spacings.pop(0)
                    message += spacer * (spacing // 2 + spacing % 2)
                    message += content.render()
                    message += spacer * (spacing // 2)

            if self.direction == MessagePaneDirection.VERTICAL:
                message += '\n'

        if self.direction == MessagePaneDirection.VERTICAL:
            message = message[:-1]
        return message

