import asyncio
import logging
import traceback
from typing import Optional

import psutil
import socketio
from aiohttp import web
from colorama import Fore, Style
from interactions import Client, Intents, listen, IntervalTrigger, Task
from interactions.api import events
from interactions.api.events import RawGatewayEvent
from interactions.api.events.internal import Startup
from interactions.api.events.processors import Processor
from interactions.api.gateway.gateway import GatewayClient
from interactions.api.gateway.state import ConnectionState
from interactions.client.errors import WebSocketClosed, LibraryException
from pydantic import BaseModel
from interactions.ext.paginators import Paginator  # TODO: Add shared paginator

from lbic.utils.models import Node, create_node, NodeLoad, ResourceType


# logging.basicConfig(level=logging.DEBUG)

class ClientSettings(BaseModel):
    """
    Settings for the LBIC client
    """
    socket_identifier: Optional[str] = 'default'
    webserver_port: Optional[int] = 1043
    socket_urls: Optional[list] = []

    balance_type: Optional[ResourceType] = ResourceType.cpu


class GateClient(GatewayClient):
    def __init__(self, state: ConnectionState, shard_info: tuple[int, int]):
        super().__init__(state, shard_info)
        self.con_state = state

    async def dispatch_event(self, data, seq, event) -> None:
        if event not in ['PRESENCE_UPDATE']:
            # print('dispatch_event', event)
            pass
        if event in ['INTERACTION_CREATE']:
            # print(data)
            lowest_load = min(self.con_state.client.nodes, key=lambda x: x.load.get_resource(self.con_state.client.settings.balance_type))
            if self.con_state.client._last_load.get_resource(self.con_state.client.settings.balance_type) <= lowest_load.load.get_resource(self.con_state.client.settings.balance_type):
                print(
                    f"{Fore.YELLOW}Lowest load is {self.con_state.client.settings.socket_identifier} (This: {self.con_state.client._last_load.get_resource(self.con_state.client.settings.balance_type)} / Lowest: {lowest_load.load.get_resource(self.con_state.client.settings.balance_type)})")
                print(f"{Fore.GREEN}Running command{Style.RESET_ALL}")
                return await super().dispatch_event(data, seq, event)
            else:
                print(
                    f"{Fore.YELLOW}Lowest load is {lowest_load.name} (Lowest: {lowest_load.load.get_resource(self.con_state.client.settings.balance_type)} / This: {self.con_state.client._last_load.get_resource(self.con_state.client.settings.balance_type)})")
                print(f"{Fore.RED}Not running command{Style.RESET_ALL}")
                return
        return await super().dispatch_event(data, seq, event)


class ConState(ConnectionState):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def _ws_connect(self) -> None:
        """Connect to the Discord Gateway."""
        self.logger.info(f"Shard {self.shard_id} is attempting to connect to gateway...")
        try:
            async with GateClient(self, (self.shard_id, self.client.total_shards)) as self.gateway:
                try:
                    await self.gateway.run()
                finally:
                    self._shard_ready.clear()
                    if self.client.total_shards == 1:
                        self.client.dispatch(events.Disconnect())
                    else:
                        self.client.dispatch(events.ShardDisconnect(self.shard_id))

        except WebSocketClosed as ex:
            if ex.code == 4011:
                raise LibraryException("Your bot is too large, you must use shards") from None
            if ex.code == 4013:
                raise LibraryException(f"Invalid Intents have been passed: {self.intents}") from None
            if ex.code == 4014:
                raise LibraryException(
                    "You have requested privileged intents that have not been enabled or approved. Check the developer dashboard"
                ) from None
            raise

        except Exception as e:
            self.client.dispatch(events.Disconnect())
            self.logger.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))


class SIOManager:
    """
    Manager for SocketIO connections
    """
    def __init__(self, bot, urls: list[str]):
        self.bot = bot
        self.clients = []
        self.urls = urls
        for f in urls:
            self.clients.append(socketio.AsyncClient())

    async def connect(self) -> None:
        """
        Establish SocketIO messaging channels
        :return: None
        """
        print('Connecting to other nodes...')
        await asyncio.sleep(20)  # Leave time to start other nodes
        for f in enumerate(self.urls):
            print('Connecting to ', f[1])
            try:
                await self.clients[f[0]].connect(f[1])
                self.clients[f[0]].on('*', self.catch_all, namespace='/')
                self.clients[f[0]].event('connect', self.on_connect, namespace='/')
                self.clients[f[0]].event('disconnect', self.on_disconnect, namespace='/')
                print(f"{Fore.CYAN}[SIOManager] {Fore.GREEN}CONNECTED TO {f[1]}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.CYAN}[SIOManager] {Fore.RED}FAILED TO CONNECT TO {f[1]}{Style.RESET_ALL}")
        await self.emit('register_node',
                        {'identifier': self.bot.settings.socket_identifier, 'load': self.bot._get_load().dict()})

    async def catch_all(self, event, data):
        print(f"{Fore.CYAN}[SIOManager] {Fore.GREEN}RECEIVED EVENT -> {event}{Style.RESET_ALL} {data}")

    async def on_connect(self):
        print(f"{Fore.CYAN}[SIOManager] {Fore.GREEN}CONNECTED{Style.RESET_ALL}")

    async def on_disconnect(self):
        print(f"{Fore.CYAN}[SIOManager] {Fore.RED}DISCONNECTED{Style.RESET_ALL}")

    def on(self, event, handler, namespace='/'):
        for f in self.clients:
            if f.connected:
                f.on(event, handler, namespace=namespace)

    async def emit(self, event, data, namespace='/'):
        for f in self.clients:
            if f.connected:
                await f.emit(event, data, namespace=namespace)


class WebServerManager:
    """
    Manager for the webserver that receives SocketIO messages
    """
    def __init__(self, bot):
        self.bot = bot
        self.web = web.Application()
        self.sockio = socketio.AsyncServer(async_mode='aiohttp')
        self.sockio.attach(self.web)

    def run_socketio_sync(self):
        self._register_endpoints()
        web.run_app(self.web, host='0.0.0.0', port=self.bot.settings.webserver_port)

    async def _run_socketio(self):
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, self.run_socketio_sync)

    async def _on_load_update(self, sid, data):
        print(f"{Fore.CYAN}[WebServerManager]{Fore.YELLOW}[{sid}]{Style.RESET_ALL} Received load update -> ", data)
        node = self._get_node(data['identifier'])
        if node is None:
            self.bot.nodes.append(create_node(data['identifier'], data, True))
        else:
            node.load = NodeLoad.parse_obj(data)

    async def _on_connect(self, sid, data):
        print(f"{Fore.CYAN}[WebServerManager]{Fore.YELLOW}[{sid}]{Style.RESET_ALL} Client connected")

    async def _register_node(self, sid, data):
        print(f"{Fore.CYAN}[WebServerManager]{Fore.YELLOW}[{sid}]{Style.RESET_ALL} Registered node -> ", data)
        if data['identifier'] == self.bot.settings.socket_identifier:
            return
        node = self._get_node(data['identifier'])
        if node is None:
            self.bot.nodes.append(create_node(data['identifier'], data['load'], True))
        else:
            node.load = NodeLoad.parse_obj(data['load'])

    async def _dashboard_get_load(self, sid):
        print(f"{Fore.CYAN}[WebServerManager]{Fore.YELLOW}[{sid}]{Style.RESET_ALL} Dashboard requested load")
        return self.bot._last_load.dict()

    def _get_node(self, name: str) -> Optional[Node]:
        for f in self.bot.nodes:
            if f.name == name:
                return f
        return None

    def _register_endpoints(self):
        self.sockio.on('connect', handler=self._on_connect, namespace='/')
        self.sockio.on('load_update', handler=self._on_load_update, namespace='/')
        self.sockio.on('register_node', handler=self._register_node, namespace='/')
        self.sockio.on('dashboard_get_load', handler=self._dashboard_get_load, namespace='/')

    def on_event(self, event, handler):
        self.sockio.on(event, handler)


class LoadClient(Client):
    def __init__(self, settings: ClientSettings = None, **kwargs):
        """
        Create a new client
        :param settings: Settings for the client
        :param kwargs: Arguments to pass to the client
        """
        super().__init__(**kwargs)

        self.nodes = []

        self._last_load = None

        self.settings = settings or ClientSettings()

        self._connection_state = ConState(client=self, shard_id=kwargs.get('shard_id', 0), intents=self.intents)
        self.sio = SIOManager(self, self.settings.socket_urls)  # Manager for socket.io connections
        self.webserver = WebServerManager(self)  # Manager for webserver

    @property
    def socket_identifier(self) -> str:
        """
        Get the socket identifier
        :return: str
        """
        return self.settings.socket_identifier

    @Processor.define("raw_interaction_create")
    async def _dispatch_interaction(self, event: RawGatewayEvent):
        print('_dispatch_interaction', event)
        await super()._dispatch_interaction.callback(self, event)

    async def _status_checker_task(self):
        print(f"{Fore.CYAN}[Client]{Style.RESET_ALL} Checking node statuses...")
        for f in self.sio.clients:
            node = self.webserver._get_node(f)
            if node is None:
                continue
            node.connected = f.connected
            print(
                f"{Fore.CYAN}[Client]{Style.RESET_ALL} Node {f} is {Fore.GREEN}CONNECTED{Style.RESET_ALL}" if f.connected else f"{Fore.CYAN}[Client]{Style.RESET_ALL} Node {f} is {Fore.RED}DISCONNECTED{Style.RESET_ALL}")

    def _get_load(self):
        data = dict(identifier=self.settings.socket_identifier, cpu=psutil.cpu_percent(),
                    memory=psutil.virtual_memory().percent,
                    disk=psutil.disk_usage('/').percent,
                    network_up=psutil.net_io_counters().bytes_sent, network_down=psutil.net_io_counters().bytes_recv,
                    total_cpus=psutil.cpu_count(logical=False), total_threads=psutil.cpu_count(logical=True),
                    total_memory=psutil.virtual_memory().total, total_disk=psutil.disk_usage('/').total,
                    latency=self.latency)
        return NodeLoad.parse_obj(data)

    async def _load_update_task(self):
        print(f"{Fore.CYAN}[Client]{Style.RESET_ALL} Sending load update")
        self._last_load = self._get_load()
        await self.sio.emit('load_update', self._last_load.dict())

    @listen(Startup)
    async def _on_startup(self):
        print(f"{Fore.CYAN}[Client]{Style.RESET_ALL} Ready")
        loop = asyncio.get_event_loop()
        Task(self._load_update_task, IntervalTrigger(seconds=5)).start()
        Task(self._status_checker_task, IntervalTrigger(seconds=15)).start()

    def start(self, token: str):
        loop = asyncio.new_event_loop()
        task1 = loop.create_task(self.sio.connect())
        task2 = loop.create_task(super().astart(token))
        task3 = loop.create_task(self.webserver._run_socketio())
        try:
            loop.run_until_complete(asyncio.gather(task1, task2, task3))
        except KeyboardInterrupt:
            pass
        finally:
            print("Shutting down...")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    async def astart(self, token: str) -> NotImplementedError:
        # TODO: Finish
        raise NotImplementedError("Unfinished")
