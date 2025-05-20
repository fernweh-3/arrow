from pathlib import Path

# Define the base path of your package
BASE_DIR = Path(__file__).resolve().parent

# Define the path to the 'data' directory
DATA_DIR = BASE_DIR / 'data'

# Define the path to the user database and data database
USER_DB_PATH = str(BASE_DIR / 'data' / 'cobrarrow_users.duckdb')
DATA_DB_PATH = str(BASE_DIR / 'data' / 'cobrarrow_data.duckdb')

HOST = 'localhost'
PORT = 50051