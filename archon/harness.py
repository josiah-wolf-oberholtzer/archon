import asyncio
import logging
import signal
from pathlib import Path

from .commands import (
    BootServerCommand,
    Command,
    ExitCommand,
    QuitServerCommand,
    StartEngineCommand,
    StopEngineCommand,
)
from .engine import Engine

logger = logging.getLogger(__name__)


class Harness:
    """
    Application harness.

    Yokes together the asyncio event-loop, a command queue, the synthesis
    engine and a text UI.
    """

    def __init__(self, analysis_path: Path):
        self.command_queue: asyncio.Queue[Command] = asyncio.Queue()
        self.engine = Engine(analysis_path)
        self.exit_future = asyncio.get_running_loop().create_future()

    async def exit(self):
        logger.info("Exiting ...")
        self.exit_future.set_result(True)

    async def run(self):
        def signal_handler(*args):
            async def bail():
                await self.command_queue.put(StopEngineCommand())
                await self.command_queue.put(QuitServerCommand())
                await self.command_queue.put(ExitCommand())

            logger.warning("Caught signal!")
            loop.create_task(bail())

        logger.info("Running harness ...")
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTSTP, signal_handler)
        await self.command_queue.put(BootServerCommand())
        await self.command_queue.put(StartEngineCommand())
        while not self.exit_future.done():
            command = await self.command_queue.get()
            await command.do(self)
        logger.info("... harness done.")


def run(analysis_path: Path):
    async def inner():
        harness = Harness(analysis_path)
        await harness.run()

    asyncio.run(inner())
