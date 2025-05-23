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
import cuequivariance as cue
from cuequivariance.group_theory.experimental.escn import escn_tp, escn_tp_compact


def test_escn():
    escn_tp(
        cue.Irreps("O3", "32x0e + 32x1o"),
        cue.Irreps("O3", "32x0e + 32x1o"),
        m_max=2,
    )


def test_escn_compact():
    escn_tp_compact(
        cue.Irreps("SO3", "32x0 + 32x1"),
        cue.Irreps("SO3", "32x0 + 32x1"),
        m_max=2,
    )
