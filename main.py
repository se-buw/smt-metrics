import os
import urllib.request

from analysis.script_runner import script_runner
from analysis.prepare_dataset import parse_dataset, prepare_dataset
from analysis.dataset_characteristics import *
from analysis.edit_paths import (
    edit_path_chain_overview,
    initial_script,
    print_levenshtein_distance_table,
)
from analysis.syntactic_analysis import (
    print_consecutive_equivalences,
    print_syntactic_uniqueness,
)
from analysis.semantic_comparison import (
    print_non_consecutive_pairs,
    print_consecutive_identical_pairs,
)
from analysis.steps_to_fix import print_steps_to_fix

# Download the dataset
os.makedirs("data/json", exist_ok=True)
if not os.path.exists("data/json/fmp_smt.json"):
    print("Downloading dataset...")
    urllib.request.urlretrieve(
        "https://zenodo.org/records/15488371/files/fmp_smt.json?download=1",
        "data/json/fmp_smt.json",
    )
print("preparing dataset...")
parse_dataset("data/json/fmp_smt.json")

"""
Note: The script_runner function is used to run the solver on the dataset.
It might take couple of hours to run depending on the hardware and the number of workers.
If you want to run the solver, uncomment the following two lines 
and set the max_worker to the number of workers you want to use.
"""
# script_runner(max_worker=8, output_csv="results/fmp-solver-results.csv")
# prepare_dataset("data/json/fmp_smt.json", "data/json/fmp_smtlib.json")

# Dataset characteristics
print("---"* 5 + "Dataset characteristics" + "---"* 5)
print_dataset_characteristics()
print("---"* 5 + "Error analysis" + "---"* 5)
error_analysis()
print("---"* 5 + "Incremental Scripts" + "---"* 5)
incremental_scripts()
print("---"* 5 + "SMT-LIB Logics" + "---"* 5)
count_smtlib_logics()
print("---"* 5 + "Time Taken by the solver" + "---"* 5)
time_taken_by_the_solver()

# edit path analysis
print("---"* 5 + "Edit Path Overview" + "---"* 5)
edit_path_chain_overview()
print("---"* 5 + "Initial Unique Scripts" + "---"* 5)
initial_script()
print("---"* 5 + "Levenshtein Distance Overview" + "---"* 5)
print_levenshtein_distance_table()

# Syntactic analysis
print("---"* 5 + "Syntactic Uniqueness Overview" + "---"* 5)
print_syntactic_uniqueness()
print("---"* 5 + "Consecutive Equivalences" + "---"* 5)
print_consecutive_equivalences()

# Semantic analysis
print("---"* 5 + "Consecutive Identical Pairs" + "---"* 5)
print_consecutive_identical_pairs()
print("---"* 5 + "Non-Consecutive Pairs" + "---"* 5)
print_non_consecutive_pairs()

# Steps to fix
print("---"* 5 + "Steps to fix" + "---"* 5)
print_steps_to_fix()
