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
from functools import cache
from typing import *

import numpy as np

import cuequivariance as cue
from cuequivariance import descriptors
import cuequivariance.segmented_tensor_product as stp
from cuequivariance.misc.linalg import round_to_sqrt_rational, triu_array


def symmetric_contraction(
    irreps_in: cue.Irreps, irreps_out: cue.Irreps, degrees: list[int]
) -> tuple[cue.EquivariantTensorProduct, np.ndarray]:
    r"""
    subscripts: ``weights[u],input[u],output[u]``

    Example:

    .. code-block:: python

        e, p = symmetric_contraction(
            4 * cue.Irreps("SO3", "0+1+2"), 4 * cue.Irreps("SO3", "0+1"), [1, 2, 3]
        )
        assert p.shape == (62, 18)

        mul = e.inputs[1].irreps.muls[0]
        w = jax.random.normal(jax.random.key(0), (p.shape[0], mul))
        w = jnp.einsum("au,ab->bu", w, p).flatten()

        cuex.equivariant_tensor_product(e, w, cuex.randn(jax.random.key(1), e.inputs[1]))
    """
    assert max(degrees) > 0
    e1 = cue.EquivariantTensorProduct.stack(
        [
            cue.EquivariantTensorProduct.stack(
                [
                    _symmetric_contraction(irreps_in, irreps_out[i : i + 1], deg)
                    for deg in reversed(degrees)
                ],
                [True, False, False],
            )
            for i in range(len(irreps_out))
        ],
        [True, False, True],
    )
    e2 = descriptors.symmetric_contraction(irreps_in, irreps_out, degrees)
    a1, a2 = [
        np.concatenate(
            [
                _flatten(
                    _stp_to_matrix(d.symmetrize_operands(range(1, d.num_operands - 1))),
                    1,
                    None,
                )
                for d in sorted(e.ds, key=lambda d: d.num_operands)
            ],
            axis=1,
        )
        for e in [e1, e2]
    ]

    # This nonzeros selection is just for lightening the inversion
    nonzeros = np.nonzero(np.any(a1 != 0, axis=0) | np.any(a2 != 0, axis=0))[0]
    a1, a2 = a1[:, nonzeros], a2[:, nonzeros]

    projection = a1 @ np.linalg.pinv(a2)
    # projection = np.linalg.lstsq(a2.T, a1.T, rcond=None)[0].T
    projection = round_to_sqrt_rational(projection)

    np.testing.assert_allclose(a1, projection @ a2, atol=1e-7)
    return e2, projection


def _flatten(
    x: np.ndarray, axis_start: Optional[int] = None, axis_end: Optional[int] = None
) -> np.ndarray:
    x = np.asarray(x)
    if axis_start is None:
        axis_start = 0
    if axis_end is None:
        axis_end = x.ndim
    assert 0 <= axis_start <= axis_end <= x.ndim
    return x.reshape(
        x.shape[:axis_start]
        + (np.prod(x.shape[axis_start:axis_end]),)
        + x.shape[axis_end:]
    )


def _stp_to_matrix(
    d: stp.SegmentedTensorProduct,
) -> np.ndarray:
    m = np.zeros([ope.num_segments for ope in d.operands])
    for path in d.paths:
        m[path.indices] = path.coefficients
    return m


# This function is an adaptation of https://github.com/ACEsuit/mace/blob/bd412319b11c5f56c37cec6c4cfae74b2a49ff43/mace/modules/symmetric_contraction.py
def _symmetric_contraction(
    irreps_in: cue.Irreps, irreps_out: cue.Irreps, degree: int
) -> cue.EquivariantTensorProduct:
    mul = irreps_in.muls[0]
    assert all(mul == m for m in irreps_in.muls)
    assert all(mul == m for m in irreps_out.muls)
    irreps_in = irreps_in.set_mul(1)
    irreps_out = irreps_out.set_mul(1)

    input_operands = range(1, degree + 1)
    output_operand = degree + 1

    abc = "abcdefgh"[:degree]
    d = stp.SegmentedTensorProduct.from_subscripts(
        f"u_{'_'.join(f'{a}' for a in abc)}_i+{abc}ui"
    )

    for i in input_operands:
        d.add_segment(i, (irreps_in.dim,))

    for _, ir in irreps_out:
        u = U_matrix_real(irreps_in, ir, degree)
        u = np.moveaxis(u, 0, -1)
        # u is shape (irreps_in.dim, ..., irreps_in.dim, u, ir_out.dim)

        if u.shape[-2] == 0:
            d.add_segment(output_operand, {"i": ir.dim})
        else:
            u = triu_array(u, degree)
            d.add_path(None, *(0,) * degree, None, c=u)

    d = d.flatten_coefficient_modes()
    d = d.append_modes_to_all_operands("u", {"u": mul})
    return cue.EquivariantTensorProduct(
        [d],
        [irreps_in.new_scalars(d.operands[0].size), mul * irreps_in, mul * irreps_out],
        layout=cue.ir_mul,
    )


# This function is an adaptation of https://github.com/ACEsuit/mace/blob/bd412319b11c5f56c37cec6c4cfae74b2a49ff43/mace/tools/cg.py
def U_matrix_real(
    irreps_in: cue.Irreps, ir_out: cue.Irrep, correlation: int
) -> np.ndarray:
    # Addaptation of the function U_matrix from MACE to make it work with cuequivariance
    # output shape is (ir_out.dim, irreps_in.dim, ..., irreps_in.dim, num_solutions)
    G = type(ir_out)

    assert isinstance(irreps_in, cue.Irreps)
    assert isinstance(ir_out, cue.Irrep)

    if correlation == 4:
        filter_ir_mid = frozenset([G(l, (-1) ** l) for l in range(11 + 1)])
    else:
        filter_ir_mid = None

    wigners = _wigner_nj(irreps_in, correlation, filter_ir_mid)
    arrays = [base_o3 for ir, base_o3 in wigners if ir == ir_out]

    if arrays:
        return np.stack(arrays, axis=-1)
    else:
        return np.zeros((ir_out.dim,) + (irreps_in.dim,) * correlation + (0,))


# This function is an adaptation of https://github.com/ACEsuit/mace/blob/bd412319b11c5f56c37cec6c4cfae74b2a49ff43/mace/tools/cg.py
@cache
def _wigner_nj(
    irreps_in: cue.Irreps, degree: int, filter_ir_mid: Optional[frozenset[cue.Irrep]]
) -> list[tuple[cue.Irrep, np.ndarray]]:
    if degree == 1:
        ret = []
        e = np.eye(irreps_in.dim)
        i = 0
        for mul, ir in irreps_in:
            for _ in range(mul):
                sl = slice(i, i + ir.dim)
                ret += [(ir, e[sl])]
                i += ir.dim
        return ret

    ret = []
    for ir_left, C_left in _wigner_nj(irreps_in, degree - 1, filter_ir_mid):
        i = 0
        for mul, ir in irreps_in:
            for ir_out in ir_left * ir:
                if filter_ir_mid is not None and ir_out not in filter_ir_mid:
                    continue

                for cg in cue.clebsch_gordan(ir_left, ir, ir_out):
                    C = np.einsum("jk,jli->ikl", C_left.reshape(ir_left.dim, -1), cg)
                    C = np.reshape(
                        C, (ir_out.dim,) + (irreps_in.dim,) * (degree - 1) + (ir.dim,)
                    )
                    C = round_to_sqrt_rational(C)
                    for u in range(mul):
                        E = np.zeros((ir_out.dim,) + (irreps_in.dim,) * degree)
                        sl = slice(i + u * ir.dim, i + (u + 1) * ir.dim)
                        E[..., sl] = C
                        # E is shape (ir_out.dim, irreps_in.dim, ..., irreps_in.dim)
                        ret += [(ir_out, E)]
            i += mul * ir.dim
    return sorted(ret, key=lambda x: x[0])