from typing import List
from qiskit import QuantumCircuit


def add_column_checks(
    qc: QuantumCircuit,
    board_qubits: List[int],
    col_ancillas: List[int],
    N: int = 4,
) -> None:

    if len(board_qubits) != N * N:
        raise ValueError(f"Pričakujem {N*N} board qubitov za {N}x{N} tablo.")
    if len(col_ancillas) != N - 1:
        raise ValueError(f"Pričakujem {N-1} stolpčnih ancill, dobil {len(col_ancillas)}.")

    # Za vsak stolpec j = 0..N-2
    for j in range(N - 1):
        anc = col_ancillas[j]

        # 1) Hadamard – prehod v X-bazo
        qc.h(anc)

        # 2) Controlled-phase (CP ~ CZ) iz vsake vrstice v ta stolpec
        for i in range(N):
            board_idx = board_qubits[i * N + j]
            qc.cz(board_idx, anc)

        # 3) Hadamard nazaj
        qc.h(anc)
