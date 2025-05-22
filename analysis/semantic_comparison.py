# use z3 to parse an smt file
import ast
import subprocess
import pandas as pd
from z3 import *
import os

TIMEOUT = 600


def check_z3_smt2(spec: str) -> str:
    """
    Run the Z3 solver on the given SMT-LIB specification and return the result.

    """
    try:
        proc = subprocess.Popen(
            ["z3", "-in"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(input=spec, timeout=TIMEOUT)

        return stdout.strip()
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return "TO"
    except Exception as e:
        return f"ERROR: {e}"


def check_semantic_comparison(spec_1: str, spec_2: str):
    """
    Compare two SMT-LIB specifications using Z3 and return the result.
    The comparison is based on the satisfiability of the negation of the conjunction of the two specifications.
        if both are unsat then they are equivalent
        if both are sat then they are incomparable
        if one is sat and the other is unsat then we have a refinement relation

        the check is very naive and ignores issues like renaming of variables
        it also ignores structures like push and pop and only takes the final list of assertions into account
        it requires some detailed analysis when some spec is unsat to begin with
    Args:
        spec_1 (str): Path to the first SMT-LIB specification.
        spec_2 (str): Path to the second SMT-LIB specification.
    Returns:
        str: "equivalent", "incomparable", "s1_refines_s2", "s2_refines_s1","unknown", or error message.

    """
    removes = ["(get-assignment)"]
    try:
        # Read and parse SMT2 files safely
        with open(spec_1, "r", encoding="utf-8") as f1:
            smt1 = f1.read()
        for remove in removes:
            smt1 = smt1.replace(remove, "")
        with open(spec_2, "r", encoding="utf-8") as f2:
            smt2 = f2.read()
        for remove in removes:
            smt2 = smt2.replace(remove, "")

        a1 = parse_smt2_string(smt1)
        a2 = parse_smt2_string(smt2)

        s1not2 = Solver()
        s1not2.add(a1)
        s1not2.add(Not(And(a2)))
        res_s1not2 = check_z3_smt2(s1not2.to_smt2())

        s2not1 = Solver()
        s2not1.add(a2)
        s2not1.add(Not(And(a1)))
        res_s2not1 = check_z3_smt2(s2not1.to_smt2())

        if res_s1not2 == "unsat" and res_s2not1 == "unsat":
            return "equivalent"
        elif res_s1not2 == "sat" and res_s2not1 == "sat":
            return "incomparable"
        elif res_s1not2 == "unsat" and res_s2not1 == "sat":
            return "s1_refines_s2"
        elif res_s1not2 == "sat" and res_s2not1 == "unsat":
            return "s2_refines_s1"
        else:
            return "unknown"
    except OSError as e:
        print(f"Error comparing {spec_1} and {spec_2}: {e}")
        return "Z3_ERROR"
    except Exception as e:
        print(f"General error comparing {spec_1} and {spec_2}: {e}")
        return "Z3_ERROR"


def write_semanttic_comparison_results():
    saving_counter = 0
    chain_list_df = pd.read_csv("results/fmp_edit_paths_chain_list.csv")
    chain_list_df["derivation_chain"] = chain_list_df["derivation_chain"].apply(
        ast.literal_eval
    )

    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df["check"] = solver_res_df["check"].fillna("[]").apply(ast.literal_eval)
    solver_res_df["basename"] = solver_res_df["file"].apply(
        lambda f: os.path.basename(f)
    )
    check_map = dict(zip(solver_res_df["basename"], solver_res_df["check"]))

    result_rows = []

    for idx, row in chain_list_df.iterrows():
        chain = row["derivation_chain"]
        if len(chain) < 2:
            result_rows.append({"id": row["id"], "semantic_compare": []})
            continue

        sem_results = []
        for i in range(len(chain) - 1):
            spec_1 = f"data/spec/{chain[i]}.smt2"
            spec_2 = f"data/spec/{chain[i+1]}.smt2"
            b1 = os.path.basename(spec_1)
            b2 = os.path.basename(spec_2)
            if "ERROR" in check_map.get(b1, []) or "ERROR" in check_map.get(b2, []):
                print(f"Skipping: {spec_1} and {spec_2}: solver check error")
                sem_results.append("ERROR")
                continue
            if os.path.exists(spec_1) and os.path.exists(spec_2):
                print(f"Comparing: {spec_1} and {spec_2}")
                res = check_semantic_comparison(spec_1, spec_2)
                sem_results.append(res)
            else:
                print(f"Missing: spec file: {spec_1} or {spec_2}")

        result_rows.append({"id": row["id"], "semantic_compare": sem_results})
        saving_counter += 1
        if saving_counter % 50 == 0:
            print(f"Saving intermediate results after {saving_counter} comparisons")
            out_df = pd.DataFrame(result_rows)
            out_df.to_csv("results/chain_semantic_comparison.csv", index=False)

    # Create new DataFrame
    out_df = pd.DataFrame(result_rows)
    out_df.to_csv("results/chain_semantic_comparison.csv", index=False)


def print_consecutive_identical_pairs():
    """
    Count and print the number of consecutive identical pairs in the semantic comparison results.
    The results are read from the CSV file `results/chain_semantic_comparison.csv`.
    """
    df = pd.read_csv("results/chain_semantic_comparison.csv")
    df["semantic_compare"] = df["semantic_compare"].apply(ast.literal_eval)
    total_equivalent = (
        df["semantic_compare"].apply(lambda x: x.count("equivalent")).sum()
    )

    total_incomparable = (
        df["semantic_compare"].apply(lambda x: x.count("incomparable")).sum()
    )
    total_s1_refines_s2 = (
        df["semantic_compare"].apply(lambda x: x.count("s1_refines_s2")).sum()
    )
    total_s2_refines_s1 = (
        df["semantic_compare"].apply(lambda x: x.count("s2_refines_s1")).sum()
    )

    total_unknown = df["semantic_compare"].apply(lambda x: x.count("unknown")).sum()
    total_error = df["semantic_compare"].apply(lambda x: x.count("ERROR")).sum()

    total = (
        total_equivalent
        + total_incomparable
        + total_s1_refines_s2
        + total_s2_refines_s1
        + total_unknown
        + total_error
    )
    print(f"Total: {total}")
    print(f"Total equivalent: {total_equivalent}")
    print(f"Percentage equivalent: {total_equivalent / total * 100:.2f}%")
    print(f"Total incomparable: {total_incomparable}")
    print(f"Percentage incomparable: {total_incomparable / total * 100:.2f}%")
    print(f"Total s1 refines s2: {total_s1_refines_s2}")
    print(f"Percentage s1 refines s2: {total_s1_refines_s2 / total * 100:.2f}%")
    print(f"Total s2 refines s1: {total_s2_refines_s1}")
    print(f"Percentage s2 refines s1: {total_s2_refines_s1 / total * 100:.2f}%")
    print(f"Total unknown: {total_unknown}")
    print(f"Percentage unknown: {total_unknown / total * 100:.2f}%")
    print(f"Total error: {total_error}")
    print(f"Percentage error: {total_error / total * 100:.2f}%")


def save_non_consecutive_equivalent_pairs():
    """
    Count the number of non-consecutive equivalent pairs in the semantic comparison results.
    The results are read from the CSV file `results/fmp_edit_paths_chain_list.csv`.
    The semantic comparison results are obtained from the `fmp-solver-results.csv` file.
    """
    chain_df = pd.read_csv("results/fmp_edit_paths_chain_list.csv")
    chain_df["derivation_chain"] = chain_df["derivation_chain"].apply(ast.literal_eval)

    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df["check"] = solver_res_df["check"].fillna("[]").apply(ast.literal_eval)
    solver_res_df["basename"] = solver_res_df["file"].apply(
        lambda f: os.path.basename(f)
    )
    check_map = dict(zip(solver_res_df["basename"], solver_res_df["check"]))

    results = []
    write_counter = 0
    for idx, row in chain_df.iterrows():
        chain = row["derivation_chain"]
        id_ = row["id"]
        count = 0
        pairs = []
        n = len(chain)
        if n < 3:
            continue
        for i in range(n):
            for j in range(i + 2, n):
                spec_1 = f"data/spec/{chain[i]}.smt2"
                spec_2 = f"data/spec/{chain[j]}.smt2"
                b1 = os.path.basename(spec_1)
                b2 = os.path.basename(spec_2)
                if "ERROR" in check_map.get(b1, []) or "ERROR" in check_map.get(b2, []):
                    continue
                skip = False
                for k in range(i + 1, j):
                    inter_spec_1 = f"data/spec/{chain[k-1]}.smt2"
                    inter_spec_2 = f"data/spec/{chain[k]}.smt2"
                    b_inter_1 = os.path.basename(inter_spec_1)
                    b_inter_2 = os.path.basename(inter_spec_2)
                    if not os.path.exists(inter_spec_1) or not os.path.exists(
                        inter_spec_2
                    ):
                        skip = True
                        break
                    if "ERROR" in check_map.get(
                        b_inter_1, []
                    ) or "ERROR" in check_map.get(b_inter_2, []):
                        skip = True
                        break
                    inter_result = check_semantic_comparison(inter_spec_1, inter_spec_2)
                    if inter_result == "equivalent":
                        skip = True
                        break
                if skip:
                    continue
                result = check_semantic_comparison(spec_1, spec_2)
                if result == "equivalent":
                    count += 1
                    pairs.append((i, j))
                write_counter += 1
                if write_counter % 50 == 0:
                    print(
                        f"Saving intermediate results after {write_counter} comparisons"
                    )
                    pd.DataFrame(results).to_csv(
                        "results/non_consecutive_equivalent_pairs.csv", index=False
                    )
        results.append(
            {"id": id_, "chain": str(chain), "count": count, "pairs": str(pairs)}
        )
    pd.DataFrame(results).to_csv(
        "results/non_consecutive_equivalent_pairs.csv", index=False
    )


def save_non_consecutive_incomparable_pairs():
    chain_df = pd.read_csv("results/fmp_edit_paths_chain_list.csv")
    chain_df["derivation_chain"] = chain_df["derivation_chain"].apply(ast.literal_eval)

    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df["check"] = solver_res_df["check"].fillna("[]").apply(ast.literal_eval)
    solver_res_df["basename"] = solver_res_df["file"].apply(
        lambda f: os.path.basename(f)
    )
    check_map = dict(zip(solver_res_df["basename"], solver_res_df["check"]))

    results = []
    write_counter = 0
    for idx, row in chain_df.iterrows():
        chain = row["derivation_chain"]
        id_ = row["id"]
        count = 0
        pairs = []
        n = len(chain)
        if n < 3:
            continue
        for i in range(n):
            for j in range(i + 2, n):
                spec_1 = f"data/spec/{chain[i]}.smt2"
                spec_2 = f"data/spec/{chain[j]}.smt2"
                b1 = os.path.basename(spec_1)
                b2 = os.path.basename(spec_2)
                if "ERROR" in check_map.get(b1, []) or "ERROR" in check_map.get(b2, []):
                    continue
                skip = False
                for k in range(i + 1, j):
                    inter_spec_1 = f"data/spec/{chain[k-1]}.smt2"
                    inter_spec_2 = f"data/spec/{chain[k]}.smt2"
                    b_inter_1 = os.path.basename(inter_spec_1)
                    b_inter_2 = os.path.basename(inter_spec_2)
                    if not os.path.exists(inter_spec_1) or not os.path.exists(
                        inter_spec_2
                    ):
                        skip = True
                        break
                    if "ERROR" in check_map.get(
                        b_inter_1, []
                    ) or "ERROR" in check_map.get(b_inter_2, []):
                        skip = True
                        break
                    inter_result = check_semantic_comparison(inter_spec_1, inter_spec_2)
                    if inter_result == "incomparable":
                        skip = True
                        break
                if skip:
                    continue
                result = check_semantic_comparison(spec_1, spec_2)
                if result == "incomparable":
                    count += 1
                    pairs.append((i, j))
                write_counter += 1
                if write_counter % 50 == 0:
                    print(
                        f"Saving intermediate results after {write_counter} comparisons"
                    )
                    pd.DataFrame(results).to_csv(
                        "results/non_consecutive_incomparable_pairs.csv", index=False
                    )
        results.append(
            {"id": id_, "chain": str(chain), "count": count, "pairs": str(pairs)}
        )
    pd.DataFrame(results).to_csv(
        "results/non_consecutive_incomparable_pairs.csv", index=False
    )


def save_non_consecutive_s1_refines_s2_pairs():
    chain_df = pd.read_csv("results/fmp_edit_paths_chain_list.csv")
    chain_df["derivation_chain"] = chain_df["derivation_chain"].apply(ast.literal_eval)

    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df["check"] = solver_res_df["check"].fillna("[]").apply(ast.literal_eval)
    solver_res_df["basename"] = solver_res_df["file"].apply(
        lambda f: os.path.basename(f)
    )
    check_map = dict(zip(solver_res_df["basename"], solver_res_df["check"]))

    results = []
    write_counter = 0
    for idx, row in chain_df.iterrows():
        chain = row["derivation_chain"]
        id_ = row["id"]
        count = 0
        pairs = []
        n = len(chain)
        if n < 3:
            continue
        for i in range(n):
            for j in range(i + 2, n):
                spec_1 = f"data/spec/{chain[i]}.smt2"
                spec_2 = f"data/spec/{chain[j]}.smt2"
                b1 = os.path.basename(spec_1)
                b2 = os.path.basename(spec_2)
                if "ERROR" in check_map.get(b1, []) or "ERROR" in check_map.get(b2, []):
                    continue
                skip = False
                for k in range(i + 1, j):
                    inter_spec_1 = f"data/spec/{chain[k-1]}.smt2"
                    inter_spec_2 = f"data/spec/{chain[k]}.smt2"
                    b_inter_1 = os.path.basename(inter_spec_1)
                    b_inter_2 = os.path.basename(inter_spec_2)
                    if not os.path.exists(inter_spec_1) or not os.path.exists(
                        inter_spec_2
                    ):
                        skip = True
                        break
                    if "ERROR" in check_map.get(
                        b_inter_1, []
                    ) or "ERROR" in check_map.get(b_inter_2, []):
                        skip = True
                        break
                    inter_result = check_semantic_comparison(inter_spec_1, inter_spec_2)
                    if inter_result == "s1_refines_s2":
                        skip = True
                        break
                if skip:
                    continue
                result = check_semantic_comparison(spec_1, spec_2)
                if result == "s1_refines_s2":
                    count += 1
                    pairs.append((i, j))
                write_counter += 1
                if write_counter % 50 == 0:
                    print(
                        f"Saving intermediate results after {write_counter} comparisons"
                    )
                    pd.DataFrame(results).to_csv(
                        "results/non_consecutive_s1_refines_s2_pairs.csv", index=False
                    )
        results.append(
            {"id": id_, "chain": str(chain), "count": count, "pairs": str(pairs)}
        )
    pd.DataFrame(results).to_csv(
        "results/non_consecutive_s1_refines_s2_pairs.csv", index=False
    )


def save_non_consecutive_s2_refines_s1_pairs():
    chain_df = pd.read_csv("results/fmp_edit_paths_chain_list.csv")
    chain_df["derivation_chain"] = chain_df["derivation_chain"].apply(ast.literal_eval)

    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df["check"] = solver_res_df["check"].fillna("[]").apply(ast.literal_eval)
    solver_res_df["basename"] = solver_res_df["file"].apply(
        lambda f: os.path.basename(f)
    )
    check_map = dict(zip(solver_res_df["basename"], solver_res_df["check"]))

    results = []
    write_counter = 0
    for idx, row in chain_df.iterrows():
        chain = row["derivation_chain"]
        id_ = row["id"]
        count = 0
        pairs = []
        n = len(chain)
        if n < 3:
            continue
        for i in range(n):
            for j in range(i + 2, n):
                spec_1 = f"data/spec/{chain[i]}.smt2"
                spec_2 = f"data/spec/{chain[j]}.smt2"
                b1 = os.path.basename(spec_1)
                b2 = os.path.basename(spec_2)
                if "ERROR" in check_map.get(b1, []) or "ERROR" in check_map.get(b2, []):
                    continue
                skip = False
                for k in range(i + 1, j):
                    inter_spec_1 = f"data/spec/{chain[k-1]}.smt2"
                    inter_spec_2 = f"data/spec/{chain[k]}.smt2"
                    b_inter_1 = os.path.basename(inter_spec_1)
                    b_inter_2 = os.path.basename(inter_spec_2)
                    if not os.path.exists(inter_spec_1) or not os.path.exists(
                        inter_spec_2
                    ):
                        skip = True
                        break
                    if "ERROR" in check_map.get(
                        b_inter_1, []
                    ) or "ERROR" in check_map.get(b_inter_2, []):
                        skip = True
                        break
                    inter_result = check_semantic_comparison(inter_spec_1, inter_spec_2)
                    if inter_result == "s2_refines_s1":
                        skip = True
                        break
                if skip:
                    continue
                result = check_semantic_comparison(spec_1, spec_2)
                if result == "s2_refines_s1":
                    count += 1
                    pairs.append((i, j))
                write_counter += 1
                if write_counter % 50 == 0:
                    print(
                        f"Saving intermediate results after {write_counter} comparisons"
                    )
                    pd.DataFrame(results).to_csv(
                        "results/non_consecutive_s2_refines_s1_pairs.csv", index=False
                    )
        results.append(
            {"id": id_, "chain": str(chain), "count": count, "pairs": str(pairs)}
        )
    pd.DataFrame(results).to_csv(
        "results/non_consecutive_s2_refines_s1_pairs.csv", index=False
    )


def print_non_consecutive_pairs():
    """
    Count and print the number of non-consecutive pairs in the semantic comparison results.
    The results are read from the CSV file `results/chain_semantic_comparison.csv`.
    The semantic comparison results are obtained from the `fmp-solver-results.csv` file.
    The results are saved to the CSV files `non_consecutive_equivalent_pairs.csv`,
    `non_consecutive_incomparable_pairs.csv`, `non_consecutive_s1_refines_s2_pairs.csv`,
    and `non_consecutive_s2_refines_s1_pairs.csv`.
    """
    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df = solver_res_df[solver_res_df["valid_spec"] == True]
    print(f"Valid specs: {len(solver_res_df)}")
    solver_res_df_wo_error = solver_res_df[
        ~solver_res_df["check"].str.contains("ERROR", na=False)
    ]
    print(f"Valid specs without errors: {len(solver_res_df_wo_error)}")

    # Non-consecutive equivalent pairs
    non_con_equiv_df = pd.read_csv("results/non_consecutive_equivalent_pairs.csv")
    non_con_equiv_df["count"] = non_con_equiv_df["count"].astype(int)
    # sum up the counts
    non_con_equiv_total_count = non_con_equiv_df["count"].sum()
    print(f"Total non-consecutive equivalent pairs: {non_con_equiv_total_count}")
    non_con_equiv_percentage = (
        non_con_equiv_total_count / len(solver_res_df_wo_error)
    ) * 100
    print(
        f"Percentage of non-consecutive equivalent pairs: {non_con_equiv_percentage:.2f}%"
    )

    # Non-consecutive incomparable pairs
    non_con_incomp_df = pd.read_csv("results/non_consecutive_incomparable_pairs.csv")
    non_con_incomp_df["count"] = non_con_incomp_df["count"].astype(int)
    non_con_incomp_total_count = non_con_incomp_df["count"].sum()
    print(f"Total non-consecutive incomparable pairs: {non_con_incomp_total_count}")
    non_con_incomp_percentage = (
        non_con_incomp_total_count / len(solver_res_df_wo_error)
    ) * 100
    print(
        f"Percentage of non-consecutive incomparable pairs: {non_con_incomp_percentage:.2f}%"
    )

    non_con_s1_refines_s2_df = pd.read_csv(
        "results/non_consecutive_s1_refines_s2_pairs.csv"
    )
    non_con_s1_refines_s2_df["count"] = non_con_s1_refines_s2_df["count"].astype(int)
    non_con_s1_refines_s2_total_count = non_con_s1_refines_s2_df["count"].sum()
    print(
        f"Total non-consecutive s1 refines s2 pairs: {non_con_s1_refines_s2_total_count}"
    )
    non_con_s1_refines_s2_percentage = (
        non_con_s1_refines_s2_total_count / len(solver_res_df_wo_error)
    ) * 100
    print(
        f"Percentage of non-consecutive s1 refines s2 pairs: {non_con_s1_refines_s2_percentage:.2f}%"
    )

    non_con_s2_refines_s1_df = pd.read_csv(
        "results/non_consecutive_s2_refines_s1_pairs.csv"
    )
    non_con_s2_refines_s1_df["count"] = non_con_s2_refines_s1_df["count"].astype(int)
    non_con_s2_refines_s1_total_count = non_con_s2_refines_s1_df["count"].sum()
    print(
        f"Total non-consecutive s2 refines s1 pairs: {non_con_s2_refines_s1_total_count}"
    )
    non_con_s2_refines_s1_percentage = (
        non_con_s2_refines_s1_total_count / len(solver_res_df_wo_error)
    ) * 100
    print(
        f"Percentage of non-consecutive s2 refines s1 pairs: {non_con_s2_refines_s1_percentage:.2f}%"
    )
