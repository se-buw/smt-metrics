import ast
import json
import z3
import re
import pandas as pd
from sexpdata import loads

from typing import Tuple


def tokenize_smtlib_script(filepath: str) -> loads:
    """
    Tokenize the SMT-LIB script in the given file.

    Args:
        filepath (str): Path to the SMT-LIB script file.

    Returns:
        list: List of tokens from the SMT-LIB script.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            script = f.read()
        # Remove comments
        script = re.sub(r";.*", "", script)
        # Wrap in parens to parse multiple top-level commands
        sexp = loads(f"({script})")
        return sexp
    except Exception as e:
        print(f"Error tokenizing SMT-LIB: {e}")
        return None


def traverse_sexp_max_depth(sexp, depth=0) -> int:
    """
    Traverse the S-expression and find the maximum depth.
    Args:
        sexp: The S-expression to traverse.
        depth: The current depth of the traversal.
    Returns:
        int: The maximum depth of the S-expression.
    """
    if isinstance(sexp, list):
        if not sexp:
            return depth
        max_sub_depth = depth
        for item in sexp:
            sub_depth = traverse_sexp_max_depth(item, depth + 1)
            if sub_depth > max_sub_depth:
                max_sub_depth = sub_depth
        return max_sub_depth
    return depth


def calculate_max_nesting_depth(filepath: str) -> int:
    """
    Calculate the maximum nesting depth of the S-expression in the given file.
    Args:
        filepath (str): Path to the SMT-LIB script file.
    Returns:
        int: The maximum nesting depth of the S-expression.
    """
    try:
        sexp = tokenize_smtlib_script(filepath)
        if sexp is None:
            return 0
        max_depth = traverse_sexp_max_depth(sexp)
        return max_depth
    except Exception as e:
        print(f"Error calculating max nesting depth: {e}")
        return 0


def analyze_smt_lib_scripts_textually(filepath: str) -> Tuple[int, dict]:
    """
    Analyze the SMT-LIB scripts in the given file and
    effective lines of code (ELOC) and the count of commands.

    Args:
        filepath (str): Path to the SMT-LIB script file.
    """

    eloc = 0
    known_textual_command_keys = [
        "assert",
        "declare-const",
        "declare-fun",
        "get-value",
        "define-fun",
        "get-model",
        "declare-datatype",
        "ite",
        "check-sat",
        "eval",
        "define-sort",
        "exists",
        "forall",
        "declare-sort",
        "implies",
        "push",
        "pop",
        "set-logic",
    ]

    raw_command_patterns = {
        "assert": r"^\(\s*assert",
        "declare-const": r"^\(\s*declare-const",
        "declare-fun": r"^\(\s*declare-fun",
        "get-value": r"^\(\s*get-value",
        "define-fun": r"^\(\s*define-fun",
        "get-model": r"^\(\s*get-model",
        "declare-datatype": r"^\(\s*declare-datatype",
        "ite": r"^\(\s*ite",
        "check-sat": r"^\(\s*check-sat\s*\)",
        "eval": r"^\(\s*eval",
        "define-sort": r"^\(\s*define-sort",
        "exists": r"^\(\s*exists",
        "forall": r"^\(\s*forall",
        "implies": r"^\(\s*implies",
        "push": r"^\(\s*push",
        "pop": r"^\(\s*pop",
        "set-logic": r"^\(\s*set-logic",
    }

    command_counts = {key: 0 for key in known_textual_command_keys}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            if stripped_line.startswith(";"):
                continue
            eloc += 1
            for cmd_name, pattern in raw_command_patterns.items():
                if re.search(pattern, stripped_line):
                    if (
                        cmd_name in command_counts
                    ):  # Ensure we only count pre-defined commands
                        command_counts[cmd_name] += 1
                    break

    except FileNotFoundError:
        return None, {key: pd.NA for key in known_textual_command_keys}
    except Exception as e:
        print(f"Error processing file textually: {e}")
        return None, {key: pd.NA for key in known_textual_command_keys}

    return eloc, command_counts


def analyze_smt_lib_with_z3(filepath: str) -> dict:
    """
    Analyze the SMT-LIB scripts in the given file using Z3
    and extract the number of assertions, distinct
    uninterpreted functions/constants, and distinct sorts.

    Args:
        filepath (str): Path to the SMT-LIB script file.
    """
    s = z3.Solver()
    g = z3.Goal()

    try:
        parsed_assertions = z3.parse_smt2_file(filepath)
        g.add(parsed_assertions)
        s.add(g)

        num_z3_assertions = len(s.assertions())
        declared_funcs_z3 = set()
        declared_sorts_z3 = set()
        processed_asts = set()

        def visit_ast(expr):
            if expr in processed_asts or not hasattr(expr, "decl"):
                return
            processed_asts.add(expr)

            if z3.is_app(expr):
                decl = expr.decl()
                if decl.kind() == z3.Z3_OP_UNINTERPRETED:
                    declared_funcs_z3.add(str(decl))
                current_sort = expr.sort()
                if hasattr(current_sort, "name"):
                    declared_sorts_z3.add(str(current_sort.name()))
                for i in range(expr.num_args()):
                    arg = expr.arg(i)
                    arg_sort = arg.sort()
                    if hasattr(arg_sort, "name"):
                        declared_sorts_z3.add(str(arg_sort.name()))
                    visit_ast(arg)
            elif z3.is_quantifier(expr):
                visit_ast(expr.body())

        for assertion_ast in s.assertions():
            visit_ast(assertion_ast)

        return {
            "num_z3_processed_assertions": num_z3_assertions,
            "num_distinct_z3_uninterpreted_funcs_consts": len(declared_funcs_z3),
            "distinct_z3_uninterpreted_funcs_consts_details": list(declared_funcs_z3),
            "num_distinct_z3_sorts": len(declared_sorts_z3),
            "distinct_z3_sorts_details": list(declared_sorts_z3),
            "z3_warning": "Z3 analysis focuses on asserted formulas. Command counts (check-sat etc.) are from textual scan.",
        }

    except z3.Z3Exception as e:
        return {
            "z3_error": str(e),
            "z3_warning": "Z3 could not fully parse/analyze. Z3 results might be incomplete.",
        }
    except FileNotFoundError:
        return {"z3_error": "File not found for Z3 analysis"}
    except Exception as e:
        return {"z3_error": f"General Error in Z3 processing: {e}"}


def create_dataframe_from_analysis(filepath: str) -> pd.DataFrame:
    """
    Create a DataFrame from the analysis of the SMT-LIB scripts.

    Args:
        filepath (str): Path to the SMT-LIB script file.

    Returns:
        pd.DataFrame: DataFrame containing the analysis results.
    """
    data_for_df = {"filepath": filepath}

    known_textual_command_keys = [
        "assert",
        "declare-const",
        "declare-fun",
        "get-value",
        "define-fun",
        "get-model",
        "declare-datatype",
        "ite",
        "check-sat",
        "eval",
        "define-sort",
        "exists",
        "forall",
        "declare-sort",
        "implies",
        "push",
        "pop",
        "set-logic",
    ]

    # --- Textual Analysis ---
    eloc, textual_command_counts = analyze_smt_lib_scripts_textually(filepath)

    if eloc is not None:
        data_for_df["eloc"] = eloc
    else:  # eloc is None, implies error during textual analysis
        data_for_df["eloc"] = pd.NA

    for cmd_key in known_textual_command_keys:
        col_name = f'textual_{cmd_key.replace("-", "_")}'
        if textual_command_counts and cmd_key in textual_command_counts:
            data_for_df[col_name] = textual_command_counts[cmd_key]
        elif eloc is None:  # If ELOC failed, textual counts are NA
            data_for_df[col_name] = pd.NA
        else:  # ELOC succeeded, but this specific command was 0 or not found by pattern
            data_for_df[col_name] = 0

    # Calculate max nesting depth
    data_for_df["max_nesting_depth"] = calculate_max_nesting_depth(filepath)

    # --- Z3 API Analysis ---
    z3_analysis_results = analyze_smt_lib_with_z3(filepath)
    if z3_analysis_results:
        data_for_df["z3_error"] = z3_analysis_results.get(
            "z3_error", None
        )  # Use None if no error key
        data_for_df["z3_warning"] = z3_analysis_results.get("z3_warning", None)

        if (
            "z3_error" not in z3_analysis_results
            or z3_analysis_results["z3_error"] is None
        ):
            data_for_df["z3_processed_assertions"] = z3_analysis_results.get(
                "num_z3_processed_assertions", pd.NA
            )
            data_for_df["z3_distinct_uninterpreted_funcs_consts"] = (
                z3_analysis_results.get(
                    "num_distinct_z3_uninterpreted_funcs_consts", pd.NA
                )
            )
            data_for_df["z3_distinct_sorts"] = z3_analysis_results.get(
                "num_distinct_z3_sorts", pd.NA
            )
        else:
            data_for_df["z3_processed_assertions"] = pd.NA
            data_for_df["z3_distinct_uninterpreted_funcs_consts"] = pd.NA
            data_for_df["z3_distinct_sorts"] = pd.NA
    else:
        data_for_df["z3_error"] = "Z3 analysis function returned no results"
        data_for_df["z3_warning"] = None
        data_for_df["z3_processed_assertions"] = pd.NA
        data_for_df["z3_distinct_uninterpreted_funcs_consts"] = pd.NA
        data_for_df["z3_distinct_sorts"] = pd.NA

    df = pd.DataFrame([data_for_df])

    column_order = ["filepath", "eloc", "max_nesting_depth"]
    for cmd_key in known_textual_command_keys:
        column_order.append(f'textual_{cmd_key.replace("-", "_")}')
    column_order.extend(
        [
            "z3_processed_assertions",
            "z3_distinct_uninterpreted_funcs_consts",
            "z3_distinct_sorts",
            "z3_error",
            "z3_warning",
        ]
    )

    df = df.reindex(columns=column_order)
    return df


def save_dataset_characteristics_to_csv():
    """
    Save the dataset characteristics to a CSV file in
    `results/fmp_dataset_characteristics.csv`
    """
    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df = solver_res_df[solver_res_df["valid_spec"] == True]
    valid_spec_paths = solver_res_df["file"].tolist()
    valid_spec_paths = [path.replace("/code/", "/spec/") for path in valid_spec_paths]
    res_df = pd.DataFrame()
    counter = 0
    for spec_path in valid_spec_paths:
        res_df = pd.concat(
            [res_df, create_dataframe_from_analysis(spec_path)], ignore_index=True
        )
        if counter % 50 == 0:
            res_df.to_csv(
                "results/fmp_dataset_characteristics.csv", index=False, encoding="utf-8"
            )
        counter += 1

    res_df.to_csv(
        "results/fmp_dataset_characteristics.csv", index=False, encoding="utf-8"
    )


def error_analysis():
    """
    Perform error analysis on the dataset characteristics
    and display the results.
    """
    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df = solver_res_df[solver_res_df["valid_spec"] == True]
    # filter ERROR
    print(f"Number of valid specs: {len(solver_res_df)}")
    solver_res_df_wo_error = solver_res_df[
        ~solver_res_df["check"].str.contains("ERROR", na=False)
    ]

    print(f"Number of valid specs without ERROR: {len(solver_res_df_wo_error)}")
    print(
        f"Number of valid specs with ERROR: {len(solver_res_df) - len(solver_res_df_wo_error)}"
    )
    print(
        f"Percentage of valid specs with ERROR: {(len(solver_res_df) - len(solver_res_df_wo_error)) / len(solver_res_df) * 100:.2f}%"
    )
    print(
        f"Percentage of valid specs without ERROR: {len(solver_res_df_wo_error) / len(solver_res_df) * 100:.2f}%"
    )


def incremental_scripts():
    """
    Display the number of valid scripts with and without incremental scripts in the dataset
    """
    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df = solver_res_df[solver_res_df["valid_spec"] == True]
    solver_res_df = solver_res_df["check"].apply(ast.literal_eval)
    solver_res_df_inc = solver_res_df[solver_res_df.apply(lambda x: len(x) > 1)]
    print(f"Number of valid specs with incremental scripts: {len(solver_res_df_inc)}")

    solver_res_df_non_inc = solver_res_df[solver_res_df.apply(lambda x: len(x) == 1)]
    print(
        f"Number of valid specs without incremental scripts: {len(solver_res_df_non_inc)}"
    )


def time_taken_by_the_solver():
    """
    Display the time taken by the solver
    """
    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df = solver_res_df[solver_res_df["valid_spec"] == True]
    solver_res_df = solver_res_df[solver_res_df["time_taken"].notna()]
    solver_res_df["time_taken"] = solver_res_df["time_taken"].astype(float)
    print(solver_res_df["time_taken"].describe())
    with open(
        "results/tables/fmp_dataset_characteristics.txt", "a", encoding="utf-8"
    ) as f:
        f.write(
            "\n\nTime taken by the solver:\n"
            + str(solver_res_df["time_taken"].describe())
        )


def count_smtlib_logics():
    """
    Count the number of different SMT-LIB logics (with typo) in the dataset
    """
    logics = []
    with open("data/json/fmp_smtlib.json", "r", encoding="utf-8") as f:
        logic_regex = re.compile(r"^\s*\(\s*set-logic\s+(\w+)")
        lines = f.readlines()
        for line in lines:
            obj = json.loads(line)
            obj["code"] = re.sub(r";.*", "", obj["code"])
            logic = logic_regex.findall(obj["code"])
            logics.append(logic[0] if logic else None)
    logics = pd.Series(logics)
    # remove None values
    logics = logics[logics.notna()]
    print(logics.value_counts())
    print(len(logics.unique()))


def print_dataset_characteristics():
    """
    Display the dataset characteristics in a table format
    """
    df = pd.read_csv("results/fmp_dataset_characteristics.csv")
    df = df.drop(columns=["z3_error", "z3_warning"])
    df = df.rename(
        columns={
            "eloc": "ELOC",
            "max_nesting_depth": "Max Nesting Depth",
            "textual_assert": "assert",
            "textual_declare_const": "declare-const",
            "textual_declare_fun": "declare-fun",
            "textual_get_value": "get-value",
            "textual_define_fun": "define-fun",
            "textual_get_model": "get-model",
            "textual_declare_datatype": "declare-datatype",
            "textual_check_sat": "check-sat",
            "textual_eval": "eval",
            "textual_forall": "forall",
            "textual_exists": "exists",
        }
    )

    # Add quantifiers column (forall + exists)
    df["quantifiers"] = df.get("forall", 0) + df.get("exists", 0)

    # Select only the columns you want in the table
    cols = [
        "ELOC",
        "Max Nesting Depth",
        "assert",
        "declare-const",
        "declare-fun",
        "get-value",
        "define-fun",
        "get-model",
        "declare-datatype",
        "check-sat",
        "eval",
        "quantifiers",
    ]
    summary = df[cols].describe().T  # Transpose so metrics are rows
    summary = summary[["25%", "50%", "75%", "max"]]
    
    solver_res_df = pd.read_csv("results/fmp-solver-results.csv")
    solver_res_df = solver_res_df[solver_res_df["valid_spec"] == True]
    solver_res_df = solver_res_df[solver_res_df["time_taken"].notna()]
    solver_res_df["time_taken"] = solver_res_df["time_taken"].astype(float)

    # Add time_taken describe to summary
    time_taken_desc = solver_res_df["time_taken"].describe()
    # Only keep the same columns as summary
    time_row = time_taken_desc[["25%", "50%", "75%", "max"]]
    time_row.name = "Time taken (s)"
    summary = pd.concat([summary, pd.DataFrame(time_row).T])

    print(
        summary.to_string(
            float_format=lambda x: f"{x:.2f}" if isinstance(x, float) else str(x),
            na_rep="NA",
        )
    )
    