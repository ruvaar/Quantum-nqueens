from qiskit import transpile
from qiskit_aer import AerSimulator
import time
from circuit import build_direct_csp_circuit


# --- helper: dekodiranje bitstringa ---


def split_bitstring(bitstring: str, board_size: int = 16, num_cols: int = 3, num_diag: int = 6):

    clean = bitstring.replace(" ", "")

    if len(clean) != board_size + num_cols + num_diag:
        raise ValueError(
            f"Pričakujem {board_size + num_cols + num_diag} bitov, "
            f"dobil: {len(clean)} (\"{clean}\")"
        )

    diag_bits = [int(b) for b in clean[0:num_diag]]
    col_bits = [int(b) for b in clean[num_diag:num_diag + num_cols]]
    board_bits = [int(b) for b in clean[num_diag + num_cols:]]

    if len(board_bits) != board_size:
        raise ValueError(
            f"Napačna dolžina board_bits: {len(board_bits)}, pričakujem {board_size}."
        )

    return board_bits, col_bits, diag_bits


def print_board(board_bits, N: int = 4):
    """
    Lep izpis 4x4 šahovnice iz seznama 16 bitov.
    1 -> 'Q', 0 -> '.'
    """
    if len(board_bits) != N * N:
        raise ValueError(f"Pričakujem {N * N} bitov za tablo, dobil: {len(board_bits)}")

    for r in range(N):
        row_bits = board_bits[r * N:(r + 1) * N]
        line = "".join("Q" if b == 1 else "." for b in row_bits)
        print(line)


# --- glavna analiza ---


def analyze_direct_csp(shots: int = 2048, optimization_level: int = 2):

    qc = build_direct_csp_circuit()
    backend = AerSimulator()

    tqc = transpile(qc, backend=backend, optimization_level=optimization_level)

    start = time.time()
    result = backend.run(tqc, shots=shots).result()
    end = time.time()
    print("Čas simulacije:", end - start, "s")
    counts = result.get_counts()

    print("=== Gate counts (direct CSP) ===")
    print(tqc.count_ops())

    print("\n=== Depth (direct CSP) ===")
    print(tqc.depth())

    print("\n=== Najpogostejša stanja (nefiltrirano) ===")
    for bitstring, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(bitstring, cnt)

    # --- filtriraj veljavne rešitve ---
    valid_counts = {}
    for bitstring, cnt in counts.items():
        board_bits, col_bits, diag_bits = split_bitstring(bitstring)

        # veljavna postavitev:
        #   - vsi stolpčni ancille = 1 (vsak od prvih 3 stolpcev ima natanko eno kraljico)
        #   - vsi diagonalni ancille = 1 (ni diagonalnih konfliktov med nobenim parom vrstic)
        if all(b == 1 for b in col_bits) and all(d == 1 for d in diag_bits):
            valid_counts[bitstring] = cnt

    total_shots = sum(counts.values())
    valid_shots = sum(valid_counts.values())

    print("\n=== Veljavne postavitve (brez stolpčnih in diagonalnih konfliktov) ===")
    print(f"Število različnih veljavnih bitstringov: {len(valid_counts)}")
    print(f"Število meritev, ki so veljavne: {valid_shots} / {total_shots}")
    print()

    # Izpišemo vsako veljavno postavitev z lepo tablo
    for bitstring, cnt in sorted(valid_counts.items(), key=lambda x: x[1], reverse=True):
        board_bits, col_bits, diag_bits = split_bitstring(bitstring)
        print(f"Bitstring: {bitstring}  (meritev: {cnt}x)")
        print(f"Stolpčni ancille (col): {col_bits}, diagonale (diag): {diag_bits}")
        print("Šahovnica:")
        print_board(board_bits)
        print("-" * 30)

    return qc, tqc, counts, valid_counts


if __name__ == "__main__":
    analyze_direct_csp()
