from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

from w_prep import prepare_all_rows
from columns import add_column_checks
from diagonals import add_diagonal_checks


def build_direct_csp_circuit() -> QuantumCircuit:
    """
    Direct CSP krog za problem 4-kraljic (N=4) po članku
    "A Quantum Approach to solve N-Queens Problem":

      - 4x4 tabla -> 16 qubitov (W-stanja po vrsticah)
      - (N-1) = 3 stolpčnih ancill za column criterion
      - N(N-1)/2 = 6 diagonalnih ancill za diagonal criterion

    Skupaj:
        16 + 3 + 6 = 25 qubitov.

    Vse qubite na koncu izmerimo v klasične bite.
    """

    N = 4
    num_board = N * N          # 16
    num_col_anc = N - 1        # 3
    num_diag_anc = N * (N - 1) // 2  # 6

    # Quantum registri
    qr_board = QuantumRegister(num_board, "q")
    qr_col = QuantumRegister(num_col_anc, "col")
    qr_diag = QuantumRegister(num_diag_anc, "diag")

    # Classical register za vse qubite
    cr = ClassicalRegister(num_board + num_col_anc + num_diag_anc, "c")

    qc = QuantumCircuit(qr_board, qr_col, qr_diag, cr)

    # Globalni indeksi v qc.qubits:
    # [0..15]  -> qr_board
    # [16..18] -> qr_col
    # [19..24] -> qr_diag
    board_qubits = list(range(num_board))
    col_ancillas = list(range(num_board, num_board + num_col_anc))
    diag_ancillas = list(range(num_board + num_col_anc,
                               num_board + num_col_anc + num_diag_anc))

    # 1) Priprava W-stanj po vrsticah (vrstični kriterij)
    prepare_all_rows(qc, board_qubits)

    # 2) Stolpčni kriterij (kolone) z 3 ancillami
    add_column_checks(qc, board_qubits, col_ancillas, N=N)

    # 3) Diagonalni kriterij z 6 ancillami
    add_diagonal_checks(qc, board_qubits, diag_ancillas, N=N)

    # 4) Meritve vseh qubitov
    qc.measure(qr_board[:] + qr_col[:] + qr_diag[:], cr[:])

    return qc


# Hiter test, če datoteko poganjamo direktno
if __name__ == "__main__":
    from qiskit_aer import AerSimulator
    from qiskit import transpile

    qc = build_direct_csp_circuit()
    backend = AerSimulator(method="statevector")  # ali "automatic"

    # Za prvi test daj raje malo strelov in minimalno optimizacijo:
    tqc = transpile(qc, backend, optimization_level=0)
    result = backend.run(tqc, shots=512).result()
    counts = result.get_counts()

    print("Število različnih izidov:", len(counts))
    print("Najpogostejši izidi:")
    for bitstring, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(bitstring, cnt)
