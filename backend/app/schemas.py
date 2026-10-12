import math
import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r'^[a-zA-Z0-9_-]+$')
    password: str = Field(min_length=8, max_length=128)


class Node(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    type: Literal['text', 'image', 'workflow', 'result']
    position: dict[str, float]
    data: dict = Field(default_factory=dict)

    @field_validator('position')
    @classmethod
    def position_valid(cls, value):
        if set(value) != {'x', 'y'} or not all(math.isfinite(v) for v in value.values()):
            raise ValueError('节点位置无效')
        return value


class Edge(BaseModel):
    id: str = Field(max_length=180)
    source: str
    target: str
    sourceHandle: str | None = None
    targetHandle: str | None = None


class Graph(BaseModel):
    nodes: list[Node] = Field(default_factory=list, max_length=500)
    edges: list[Edge] = Field(default_factory=list, max_length=1000)
    viewport: dict[str, float] = Field(default_factory=lambda: {'x': 0, 'y': 0, 'zoom': 1})
    selectionMode: Literal['manual', 'auto'] = 'manual'


class CanvasCreate(BaseModel):
    name: str = Field(default='未命名画布', min_length=1, max_length=100)


class CanvasSave(CanvasCreate):
    graph: Graph
    revision: int = Field(ge=1)


class Parameter(BaseModel):
    key: str = Field(pattern=r'^[a-zA-Z][a-zA-Z0-9_]{0,39}$')
    label: str = Field(min_length=1, max_length=60)
    type: Literal['text', 'integer', 'number', 'select'] = 'text'
    default: str | int | float
    min: float | None = None
    max: float | None = None
    options: list[str] = Field(default_factory=list, max_length=100)
    node_id: str = Field(min_length=1, max_length=80)
    field: str = Field(min_length=1, max_length=80)


class Binding(BaseModel):
    node_id: str = Field(min_length=1, max_length=80)
    field: str = Field(min_length=1, max_length=80)


class TemplateConfig(BaseModel):
    workflow: dict = Field(default_factory=dict)
    workflow_id: str = ''
    prompt_binding: Binding
    image_binding: Binding | None = None
    parameters: list[Parameter] = Field(default_factory=list, max_length=30)
    output_nodes: list[str] = Field(default_factory=list)


class TemplateBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal['text-to-image', 'image-edit']
    provider: Literal['comfyui', 'runninghub']
    enabled: bool = True
    config: TemplateConfig


class RunBody(BaseModel):
    node_id: str | None = None


class ResumeBody(BaseModel):
    asset_id: str
