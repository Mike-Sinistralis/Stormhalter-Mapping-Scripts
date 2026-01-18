import os
import glob
import subprocess
import sys

from db_config import DB_CONFIG

# Pull credentials from db_config.py
DB_NAME = DB_CONFIG["dbname"]
DB_USER = DB_CONFIG["user"]
DB_PASSWORD = DB_CONFIG["password"]

BACKUP_FOLDER = r".\backup"


def find_latest_backup():
    """Find the most recent backup file in the backup folder."""
    patterns = [
        os.path.join(BACKUP_FOLDER, "*.dump"),
        os.path.join(BACKUP_FOLDER, "*.sql"),
        os.path.join(BACKUP_FOLDER, "*.backup"),
    ]

    all_files = []
    for pattern in patterns:
        all_files.extend(glob.glob(pattern))

    if not all_files:
        return None

    # Sort by modification time, newest first
    all_files.sort(key=os.path.getmtime, reverse=True)
    return all_files[0]


def run_psql(command, database="postgres"):
    """Run a psql command."""
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    cmd = [
        "psql",
        "-h", "localhost",
        "-U", DB_USER,
        "-d", database,
        "-c", command
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result


def database_exists():
    """Check if the database already exists."""
    result = run_psql(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
    return DB_NAME in result.stdout or "1" in result.stdout


def create_database():
    """Create the database."""
    print(f"Creating database '{DB_NAME}'...")
    result = run_psql(f"CREATE DATABASE {DB_NAME}")

    if result.returncode != 0:
        if "already exists" in result.stderr:
            print(f"Database '{DB_NAME}' already exists.")
            return True
        print(f"Error creating database: {result.stderr}")
        return False

    print(f"Database '{DB_NAME}' created successfully.")
    return True


def restore_backup(backup_file):
    """Restore the database from a backup file."""
    print(f"Restoring from backup: {backup_file}")

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    # Determine restore method based on file extension
    ext = os.path.splitext(backup_file)[1].lower()

    if ext in (".dump", ".backup"):
        # Custom format - use pg_restore
        cmd = [
            "pg_restore",
            "-h", "localhost",
            "-U", DB_USER,
            "-d", DB_NAME,
            "--no-owner",
            "--no-privileges",
            "--clean",
            "--if-exists",
            backup_file
        ]
    else:
        # SQL format - use psql
        cmd = [
            "psql",
            "-h", "localhost",
            "-U", DB_USER,
            "-d", DB_NAME,
            "-f", backup_file
        ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    # pg_restore may return warnings that aren't fatal errors
    if result.returncode != 0 and ext not in (".dump", ".backup"):
        print(f"Error restoring backup: {result.stderr}")
        return False

    if result.stderr:
        # Filter out common non-fatal warnings
        warnings = [line for line in result.stderr.split('\n')
                   if line and "WARNING" not in line and "NOTICE" not in line]
        if warnings:
            print("Restore messages:")
            for warning in warnings[:10]:  # Show first 10
                print(f"  {warning}")

    print("Backup restored successfully.")
    return True


def main():
    print("=" * 50)
    print("Stormhalter Database Initialization")
    print("=" * 50)
    print()

    # Check if PostgreSQL tools are available
    try:
        result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
        print(f"Found: {result.stdout.strip()}")
    except FileNotFoundError:
        print("ERROR: PostgreSQL command-line tools not found.")
        print()
        print("Make sure PostgreSQL is installed and the bin directory is in your PATH.")
        print("Typical location: C:\\Program Files\\PostgreSQL\\16\\bin")
        print()
        print("To add to PATH:")
        print("1. Search for 'Environment Variables' in Windows")
        print("2. Click 'Environment Variables...'")
        print("3. Under 'System variables', find 'Path' and click 'Edit'")
        print("4. Click 'New' and add the PostgreSQL bin directory")
        print("5. Click OK and restart your Command Prompt")
        sys.exit(1)

    print()

    # Find backup file
    backup_file = find_latest_backup()
    if not backup_file:
        print(f"ERROR: No backup files found in {BACKUP_FOLDER}")
        print("Please place a .dump, .sql, or .backup file in the backup folder.")
        sys.exit(1)

    print(f"Found backup file: {backup_file}")
    print()

    # Check if database exists
    if database_exists():
        print(f"Database '{DB_NAME}' already exists.")
        response = input("Do you want to drop and recreate it? (yes/no): ").strip().lower()
        if response != "yes":
            print("Aborted.")
            sys.exit(0)

        print(f"Dropping database '{DB_NAME}'...")
        # Terminate existing connections
        run_psql(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{DB_NAME}' AND pid <> pg_backend_pid()
        """)
        result = run_psql(f"DROP DATABASE {DB_NAME}")
        if result.returncode != 0:
            print(f"Error dropping database: {result.stderr}")
            sys.exit(1)
        print("Database dropped.")
        print()

    # Create database
    if not create_database():
        sys.exit(1)
    print()

    # Restore backup
    if not restore_backup(backup_file):
        sys.exit(1)

    print()
    print("=" * 50)
    print("Database initialization complete!")
    print("=" * 50)
    print()
    print("You can now run the mapping scripts.")
    print("Make sure your password in db_config.py matches your PostgreSQL password.")


if __name__ == "__main__":
    main()
