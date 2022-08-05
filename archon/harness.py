import asyncio
import logging
import signal
from pathlib import Path

import supriya

from .query import Database

logger = logging.getLogger(__name__)


class Command:
    async def do(self, harness: "Harness"):
        raise NotImplementedError


class BootCommand(Command):
    async def do(self, harness: "Harness"):
        await harness.boot()


class QuitCommand(Command):
    async def do(self, harness: "Harness"):
        await harness.quit()


class Harness:
    def __init__(self, analysis_path: Path, loop):
        self.clock = supriya.AsyncClock()
        self.command_queue = asyncio.Queue()
        self.database = Database.new(analysis_path)
        self.exit_future = loop.create_future()
        self.server = supriya.AsyncServer()
        self.provider = supriya.Provider.from_context(self.server)

    async def boot(self):
        logger.info("Booting ...")
        await self.server.boot()

    async def run(self):
        def signal_handler(*args):
            async def bail():
                await self.command_queue.put(QuitCommand())

            logger.warning("Caught signal!")
            loop.create_task(bail())

        logger.info("Running harness ...")
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTSTP, signal_handler)
        await self.command_queue.put(BootCommand())
        while not self.exit_future.done():
            command = await self.command_queue.get()
            await command.do(self)
        logger.info("... harness done.")

    async def quit(self):
        logger.info("Quitting ...")
        await self.server.quit()
        self.exit_future.set_result(True)


def run(analysis_path: Path):
    loop = asyncio.get_event_loop()
    harness = Harness(analysis_path, loop)
    loop.run_until_complete(harness.run())
