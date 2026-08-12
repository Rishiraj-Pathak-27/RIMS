from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CSV_PATH = BASE_DIR / "data" / "03_gold_load_sql.csv"


def load_data(csv_path: str | Path | None = None) -> pd.DataFrame:
    data_path = Path(csv_path) if csv_path is not None else DEFAULT_CSV_PATH
    if not data_path.is_absolute():
        data_path = (BASE_DIR / data_path).resolve()

    if not data_path.exists():
        raise FileNotFoundError(f"CSV file not found: {data_path}")

    return pd.read_csv(data_path)


if __name__ == "__main__":
    dataframe = load_data()
    print("Dataset loaded successfully!")
    print("Shape:", dataframe.shape)
    print("Columns:", dataframe.columns.tolist())