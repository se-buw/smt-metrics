import os
import sys
import csv
import logging
import re
import subprocess
import time
import concurrent.futures
from z3 import *

# Settings
TIMEOUT = 600
MAX_WORKER = 4

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add file handler to save logs to a file
file_handler = logging.FileHandler("fmp-solver-results.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)


def run_solver(spec_path: str, timeout: int) -> tuple[str, str | float]:
    """
    Run the Z3 solver on the given SMT-LIB file and return the result.
    also write the output to a file.
    Args:
        spec_path (str): Path to the SMT-LIB file.
        timeout (int): Timeout for the solver in seconds.
    Returns:
        tuple: A tuple containing:
            - valid_spec (str): "True" if the spec is valid, "False" otherwise.
            - sat_unsat_results (str): The result of the solver ("sat", "unsat", "unknown", or "ERROR").
            - time_taken (float): Time taken by the solver in seconds.
    """
    error_regex = re.compile(r"^\(error.*", re.MULTILINE)
    with open(spec_path, "r", encoding="utf-8") as f:
        smt_spec = f.read()
    try:
        start = time.time()
        proc = subprocess.Popen(
            ["z3", "-in"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(input=smt_spec, timeout=timeout)
        output_content = stdout + stderr
        time_taken = time.time() - start
        output_dir = "data/output/"
        os.makedirs(output_dir, exist_ok=True)

        # Write to the file
        output_file = f"{output_dir}{spec_path.split('/')[-1].replace('.smt2', '.txt')}"
        with open(output_file, "w") as f:
            f.write(output_content)

        valid_spec = True
        if error_regex.search(output_content):
            sat_unsat_results = ["ERROR"]
            if not re.search(r"\(\s*(assert|declare-|check-)", smt_spec):
                valid_spec = False
        else:
            output_lines = stdout.splitlines()
            sat_unsat_results = [
                line for line in output_lines if line in {"sat", "unsat", "unknown"}
            ]
        return valid_spec, sat_unsat_results, time_taken
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return "NA", "NA", "TO"
    except Exception as e:
        return "ERROR", "ERROR", str(e)


def process_smt_file(file_path: str) -> dict:
    """
    Process a single SMT-LIB file and return the result.
    Args:
        file_path (str): Path to the SMT-LIB file.
    Returns:
        dict: A dictionary containing:
            - file (str): Path to the SMT-LIB file.
            - valid_spec (str): "True" if the spec is valid, "False" otherwise.
            - check (str): The result of the solver ("sat", "unsat", "unknown", or "ERROR").
            - time_taken (float): Time taken by the solver in seconds.
    """
    try:
        valid_spec, result, time_taken = run_solver(file_path, TIMEOUT)
        logger.info(
            f"PID: {os.getpid()} - File: {file_path}, Valid Spec: {valid_spec}, Result: {result}, Time Taken: {time_taken}"
        )
        return {
            "file": file_path,
            "valid_spec": valid_spec,
            "check": result,
            "time_taken": time_taken,
        }

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return {
            "file": file_path,
            "valid_spec": "ERROR",
            "check": "ERROR",
            "time_taken": "NA",
        }


def write_to_csv(file_path: str, results: list, mode: str = "a"):
    """
    Write the results to a CSV file.
    Args:
        file_path (str): Path to the CSV file.
        results (list): List of dictionaries containing the results.
        mode (str): Mode to open the file ("w" for write, "a" for append).
    Returns:
        None
    """
    fieldnames = ["file", "valid_spec", "check", "time_taken"]
    with open(file_path, mode=mode, newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC
        )
        if mode == "w":
            writer.writeheader()
        for result in results:
            writer.writerow(result)


def list_files(directory: str) -> list[str]:
    """
    List all SMT-LIB files in the given directory and its subdirectories.
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


def script_runner(max_worker: int, output_csv: str):
    """
    Main function to process SMT-LIB files in parallel and write the results to a CSV file.
    Args:
        max_worker (int): Maximum number of worker processes.
        output_csv (str): Path to the output CSV file.
    Returns:
        None
    """
    smt_files = list_files("data/code/")
    logger.debug(f"Total files: {len(smt_files)}")

    batch_size = 100

    write_to_csv(output_csv, [], mode="w")

    try:
        for i in range(0, len(smt_files), batch_size):
            batch = smt_files[i : i + batch_size]
            results = []
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=max_worker
            ) as executor:
                futures_to_file = {
                    executor.submit(process_smt_file, file): file for file in batch
                }
                futures = list(futures_to_file.keys())
                for future in concurrent.futures.as_completed(futures):
                    file = futures_to_file[future]
                    try:
                        result = future.result()
                        results.append(result)
                        logger.debug(f"Processed file: {file}")
                    except Exception as e:
                        logger.error(f"Error processing file {file}: {e}")
            if results:
                write_to_csv(output_csv, results, mode="a")

    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt caught, shutting down...")
        executor.shutdown(wait=False, cancel_futures=True)
        sys.exit(1)

