# Copyright 2019-2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from functools import lru_cache, singledispatch
from typing import List, Optional, Tuple, Union

import numpy as np

from braket.default_simulator.operation import GateOperation, KrausOperation, Observable


def from_braket_instruction(instruction) -> Union[GateOperation, KrausOperation]:
    """ Instantiates the concrete `GateOperation` object from the specified braket instruction.

    Args:
        instruction: instruction for a circuit specified using the `braket.ir.jacqd` format.
    Returns:
        GateOperation: instance of the concrete GateOperation class corresponding to
        the specified instruction.

    Raises:
        ValueError: If no concrete `GateOperation` class has been registered
            for the instruction type.
    """
    return _from_braket_instruction(instruction)


@singledispatch
def _from_braket_instruction(instruction):
    raise ValueError(f"Instruction {instruction} not recognized")


@lru_cache()
def pauli_eigenvalues(num_qubits: int) -> np.ndarray:
    """ The eigenvalues of Pauli operators and their tensor products.

    Args:
        num_qubits (int): the number of qubits the operator acts on
    Returns:
        np.ndarray: the eigenvalues of a Pauli product operator of the given size
    """
    if num_qubits == 1:
        return np.array([1, -1])
    return np.concatenate([pauli_eigenvalues(num_qubits - 1), -pauli_eigenvalues(num_qubits - 1)])


def ir_matrix_to_ndarray(matrix: List[List[List[float]]]) -> np.ndarray:
    """ Converts a JAQCD matrix into a numpy array.

    Args:
        matrix (List[List[List[float]]]: The IR representation of a matrix

    Returns:
        np.ndarray: The numpy ndarray representation of the matrix
    """
    return np.array([[complex(element[0], element[1]) for element in row] for row in matrix])


def check_matrix_dimensions(matrix: np.ndarray, targets: Tuple[int, ...]) -> None:
    """ Checks that the matrix is of the correct shape to act on the targets.

    Args:
        matrix (np.ndarray): The matrix to check
        targets (Tuple[int, ...]): The target qubits the matrix acts on

    Raises:
        ValueError: If the matrix is not a square matrix or operates on a space
            of different dimension than that generated by the target qubits
    """
    if len(matrix.shape) != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"{matrix} is not a two-dimensional square matrix")

    dimension = 2 ** len(targets)
    if dimension != matrix.shape[0]:
        raise ValueError(
            f"`matrix` operates on space of dimension {matrix.shape[0]} instead of {dimension}"
        )


def check_unitary(matrix: np.ndarray):
    """ Checks that the given matrix is unitary.

    Args:
        matrix (np.ndarray): The matrix to check

    Raises:
        ValueError: If the matrix is not unitary
    """
    if not np.allclose(np.eye(len(matrix)), matrix.dot(matrix.T.conj())):
        raise ValueError(f"{matrix} is not unitary")


def check_hermitian(matrix: np.ndarray):
    """ Checks that the given matrix is Hermitian.

    Args:
        matrix (np.ndarray): The matrix to check

    Raises:
        ValueError: If the matrix is not Hermitian
    """
    if not np.allclose(matrix, matrix.T.conj()):
        raise ValueError(f"{matrix} is not Hermitian")


def check_CPTP(matrices: List[np.ndarray]):
    """ Checks that the given matrices satisfy CPTP.

    Args:
        matrices (List[np.ndarray]): The matrices to check

    Raises:
        ValueError: If the matrices does not satisify CPTP
    """
    E = sum([np.dot(matrix.T.conjugate(), matrix) for matrix in matrices])
    if not np.allclose(E, np.eye(*E.shape)):
        raise ValueError(f"{matrices} does not satisfy CPTP")


def get_matrix(operation) -> Optional[np.ndarray]:
    """ Gets the matrix of the given operation.

    For a `GateOperation`, this is the gate's unitary matrix, and for an `Observable`,
    this is its diagonalizing matrix.

    Args:
        operation: The operation whose matrix is needed

    Returns:
        np.ndarray: The matrix of the operation
    """
    return _get_matrix(operation)


@singledispatch
def _get_matrix(operation):
    raise ValueError(f"Unrecognized operation: {operation}")


@_get_matrix.register
def _(gate: GateOperation):
    return gate.matrix


@_get_matrix.register
def _(kraus: KrausOperation):
    return kraus.matrices


@_get_matrix.register
def _(observable: Observable):
    return observable.diagonalizing_matrix
