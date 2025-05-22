# SMT-LIB Metrics


## Introduction
This repository contains the artifacts for the paper "On Writing SMT-LIB Scripts: Metrics and a new Dataset" submitted to the 23rd International Workshop on Satisfiability Modulo Theories. The repository contains the following structure:

```
+---analysis    # Python scripts used to analyze the data
|       dataset_characteristics.py
|       edit_paths.py
|       ...
+---results     # Results of the analysis
|   |   chain_semantic_comparison.csv
|   |   fmp_dataset_characteristics.csv
|   |   fmp-solver-results.csv
|   |   ...                   
|-main.py  # Main script to run the analysis
|-poetry.lock  # Poetry lock file
|-pyproject.toml  # Poetry project file
```

## Requirements
- Python >= 3.8
- Poetry >= 1.0.0

## Preparing the environment
- **Formal Methods Playground SMT-LIB Dataset**
    - Download the Formal Methods Playground SMT-LIB Dataset from [https://doi.org/10.5281/zenodo.15488370](https://doi.org/10.5281/zenodo.15488370)
    - All the json files should be placed in the `data/json/fmp_smt.json` 
- Create a virtual environment using Poetry: `proetry shell`
- Install the required dependencies using Poetry: `poetry install`

## Running the analysis
All the scripts are located in the `analysis` folder. To run the analysis, execute the following command:

```bash
python analysis/<script_name>.py
```
Otherwise, you can run the main script `main.py` to run all the analysis scripts in order. 


## Results
The preliminary results are stored in the `results` folder.



## License
This repository is licensed under the MIT License. Please see the LICENSE file for more details.
