# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import importlib.resources

__version__ = (
    importlib.resources.files(__package__).joinpath("VERSION").read_text().strip()
)

from .primitives.tensor_product import TensorProduct
from .primitives.symmetric_tensor_product import (
    SymmetricTensorProduct,
    IWeightedSymmetricTensorProduct,
)
from .primitives.transpose import TransposeSegments, TransposeIrrepsLayout

from .primitives.equivariant_tensor_product import EquivariantTensorProduct
from .operations.tp_channel_wise import ChannelWiseTensorProduct
from .operations.tp_fully_connected import FullyConnectedTensorProduct
from .operations.linear import Linear
from .operations.symmetric_contraction import SymmetricContraction
from .operations.rotation import (
    Rotation,
    encode_rotation_angle,
    vector_to_euler_angles,
    Inversion,
)
from .operations.spherical_harmonics import spherical_harmonics

from cuequivariance_torch import layers

__all__ = [
    "TensorProduct",
    "SymmetricTensorProduct",
    "IWeightedSymmetricTensorProduct",
    "TransposeSegments",
    "TransposeIrrepsLayout",
    "EquivariantTensorProduct",
    "ChannelWiseTensorProduct",
    "FullyConnectedTensorProduct",
    "Linear",
    "SymmetricContraction",
    "Rotation",
    "Inversion",
    "encode_rotation_angle",
    "vector_to_euler_angles",
    "spherical_harmonics",
    "layers",
]