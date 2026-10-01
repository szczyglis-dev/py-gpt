from types import SimpleNamespace
from unittest.mock import Mock

from pygpt_net.controller.kernel.kernel import Kernel
from pygpt_net.core.events import KernelEvent


def test_ordinary_continuation_waits_for_output_lifecycle():
    window = SimpleNamespace()
    kernel = Kernel(window)
    kernel.stack = Mock()
    context = SimpleNamespace(reply_context=object())
    kernel.queue(context, {}, KernelEvent(KernelEvent.AGENT_CONTINUE))
    kernel.stack.add.assert_called_once_with(context.reply_context)
    kernel.stack.handle.assert_not_called()
