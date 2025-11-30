#!/usr/bin/env python3
"""Import LinkedIn connections from CSV export"""

import csv
import yaml
from datetime import datetime
from database.db import Database
from linkedin.connection_manager import ConnectionManager

def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def import_from_csv(csv_file_path):
    """Import connections from LinkedIn's Connections.csv export"""

    print("\n" + "="*60)
    print("Importing LinkedIn Connections from CSV")
    print("="*60)

    config = load_config()
    db = Database(config)
    session = db.get_session()
    conn_manager = ConnectionManager(session, config)

    imported = 0
    skipped = 0
    errors = 0

    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            # LinkedIn's export uses these column names:
            # First Name, Last Name, Email Address, Company, Position, Connected On
            reader = csv.DictReader(f)

            print(f"\nReading connections from: {csv_file_path}")
            print("Processing...")

            for row in reader:
                try:
                    # Extract data from CSV
                    first_name = row.get('First Name', '').strip()
                    last_name = row.get('Last Name', '').strip()
                    company = row.get('Company', '').strip()
                    position = row.get('Position', '').strip()
                    email = row.get('Email Address', '').strip()
                    connected_on = row.get('Connected On', '').strip()

                    # Build full name
                    if first_name or last_name:
                        name = f"{first_name} {last_name}".strip()
                    else:
                        print(f"  ⚠ Skipping: No name found")
                        skipped += 1
                        continue

                    # Create profile URL (we'll use email as unique identifier if available)
                    # LinkedIn CSV doesn't include profile URLs, so we generate a placeholder
                    if email:
                        profile_url = f"https://linkedin.com/in/imported-{email.replace('@', '-at-').replace('.', '-')}"
                    else:
                        # Use name-based URL if no email
                        url_slug = name.lower().replace(' ', '-').replace('.', '')
                        profile_url = f"https://linkedin.com/in/imported-{url_slug}"

                    # Parse connection date
                    connection_date = None
                    if connected_on:
                        try:
                            # LinkedIn format: "DD MMM YYYY" (e.g., "15 Jan 2023")
                            connection_date = datetime.strptime(connected_on, '%d %b %Y')
                        except:
                            try:
                                # Alternative format: "MM/DD/YYYY"
                                connection_date = datetime.strptime(connected_on, '%m/%d/%Y')
                            except:
                                pass

                    # Add connection
                    connection = conn_manager.add_connection(
                        name=name,
                        profile_url=profile_url,
                        title=position if position else None,
                        company=company if company else None,
                        connection_source="linkedin_csv_import"
                    )

                    # Update connection date if we have it
                    if connection_date:
                        connection.connection_date = connection_date
                        session.commit()

                    imported += 1

                    if imported % 10 == 0:
                        print(f"  Imported {imported} connections...")

                except Exception as e:
                    print(f"  ✗ Error importing {row.get('First Name', '')} {row.get('Last Name', '')}: {e}")
                    errors += 1
                    continue

        print("\n" + "="*60)
        print("Import Complete")
        print("="*60)
        print(f"✓ Successfully imported: {imported}")
        print(f"⚠ Skipped: {skipped}")
        print(f"✗ Errors: {errors}")
        print(f"\nTotal connections in database: {conn_manager.get_all_connections().__len__()}")

        # Show sample of imported connections
        print("\n" + "="*60)
        print("Sample of Imported Connections")
        print("="*60)

        sample = conn_manager.get_all_connections()[:5]
        for conn in sample:
            print(f"\n  {conn.name}")
            print(f"    Title: {conn.title or 'N/A'}")
            print(f"    Company: {conn.company or 'N/A'}")
            print(f"    Quality: {conn.quality_score}/10")

        print("\n✓ Run 'python3 main.py network-analytics' to see your network stats!\n")

    except FileNotFoundError:
        print(f"\n✗ Error: Could not find file: {csv_file_path}")
        print("\nMake sure you've downloaded your LinkedIn connections CSV.")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()
        db.close()

    return True

def show_instructions():
    """Show instructions for exporting LinkedIn connections"""
    print("\n" + "="*60)
    print("How to Export Your LinkedIn Connections")
    print("="*60)
    print("""
1. Go to LinkedIn and log in
2. Click on "Me" (your profile icon) → Settings & Privacy
3. Click "Data privacy" in the left menu
4. Under "Get a copy of your data", click "Get a copy of your data"
5. Select "Want something in particular? Select the data files you're most interested in"
6. Check the box for "Connections"
7. Click "Request archive"
8. Wait for LinkedIn to email you (usually takes ~10 minutes)
9. Download the archive and extract the "Connections.csv" file
10. Run this script:
    python3 import_linkedin_connections.py path/to/Connections.csv

Note: The CSV file will have columns like:
- First Name, Last Name
- Email Address
- Company, Position
- Connected On
""")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("\nUsage: python3 import_linkedin_connections.py <path-to-Connections.csv>")
        show_instructions()
        sys.exit(1)

    csv_file = sys.argv[1]

    if csv_file in ['--help', '-h', 'help']:
        show_instructions()
        sys.exit(0)

    import_from_csv(csv_file)
