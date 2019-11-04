from typing import TYPE_CHECKING
import asyncio
from typing import Optional
from threading import Thread
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.keys import Keys
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from IPython import embed
from lft.event.mediators import DelayedEventMediator
from lft.event.mediators.delayed_event_mediator import (DelayedEventInstantMediatorExecutor,
                                                        DelayedEventRecorderMediatorExecutor)

if TYPE_CHECKING:
    from lft.app import App


class Console:
    def __init__(self, app: 'App'):
        self._app = app
        self._running = False

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._queue: Optional[asyncio.Queue] = None

        self._thread: Optional[Thread] = None
        self._prompt_app: Optional[Application] = None

    def start(self):
        self._running = True
        self._queue = asyncio.Queue(1)

        self._loop = asyncio.get_event_loop()
        self._loop.create_task(self._execute())

        kb = KeyBindings()
        kb.add(Keys.Escape)(self._handle)
        kb.add(Keys.ControlC)(self._exit)
        self._prompt_app = Application(layout=Layout(Window()), key_bindings=kb)

        self._thread = Thread(target=self._prompt_app.run)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._prompt_app:
            self._prompt_app.exit()
            self._prompt_app = None

    def _handle(self, event: KeyPressEvent):
        async def _put_threadsafe():
            try:
                key = event.key_sequence[0].key
                self._queue.put_nowait(key)
            except asyncio.QueueFull:
                pass

        asyncio.run_coroutine_threadsafe(_put_threadsafe(), self._loop)

    def _exit(self, event: KeyPressEvent):
        self.stop()
        self._app.close()

    async def _execute(self):
        key = await self._queue.get()

        self.stop()
        try:
            handler = Handler()
            await handler.handle(key, self._app)
        finally:
            self.start()


class Handler:
    def __init__(self):
        self._handlers = {
            Keys.Escape: self._handle_run_ipython
        }

    async def handle(self, key, app: 'App'):
        try:
            handler = self._handlers[key]
        except KeyError:
            pass
        else:
            await handler(app)

    async def _handle_run_ipython(self, app: 'App'):
        loop = asyncio.get_event_loop()
        start_time = loop.time()

        try:
            embed(colors='Neutral')
        finally:
            for node in app.nodes:
                mediator = node.event_system.get_mediator(DelayedEventMediator)
                self._restore_delayed_mediator(start_time, mediator)

    def _restore_delayed_mediator(self,
                                  start_time: float,
                                  mediator: DelayedEventMediator):
        executor = mediator._executor
        if (not isinstance(executor, DelayedEventInstantMediatorExecutor) and
                not isinstance(executor, DelayedEventRecorderMediatorExecutor)):
            return

        old_handlers = executor.handlers
        executor.handlers = set()

        for old_handler in old_handlers:
            old_handler.timer_handler.cancel()
            diff = old_handler.timer_handler.when() - start_time
            mediator.execute(diff, old_handler.event)
