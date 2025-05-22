import ast
import hashlib
import os
import pandas as pd
from collections import defaultdict


def compute_file_hash(file_path):
    """Compute the MD5 hash of a file's content.
    Args:
        file_path (str): Path to the file.
    Returns:
        str: MD5 hash of the file's content.
    """
    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read()
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def list_files(directory: str) -> list[str]:
    """List all SMT-LIB files in a directory and its subdirectories.
    Args:
        directory (str): Path to the directory.
    Returns:
        list: List of paths to SMT-LIB files.
    """
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".smt2"):
                files.append(os.path.join(root, filename))
    return files


def syntactic_equivalences():
    """Find syntactic equivalences among SMT-LIB files in the specified directory.
    And save the results to a CSV file.
    Args:
        None
    """
    spec_path = list_files("data/spec/")
    print(f"Found {len(spec_path)} files in the directory.")
    file_hashes = {}
    for spec in spec_path:
        file_hashes[spec] = compute_file_hash(spec)
    syntactic_equivalences = []
    for i, spec1 in enumerate(spec_path):
        for j in range(i + 1, len(spec_path)):
            spec2 = spec_path[j]
            if file_hashes[spec1] == file_hashes[spec2]:
                print(f"Files {spec1} and {spec2} are syntactically equivalent")
                syntactic_equivalences.append((spec1, spec2))
    pd.DataFrame(syntactic_equivalences, columns=["file1", "file2"]).to_csv(
        "results/fmp_syntactic_equivalences.csv", index=False
    )


def print_syntactic_uniqueness() -> dict:
    """Print the syntactic uniqueness overview.
    Args:
        None
    Returns:
        dict: Overview of syntactic uniqueness.
    """
    fmp_df = pd.read_csv("results/fmp_syntactic_equivalences.csv")
    fmp_duplicate = pd.concat([fmp_df["file1"], fmp_df["file2"]]).unique()
    fmp_duplicate = set(fmp_duplicate)

    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df = solver_res_df[solver_res_df["valid_spec"] == True]
    solver_res_df["check"] = solver_res_df["check"].fillna("[]").apply(ast.literal_eval)
    solver_res_df["basename"] = solver_res_df["file"].apply(
        lambda f: os.path.basename(f)
    )
    check_map = dict(zip(solver_res_df["basename"], solver_res_df["check"]))
    valid_spec = solver_res_df["file"].unique()
    valid_spec = [path.replace("/code/", "/spec/") for path in valid_spec]
    valid_spec = set(valid_spec)
    fmp_unique = valid_spec - fmp_duplicate

    correct_unique_spec = 0
    error_unique_spec = 0
    for file in fmp_duplicate:
        bp = os.path.basename(file)
        if "ERROR" in check_map.get(bp, []):
            error_unique_spec += 1
        else:
            correct_unique_spec += 1

    consecutive_identical = print_consecutive_equivalences()

    fmp_overview = {
        "Syntactically Unique Scripts": len(fmp_unique),
        "% Syntactically Unique Scripts": (len(fmp_unique) / len(valid_spec)) * 100,
        "Syntactically Correct Scripts (in unique scripts)": correct_unique_spec,
        "% Syntactically Correct Scripts (in unique scripts)": (
            correct_unique_spec / len(fmp_unique)
        )
        * 100,
        "Syntactically Incorrect Scripts (in unique scripts)": error_unique_spec,
        "% Syntactically Incorrect Scripts (in unique scripts)": (
            error_unique_spec / len(fmp_unique)
        )
        * 100,
        "Consecutive Identical Scripts": consecutive_identical["consecutive_identical"],
        "% Consecutive Identical Scripts": consecutive_identical[
            "consecutive_identical_percentage"
        ],
        "Non-Consecutive Identical Scripts": consecutive_identical[
            "non_consecutive_identical"
        ],
        "% Non-Consecutive Identical Scripts": consecutive_identical[
            "non_consecutive_identical_percentage"
        ],
    }
    print(f"Syntactically Unique Scripts: {len(fmp_unique)}")
    print(
        f"% Syntactically Unique Scripts: {(len(fmp_unique) / len(valid_spec)) * 100:.2f}%"
    )
    print(
        f"Syntactically Correct Scripts (in unique scripts): {correct_unique_spec}"
    )
    print(
        f"% Syntactically Correct Scripts (in unique scripts): {(correct_unique_spec / len(fmp_unique)) * 100:.2f}%"
    )
    print(
        f"Syntactically Incorrect Scripts (in unique scripts): {error_unique_spec}"
    )
    print(
        f"% Syntactically Incorrect Scripts (in unique scripts): {(error_unique_spec / len(fmp_unique)) * 100:.2f}%"
    )
    print(
        f"Consecutive Identical Scripts: {consecutive_identical['consecutive_identical']}"
    )
    print(
        f"% Consecutive Identical Scripts: {consecutive_identical['consecutive_identical_percentage']:.2f}%"
    )
    print(
        f"Non-Consecutive Identical Scripts: {consecutive_identical['non_consecutive_identical']}"
    )
    print(
        f"% Non-Consecutive Identical Scripts: {consecutive_identical['non_consecutive_identical_percentage']:.2f}%"
    )
    return fmp_overview


def print_consecutive_equivalences():
    """Find consecutive syntactic equivalences among SMT-LIB files in the specified directory.
    and save the results to a CSV file.
    Args:
        None
    Returns:
        dict: Overview of consecutive syntactic equivalences.
    """
    df = pd.read_csv("results/fmp_edit_paths_chain_list.csv")
    df["derivation_chain"] = df["derivation_chain"].apply(ast.literal_eval)

    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df["check"] = solver_res_df["check"].fillna("[]").apply(ast.literal_eval)
    solver_res_df["basename"] = solver_res_df["file"].apply(
        lambda f: os.path.basename(f)
    )
    check_map = dict(zip(solver_res_df["basename"], solver_res_df["check"]))

    file_hashes = {}
    all_files = set()

    # Compute hashes for all files
    for chain in df["derivation_chain"]:
        for file in chain:
            if file not in file_hashes:
                file_path = f"data/spec/{str(file)}.smt2"
                basename = os.path.basename(file_path)
                if "ERROR" in check_map.get(basename, []):
                    continue
                if not os.path.exists(file_path):
                    continue
                file_hashes[file] = compute_file_hash(file_path)
            all_files.add(file)

    # Mapping of hashes to file names
    hash_to_files = defaultdict(set)
    for file, h in file_hashes.items():
        if h:
            hash_to_files[h].add(file)

    # Identify identical files
    identical_files = {h: files for h, files in hash_to_files.items() if len(files) > 1}

    # Identify consecutive identical files
    consecutive_identical = []
    non_consecutive_identical = []

    for chain in df["derivation_chain"]:
        previous_hash = None
        seen_hashes = set()
        for file in chain:
            file_hash = file_hashes.get(file)
            if not file_hash:
                continue

            # Check for consecutive identical files
            if file_hash == previous_hash:
                consecutive_identical.append(file)

            # Check for non-consecutive identical files
            elif file_hash in seen_hashes:
                non_consecutive_identical.append(file)

            seen_hashes.add(file_hash)
            previous_hash = file_hash

    result = {
        "consecutive_identical": len(consecutive_identical),
        "consecutive_identical_percentage": len(consecutive_identical)
        / len(all_files)
        * 100,
        "non_consecutive_identical": len(non_consecutive_identical),
        "non_consecutive_identical_percentage": len(non_consecutive_identical)
        / len(all_files)
        * 100,
    }
    print(f"Consecutive identical files: {result['consecutive_identical']}")
    print(
        f"Percentage of consecutive identical files: {result['consecutive_identical_percentage']:.2f}%"
    )
    print(
        f"Non-consecutive identical files: {result['non_consecutive_identical']}"
    )
    print(
        f"Percentage of non-consecutive identical files: {result['non_consecutive_identical_percentage']:.2f}%"
    )
    return result
