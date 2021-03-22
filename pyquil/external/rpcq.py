from typing import Dict, List, Union, Optional, Any
from typing_extensions import Literal
from pydantic import BaseModel, Field
from rpcq.messages import TargetDevice


class Operator(BaseModel):
    operator: Optional[str] = None
    duration: Optional[float] = None
    fidelity: Optional[float] = None


class MeasureInfo(Operator):
    qubit: Optional[Union[int, str]] = None
    target: Optional[Union[int, str]] = None
    operator_type: Literal["measure"] = "measure"


class GateInfo(Operator):
    parameters: List[Union[float, str]] = Field(default_factory=list)
    arguments: List[Union[float, str]] = Field(default_factory=list)
    operator_type: Literal["gate"] = "gate"


class Qubit(BaseModel):
    id: int
    dead: Optional[bool] = False
    gates: List[Union[GateInfo, MeasureInfo]] = Field(default_factory=list)

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        exclude = kwargs.get("exclude") or set()
        if not self.dead:
            exclude.add("dead")
        kwargs["exclude"] = {"dead"}
        return super().dict(**kwargs)


class Edge(BaseModel):
    ids: List[int]
    dead: Optional[bool] = False
    gates: List[GateInfo] = Field(default_factory=list)

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        exclude = kwargs.get("exclude") or set()
        if not self.dead:
            exclude.add("dead")
        kwargs["exclude"] = {"dead"}
        return super().dict(**kwargs)


class CompilerISA(BaseModel):
    qubits: Dict[str, Qubit] = Field(default_factory=dict, alias="1Q")
    edges: Dict[str, Edge] = Field(default_factory=dict, alias="2Q")


def add_qubit(device: CompilerISA, node_id: int) -> Qubit:
    if node_id not in device.qubits:
        device.qubits[str(node_id)] = Qubit(id=node_id)
    return device.qubits[str(node_id)]


def get_qubit(device: CompilerISA, node_id: int) -> Optional[Qubit]:
    return device.qubits.get(str(node_id))


def make_edge_id(qubit1: int, qubit2: int) -> str:
    return "-".join([str(qubit) for qubit in sorted([qubit1, qubit2])])


def add_edge(device: CompilerISA, qubit1: int, qubit2: int) -> Edge:
    edge_id = make_edge_id(qubit1, qubit2)
    if edge_id not in device.edges:
        device.edges[edge_id] = Edge(ids=sorted([qubit1, qubit2]))
    return device.edges[edge_id]


def get_edge(device: CompilerISA, qubit1: int, qubit2: int) -> Optional[Edge]:
    edge_id = make_edge_id(qubit1, qubit2)
    return device.edges.get(edge_id)


def _edge_ids_from_id(edge_id: str) -> List[int]:
    return [int(node_id) for node_id in edge_id.split("-")]


def _compiler_isa_from_dict(data: Dict[str, Dict[str, Any]]) -> CompilerISA:
    compiler_isa_data = {
        "1Q": {k: {"id": int(k), **v} for k, v in data.get("1Q", {}).items()},
        "2Q": {k: {"ids": _edge_ids_from_id(k), **v} for k, v in data.get("2Q", {}).items()},
    }
    return CompilerISA.parse_obj(compiler_isa_data)


def compiler_isa_to_target_device(compiler_isa: CompilerISA) -> TargetDevice:
    return TargetDevice(isa=compiler_isa.dict(by_alias=True), specs={})


class Supported1QGate:
    I = "I"
    RX = "RX"
    RZ = "RZ"
    MEASURE = "MEASURE"
    WILDCARD = "WILDCARD"


class Supported2QGate:
    WILDCARD = "WILDCARD"
    CZ = "CZ"
    ISWAP = "ISWAP"
    CPHASE = "CPHASE"
    XY = "XY"