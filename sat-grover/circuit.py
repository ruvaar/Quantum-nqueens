# circuit.py -- SAT + Grover za problem 4-kraljic z "pravim" CNF orakljem

from math import pi, sqrt
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import PhaseOracle


# =========================
# 1) CSP LOGIKA (4-QUEENS)
# =========================

def decode_assignment(bits):
    """
    Pretvori 8-bitni assignment (LSB-first) v seznam stolpcev [c0, c1, c2, c3],
    kjer ima vsaka vrstica 2 bita (b0 = LSB, b1 = MSB) in col = b0 + 2*b1.
    """
    cols = []
    for row in range(4):
        b0 = bits[2 * row]
        b1 = bits[2 * row + 1]
        col = b0 + 2 * b1
        cols.append(col)
    return cols


def is_valid_assignment(bits):
    """
    ČE BI assignment preverjali klasično:
      - vse 4 kraljice morajo biti v različnih stolpcih
      - ne sme biti diagonalnih napadov

    To funkcijo še vedno uporabljamo samo za:
      - generiranje seznama rešitev (za izračun optimalnih Grover iteracij)
    NE pa več za gradnjo oraklja.
    """
    cols = decode_assignment(bits)

    # 1) stolpci morajo biti vsi različni
    if len(set(cols)) != 4:
        return False

    # 2) diagonalni napadi: |dr| == |dc|
    for i in range(4):
        for j in range(i + 1, 4):
            if abs(i - j) == abs(cols[i] - cols[j]):
                return False

    return True


def generate_valid_patterns():
    """
    Klasično pregleda vseh 2^8 = 256 assignmentov in vrne tiste,
    ki zadovoljijo N-kraljice.

    To je uporabno za:
      - preverjanje, koliko rešitev imamo (num_solutions),
      - testiranje pravilnosti kvantne implementacije.

    Orakel **ne** uporablja tega seznama, zato je pristop "pravi" CNF.
    """
    valid = []
    for x in range(256):
        bits = [(x >> i) & 1 for i in range(8)]  # LSB-first
        if is_valid_assignment(bits):
            valid.append(bits)
    return valid


# ======================================
# 2) CNF / BOOLEAN IZRAZ ZA 4-KRALJICE
# ======================================

def _nqueens4_boolean_expression():
    """
    Zgradi boolean izraz F(x0..x7) za problem 4-kraljic z binarnim kodiranjem.

    Kodiranje:
      - vrstica 0: (x0 = LSB, x1 = MSB)
      - vrstica 1: (x2 = LSB, x3 = MSB)
      - vrstica 2: (x4 = LSB, x5 = MSB)
      - vrstica 3: (x6 = LSB, x7 = MSB)

    Formula F = (vsi stolpci različni) AND (ni diagonalnih konfliktov).

    Sintaksa je Qiskit-ova:
      - &  ... AND
      - |  ... OR
      - ~  ... NOT
      - ^  ... XOR
    """

    def v(idx):
        return f"x{idx}"

    def row_bits(r):
        """
        Vrne (b0, b1) za vrstico r, kjer je:
          - b0: LSB (x0, x2, x4, x6)
          - b1: MSB (x1, x3, x5, x7)
        """
        b0 = v(2 * r)
        b1 = v(2 * r + 1)
        return b0, b1

    clauses = []

    # ---- 2.1 Stolpčni pogoji: col(r1) != col(r2) za vsako dvojico vrstic ----
    #
    # col(r) = (b1, b0) v {0,1,2,3}
    # col(r1) != col(r2)   <=>   (b1_r1 XOR b1_r2) OR (b0_r1 XOR b0_r2)
    #
    for r1 in range(4):
        for r2 in range(r1 + 1, 4):
            b0_r1, b1_r1 = row_bits(r1)
            b0_r2, b1_r2 = row_bits(r2)
            col_diff = f"(({b1_r1} ^ {b1_r2}) | ({b0_r1} ^ {b0_r2}))"
            clauses.append(col_diff)

    # ---- 2.2 Diagonalni pogoji: ni diagonalnih napadov ----
    #
    # Queen(i, ci), Queen(j, cj) sta na isti diagonali, če velja:
    #   |i - j| == |ci - cj|
    #
    # Za vsak par vrstic (r1, r2) naštejemo vse (c1, c2) v {0..3}^2,
    # ki izpolnijo |r1-r2| == |c1-c2|. Te kombinacije so "slabe".
    # Dobimo izraz:
    #   conflict(r1,r2) = OR_k [ (col(r1) == c1_k) AND (col(r2) == c2_k) ]
    # in potem diagonalni pogoj:
    #   diag_ok(r1,r2) = NOT conflict(r1,r2) = ~( ... )
    #

    def col_eq_expr(r, col_val):
        """
        Boolean izraz za "col(r) == col_val", kjer je col_val v {0,1,2,3}.
        Kodiranje:
          - b0 = LSB, b1 = MSB, col = b0 + 2*b1
        """
        b0, b1 = row_bits(r)
        v0 = col_val & 1         # LSB
        v1 = (col_val >> 1) & 1  # MSB

        lit0 = b0 if v0 == 1 else f"~{b0}"
        lit1 = b1 if v1 == 1 else f"~{b1}"

        # (b1 == v1) AND (b0 == v0)
        return f"({lit1} & {lit0})"

    for r1 in range(4):
        for r2 in range(r1 + 1, 4):
            bad_terms = []
            for c1 in range(4):
                for c2 in range(4):
                    if abs(r1 - r2) == abs(c1 - c2):
                        term = f"({col_eq_expr(r1, c1)} & {col_eq_expr(r2, c2)})"
                        bad_terms.append(term)
            if bad_terms:
                conflict_expr = " | ".join(bad_terms)
                diag_ok = f"~({conflict_expr})"
                clauses.append(diag_ok)

    # Končna formula: AND vseh pogojev
    # F = ∧_i clause_i
    expr = " & ".join(f"({c})" for c in clauses)
    return expr


def build_nqueens4_oracle():
    """
    Zgradi Qiskit PhaseOracle za 4-kraljice iz boolean izraza.

    Orakel implementira diagonalni operator:
        |x> -> (-1)^{F(x)} |x>
    kjer je F(x) = 1 natanko za veljavne postavitve 4-kraljic.
    """
    expr = _nqueens4_boolean_expression()
    var_order = [f"x{i}" for i in range(8)]  # eksplicitni vrstni red spremenljivk
    oracle = PhaseOracle(expr, var_order=var_order)
    return oracle


# =========================
# 3) GROVERJEVE ITERACIJE
# =========================

def optimal_grover_iterations(num_qubits: int, num_solutions: int) -> int:
    """
    Standardna formula za optimalno število Groverjevih iteracij:
        k ≈ (pi/4) * sqrt(N / M)
    kjer je N = 2^num_qubits, M pa število rešitev.
    """
    N = 2 ** num_qubits
    k_real = (pi / 4.0) * sqrt(N / num_solutions)
    return int(round(k_real))


def apply_diffuser(qc: QuantumCircuit, data_qubits):
    """
    Difuzor za Groverjev algoritem na danem seznamu data_qubits.

    Implementira operacijo:
        D = 2|s><s| - I
    kjer je |s> uniformna superpozicija.
    """
    n = len(data_qubits)

    # H na vse
    for q in data_qubits:
        qc.h(q)
    # X na vse
    for q in data_qubits:
        qc.x(q)

    # multi-controlled Z na zadnjem qubitu (realiziran preko H + MCX + H)
    qc.h(data_qubits[n - 1])
    if n > 1:
        qc.mcx(list(data_qubits[:-1]), data_qubits[n - 1])
    qc.h(data_qubits[n - 1])

    # X nazaj
    for q in data_qubits:
        qc.x(q)
    # H nazaj
    for q in data_qubits:
        qc.h(q)


# =========================
# 4) GRADNJA CELOTNEGA KROGA
# =========================

def build_sat_grover_circuit(num_iterations: int | None = None) -> QuantumCircuit:
    """
    Zgradi Groverjev krog za SAT pristop 4-kraljic:

      - 8 data qubitov (binarno kodiranje 4 vrstic x 2 bita na vrstico)
      - nekaj notranjih ancill, ki jih doda PhaseOracle za CNF

    Koraki:
      1. Zgradimo PhaseOracle iz boolean izraza F(x0..x7).
      2. Na 8 data qubitih pripravimo uniformno superpozicijo.
      3. Izvedemo k iteracij Groverjevega operatorja:
           - orakel (PhaseOracle)
           - difuzor nad 8 data qubiti
      4. Izmerimo samo 8 data qubitov.
    """
    oracle = build_nqueens4_oracle()

    # Koliko qubitov ima orakel skupaj in koliko ancill uporablja?
    total_qubits = oracle.num_qubits
    num_ancillas = oracle.num_ancillas
    num_data = total_qubits - num_ancillas  # pri nas mora biti 8

    if num_data != 8:
        raise ValueError(f"Pričakoval sem 8 data qubitov, dobil pa {num_data}.")

    # Quantum registri v glavnem krogu:
    qr_data = QuantumRegister(num_data, "x")

    if num_ancillas > 0:
        qr_anc = QuantumRegister(num_ancillas, "anc")
        cr = ClassicalRegister(num_data, "c")
        qc = QuantumCircuit(qr_data, qr_anc, cr)
        qubit_mapping = list(qr_data) + list(qr_anc)
    else:
        cr = ClassicalRegister(num_data, "c")
        qc = QuantumCircuit(qr_data, cr)
        qubit_mapping = list(qr_data)

    # Število iteracij: če ni podano, ga ocenimo iz števila rešitev
    if num_iterations is None:
        num_solutions = len(generate_valid_patterns())
        num_iterations = optimal_grover_iterations(num_data, num_solutions)

    # 1) uniformna superpozicija na data qubitih
    qc.h(qr_data)

    # 2) Groverjeve iteracije: orakel + difuzor
    for _ in range(num_iterations):
        # Orakel (CNF → PhaseOracle)
        qc.compose(oracle, qubits=qubit_mapping, inplace=True)
        # Difuzor samo nad data qubiti
        apply_diffuser(qc, qr_data)

    # 3) meritve samo data qubitov
    qc.measure(qr_data, cr)

    return qc


# Hiter sanity-check, če poganjamo circuit.py direktno
if __name__ == "__main__":
    from qiskit_aer import AerSimulator
    from qiskit import transpile

    qc = build_sat_grover_circuit()
    backend = AerSimulator()
    tqc = transpile(qc, backend=backend, optimization_level=1)
    result = backend.run(tqc, shots=1024).result()
    counts = result.get_counts()

    print("Najpogostejša stanja:")
    for state, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(state, cnt)
