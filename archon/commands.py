import logging

import archon.harness

logger = logging.getLogger(__name__)


class Command:
    async def do(self, harness: "archon.harness.Harness") -> None:
        raise NotImplementedError


class BootServerCommand(Command):
    async def do(self, harness: "archon.harness.Harness") -> None:
        logger.info(f"Executing {self}")
        await harness.engine.boot_server()


class ExitCommand(Command):
    def __init__(self, graceful: bool = True):
        self.graceful = graceful

    async def do(self, harness: "archon.harness.Harness") -> None:
        logger.info(f"Executing {self}")
        if self.graceful:
            await harness.engine.stop(graceful=self.graceful)
            await harness.engine.quit_server(graceful=self.graceful)
        await harness.exit()


class QuitServerCommand(Command):
    def __init__(self, graceful: bool = True):
        self.graceful = graceful

    async def do(self, harness: "archon.harness.Harness") -> None:
        logger.info(f"Executing {self}")
        await harness.engine.quit_server(graceful=self.graceful)


class StartEngineCommand(Command):
    async def do(self, harness: "archon.harness.Harness") -> None:
        logger.info(f"Executing {self}")
        await harness.engine.start()


class StopEngineCommand(Command):
    def __init__(self, graceful: bool = True):
        self.graceful = graceful

    async def do(self, harness: "archon.harness.Harness") -> None:
        logger.info(f"Executing {self}")
        await harness.engine.stop(graceful=self.graceful)


class ToggleEngineCommand(Command):
    def __init__(self, graceful: bool = True):
        self.graceful = graceful

    async def do(self, harness: "archon.harness.Harness") -> None:
        logger.info(f"Executing {self}")
        if harness.engine.is_running:
            await harness.engine.stop(graceful=self.graceful)
        else:
            await harness.engine.start()


class ToggleServerCommand(Command):
    def __init__(self, graceful: bool = True):
        self.graceful = graceful

    async def do(self, harness: "archon.harness.Harness") -> None:
        logger.info(f"Executing {self}")
        if harness.engine.server.is_running:
            await harness.engine.quit_server(graceful=self.graceful)
        else:
            await harness.engine.boot_server()
