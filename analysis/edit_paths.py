import ast
import json
import Levenshtein
import numpy as np
import pandas as pd
import os


def fmp_smt_longest_chain_overview(input_file: str, output_file: str):
    """
    Reads a JSON file containing derivation chains, processes the data,
    and writes the longest derivation chains to a CSV file separated by " -> ".
    The JSON file is expected to contain a list of dictionaries with "id" and "parent" keys.
    """
    data = []
    with open(input_file, encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))

    df = pd.DataFrame(data)
    df = df[["id", "parent"]]
    df.columns = ["id", "parent"]

    df["id"] = df["id"].apply(
        lambda x: str(int(x)) if isinstance(x, float) and x.is_integer() else str(x)
    )
    df["parent"] = df["parent"].apply(
        lambda x: str(int(x)) if isinstance(x, float) and x.is_integer() else str(x)
    )

    # Build the derivation map
    derivation_map = dict(zip(df["id"], df["parent"]))

    def get_derivation_chain(start_id, derivation_map):
        chain = [start_id]
        current = start_id
        visited = set()
        while current in derivation_map and current not in visited:
            visited.add(current)
            next_id = derivation_map[current]
            if not next_id:  # Stop if the chain ends
                break
            # Check if the file exists, otherwise link to the next node
            file_path = f"data/spec/{next_id}.smt2"
            if (not os.path.exists(file_path)) and (not file_path.endswith("nan.smt2")):
                print(f"File {file_path} does not exist. Skipping this node.")
                current = next_id  # Skip to the next node
                continue
            chain.append(next_id)
            current = next_id
        return chain

    # Generate all chains
    all_chains = []
    for _, row in df.iterrows():
        chain = get_derivation_chain(row["id"], derivation_map)
        all_chains.append(chain)

    # Remove chains that are subsequences of longer chains
    longest_chains = []
    for chain in all_chains:
        if not any(
            set(chain).issubset(set(other_chain)) and chain != other_chain
            for other_chain in all_chains
        ):
            longest_chains.append(chain)

    # Write the longest chains to the output file
    with open(output_file, "w") as f:
        f.write("id,chain_length,derivation_chain\n")
        for chain in longest_chains:
            f.write(f"{chain[0]},{len(chain)},{' -> '.join(chain)}\n")


def fmp_smt_chain_to_list(input_file: str, output_file: str):
    """
    Reads a CSV file containing derivation chains, processes the data,
    and writes the derivation chains as lists to a new CSV file.
    The CSV file is expected to contain a column "derivation_chain" with chains separated by " -> ".
    """
    df = pd.read_csv(input_file)
    df["id"] = df["id"].apply(
        lambda x: str(int(x)) if isinstance(x, float) and x.is_integer() else str(x)
    )
    for i, row in df.iterrows():
        chain = row["derivation_chain"].split(" -> ")
        chain.reverse()
        df.at[i, "derivation_chain"] = list(chain)
    df.to_csv(output_file, index=False)


def calculate_levenshtein_distance(file_1: str, file_2: str) -> float:
    """
    Calculate the Levenshtein distance between two files.
    If a file does not exist, it is treated as an empty string.
    Args:
        file_1 (str): Path to the first file.
        file_2 (str): Path to the second file.
    Returns:
        float: Levenshtein distance between the two files.
    """
    try:
        with open(file_1, encoding="utf-8") as f:
            s1 = f.read()
    except FileNotFoundError:
        s1 = ""

    try:
        with open(file_2, encoding="utf-8") as f:
            s2 = f.read()
    except FileNotFoundError:
        s2 = ""

    distance = Levenshtein.distance(s1, s2)
    return distance


def fmp_smt_chain_distance() -> None:
    """
    Reads the CSV file (`results/fmp_edit_paths_chain_list.csv`) containing derivation chains,
    calculates the Levenshtein distance between consecutive files in the chains, and writes the
    results to a new CSV file (`results/fmp_edit_paths_chain_levenshtein.csv`).
    The CSV file is expected to contain a column "derivation_chain" with chains as lists.
    """

    input_file = "results/fmp_edit_paths_chain_list.csv"
    df = pd.read_csv(input_file)
    df["parsed_chain"] = df["derivation_chain"].apply(ast.literal_eval)

    data_dir = "data/spec/"
    output_data = []
    for _, row in df.iterrows():
        id = row["id"]
        parsed_chain = row["parsed_chain"]
        chain_len = len(parsed_chain)
        # Skip rows with chains of length less than 3
        if chain_len < 3:
            continue
        distances = []
        for i in range(chain_len - 1):
            # Calculate distance between two files
            s1 = data_dir + str(parsed_chain[i]) + ".smt2"
            s2 = data_dir + str(parsed_chain[i + 1]) + ".smt2"
            distance = calculate_levenshtein_distance(s1, s2)
            distances.append(distance)
        output_row = [id, chain_len, str(distances)]
        output_data.append(output_row)

    output_df = pd.DataFrame(
        output_data,
        columns=["id", "chain_len", "distances"],
    )

    output_file = "results/fmp_edit_paths_chain_levenshtein.csv"
    output_df.to_csv(output_file, index=False)


def edit_path_chain_overview() -> dict:
    """
    Reads the CSV file (`results/fmp_edit_paths_chain_list.csv`) containing derivation chains,
    processes the data, and writes an overview of the edit paths to a new CSV file.
    The CSV file is expected to contain a column "derivation_chain" with chains as lists.

    Returns:
        dict: A dictionary containing the overview of the edit paths.

    """
    fmp_df = pd.read_csv("results/fmp_edit_paths_chain_list.csv")
    fmp_df["derivation_chain"] = fmp_df["derivation_chain"].apply(ast.literal_eval)
    fmp_chain_length = fmp_df["chain_length"]
    fmp_status_df = pd.read_csv("results/fmp_edit_paths_status.csv")
    fmp_status_df["status_chain"] = fmp_status_df["status_chain"].apply(
        ast.literal_eval
    )
    fmp_status_df["filtered_status_chain"] = fmp_status_df["status_chain"].apply(
        lambda statuses: [status for status in statuses if status != "UNKNOWN"]
    )
    fmp_status_df["has_parse_error"] = fmp_status_df["filtered_status_chain"].apply(
        lambda statuses: "ERROR" in statuses
    )
    fmp_status_df["all_parse_error"] = fmp_status_df["filtered_status_chain"].apply(
        lambda statuses: all(status == "ERROR" for status in statuses)
    )

    overview = {
        "Edit Paths": int(len(fmp_df)),
        "With Invalid Scripts (\\%)": round(
            float(fmp_status_df["has_parse_error"].sum()) / len(fmp_df) * 100, 2
        ),
        "Without Valid Scripts (\\%)": round(
            float(fmp_status_df["all_parse_error"].sum()) / len(fmp_df) * 100, 2
        ),
        "Edit Path Length $ge$ 5 (\\%)": round(
            float((fmp_chain_length >= 5).sum()) / fmp_chain_length.count() * 100, 2
        ),
        "Max Edit Path Length": int(fmp_chain_length.max()),
    }

    print(
        fmp_df["chain_length"]
        .describe()
        .to_string(
            index=True,
            header=True,
            float_format="%.2f",
        )
    )

    return overview


def initial_script():
    """
    Reads the CSV file (`results/fmp_edit_paths_chain_list.csv`) containing derivation chains,
    processes the data, and counts the number of unique initial scripts in the chains.
    The CSV file is expected to contain a column "derivation_chain" with chains as lists.
    """
    df = pd.read_csv("results/fmp_edit_paths_chain_list.csv")
    df["parsed_chain"] = df["derivation_chain"].apply(ast.literal_eval)
    # first element of the chain
    df["initial_script"] = df["parsed_chain"].apply(
        lambda x: x[0] if len(x) > 0 else None
    )
    initial_scripts = df["initial_script"].unique()
    print(f"Initial scripts: {len(initial_scripts)}")
    return len(initial_scripts)


def print_levenshtein_distance_table():
    fmp_distance_df = pd.read_csv("results/fmp_edit_paths_chain_levenshtein.csv")
    fmp_distance_df["distances"] = fmp_distance_df["distances"].apply(ast.literal_eval)
    fmp_all_distances = [
        distance for sublist in fmp_distance_df["distances"] for distance in sublist
    ]
    # Drop edit distance 0
    fmp_all_distances = [distance for distance in fmp_all_distances if distance != 0]

    q1, median, q3 = np.percentile(fmp_all_distances, [25, 50, 75])
    max_val = np.max(fmp_all_distances)

    stats = pd.DataFrame(
        [
            ["25th Percentile", f"{q1:.0f}"],
            ["Median", f"{median:.0f}"],
            ["75th Percentile", f"{q3:.0f}"],
            ["Max", f"{max_val:.0f}"],
        ],
        columns=["Statistic", "Levenshtein Distance"],
    )
    print(
        stats.to_string(
            index=False,
        )
    )
