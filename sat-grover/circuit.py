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

#for calculating optimal iterations
def is_valid_assignment(bits):

    cols = decode_assignment(bits)

    if len(set(cols)) != 4:
        return False
    
    for i in range(4):
        for j in range(i + 1, 4):
            if abs(i - j) == abs(cols[i] - cols[j]):
                return False

    return True

# classical way of finding all valid patterns
def generate_valid_patterns():
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


    def v(idx):
        return f"x{idx}"

    def row_bits(r):

        b0 = v(2 * r)
        b1 = v(2 * r + 1)
        return b0, b1

    clauses = []

    # Stolpčni pogoji: col(r1) != col(r2) za vsako dvojico vrstic ----
    # col(r) = (b1, b0) v {0,1,2,3}
    # col(r1) != col(r2)   <=>   (b1_r1 XOR b1_r2) OR (b0_r1 XOR b0_r2)

    for r1 in range(4):
        for r2 in range(r1 + 1, 4):
            b0_r1, b1_r1 = row_bits(r1)
            b0_r2, b1_r2 = row_bits(r2)
            col_diff = f"(({b1_r1} ^ {b1_r2}) | ({b0_r1} ^ {b0_r2}))"
            clauses.append(col_diff)

    def col_eq_expr(r, col_val):

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
    expr = _nqueens4_boolean_expression()
    var_order = [f"x{i}" for i in range(8)]  
    oracle = PhaseOracle(expr, var_order=var_order)
    return oracle


# =========================
# 3) GROVERJEVE ITERACIJE
# =========================

def optimal_grover_iterations(num_qubits: int, num_solutions: int) -> int:
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

    oracle = build_nqueens4_oracle()


    total_qubits = oracle.num_qubits
    num_ancillas = oracle.num_ancillas
    num_data = total_qubits - num_ancillas  


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
    num_solutions = None
    if num_iterations is None:
        num_solutions = len(generate_valid_patterns())
        num_iterations = optimal_grover_iterations(num_data, num_solutions)

    num_iterations = int(num_iterations)

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

    metadata = dict(qc.metadata) if qc.metadata else {}
    metadata["num_iterations"] = num_iterations
    metadata["num_data_qubits"] = num_data
    metadata["num_ancillas"] = num_ancillas
    if num_solutions is not None:
        metadata["num_solutions"] = num_solutions
    qc.metadata = metadata

    return qc


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
