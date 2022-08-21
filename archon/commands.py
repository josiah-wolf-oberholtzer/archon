import archon.harness


class Command:
    async def do(self, harness: "archon.harness.Harness") -> None:
        raise NotImplementedError


class BootServerCommand(Command):
    async def do(self, harness: "archon.harness.Harness") -> None:
        await harness.engine.boot_server()


class ExitCommand(Command):
    def __init__(self, graceful: bool = True):
        self.graceful = graceful

    async def do(self, harness: "archon.harness.Harness") -> None:
        if self.graceful:
            await harness.engine.stop()
            await harness.engine.quit_server()
        await harness.exit()


class QuitServerCommand(Command):
    async def do(self, harness: "archon.harness.Harness") -> None:
        await harness.engine.quit_server()


class StartEngineCommand(Command):
    async def do(self, harness: "archon.harness.Harness") -> None:
        await harness.engine.start()


class StopEngineCommand(Command):
    async def do(self, harness: "archon.harness.Harness") -> None:
        await harness.engine.stop()


class ToggleEngineCommand(Command):
    async def do(self, harness: "archon.harness.Harness") -> None:
        if harness.engine.is_running:
            await harness.engine.stop()
        else:
            await harness.engine.start()


class ToggleServerCommand(Command):
    async def do(self, harness: "archon.harness.Harness") -> None:
        if harness.engine.server.is_running:
            await harness.engine.quit_server()
        else:
            await harness.engine.boot_server()
