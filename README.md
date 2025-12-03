# sum-impact-assessment-models
SUM impact assessment models

# Introduction
The library contains different models to analyse living labs' measures and KPIs. The models will provide analytic data to analyse and study the impact of the measures implemented in the Living Labs.

The results are expected to be displayed in a graphical interface, through a web application connected to SUM Open Data Platform : sum-odp.eu 

# Features
The models execute the following analysis : 
- the impact analysis evaluates the effects of measures on specific outcomes (e.g. social, economic)
- the multi-criteria decision analysis based on Promethee-Gaia methodology, compares and ranks alternatives based on multiple weighted criteria.

The model requires the following information : 
- Living labs
- New Shared Modes measures implemented by Living Labs
- Normalized variatons of KPIs values (comparison before and after values), for every Living Lab

# How to contribute

## Local installation for development

Ensure you have Python installed (recommended: Python 3.13+).

1. Clone the repository
2. Create an environment
3. Install the necessary packages
4. Create experiments and run the models
5. Analyze the results

### 1. Clone the repository

Clone the repository using the following command:

```bash
git clone https://github.com/INRIA/sum-impact-assessment-models
```

### 2. Create an environment

Check the [Python packaging user guide](https://packaging.python.org/en/latest/tutorials/managing-dependencies/) for more information on how to manage dependencies in Python.

On Debian protected environment, create a virtual enviornment first :

#### Environment with python natively
```bash
python3 -m venv env && source env/bin/activate && pip install pipenv
pip install pipenv
```

Install library pipenv to handle the environment and the dependencies.

#### Environment with pipenv
Install `pipenv`, then create and activate environment. Finally install dependencies. 

```bash
pip install pipenv
pipenv lock 
pipenv install --dev
```

## Build and publish the package

### 1. Install dependencies
Create environment and install pipenv, then install dependencies. 
Finally, build the package. 

```bash
pip install pipenv
pipenv lock
pipenv install --dev
```

#### 1.1. Run tests 
```bash
pipenv run pytest
```

#### 1.2. Build package 
```bash
# Build the wheel
python3 -m build

# Generate the docs
python3 build_docs.py
```
**The compiled wheel package .whl file will be at `./dist` folder.**


```bash
# OPTIONAL : clean and reset the build files 
rm -rf build dist *.egg-info
```

#### 1.3. Build the doc files 
```bash
# Generate the docs
python3 build_docs.py
```

**The documentation will be at `./docs` folder.**

