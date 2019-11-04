import asyncio
import os
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import List, Optional
from lft.app import Node
from lft.app.data import DefaultData
from lft.app.console import Console
from lft.consensus.events import InitializeEvent

RECORD_PATH = "record.log"


class App(ABC):
    def __init__(self):
        self.console = Console(self)
        self.nodes: Optional[List[Node]] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def __del__(self):
        self.close()

    def start(self):
        self.nodes = self._gen_nodes()

        for node in self.nodes:
            for peer in (peer for peer in self.nodes if peer != node):
                node.register_peer(peer)

        self.console.start()
        self._start(self.nodes)
        self._run_forever(self.nodes)

    def close(self):
        self.console.stop()
        if self.loop and self.loop.is_running():
            self.loop.stop()

    @abstractmethod
    def _start(self, nodes: List[Node]):
        raise NotImplementedError

    @abstractmethod
    def _gen_nodes(self) -> List[Node]:
        raise NotImplementedError

    def _run_forever(self, nodes: List[Node]):
        self.loop = asyncio.get_event_loop()
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            print()
            print("Keyboard Interrupt")
        finally:
            for node in nodes:
                node.close()
            for task in asyncio.Task.all_tasks():
                task.cancel()
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()

    def _raise_init_event(self, init_node: Node, nodes: List[Node]):
        genesis_data = DefaultData(
            id_=b'genesis',
            prev_id=b'',
            proposer_id=nodes[0].node_id,
            number=0,
            term_num=0,
            round_num=0,
            prev_votes=[]
        )
        event = InitializeEvent(0, 0, genesis_data, [], [node.node_id for node in nodes])
        event.deterministic = False
        init_node.event_system.simulator.raise_event(event)


class InstantApp(App):
    def __init__(self, number: int):
        super().__init__()
        self.number = number

    def _start(self, nodes: List[Node]):
        for node in nodes:
            node.start(False)

            self._raise_init_event(node, nodes)

    def _gen_nodes(self) -> List[Node]:
        return [Node(os.urandom(16)) for _ in range(self.number)]


class RecordApp(App):
    def __init__(self, number: int, path: Path):
        super().__init__()
        self.number = number
        self.path = path

    def _start(self, nodes: List[Node]):
        for node in nodes:
            node_path = self.path.joinpath(node.node_id.hex())
            node_path.mkdir()

            record_io = open(str(node_path.joinpath(RECORD_PATH)), 'w')
            node.start_record(record_io, blocking=False)

            self._raise_init_event(node, nodes)

    def _gen_nodes(self) -> List[Node]:
        self.path.mkdir(parents=True, exist_ok=True)
        return [Node(os.urandom(16)) for _ in range(self.number)]


class ReplayApp(App):
    def __init__(self, path: Path, node: bytes):
        super().__init__()
        self.path = path
        self.node = node

    def _gen_nodes(self) -> List[Node]:
        return [Node(self.node)]

    def _get_nodes_id(self):
        return [Path(path) for path in os.listdir(str(self.path))]

    def _start(self, nodes: List[Node]):
        for node in nodes:
            node_path = self.path.joinpath(node.node_id.hex())
            record_io = open(str(node_path.joinpath(RECORD_PATH)), 'r')

            node.start_replay(record_io, blocking=False)


class Mode(Enum):
    instant = "instant"
    record = "record"
    replay = "replay"

