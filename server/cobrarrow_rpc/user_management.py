from datetime import datetime
import base64
import argparse
import duckdb
from config import USER_DB_PATH


# Connect to DuckDB
conn = duckdb.connect(USER_DB_PATH)

# Create users table
conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        username TEXT UNIQUE,
        password TEXT,
        status TEXT,
        createtime TIMESTAMP,
        modifytime TIMESTAMP
    )
''')

def add_user(email, first_name, last_name, username, password):
    """
    Add a new user to the database.

    Args:
        email (str): User's email address.
        first_name (str): User's first name.
        last_name (str): User's last name.
        username (str): User's username.
        password (str): User's password (will be base64 encoded).
    """
    status="active"
    hashed_password = base64.b64encode(password.encode())
    conn.execute('''
        INSERT INTO users (email, first_name, last_name, username, password, status, createtime, modifytime)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (email, first_name, last_name, username, hashed_password, status, datetime.now(), datetime.now()))
    print(f"User {username} created successfully.")

def show_users():
    """
    Display all users and their statuses.
    """
    result = conn.execute('SELECT email, first_name, last_name, username, status FROM users').fetchall()
    for row in result:
        print(row)

def change_password(username, new_password):
    """
    Change the password for an existing user.

    Args:
        username (str): The username of the user whose password is to be changed.
        new_password (str): The new password (will be base64 encoded).
    """
    hashed_password = base64.b64encode(new_password.encode())
    conn.execute('''
        UPDATE users
        SET password = ?, modifytime = ?
        WHERE username = ?
    ''', (hashed_password, datetime.now(), username))
    print(f"Password for {username} updated successfully.")


def delete_user(username):
    """
    Mark a user as inactive in the database.

    Args:
        username (str): The username of the user to be marked as inactive.
    """
    conn.execute('''
        UPDATE users
        SET status = ?, modifytime = ?
        WHERE username = ?
    ''', ('inactive', datetime.now(), username))
    print(f"User {username} deleted successfully.")


def main():
    """
    Entry point for the command-line user management script using DuckDB.

    This function sets up the command-line interface (CLI) using argparse, 
    allowing users to perform various operations on a user database. The supported 
    operations include adding a new user, showing all users, changing a user's 
    password, and deleting a user by marking them as inactive.

    The function parses the command-line arguments, executes the corresponding 
    action, and provides feedback to the user.

    Supported Commands:
        - add: Add a new user to the database.
        - show: Display all users and their statuses.
        - change-password: Update the password for an existing user.
        - delete: Mark a user as inactive.

    Example Usage:
        python user_management.py add --email user@example.com --first-name John --last-name Doe --username johndoe --password 123456
        python user_management.py show
        python user_management.py change-password --username johndoe --new-password newpassword123
        python user_management.py delete --username johndoe

    Args:
        None: All arguments are handled via the command-line interface.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="User management script using DuckDB.")
    subparsers = parser.add_subparsers(dest="command")

    # Add subcommand
    add_parser = subparsers.add_parser("add", help="Add a new user")
    add_parser.add_argument("--email", required=True, help="User's email")
    add_parser.add_argument("--first-name", required=True, help="User's first name")
    add_parser.add_argument("--last-name", required=True, help="User's last name")
    add_parser.add_argument("--username", required=True, help="User's username")
    add_parser.add_argument("--password", required=True, help="User's password")

    # Show subcommand
    subparsers.add_parser("show", help="Show all users")

    # Change password subcommand
    change_pass_parser = subparsers.add_parser("change-password", help="Change a user's password")
    change_pass_parser.add_argument("--username", required=True, help="User's username")
    change_pass_parser.add_argument("--new-password", required=True, help="User's new password")

    # Delete subcommand
    delete_parser = subparsers.add_parser("delete", help="Delete a user")
    delete_parser.add_argument("--username", required=True, help="User's username")

    args = parser.parse_args()

    if args.command == "add":
        add_user(args.email, args.first_name, args.last_name, args.username, args.password)
    elif args.command == "show":
        show_users()
    elif args.command == "change-password":
        change_password(args.username, args.new_password)
    elif args.command == "delete":
        delete_user(args.username)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
