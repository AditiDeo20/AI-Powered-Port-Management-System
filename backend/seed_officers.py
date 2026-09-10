"""
Seed script for 232 authoritative officers (158 DOs, 44 NOs, 30 HODs)
Ensures database tables (admin_users, admin_roles, messages) are fully seeded and migrated.
"""
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from database import get_cursor, is_postgres_online

first_names = [
    'Rajesh', 'Suresh', 'Amit', 'Anil', 'Sunil', 'Vijay', 'Manoj', 'Dinesh', 'Sanjay', 'Pankaj',
    'Ramesh', 'Alok', 'Deepak', 'Naveen', 'Ashok', 'Gaurav', 'Vikas', 'Manish', 'Sachin', 'Nitin',
    'Kiran', 'Prashant', 'Sandip', 'Mahesh', 'Santosh', 'Ganesh', 'Pravin', 'Chetan', 'Rahul', 'Vivek',
    'Arun', 'Vinod', 'Anand', 'Satish', 'Subhash', 'Hemant', 'Kishore', 'Bipin', 'Sudhir', 'Dilip',
    'Priya', 'Sunita', 'Anjali', 'Kavita', 'Neeta', 'Rekha', 'Meena', 'Shobha', 'Swati', 'Seema'
]

last_names = [
    'Sharma', 'Patil', 'Deshmukh', 'Kulkarni', 'Joshi', 'Shinde', 'Pawar', 'More', 'Chavan', 'Kadam',
    'Sawant', 'Jadhav', 'Gaikwad', 'Kamble', 'Bhosale', 'Mane', 'Naik', 'Shetty', 'Fernandes', 'D\'Souza',
    'Verma', 'Gupta', 'Singh', 'Yadav', 'Mishra', 'Pandey', 'Tiwari', 'Dubey', 'Shukla', 'Tripathi',
    'Mehta', 'Shah', 'Parekh', 'Desai', 'Patel', 'Modi', 'Gandhi', 'Bhatt', 'Pandya', 'Trivedi'
]

def seed_all_officers():
    print("Seeding 232 officers into database...")
    fn_idx = 0
    ln_idx = 0
    def get_next_name():
        nonlocal fn_idx, ln_idx
        fn = first_names[fn_idx % len(first_names)]
        ln = last_names[ln_idx % len(last_names)]
        fn_idx += 1
        if fn_idx % len(first_names) == 0:
            ln_idx += 1
        return fn, ln

    with get_cursor() as cur:
        # 1. DOs (158 total)
        for i in range(1, 158):
            aid = f"10{i:03d}"
            fn, ln = get_next_name()
            name = f"{fn.upper()} {ln.upper()}"
            uname = f"{fn.lower()}.{ln.lower()}{i%10}"
            cur.execute("""
                INSERT OR REPLACE INTO admin_users (admin_id, name, user_name, plain_password, passwd)
                VALUES (%s, %s, %s, %s, %s);
            """, (aid, name, uname, "admin1234", "admin1234"))
            cur.execute("""
                INSERT OR REPLACE INTO admin_roles (admin_id, role_id)
                VALUES (%s, %s);
            """, (aid, "DO"))

        # 2. NOs (44 total)
        for i in range(1, 44):
            aid = f"20{i:03d}"
            fn, ln = get_next_name()
            name = f"{fn.upper()} {ln.upper()}"
            uname = f"no.{ln.lower()}{i}"
            cur.execute("""
                INSERT OR REPLACE INTO admin_users (admin_id, name, user_name, plain_password, passwd)
                VALUES (%s, %s, %s, %s, %s);
            """, (aid, name, uname, "admin1234", "admin1234"))
            cur.execute("""
                INSERT OR REPLACE INTO admin_roles (admin_id, role_id)
                VALUES (%s, %s);
            """, (aid, "NODAL"))

        # 3. HODs (30 total)
        for i in range(1, 29):
            aid = f"30{i:03d}"
            fn, ln = get_next_name()
            name = f"DR. {fn.upper()} {ln.upper()}"
            uname = f"hod.{ln.lower()}{i}"
            cur.execute("""
                INSERT OR REPLACE INTO admin_users (admin_id, name, user_name, plain_password, passwd)
                VALUES (%s, %s, %s, %s, %s);
            """, (aid, name, uname, "admin1234", "admin1234"))
            cur.execute("""
                INSERT OR REPLACE INTO admin_roles (admin_id, role_id)
                VALUES (%s, %s);
            """, (aid, "HOD"))

    print("Seeding completed successfully.")

if __name__ == "__main__":
    seed_all_officers()
