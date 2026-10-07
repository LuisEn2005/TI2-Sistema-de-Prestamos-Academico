"""
<<valueobject>> PoliticaSancionId
Generado a partir del bounded context: shared_kernel
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from typing import Union
from uuid import UUID


@dataclass
class PoliticaSancionId:
    valor: Optional[Union[UUID, int]] = None

