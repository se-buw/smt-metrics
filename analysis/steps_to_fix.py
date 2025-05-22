import ast
import os
import numpy as np
import pandas as pd


def create_status_chain_csv():
    """
    Create a CSV file that contains the status of each derivation chain.
    The status can be one of the following:
    - SAT
    - UNSAT
    - ERROR
    - NO_CHECK
    - MULTIPLE_CHECKS
    The CSV file will be saved as "results/fmp_edit_paths_status.csv".
    The derivation chain is a list of file paths that represent the steps taken to derive the final specification.
    """
    chain_df = pd.read_csv("results/fmp_edit_paths_chain_list.csv")
    chain_df["derivation_chain"] = chain_df["derivation_chain"].apply(ast.literal_eval)
    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df["check"] = solver_res_df["check"].fillna("[]").apply(ast.literal_eval)
    solver_res_df = solver_res_df[solver_res_df["valid_spec"] == True]
    check_map = dict(zip(solver_res_df["file"], solver_res_df["check"]))

    result_rows = []
    for _, row in chain_df.iterrows():
        chain = row["derivation_chain"]
        status_chain = []
        for i in range(len(chain)):
            spec_path = f"data/code/{chain[i]}.smt2"
            check_res = check_map.get(spec_path, [])
            if len(check_res) == 0:
                # there is no check-sat in the spec file
                status_chain.append("NO_CHECK")
            elif len(check_res) == 1:
                if check_res[0] == "ERROR":
                    status_chain.append("ERROR")
                elif check_res[0] == "sat":
                    status_chain.append("SAT")
                elif check_res[0] == "unsat":
                    status_chain.append("UNSAT")
            else:
                status_chain.append("MULTIPLE_CHECKS")
        result_rows.append(
            {"id": row["id"], "derivation_chain": chain, "status_chain": status_chain}
        )
    result_df = pd.DataFrame(result_rows)
    result_df.to_csv("results/fmp_edit_paths_status.csv", index=False)


def calculate_syntaxerror_fix_steps(status_chain) -> list:
    """
    Calculate the number of steps to fix the first occurrence of consecutive syntax errors.
    Args:
        status_chain (list): A list of status values (e.g., "ERROR", "SAT", "UNSAT").
    Returns:
        list: A list of steps to fix the first occurrence of consecutive syntax errors.
    """
    steps = []
    i = 0
    while i < len(status_chain):
        if status_chain[i] == "ERROR":
            # Record the first occurrence of consecutive PARSEERRORs
            start = i
            while i + 1 < len(status_chain) and status_chain[i + 1] == "ERROR":
                i += 1
            # Find the next non-PARSEERROR value
            for j in range(i + 1, len(status_chain)):
                if status_chain[j] != "ERROR":
                    steps.append(j - start)
                    break
        i += 1
    return steps


def calculate_unsat_to_sat_steps(status_chain) -> list:
    """Calculate the number of steps to fix the first occurrence of consecutive UNSAT.
    Args:
        status_chain (list): A list of status values (e.g., "ERROR", "SAT", "UNSAT").
    Returns:
        list: A list of steps to fix the first occurrence of consecutive UNSAT.
    """
    steps = []
    i = 0
    while i < len(status_chain):
        if status_chain[i] == "UNSAT":
            # Skip to the last consecutive UNSAT
            while i + 1 < len(status_chain) and status_chain[i + 1] == "UNSAT":
                i += 1
            # Find the next SAT
            for j in range(i + 1, len(status_chain)):
                if status_chain[j] == "SAT":
                    steps.append(j - i)
                    break
        i += 1
    return steps


def save_steps_to_fix_csv():
    """
    Save the steps to fix the first occurrence of consecutive syntax errors and UNSAT to SAT.
    The results will be saved in a CSV file.
    """

    status_df = pd.read_csv("results/fmp_edit_paths_status.csv")
    status_df["status_chain"] = status_df["status_chain"].apply(ast.literal_eval)
    status_df["parseerror_fix_steps"] = status_df["status_chain"].apply(
        calculate_syntaxerror_fix_steps
    )

    status_df["unsat_to_sat_steps"] = status_df["status_chain"].apply(
        calculate_unsat_to_sat_steps
    )
    status_df.to_csv("results/fmp_steps_to_fix.csv", index=False)


def print_steps_to_fix():
    fmp_fix_steps_path = "results/fmp_steps_to_fix.csv"
    fmp_fix_steps_df = pd.read_csv(fmp_fix_steps_path)

    fmp_fix_steps_df["parseerror_fix_steps"] = fmp_fix_steps_df[
        "parseerror_fix_steps"
    ].apply(ast.literal_eval)
    fmp_fix_steps_df["unsat_to_sat_steps"] = fmp_fix_steps_df[
        "unsat_to_sat_steps"
    ].apply(ast.literal_eval)

    fmp_parseerror_fix_steps = [
        step for steps in fmp_fix_steps_df["parseerror_fix_steps"] for step in steps
    ]
    fmp_unsat_to_sat_steps = [
        step for steps in fmp_fix_steps_df["unsat_to_sat_steps"] for step in steps
    ]

    stats = []
    for label, dataset in zip(
        ["Fix Syntax Error", "UNSAT to SAT"],
        [fmp_parseerror_fix_steps, fmp_unsat_to_sat_steps],
    ):
        q1, median, q3 = np.percentile(dataset, [25, 50, 75])
        max_val = np.max(dataset)
        stats.append(
            [label, f"{q1:.0f}", f"{median:.0f}", f"{q3:.0f}", f"{max_val:.0f}"]
        )

    df = pd.DataFrame(stats, columns=["Type", "Q1", "Median", "Q3", "Max"])

    print(
        df.to_string(
            index=False,
        )
    )
