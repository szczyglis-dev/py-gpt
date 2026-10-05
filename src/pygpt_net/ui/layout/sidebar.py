"""Logical main-pane ordering, shared by layout persistence and animations."""
from enum import Enum


class ToolboxPlacement(str, Enum):
    LEFT = 'left'
    MIDDLE = 'middle'
    RIGHT = 'right'


def placement(config=None):
    value = config.get('layout.toolbox.placement', 'middle') if config is not None else 'middle'
    try:
        return ToolboxPlacement(value).value
    except (ValueError, TypeError):
        return ToolboxPlacement.MIDDLE.value


def pane_order(position='middle'):
    if position == 'left':
        return ('toolbox', 'ctx', 'chat')
    if position == 'right':
        return ('ctx', 'chat', 'toolbox')
    return ('ctx', 'toolbox', 'chat')


def pane_sizes(toolbox, conversations, chat, position='middle'):
    widths = dict(toolbox=toolbox, ctx=conversations, chat=chat)
    return [widths[name] for name in pane_order(position)]


def order_name(position='middle'):
    return {'left': 'toolbox-first', 'middle': 'contexts-first', 'right': 'toolbox-right'}[position]
