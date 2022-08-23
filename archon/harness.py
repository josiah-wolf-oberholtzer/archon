import asyncio
import functools
import logging
import signal
from pathlib import Path

from .commands import BootServerCommand, Command, ExitCommand, StartEngineCommand
from .engine import Engine

logger = logging.getLogger(__name__)


class Harness:
    """
    Application harness.

    Yokes together the asyncio event-loop, a command queue, the synthesis
    engine and a text UI.
    """

    def __init__(self, analysis_path: Path, loop):
        self.command_queue: asyncio.Queue[Command] = asyncio.Queue()
        self.engine = Engine(analysis_path)
        self.exit_future = loop.create_future()

    async def exit(self):
        logger.info("Exiting ...")
        self.exit_future.set_result(True)

    async def run(self):
        logger.info("Running harness ...")
        await self.command_queue.put(BootServerCommand())
        await self.command_queue.put(StartEngineCommand())
        while not self.exit_future.done():
            command = await self.command_queue.get()
            logger.info(f"Handling command: {command}")
            await command.do(self)
        logger.info("... harness done.")

    def shutdown(self, signal_name, *args):
        async def shutdown_async(sig):
            logger.warning(f"Caught signal: {signal_name}")
            await self.command_queue.put(ExitCommand())

        asyncio.get_running_loop().create_task(shutdown_async(signal_name))


def run(analysis_path: Path):
    loop = asyncio.get_event_loop()
    harness = Harness(analysis_path, loop)
    for signal_name in ("SIGINT", "SIGTSTP", "SIGQUIT", "SIGTERM", "SIGHUP"):
        loop.add_signal_handler(
            getattr(signal, signal_name),
            functools.partial(harness.shutdown, signal_name),
        )
    loop.run_until_complete(harness.run())
