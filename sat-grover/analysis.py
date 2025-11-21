from qiskit import transpile
from qiskit_aer import AerSimulator
import time

from circuit import (
    build_sat_grover_circuit,
    decode_assignment,
    is_valid_assignment,
    generate_valid_patterns,
)


def bitstring_to_bits(bitstring: str):
    """
    Pretvori Qiskit bitstring (npr. '01001110') v seznam bitov LSB-first,
    tj. bits[0] = x0, bits[1] = x1, ...

    Qiskit: levi znak = najvišji klasični bit, desni = c0.
    Pri nas: q[0] -> c0 -> bitstring[-1] -> bits[0].
    """
    return [int(b) for b in bitstring[::-1]]


def format_columns(cols):
    """
    Lepši izpis stolpcev: [1, 3, 0, 2] -> '(r0->c1, r1->c3, r2->c0, r3->c2)'.
    """
    return "(" + ", ".join(f"r{r}->c{c}" for r, c in enumerate(cols)) + ")"


def analyze_sat_grover(num_iterations: int | None = None,
                       shots: int = 4096,
                       optimization_level: int = 1):
    """
    Zažene SAT+Grover pristop za problem 4-kraljic z "pravim" CNF-orakljem.

    Koraki:
      - zgradi vezje z build_sat_grover_circuit (če num_iterations=None,
        uporabi optimalno število iteracij glede na # rešitev),
      - vezje transpila na AerSimulator,
      - simulira meritve,
      - izpiše:
          * globino in število vrat pred/po transpilanju,
          * najpogostejša merjena stanja,
          * verjetnost, da dobimo veljavno postavitev 4-kraljic.
    """
    backend = AerSimulator()

    print("=== Gradnja Groverjevega vezja (SAT pristop, 4-kraljice) ===")
    qc = build_sat_grover_circuit(num_iterations=num_iterations)
    print(f"Število qubitov v vezju: {qc.num_qubits}")
    print(f"Število klasičnih bitov: {qc.num_clbits}")
    print("Globina (pred transpilanjem):", qc.depth())
    print("Število vrat (pred transpilanjem):", qc.count_ops())

    print("\n=== Transpilacija vezja ===")
    t_start = time.time()
    tqc = transpile(qc, backend=backend, optimization_level=optimization_level)
    t_end = time.time()
    print(f"Transpilacija končana v {t_end - t_start:.3f} s")
    print("Globina (po transpilanju):", tqc.depth())
    print("Število vrat (po transpilanju):", tqc.count_ops())

    print("\n=== Simulacija na AerSimulatorju ===")
    t_start = time.time()
    job = backend.run(tqc, shots=shots)
    result = job.result()
    t_end = time.time()
    print(f"Čas simulacije: {t_end - t_start:.3f} s")

    counts = result.get_counts()
    total_shots = sum(counts.values())

    print("\nNajpogostejša merjena stanja (top 10):")
    for bitstring, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        bits = bitstring_to_bits(bitstring)
        cols = decode_assignment(bits)
        valid = is_valid_assignment(bits)
        flag = "✅" if valid else "❌"
        print(f"{bitstring}  ({cnt}x, {cnt / total_shots:.3%})  -> {cols} {flag}")

    # --- analiza pravilnih rešitev ---
    num_correct = 0
    correct_states = []

    for bitstring, cnt in counts.items():
        bits = bitstring_to_bits(bitstring)
        if is_valid_assignment(bits):
            num_correct += cnt
            correct_states.append((bitstring, cnt, decode_assignment(bits)))

    success_prob = num_correct / total_shots if total_shots > 0 else 0.0

    print("\n=== Analiza pravilnih rešitev ===")
    print(f"Skupno število meritev: {total_shots}")
    print(f"Pravilnih meritev: {num_correct} (p = {success_prob:.3%})")

    if correct_states:
        print("Pravilne konfiguracije (bitstring -> stolpci):")
        for bitstring, cnt, cols in sorted(correct_states, key=lambda x: x[1], reverse=True):
            print(f"  {bitstring}  ({cnt}x, {cnt / total_shots:.3%})  -> {format_columns(cols)}")
    else:
        print("Nobena meritev ni dala veljavne postavitve 4-kraljic. 😢")

    # sanity check: koliko rešitev najde klasični CSP/SAT
    valid_patterns = generate_valid_patterns()
    print(f"\nŠtevilo veljavnih rešitev po klasičnem preverjanju: {len(valid_patterns)}")

    return qc, tqc, counts


if __name__ == "__main__":
    analyze_sat_grover()
