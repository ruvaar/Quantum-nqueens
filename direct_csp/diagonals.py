from typing import List, Dict, Tuple
from qiskit import QuantumCircuit


def diagonal_pairs_for_4x4() -> List[Tuple[int, int]]:
    """
    Vrne vse pare indeksov (i, j) na 4x4 tabli, ki ležita na isti diagonali
    (vključno z obema smereh, \\ in /), pri čemer je j > i.

    Indeksiranje:
        index = row * 4 + col, row, col v {0,1,2,3}
    """
    pairs: List[Tuple[int, int]] = []
    N = 4
    for r1 in range(N):
        for c1 in range(N):
            i = r1 * N + c1
            for r2 in range(r1 + 1, N):  # r2 > r1
                for c2 in range(N):
                    if abs(r1 - r2) == abs(c1 - c2):
                        j = r2 * N + c2
                        pairs.append((i, j))
    return pairs


DIAG_PAIRS = diagonal_pairs_for_4x4()


def add_diagonal_checks(
    qc: QuantumCircuit,
    board_qubits: List[int],
    diag_ancillas: List[int],
    N: int = 4,
) -> None:
    """
    Implementacija diagonalnega kriterija po članku:

        - Uporabimo N(N-1)/2 ancilla qubitov, vsak predstavlja en par vrstic.
        - Vsaka ancilla se inicializira v |1>.
        - Za vsak par diagonalno poravnanih polj med tema dvema vrsticama
          izvedemo Toffoli (CCX) na ustrezno ancillo.
        - Če sta na takem paru obe kraljici (oba qubita v |1>), se ancilla
          preklopi iz |1> v |0>.

    Ker W-stanja zagotavljajo natanko eno kraljico na vrstico, je za vsak
    par vrstic možen največ en diagonalni konflikt, zato XOR-učinek več
    Toffolijev ni problem.

    Parametri:
        qc           : QuantumCircuit
        board_qubits : globalni indeksi N*N qubitov za tablo
        diag_ancillas: globalni indeksi N(N-1)/2 ancilla qubitov
        N            : velikost šahovnice (privzeto 4)
    """
    if len(board_qubits) != N * N:
        raise ValueError(f"Pričakujem {N*N} board qubitov za {N}x{N} tablo.")
    expected_anc = N * (N - 1) // 2
    if len(diag_ancillas) != expected_anc:
        raise ValueError(f"Pričakujem {expected_anc} diagonalnih ancill, dobil {len(diag_ancillas)}.")

    # Povezava (row-pair) -> ancilla indeks
    row_pairs: List[Tuple[int, int]] = []
    for r1 in range(N):
        for r2 in range(r1 + 1, N):
            row_pairs.append((r1, r2))

    if len(row_pairs) != expected_anc:
        raise RuntimeError("Število parov vrstic se ne ujema z N(N-1)/2.")

    rowpair_to_anc: Dict[Tuple[int, int], int] = {
        (r1, r2): anc for (r1, r2), anc in zip(row_pairs, diag_ancillas)
    }

    # Inicializiramo vse diagonalne ancille v |1>
    for anc in diag_ancillas:
        qc.x(anc)

    # Za vsak diagonalni par (i, j) iz DIAG_PAIRS poiščemo, kateri par vrstic je to,
    # in uporabimo ustrezno ancillo.
    for i, j in DIAG_PAIRS:
        r1, c1 = divmod(i, N)
        r2, c2 = divmod(j, N)
        key = (min(r1, r2), max(r1, r2))
        anc = rowpair_to_anc[key]
        qc.ccx(board_qubits[i], board_qubits[j], anc)
