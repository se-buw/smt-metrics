import csv
import os
import re
import pandas as pd


def list_spec_output_files(directory: str) -> list[str]:
    """List all the solver output files in the given directory."""

    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".txt"):
                files.append(os.path.join(root, filename))
    return files


def error_category(
    smt_file_path: str, error_file_path: str, output_file: str, mode: str = "a"
):
    """
    Categorize errors from the SMT file and the error file, and write them to a CSV file.
    Args:
        smt_file_path (str): Path to the SMT file.
        error_file_path (str): Path to the error file.
        output_file (str): Path to the output CSV file.
        mode (str): Mode for writing the output file ('w' for write, 'a' for append).
    Returns:
        None
    """
    with open(error_file_path, "r", encoding="utf-8") as error_file:
        error_lines = error_file.readlines()

    with open(smt_file_path, "r", encoding="utf-8") as smt_file:
        smt_lines = smt_file.readlines()

    # Regex to extract error details
    error_pattern = re.compile(r'\(error "line (\d+) column (\d+): (.+?)"\)')

    # Process errors
    error_details = []
    seen_lines = set()  # To track processed lines
    for line in error_lines:
        match = error_pattern.search(line)
        if match:
            line_number = int(match.group(1))
            column_number = int(match.group(2))
            error_message = match.group(3)

            # Skip if this line has already been processed
            if line_number in seen_lines:
                continue
            seen_lines.add(line_number)

            # Fetch the corresponding line from the SMT file
            if 1 <= line_number <= len(smt_lines):
                smt_line = smt_lines[line_number - 1].strip()
                # Extract the specific part of the line causing the error
                error_context = smt_line.split()[0] if smt_line else "N/A"
            else:
                error_context = "N/A"

            error_details.append(
                {
                    "line": line_number,
                    "column": column_number,
                    "message": error_message,
                    "context": error_context,
                }
            )

    if mode == "w":
        # Write the header to the output file
        with open(output_file, "w", newline="", encoding="utf-8") as output_file:
            writer = csv.writer(output_file, quoting=csv.QUOTE_ALL)
            writer.writerow(
                ["smt_file_path", "error_message", "(line, column)", "context"]
            )
    # Write the error details to the output file
    elif mode == "a":
        with open(output_file, "a", newline="", encoding="utf-8") as output_file:
            writer = csv.writer(output_file, quoting=csv.QUOTE_ALL)
            for error in error_details:
                writer.writerow(
                    [
                        smt_file_path,
                        error["message"],
                        f"({error['line']}, {error['column']})",
                        error["context"].replace("(", "").replace(")", ""),
                    ]
                )


def create_error_category_csv():
    """
    Create a CSV file for error categorization.
    The CSV file will contain the error messages and
    their corresponding categories (i.e., in which command they occur).
    The file is saved as `results/fmp_error_category.csv`.
    """
    error_paths = list_spec_output_files("data/spec_output/")
    error_category(
        "data/spec/1.smt2",
        "data/spec_output/1.txt",
        "results/fmp_error_category.csv",
        mode="w",
    )
    for error_path in error_paths:
        # Extract the corresponding SMT file path
        smt_file_path = error_path.replace("data/spec_output/", "data/spec/").replace(
            ".txt", ".smt2"
        )
        if os.path.exists(smt_file_path):
            error_category(
                smt_file_path, error_path, "results/fmp_error_category.csv", mode="a"
            )
        else:
            print(f"SMT file not found for {error_path}")


def categorize_errors(input_csv: str, output_csv: str):
    """
    Categorize errors based on predefined categories and save to a new CSV file.
    Args:
        input_csv (str): Path to the input CSV file containing error messages.
        output_csv (str): Path to the output CSV file for categorized errors.
    Returns:
        None
    """
    categories = {
        "ambiguous constant reference": r"ambiguous constant reference",
        "array operation requires one sort parameter": r"array operation requires one sort parameter",
        "command is only available in interactive mode": r"command is only available in interactive mode",
        "datatype constructors have not been created": r"datatype constructors have not been created",
        "domain sort * and parameter * do not match": r"domain sort (.*?) and parameter (.*?) do not match",
        "expecting one integer parameter to bit-vector sort": r"expecting one integer parameter to bit-vector sort",
        "failed to open file": r"failed to open file (.+)",
        "function expects arity+1 rational parameters": r"function expects arity\+1 rational parameters",
        "invalid array sort definition": r"invalid array sort definition(.*?)",
        "invalid assert command": r"invalid assert command(.*?)",
        "invalid attributed expression": r"invalid attributed expression(.*?)",
        "invalid bit-vector literal": r"invalid bit-vector literal(.*?)",
        "invalid command argument": r"invalid command argument(.*?)",
        "invalid command": r"invalid command(.*?)",
        "invalid const array definition": r"invalid const array definition(.*?)",
        "invalid constant declaration": r"invalid constant declaration(.*?)",
        "invalid constant definition": r"invalid constant definition(.*?)",
        "invalid constructor declaration": r"invalid constructor declaration(.*?)",
        "invalid datatype declaration": r"invalid datatype declaration(.*?)",
        "invalid declaration": r"invalid declaration(.*?)",
        "invalid expression": r"invalid expression(.*?)",
        "invalid function application": r"invalid function application(.*?)",
        "invalid function declaration": r"invalid function declaration(.*?)",
        "invalid function/constant definition": r"invalid function/constant definition(.*?)",
        "Invalid function name": r"Invalid function name(.*?)",
        "invalid get-value command": r"invalid get-value command(.*?)",
        "invalid indexed identifier": r"invalid indexed identifier(.*?)",
        "invalid list of sorted variables": r"invalid list of sorted variables(.*?)",
        "invalid named expression, declaration already defined with this name *": r"invalid named expression(.*?)",
        "invalid non-Boolean sort applied to Pseudo-Boolean relation": r"invalid non-Boolean sort applied to Pseudo-Boolean relation(.*?)",
        "invalid number of parameters to sort constructor": r"invalid number of parameters to sort constructor(.*?)",
        "invalid pattern binding, '(' expected got *": r"invalid pattern binding(.*?)",
        "invalid pop command, argument is greater than the current stack depth": r"invalid pop command(.*?)",
        "invalid push command, integer expected": r"invalid push command(.*?)",
        "invalid qualified/indexed identifier, '_' or 'as' expected": r"invalid qualified/indexed identifier(.*?)",
        "invalid quantified expression, syntax error: *": r"invalid quantified expression(.*?)",
        "invalid quantifier, list of sorted variables is empty": r"invalid quantifier, list of sorted variables is empty(.*?)",
        "invalid s-expression, unexpected end of file": r"invalid s-expression, unexpected end of file(.*?)",
        "invalid sort declaration": r"invalid sort declaration(.*?)",
        "invalid sort,": r"invalid sort(.*?)",
        "invalid sorted variable": r"invalid sorted variable(.*?)",
        "logic does not support *": r"logic does not support(.*?)",
        "logic must be set before initialization": r"logic must be set before initialization(.*?)",
        "map expects to take as many arguments as the function being mapped, it was given * but expects *": r"map expects to take as many arguments as the function being mapped(.*?)",
        "model is not available": r"model is not available(.*?)",
        "named expression already defined": r"named expression already defined(.*?)",
        "no arguments supplied to arithmetical operator": r"no arguments supplied to arithmetical operator(.*?)",
        "Parsing function declaration": r"Parsing function declaration(.*?)",
        "quantifier body must be a Boolean expression": r"quantifier body must be a Boolean expression(.*?)",
        "select requires * arguments, but was provided with * arguments": r"select requires (.*?) arguments, but was provided with(.*?)",
        "select takes at least two arguments": r"select takes at least two arguments(.*?)",
        "sort already defined *": r"sort already defined(.*?)",
        "sort constructor expects parameters": r"sort constructor expects parameters(.*?)",
        "sort mismatch": r"Sort mismatch(.*?)",
        "Sorts * and * are incompatible": r"Sorts (.*?) and (.*?) incompatible(.*?)",
        "store expects the first argument *": r"store expects the first argument(.*?)",
        "store takes at least * arguments": r"store takes at least(.*?) arguments(.*?)",
        "the logic has already been set": r"the logic has already been set(.*?)",
        "unbounded objectives on quantified constraints is not supported": r"unbounded objectives on quantified constraints is not supported(.*?)",
        "unexpected character": r"unexpected character(.*?)",
        "unexpected end of *": r"unexpected end of(.*?)",
        "Unexpected number of arguments": r"Unexpected number of arguments(.*?)",
        "unexpected token used as datatype name": r"unexpected token used as datatype name(.*?)",
        "unknown constant *": r"unknown constant(.*?)",
        "unknown sort *": r"unknown sort(.*?)",
        "unsat assumptions construction is not enabled": r"unsat assumptions construction is not enabled(.*?)",
        "unsat core construction is not enabled": r"unsat core construction is not enabled(.*?)",
        "unsat core is not available": r"unsat core is not available(.*?)",
        "Wrong number of arguments (0) passed to function *": r"Wrong number of arguments(.*?) passed to function(.*?)",
    }

    with open(input_csv, "r", encoding="utf-8") as infile, open(
        output_csv, "w", newline="", encoding="utf-8"
    ) as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["category"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)

        writer.writeheader()
        for row in reader:
            error_message = row["error_message"]
            category = "Uncategorized"
            for cat, pattern in categories.items():
                if re.search(pattern, error_message, re.IGNORECASE):
                    category = cat
                    break
            row["category"] = category
            writer.writerow(row)


def save_contexts_count():
    df = pd.read_csv("results/fmp_error_category.csv")
    x = df["context"].value_counts()
    x.to_csv("results/tables/context_counts.csv", quoting=csv.QUOTE_ALL)


def print_top_10_categories():
    """
    Print the top 10 error categories and their counts and percentages.
    """
    df = pd.read_csv("results/fmp_error_category_categorized.csv")
    df = df[["category"]]
    # top 10 categories with counts and percentages
    count = df["category"].value_counts()
    count = count[:10]
    count = count.reset_index()
    count.columns = ["category", "count"]
    count["percentage"] = (count["count"] / df.shape[0]) * 100
    count = count.sort_values(by="count", ascending=False)
    count["percentage"] = count["percentage"].round(2)
    count["percentage"] = count["percentage"].astype(str) + "\\%"

    print(
        count.to_string(
            index=False,
            header=True,
        )
    )

def print_error_context_counts():
    df = pd.read_excel("results/fmp_error_context_counts.xlsx", sheet_name="context_counts")
    print(df.iloc[0:16, 7:9].to_string(index=False, header=False))


