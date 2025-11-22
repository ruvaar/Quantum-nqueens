
from qiskit import QuantumCircuit
import numpy as np


def prepare_w_row(qc: QuantumCircuit, row_qubits: list[int]) -> None:
    """
    Pripravi W-row / one-hot superpozicijo na 4 qubitih,
    ki predstavljajo eno vrstico šahovnice.

    row_qubits: seznam 4 indeksov qubitov v vezju `qc`, npr. [0, 1, 2, 3].

    Pripravljeno stanje je (neznormirano zapisano):
        |1000> + |0100> + |0010> + |0001>
    oz. normirano:
        (1/2)(|1000> + |0100> + |0010> + |0001>)
    """

    if len(row_qubits) != 4:
        raise ValueError("prepare_w_row trenutno podpira samo 4 qubite (N=4).")

    # 4 qubiti -> 2^4 = 16 osnovnih stanj
    # Qiskit indeksira amplitudo tako, da je state[1] = |0001>,
    # state[2] = |0010>, state[4] = |0100>, state[8] = |1000>, če
    # podamo qubite v vrstnem redu [q0, q1, q2, q3].
    state = np.zeros(16, dtype=complex)

    amp = 0.5  # 1/2 za normirano superpozicijo 4 stanj
    state[1] = amp   # |0001>
    state[2] = amp   # |0010>
    state[4] = amp   # |0100>
    state[8] = amp   # |1000>

    # Inicializiramo podprstavek (subsystem) znotraj glavnega kroga
    qc.initialize(state, row_qubits)


def prepare_all_rows(qc: QuantumCircuit, board_qubits: list[int]) -> None:
    """
    Pripravi W-row superpozicijo za VSE vrstice 4x4 šahovnice.

    board_qubits: seznam 16 indeksov qubitov, ki predstavljajo ploščo
                  v vrstnem redu:
                      vrstica 0: qubiti [0,1,2,3]
                      vrstica 1: qubiti [4,5,6,7]
                      vrstica 2: qubiti [8,9,10,11]
                      vrstica 3: qubiti [12,13,14,15]

    Funkcija na vsako četvorko qubitov pokliče `prepare_w_row`.
    """

    if len(board_qubits) != 16:
        raise ValueError("prepare_all_rows pričakuje točno 16 qubitov za 4x4 tablo.")

    for row in range(4):
        start = 4 * row
        row_slice = board_qubits[start:start + 4]
        prepare_w_row(qc, row_slice)


# Hiter lokalni test (po želji):
if __name__ == "__main__":
    from qiskit import QuantumRegister

    board = QuantumRegister(16, "q")
    qc = QuantumCircuit(board)

    # qubiti so 0..15 v istem vrstnem redu kot v registerju
    prepare_all_rows(qc, list(range(16)))

    print(qc.draw())
