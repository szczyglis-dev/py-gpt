"""Main sidebar order. Restart the application after changing this constant."""

# False: conversations, toolbox, chat. True: toolbox, conversations, chat.
TOOLBOX_FIRST = False


def pane_sizes(toolbox, conversations, chat):
    return [toolbox, conversations, chat] if TOOLBOX_FIRST else [conversations, toolbox, chat]


def order_name():
    return 'toolbox-first' if TOOLBOX_FIRST else 'contexts-first'
