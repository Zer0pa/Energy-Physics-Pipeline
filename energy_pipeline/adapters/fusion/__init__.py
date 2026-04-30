"""Fusion / plasma adapter stack — L1 nuclear/transport, L2 gyrokinetic, L3 MHD/equilibrium,
L4 IMAS/scenario, L5 reactor engineering, plus a 50-task fusion reasoning benchmark.

Boundary: research infrastructure for in silico fusion / plasma physics. Blanket and
breeding-blanket study allowed; weapons-grade tritium / stockpile / extraction
optimization / military / defence applications are blocked at every adapter input
(see `energy_pipeline.boundary.check_fusion_intent`).
"""
from energy_pipeline.adapters.fusion.l1 import (
    OpenMcManifestAdapter,
    NuclearLibraryManifest,
    NUCLEAR_LIBRARY_KEYS,
)
from energy_pipeline.adapters.fusion.l2 import (
    TglfReducedAdapter,
    CgyroNonlinearAdapter,
    GyroSwinSurrogateAdapter,
    cross_model_disagreement,
)
from energy_pipeline.adapters.fusion.l3 import (
    FreeGS4eAdapter,
    JorekDryRunAdapter,
    BoutDryRunAdapter,
)
from energy_pipeline.adapters.fusion.l4 import (
    ImasPythonAdapter,
    OmasConverterAdapter,
    ReducedTransportCpuAdapter,
    DuqtoolsConfigAdapter,
)
from energy_pipeline.adapters.fusion.l5 import (
    ParamakGeometryAdapter,
    OpenmcCsgFixedSourceAdapter,
    OpenmcR2sAdapter,
)
from energy_pipeline.adapters.fusion.imas_fixture import (
    IMAS_DD_VERSION,
    write_fixture as write_imas_fixture,
    read_fixture as read_imas_fixture,
)
from energy_pipeline.adapters.fusion.reasoning_bench import (
    FusionReasoningBench,
    generate_bench_tasks,
    BENCH_CATEGORIES,
)

__all__ = [
    # L1
    "OpenMcManifestAdapter",
    "NuclearLibraryManifest",
    "NUCLEAR_LIBRARY_KEYS",
    # L2
    "TglfReducedAdapter",
    "CgyroNonlinearAdapter",
    "GyroSwinSurrogateAdapter",
    "cross_model_disagreement",
    # L3
    "FreeGS4eAdapter",
    "JorekDryRunAdapter",
    "BoutDryRunAdapter",
    # L4
    "ImasPythonAdapter",
    "OmasConverterAdapter",
    "ReducedTransportCpuAdapter",
    "DuqtoolsConfigAdapter",
    "IMAS_DD_VERSION",
    "write_imas_fixture",
    "read_imas_fixture",
    # L5
    "ParamakGeometryAdapter",
    "OpenmcCsgFixedSourceAdapter",
    "OpenmcR2sAdapter",
    # Reasoning bench
    "FusionReasoningBench",
    "generate_bench_tasks",
    "BENCH_CATEGORIES",
]
