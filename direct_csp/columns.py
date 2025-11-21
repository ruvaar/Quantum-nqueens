from typing import List
from qiskit import QuantumCircuit


def add_column_checks(
    qc: QuantumCircuit,
    board_qubits: List[int],
    col_ancillas: List[int],
    N: int = 4,
) -> None:
    """
    Implementacija stolpčnega kriterija po članku
    "A Quantum Approach to solve N-Queens Problem"
    (Direct Column Algorithm), specializirano za N=4.

    Ideja:
        - Imamo N vrstic z W-stanji (exactly-one na vrstico).
        - Uporabimo (N-1) ancilla qubitov, ki predstavljajo prve (N-1) stolpcev.
        - Vsak ancilla gre skozi:
            H ── CZ(ctrl=vsaka kraljica v stolpcu) ── H

        Rezultat:
            - Če ima stolpec j (0 <= j < N-1) natanko eno kraljico,
              bo ancilla_j v stanju |1>.
            - V nasprotnem primeru (0 ali >1 kraljic) bo v |0>.
        - Zadnji stolpec N-1 je določen iz pogojev po vrsticah in
          prvih (N-1) stolpcev.

    Parametri:
        qc           : QuantumCircuit
        board_qubits : globalni indeksi qubitov za tablo (dolžine N*N)
        col_ancillas : globalni indeksi (N-1) ancilla qubitov za stolpce
        N            : velikost šahovnice (privzeto 4)
    """
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
