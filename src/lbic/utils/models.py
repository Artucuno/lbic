import enum

from pydantic import BaseModel
from typing import Optional, List, Any


class ResourceType(enum.Enum):
    cpu = 1
    ram = 2
    storage = 3
    netup = 4
    netdown = 5
    latency = 6
    gpu = 7


class NodeLoad(BaseModel):
    cpu: float
    memory: float
    disk: float
    network_up: float
    network_down: float
    total_cpus: int
    total_threads: int
    total_memory: int
    total_disk: int
    identifier: Optional[str] = None
    latency: Optional[float] = None

    def get_resource(self, resource: ResourceType):
        """
        Get the value of a resource
        :param resource: The resource to get
        :return: The value of the resource
        """
        if resource == ResourceType.cpu:
            return self.cpu
        elif resource == ResourceType.ram:
            return self.memory
        elif resource == ResourceType.storage:
            return self.disk
        elif resource == ResourceType.netup:
            return self.network_up
        elif resource == ResourceType.netdown:
            return self.network_down
        elif resource == ResourceType.latency:
            return self.latency
        elif resource == ResourceType.gpu:
            raise NotImplementedError("GPU resource not implemented")
        else:
            raise ValueError(f"Invalid resource type {resource}")


class Node(BaseModel):
    name: str
    load: NodeLoad = None

    connected: bool = False

    def get_resource(self, resource: ResourceType):
        """
        Get the value of a resource
        :param resource: The resource to get
        :return: The value of the resource
        """
        if resource == ResourceType.cpu:
            return self.load.cpu
        elif resource == ResourceType.ram:
            return self.load.memory
        elif resource == ResourceType.storage:
            return self.load.disk
        elif resource == ResourceType.netup:
            return self.load.network_up
        elif resource == ResourceType.netdown:
            return self.load.network_down
        elif resource == ResourceType.latency:
            return self.load.latency
        elif resource == ResourceType.gpu:
            raise NotImplementedError("GPU resource not implemented")
        else:
            raise ValueError(f"Invalid resource type {resource}")


def get_node(nodes: list[Node], name: str) -> Optional[Node]:
    for node in nodes:
        if node.name == name:
            return node
    return None


def create_node(name: str, load: NodeLoad = None, connected: bool = False) -> Node:
    return Node(name=name, load=load, connected=connected)
