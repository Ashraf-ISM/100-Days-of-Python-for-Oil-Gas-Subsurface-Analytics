# Getting Started

This guide gets you from zero to running your first notebook with minimal friction.

## 1) Prerequisites
- Python 3.9+
- Git
- Conda or venv
- Jupyter Lab or Notebook

## 2) Clone the Repository
```bash
git clone https://github.com/Ashraf-ISM/100-Days-of-Python-for-Oil-Gas-Subsurface-Analytics.git
cd 100-Days-of-Python-for-Oil-Gas-Subsurface-Analytics
```

## 3) Install Dependencies
### Conda (recommended)
```bash
conda env create -f environment.yml
conda activate subsurface-analytics
```

### pip + venv
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4) Verify Install
```bash
python -c "import numpy, pandas, lasio; print('Setup complete')"
```

## 5) Run a Notebook
```bash
jupyter lab
```
Open `notebooks/day-01/` and start with the LAS basics notebook.

## 6) Run Tests (Optional)
```bash
pip install -r requirements-dev.txt
pytest
```

## 7) Next Steps
- Review the roadmap in `docs/ROADMAP.md`
- Check the daily workflow in the README
- Track your progress in the badges and checklist
