import os
import json
import shutil
import pandas as pd

def parse_dataset(input_file: str) -> None:
    os.makedirs(f"data/code", exist_ok=True)
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue  # skip empty lines
            data = json.loads(line)
            file_name = data["id"]
            code = data["code"]
            with open(f"data/code/{file_name}.smt2", "w", encoding="utf-8") as code_file:
                code_file.write(code)


def prepare_dataset() -> None:
    """
    Prepares the dataset by filtering the input JSON file based on valid spec IDs
    and copying the corresponding spec and spec output files to the data directory
    and parsing the dataset into separate files.
    The valid spec IDs are obtained from the results of the fmp-solver provided in the results directory.
    
    Args:
        input_file (str): Path to the input JSON file.
    """
    df = pd.read_csv("results/fmp-solver-results.csv", encoding="utf-8")
    df = df[df["valid_spec"] == True]
    valid_spec_paths = df["file"].tolist()

    
    # copy the valid spec and spec output files to the data directory
    os.makedirs("data/spec", exist_ok=True)
    os.makedirs("data/spec_output", exist_ok=True)
    for spec in valid_spec_paths:
        spec_file = spec.split("/")[-1]
        print(f"Copying {spec} to data/spec/{spec_file}")
        shutil.copy(spec, f"data/spec/{spec_file}")
        spec_output_file = spec.replace("/code/", "/output/").replace(".smt2", ".txt")
        shutil.copy(spec_output_file, f"data/spec_output/{spec_file.replace('.smt2', '.txt')}")
        
        
