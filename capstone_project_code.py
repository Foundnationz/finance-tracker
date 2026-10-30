# ============================================================
# FINANCE TRACKER APP
# Converted from Google Colab to VSCode (tkinter UI)
# ============================================================

# --- IMPORTS ---
# sqlite3: built-in Python library to create and manage a local database file
# re: built-in library for checking text patterns (used in password/email validation)
# random: built-in library to pick random items from a list (used for quotes)
# bcrypt: library to securely hash passwords before storing them
# datetime, timedelta: built-in tools for working with dates and times
# relativedelta: adds months/years to dates (e.g. monthly budget end date)
# tkinter: built-in Python GUI library, replaces ipywidgets from Colab
# matplotlib: library for drawing charts (pie chart, line chart)
# pandas: library for displaying data in table format
# monthrange: gets the number of days in a given month

import sys
import os
import sqlite3
import re
import random
import bcrypt
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from contextlib import contextmanager

# ============================================================
# DATABASE PATH
# ============================================================
# This tells Python where to save the database file.
# It will be created automatically in the same folder
# as this Python file when you run the app for the first time.
# You do NOT need to create it manually.
# ============================================================

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "budgeting_app.db")

# ============================================================
# GLOBAL VARIABLE
# ============================================================
# current_user stores the logged-in user's data (id, username, email, etc.)
# It starts as None because no one is logged in when the app first opens.
# ============================================================

current_user = None

# ============================================================
# DATABASE HELPER — Context Manager
# ============================================================
# Instead of writing conn = sqlite3.connect() and conn.close()
# in every single function (which your original code did 30+ times),
# we use this helper. The 'with get_db() as conn:' pattern
# automatically closes the connection even if an error occurs.
# ============================================================

@contextmanager
def get_db():
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")  # Enforce foreign key rules
    try:
        yield conn
    finally:
        conn.close()

# ============================================================
# DATABASE SETUP
# ============================================================
# This function creates all the tables in your database.
# Tables are like spreadsheets — each one stores a specific
# type of data (users, accounts, budgets, etc.)
#
# CREATE TABLE IF NOT EXISTS means:
#   "Create this table only if it doesn't already exist"
#   So running this function multiple times is safe —
#   it won't delete your existing data.
#
# Data types used:
#   INTEGER = whole numbers (1, 2, 3)
#   TEXT    = words/sentences ("hello")
#   REAL    = decimal numbers (10.50)
#
# PRIMARY KEY AUTOINCREMENT = SQLite automatically assigns
#   a unique ID number to each new row (1, 2, 3, 4...)
#
# FOREIGN KEY = links one table to another
#   e.g. accounts.user_id links to users.id
#   This means every account must belong to a real user
# ============================================================

def create_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # --- USERS TABLE ---
        # Stores login credentials and streak data for each user
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                last_login_date TEXT,
                streak_count INTEGER DEFAULT 0
            )
        ''')

        # --- ACCOUNTS TABLE ---
        # Stores bank/wallet accounts belonging to a user
        # One user can have up to 5 accounts (enforced in the UI)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_name TEXT NOT NULL,
                balance REAL NOT NULL,
                notes TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # --- BUDGETS TABLE ---
        # Stores spending limits the user sets for categories
        # timeframe: Daily / Weekly / Monthly / Yearly
        # spent: how much has been used (calculated dynamically, not stored)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                budget_name TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                category TEXT,
                amount REAL NOT NULL,
                spent REAL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # --- TRANSACTIONS TABLE ---
        # Stores every income or expense the user records
        # type: either 'income' or 'expense'
        # account_id: which account this transaction affects
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_id INTEGER,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        ''')

        # --- CATEGORIES TABLE ---
        # Stores custom category names the user creates
        # e.g. "Salary" as income, "Groceries" as expense
        # UNIQUE(user_id, type, name) prevents duplicate categories
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                UNIQUE(user_id, type, name),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # --- SUBSCRIPTIONS TABLE ---
        # Stores recurring charges (Netflix, Spotify, etc.)
        # charge_dates: comma-separated day numbers e.g. "1,15"
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subscription_name TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                charge_dates TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # --- WISHLIST TABLE ---
        # Stores items the user wants to save up for
        # progress: 0 to 100, how much has been funded
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wishlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT NOT NULL,
                price REAL NOT NULL,
                notes TEXT,
                link TEXT,
                progress REAL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # --- SETTINGS TABLE ---
        # Stores user preferences like currency symbol.
        # One row per user.
        # default currency is USD ($)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                currency_symbol TEXT DEFAULT '$',
                currency_name TEXT DEFAULT 'USD',
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # --- TAGS TABLE ---
        # Stores tags linked to individual transactions
        # e.g. #work #personal #emergency
        # One transaction can have multiple tags
        # Each tag is stored as a separate row
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER,
                user_id INTEGER,
                tag_name TEXT NOT NULL,
                FOREIGN KEY(transaction_id) REFERENCES transactions(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # --- RECURRING TRANSACTIONS TABLE ---
        # Stores transactions that repeat automatically
        # on a set frequency (daily, weekly, monthly, yearly)
        # next_due_date = the next date it should auto-fire
        # last_processed = last date it was actually added
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recurring_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_id INTEGER,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                frequency TEXT NOT NULL,
                next_due_date TEXT NOT NULL,
                last_processed TEXT,
                name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        ''')

        # --- BADGES TABLE ---
        # Stores achievement badges the user has earned
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                badge_name TEXT NOT NULL,
                badge_description TEXT,
                date_awarded TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Add optional fields AFTER all tables exist.
        # These definitions are developer-controlled, not user input.
        optional_columns = {
            "transactions": {
                "notes": "TEXT DEFAULT ''",
                "reference": "TEXT DEFAULT ''",
                "necessity": "TEXT DEFAULT 'unset'",
            },
            "recurring_transactions": {
                "notes": "TEXT DEFAULT ''",
                "tags": "TEXT DEFAULT ''",
                "necessity": "TEXT DEFAULT 'unset'",
            },
            "subscriptions": {
                "notes": "TEXT DEFAULT ''",
                "necessity": "TEXT DEFAULT 'unset'",
            },
        }

        for table_name, column_definitions in optional_columns.items():
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {
                column[1] for column in cursor.fetchall()
            }

            for column_name, definition in column_definitions.items():
                if column_name not in existing_columns:
                    cursor.execute(
                        f'ALTER TABLE "{table_name}" '
                        f'ADD COLUMN "{column_name}" {definition}'
                    )

        # Add budget notes for existing databases.
        # Run this AFTER the budgets table has been created.
        cursor.execute("PRAGMA table_info(budgets)")
        budget_columns = {
            column[1] for column in cursor.fetchall()
        }

        if "notes" not in budget_columns:
            cursor.execute(
                "ALTER TABLE budgets "
                "ADD COLUMN notes TEXT NOT NULL DEFAULT ''"
            )

        # Store the originating recurring rule's ID on transactions.
        # Older transactions remain NULL because their origin is unverified.
        cursor.execute("PRAGMA table_info(transactions)")
        transaction_columns = {
            column[1] for column in cursor.fetchall()
        }

        if "recurring_rule_id" not in transaction_columns:
            cursor.execute(
                "ALTER TABLE transactions "
                "ADD COLUMN recurring_rule_id INTEGER"
            )

        cursor.execute(
            '''CREATE INDEX IF NOT EXISTS idx_transactions_recurring_rule
               ON transactions (user_id, recurring_rule_id)'''
        )

                # Link generated expenses to their originating subscription.
        # Older transactions remain NULL because their origin is unverified.
        cursor.execute("PRAGMA table_info(transactions)")
        transaction_columns = {
            column[1] for column in cursor.fetchall()
        }

        if "subscription_id" not in transaction_columns:
            cursor.execute(
                "ALTER TABLE transactions "
                "ADD COLUMN subscription_id INTEGER"
            )

        cursor.execute(
            '''CREATE INDEX IF NOT EXISTS idx_transactions_subscription
               ON transactions (user_id, subscription_id)'''
        )

        # Prepare recurring rules to represent subscriptions too.
        # This does not create, activate or process any schedules.
        shared_schedule_columns = {
            "recurring_transactions": {
                "schedule_kind": "TEXT NOT NULL DEFAULT 'recurring'",
                "monthly_charge_days": "TEXT",
                "schedule_start_date": "TEXT",
            },
            "subscriptions": {
                "recurring_rule_id": "INTEGER",
            },
        }

        for table_name, column_definitions in shared_schedule_columns.items():
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {
                column[1] for column in cursor.fetchall()
            }

            for column_name, definition in column_definitions.items():
                if column_name not in existing_columns:
                    cursor.execute(
                        f'ALTER TABLE "{table_name}" '
                        f'ADD COLUMN "{column_name}" {definition}'
                    )

        # A recurring rule can be linked to at most one subscription.
        # Existing subscriptions remain unlinked (NULL) for now.
        cursor.execute(
            '''CREATE UNIQUE INDEX IF NOT EXISTS
                   idx_subscriptions_recurring_rule_unique
               ON subscriptions (recurring_rule_id)
               WHERE recurring_rule_id IS NOT NULL'''
        )

        # Remember processed schedule occurrences independently of
        # transactions, so deleting a transaction does not regenerate it.
        cursor.execute(
            """SELECT 1
               FROM sqlite_master
               WHERE type = 'table'
               AND name = 'processed_schedule_occurrences'"""
        )
        occurrence_table_exists = cursor.fetchone() is not None

        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS processed_schedule_occurrences (
                user_id INTEGER NOT NULL,
                recurring_rule_id INTEGER NOT NULL,
                scheduled_date TEXT NOT NULL,
                PRIMARY KEY (
                    user_id,
                    recurring_rule_id,
                    scheduled_date
                )
            )'''
        )

        if not occurrence_table_exists:
            # One-time migration:
            # existing linked transactions count as processed occurrences.
            cursor.execute(
                '''INSERT OR IGNORE INTO processed_schedule_occurrences
                   (user_id, recurring_rule_id, scheduled_date)
                   SELECT user_id, recurring_rule_id, date
                   FROM transactions
                   WHERE user_id IS NOT NULL
                     AND recurring_rule_id IS NOT NULL'''
            )

        # Month-level settings history for monthly budgets.
        # effective_month is an inclusive month boundary: YYYY-MM-01.
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS budget_monthly_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                budget_id INTEGER NOT NULL,
                effective_month TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                category TEXT NOT NULL,

                UNIQUE (budget_id, effective_month),

                CHECK (
                    length(effective_month) = 10
                    AND effective_month GLOB
                        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-01'
                    AND substr(effective_month, 6, 2)
                        BETWEEN '01' AND '12'
                ),

                FOREIGN KEY(user_id)
                    REFERENCES users(id),

                FOREIGN KEY(budget_id)
                    REFERENCES budgets(id)
                    ON DELETE CASCADE
            )'''
        )

        cursor.execute(
            '''CREATE INDEX IF NOT EXISTS idx_budget_history_lookup
               ON budget_monthly_history
                  (user_id, budget_id, effective_month)'''
        )

        initialise_monthly_budget_history(conn)

        conn.commit()

# ============================================================
# VALIDATION HELPERS
# ============================================================
# These functions check if user input is in the correct format
# before saving anything to the database.
# They all return True (valid) or False (invalid).
# ============================================================

def is_valid_username(username):
    # Username must be between 6 and 10 characters long
    return 6 <= len(username) <= 10

def is_valid_email(email):
    # Accepts any properly formatted email address
    # Your original only allowed @gmail.com which blocked
    # Outlook, Yahoo, school emails, etc.
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email))

def is_valid_password(password):
    # Password must have:
    # - At least 8 characters
    # - At least 1 uppercase letter
    # - At least 1 number
    # - At least 1 special symbol
    return (
        len(password) >= 8 and
        re.search(r'[A-Z]', password) and
        re.search(r'\d', password) and
        re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=~`\\/\[\];]', password)
    )

def username_exists(username):
    # Checks if a username is already taken in the database
    # Returns True if taken, False if available
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        return cursor.fetchone() is not None

# ============================================================
# PASSWORD HASHING
# ============================================================
# NEVER store passwords as plain text in a database.
# If someone gets access to your DB file, they see everything.
#
# bcrypt converts "MyPass*123" into a scrambled string like:
# "$2b$12$eImiTXuWVxfM37uY4JANjQ..."
# which cannot be reversed back to the original password.
#
# To check login: we hash what the user typed and compare
# hashes — we never "decode" the stored password.
# ============================================================

def hash_password(password):
    # bcrypt.hashpw needs bytes, not string — encode() converts it
    # gensalt() adds randomness so same password = different hash each time
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password, hashed_password):
    # bcrypt.checkpw handles the comparison safely
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# ============================================================
# AUTHENTICATION FUNCTIONS
# ============================================================

def register_user(username, email, password):
    # Hash the password before storing — plain text passwords removed
    hashed = hash_password(password)
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, email, password, last_login_date, streak_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, hashed, datetime.today().strftime("%Y-%m-%d"), 0))
            conn.commit()
        return True, "✅ Registration successful! Please login."
    except sqlite3.IntegrityError:
        return False, "❌ Username or email already exists."

def login_user(username, password):
    """
    Authenticates the user.

    A scheduled-processing failure is reported separately and
    does not turn valid credentials into a failed login.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()

    if user is None:
        return None

    if not verify_password(password, user[3]):
        return None

    user_id = user[0]

    update_streak(user_id)

    processing_error = None

    try:
        process_recurring_transactions(user_id)
    except (sqlite3.Error, ValueError, OverflowError) as error:
        processing_error = str(error)

        # Keep diagnostic details in the VSCode terminal.
        import traceback
        traceback.print_exc()

    # Check achievements after processing, so newly generated
    # transactions can count toward transaction milestones.
    check_and_award_badges(user_id)

    def show_login_notices():
        # Do not show a delayed notice for a user who has already
        # logged out or switched accounts.
        if current_user is None or current_user[0] != user_id:
            return

        if processing_error is not None:
            messagebox.showwarning(
                "Signed In — Schedule Processing Failed",
                (
                    "You have signed in successfully, but scheduled "
                    "transaction processing did not complete.\n\n"
                    "Changes made by that processing attempt were "
                    "rolled back. Due occurrences may still be pending, "
                    "so balances and budget totals may not include them.\n\n"
                    "Do not manually add replacement expenses until "
                    "you have checked the problem, to avoid duplicates.\n\n"
                    f"Details: {processing_error}"
                ),
                parent=root
            )

            # Avoid immediately presenting budget alerts based on
            # potentially incomplete scheduled-expense totals.
            return

        try:
            alerts = check_budget_alerts(user_id)
            show_budget_alert_popup(user_id, alerts)
        except (sqlite3.Error, ValueError, OverflowError):
            import traceback
            traceback.print_exc()

            messagebox.showwarning(
                "Budget Alerts Unavailable",
                (
                    "You are signed in, but budget alerts could not "
                    "be checked. Review the VSCode terminal for details."
                ),
                parent=root
            )

    # The successful login handler opens the main menu before
    # this delayed callback displays its notices.
    root.after(800, show_login_notices)

    return user

# ============================================================
# STREAK LOGIC
# ============================================================
# A streak counts how many consecutive days the user has
# logged in. It resets to 1 if they miss a day.
#
# Logic:
# - If last login was TODAY: do nothing, keep streak
# - If last login was YESTERDAY: add 1 to streak
# - If last login was before yesterday: reset to 1
# - If never logged in before (None): start at 1
# ============================================================

def update_streak(user_id):
    current_date = datetime.today().strftime("%Y-%m-%d")
    yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT last_login_date, streak_count FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        last_login_date, streak_count = row

        # Handle brand new user with no login date
        if last_login_date is None or last_login_date == current_date:
            # Either new user or already logged in today — set to 1 if new
            if last_login_date is None:
                streak_count = 1
                cursor.execute(
                    "UPDATE users SET last_login_date = ?, streak_count = ? WHERE id = ?",
                    (current_date, streak_count, user_id)
                )
                conn.commit()
            return streak_count

        # User logged in before — check if yesterday or earlier
        if last_login_date == yesterday:
            streak_count += 1  # Consecutive day — increment
        else:
            streak_count = 1   # Missed a day — reset

        cursor.execute(
            "UPDATE users SET last_login_date = ?, streak_count = ? WHERE id = ?",
            (current_date, streak_count, user_id)
        )
        conn.commit()

    return streak_count

# ============================================================
# FINANCIAL QUOTES
# ============================================================
# Shown randomly on the welcome/auth screen.
# These are real financial concepts — good educational touch.
# ============================================================

quotes = [
    "Save 3-6 months' worth of living expenses as an emergency fund. (Emergency Fund Rule)",
    "Allocate 50%  for needs, 30% for wants, 20% for savings. (The 50/30/20 Rule)",
    "Pay yourself first — save before you spend. (Pay Yourself First Principle)",
    "Pay off smallest debts first for momentum. (Debt Snowball Method)",
    "Divide 72 by your return rate to find how long to double money. (Rule of 72)",
    "Money today is worth more than the same amount in the future. (Time Value of Money)",
    "Subtract your age from 100 for your stock percentage. (Rule of 100)",
    "Withdraw 4% yearly from retirement savings. (The 4% Rule)",
    "Small recurring costs add up significantly over time. (The Latte Factor)",
    "Spread investments across asset classes to reduce risk. (Asset Allocation)",
    "Save 10% of annual income for retirement. (Rule of 10)",
    "20% of spending causes 80% of costs — focus there. (80/20 Rule)",
    "New purchases often trigger desire for more. (The Diderot Effect)",
    "Don't keep investing in losing projects because of past spending. (Sunk Cost Fallacy)",
    "Divide 115 by interest rate to find doubling time with compound interest. (Rule of 115)",
    "Split retirement savings into short, medium, long-term buckets. (3-Bucket Strategy)",
    "Keep monthly debt payments below 36% of income. (Debt-to-Income Ratio)",
    "Invest fixed amounts regularly regardless of market conditions. (Dollar-Cost Averaging)",
    "Spend 5 hours a week on financial education. (The 5-Hour Rule)",
    "Recognize biases like overconfidence that lead to bad financial decisions. (Behavioral Biases Theory)"
]

# ============================================================
# MAIN APPLICATION WINDOW
# ============================================================
# In tkinter, everything lives inside a "root" window.
# Think of it like an empty canvas you place things onto.
#
# We use a single root window throughout the whole app and
# swap "frames" (pages) in and out — similar to how websites
# show different pages without reloading the browser.
#
# Frame switching pattern:
#   1. Destroy the current frame's contents
#   2. Build and display the new frame's contents
# This keeps the window the same size and position always.
# ============================================================

def launch_app():
    """
    Creates the main tkinter window and starts the application.
    Call this once at the bottom of the file.
    """
    global root

    # Create the main window
    root = tk.Tk()
    root.title("💰 Finance Tracker")
    root.geometry("750x650")         # Width x Height in pixels
    root.resizable(True, True)       # Allow resizing
    root.configure(bg="#f0f4f8")     # Light blue-grey background

    # Show the first screen (welcome/auth choice)
    show_auth_choice_screen()

    # root.mainloop() keeps the window open and listening for clicks
    # Without this, the window would open and immediately close
    root.mainloop()


def clear_window():
    """
    Removes all widgets from the root window.

    Mouse-wheel bindings are removed first so that an old
    scrolling callback cannot try to access a destroyed canvas.
    """
    # Remove global scrolling callbacks belonging to the old screen
    root.unbind_all("<MouseWheel>")
    root.unbind_all("<Button-4>")
    root.unbind_all("<Button-5>")

    # Destroy all widgets from the old screen
    for widget in root.winfo_children():
        widget.destroy()


def make_scrollable_frame(parent):
    """
    Creates a scrollable area inside a frame.
    Mouse wheel scrolling works on all child widgets.
    """
    outer = tk.Frame(parent, bg="#f0f4f8")
    outer.pack(fill="both", expand=True)

    canvas = tk.Canvas(outer, bg="#f0f4f8", highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#f0f4f8")

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    # Keep the canvas item ID so its width can be updated.
    content_window = canvas.create_window(
        (0, 0),
        window=scroll_frame,
        anchor="nw"
    )

    canvas.configure(yscrollcommand=scrollbar.set)

    def resize_scroll_content(event):
        # Make the inner frame match the canvas's visible width.
        canvas.itemconfigure(
            content_window,
            width=max(event.width, 1)
        )

    canvas.bind("<Configure>", resize_scroll_content)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # ← Everything below is now correctly indented INSIDE the function
    # All these functions can now see 'canvas' properly

    def scroll(event):
        """
        Scrolls only while this canvas still exists.

        A screen change can destroy the canvas while a queued
        mouse-wheel event is still waiting to run.
        """
        try:
            if not canvas.winfo_exists():
                return

            # Windows normally reports event.delta in multiples of 120.
            direction = int(-1 * (event.delta / 120))

            # Some devices may report a smaller delta.
            if direction == 0:
                direction = -1 if event.delta > 0 else 1

            canvas.yview_scroll(direction, "units")

        except tk.TclError:
            # The canvas was destroyed before the queued event finished.
            # Safely ignore that old event.
            return

    def bind_scroll(widget):
        widget.bind("<MouseWheel>", scroll)
        for child in widget.winfo_children():
            bind_scroll(child)

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        bind_scroll(scroll_frame)

    def on_enter(event):
        # Only activate scrolling if this canvas still exists.
        try:
            if canvas.winfo_exists():
                root.bind_all("<MouseWheel>", scroll)
        except tk.TclError:
            pass

    def on_leave(event):
        # Remove this screen's global mouse-wheel callback.
        root.unbind_all("<MouseWheel>")

    canvas.bind("<MouseWheel>", scroll)
    scroll_frame.bind("<MouseWheel>", scroll)
    scroll_frame.bind("<Configure>", on_frame_configure)
    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Leave>", on_leave)
    scroll_frame.bind("<Enter>", on_enter)
    scroll_frame.bind("<Leave>", on_leave)

    return scroll_frame


# ============================================================
# REUSABLE UI HELPER FUNCTIONS
# ============================================================
# Instead of rewriting the same button/label styling every time,
# these helpers let us write one line to create styled widgets.
# ============================================================

def make_label(parent, text, font_size=11, bold=False, color="#2d3748", bg="#f0f4f8"):
    """Creates a styled text label."""
    weight = "bold" if bold else "normal"
    return tk.Label(
        parent, text=text,
        font=("Segoe UI", font_size, weight),
        fg=color, bg=bg
    )

def make_button(parent, text, command, color="#4a90d9", text_color="white", width=20):
    """Creates a styled button."""
    return tk.Button(
        parent, text=text, command=command,
        bg=color, fg=text_color,
        font=("Segoe UI", 10, "bold"),
        relief="flat", cursor="hand2",
        padx=10, pady=6, width=width,
        activebackground="#357abd",
        activeforeground="white"
    )

def make_entry(parent, show=None, width=30):
    """Creates a styled text input field. Use show='*' for passwords."""
    return tk.Entry(
        parent, show=show, width=width,
        font=("Segoe UI", 10),
        relief="solid", bd=1
    )

def make_frame(parent, bg="#f0f4f8", pady=5, padx=10):
    """Creates a simple container frame."""
    f = tk.Frame(parent, bg=bg)
    f.pack(pady=pady, padx=padx, fill="x")
    return f

def open_add_category_popup(user_id, tx_type, dropdown_widget, dropdown_var, parent_window=None):
    """
    Opens a small popup to add a new category from any form.

    Parameters:
        user_id        — the logged-in user's ID
        tx_type        — 'income' or 'expense' (which type to add)
        dropdown_widget — the Combobox widget to refresh after saving
        dropdown_var   — the StringVar linked to the dropdown
        parent_window  — optional parent window (usually root or a Toplevel)

    After saving, the dropdown refreshes and the new category
    is automatically selected. All other form fields remain unchanged.
    """
    # Use root as parent if none given
    parent = parent_window if parent_window else root

    # Create the popup window
    popup = tk.Toplevel(parent)
    popup.title(f"Add {tx_type.capitalize()} Category")
    popup.geometry("380x200")
    popup.resizable(False, False)
    popup.configure(bg="#f0f4f8")

    # Tie popup to the parent window
    popup.transient(parent)
    popup.grab_set()

    # ── Title ────────────────────────────────────────────────
    tk.Label(
        popup,
        text=f"➕ Add New {tx_type.capitalize()} Category",
        font=("Segoe UI", 13, "bold"),
        bg="#f0f4f8", fg="#2b6cb0"
    ).pack(pady=(15, 5))

    tk.Label(
        popup,
        text="This category will be available in all relevant forms.",
        font=("Segoe UI", 9, "italic"),
        bg="#f0f4f8", fg="#718096"
    ).pack()

    # ── Name input ───────────────────────────────────────────
    tk.Label(
        popup,
        text="Category Name:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=30, pady=(10, 0))

    name_entry = make_entry(popup, width=30)
    name_entry.pack(padx=30, pady=(2, 5))
    name_entry.focus()  # Put cursor in the field automatically

    # ── Message label ────────────────────────────────────────
    msg_label = tk.Label(
        popup, text="",
        font=("Segoe UI", 10),
        bg="#f0f4f8", fg="red",
        wraplength=320
    )
    msg_label.pack(pady=5)

    # ── Save function ─────────────────────────────────────────
    def on_save():
        new_cat = name_entry.get().strip()

        # Validate not empty
        if not new_cat:
            msg_label.config(
                text="❌ Category name cannot be empty.", fg="red")
            return

        # Validate length
        if len(new_cat) > 30:
            msg_label.config(
                text="❌ Category name must be 30 characters or fewer.",
                fg="red")
            return

        with get_db() as conn:
            cursor = conn.cursor()

            # Check for duplicate — same user, same type, same name
            cursor.execute(
                "SELECT 1 FROM categories WHERE user_id = ? AND type = ? AND name = ?",
                (user_id, tx_type, new_cat)
            )
            if cursor.fetchone():
                msg_label.config(
                    text="❌ This category already exists.", fg="red")
                return

            # Save the new category
            cursor.execute(
                "INSERT INTO categories (user_id, type, name) VALUES (?, ?, ?)",
                (user_id, tx_type, new_cat)
            )
            conn.commit()

        # ── Refresh the dropdown after saving ────────────────
        # Fetch updated category list for this type
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM categories WHERE user_id = ? AND type = ?",
                (user_id, tx_type)
            )
            updated_cats = [row[0] for row in cursor.fetchall()]

        # Update the dropdown values without rebuilding the screen
        dropdown_widget["values"] = updated_cats

        # Auto-select the newly added category
        dropdown_var.set(new_cat)

        # Close the popup
        popup.destroy()

    # ── Buttons ───────────────────────────────────────────────
    btn_frame = tk.Frame(popup, bg="#f0f4f8")
    btn_frame.pack(pady=10)

    make_button(
        btn_frame, "✅ Save",
        on_save, color="#38a169", width=12
    ).pack(side="left", padx=5)

    make_button(
        btn_frame, "✖ Cancel",
        popup.destroy, color="#718096", width=12
    ).pack(side="left", padx=5)

    # Allow Enter key to save
    popup.bind("<Return>", lambda e: on_save())

# ============================================================
# AUTH CHOICE SCREEN
# ============================================================
# This is the first screen the user sees when opening the app.
# It shows the app title, a random financial quote,
# and two buttons: Login or Register.
# ============================================================

def show_auth_choice_screen():
    global current_user
    current_user = None

    clear_window()
    
    # Outer container — centers everything
    outer = tk.Frame(root, bg="#f0f4f8")
    outer.pack(expand=True, fill="both", padx=40, pady=30)

    # App title
    make_label(outer, "💰 Finance Tracker", font_size=22, bold=True, color="#2b6cb0").pack(pady=(20, 5))
    make_label(outer, "Your personal budgeting companion", font_size=11, color="#718096").pack(pady=(0, 20))

    # Random financial quote displayed in a styled box
    quote = random.choice(quotes)
    quote_frame = tk.Frame(outer, bg="#ebf8ff", relief="solid", bd=1)
    quote_frame.pack(fill="x", pady=(0, 25), padx=20)
    tk.Label(
        quote_frame, text=f'💡 "{quote}"',
        font=("Segoe UI", 9, "italic"),
        fg="#2c5282", bg="#ebf8ff",
        wraplength=550, justify="center", pady=12, padx=10
    ).pack()

    # Divider line
    ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=10, padx=20)

    make_label(outer, "Please choose an option to continue:", font_size=11, color="#4a5568").pack(pady=(5, 15))

    # Button row
    btn_frame = tk.Frame(outer, bg="#f0f4f8")
    btn_frame.pack()
    make_button(btn_frame, "🔑  Login", show_login_screen, color="#38a169").pack(side="left", padx=10)
    make_button(btn_frame, "📝  Register", show_register_screen, color="#3182ce").pack(side="left", padx=10)

    # Footer
    make_label(outer, "Track. Save. Achieve.", font_size=9, color="#a0aec0").pack(pady=(30, 0))


# ============================================================
# LOGIN SCREEN
# ============================================================
# User enters their username and password.
# On submit:
#   1. We look up the username in the database
#   2. We verify the password using bcrypt (hash comparison)
#   3. If valid → go to main menu
#   4. If invalid → show error message
# ============================================================

def show_login_screen():
    clear_window()

    outer = tk.Frame(root, bg="#f0f4f8")
    outer.pack(expand=True, fill="both", padx=60, pady=40)

    make_label(outer, "🔑 Login", font_size=18, bold=True,
               color="#2b6cb0").pack(pady=(10, 20))

    # Form card
    card = tk.Frame(outer, bg="white", relief="solid", bd=1)
    card.pack(fill="x", padx=20, pady=10)
    card.columnconfigure(1, weight=1)

    # Username field
    tk.Label(card, text="Username:",
             font=("Segoe UI", 10, "bold"),
             bg="white", fg="#4a5568").grid(
             row=0, column=0, sticky="w", padx=20, pady=(20, 8))
    username_entry = make_entry(card, width=35)
    username_entry.grid(row=0, column=1, padx=20,
                        pady=(20, 8), sticky="ew")

    # Password field
    tk.Label(card, text="Password:",
             font=("Segoe UI", 10, "bold"),
             bg="white", fg="#4a5568").grid(
             row=1, column=0, sticky="w", padx=20, pady=8)
    password_entry = make_entry(card, show="*", width=35)
    password_entry.grid(row=1, column=1, padx=20,
                        pady=8, sticky="ew")

    # Message label — shows errors or success
    msg_label = tk.Label(outer, text="",
                         font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red", wraplength=400)
    msg_label.pack(pady=8)

    def on_login():
        # ← Now correctly indented INSIDE show_login_screen
        # Can now see username_entry, password_entry, msg_label
        username = username_entry.get().strip()
        password = password_entry.get()

        if not username or not password:
            msg_label.config(
                text="❌ Please fill in all fields.", fg="red")
            return

        user = login_user(username, password)
        if user:
            root.unbind("<Return>")   # Clean up binding before leaving
            show_main_menu(user)
        else:
            msg_label.config(
                text="❌ Invalid username or password.", fg="red")

    def go_back():
        root.unbind("<Return>")       # Clean up binding before leaving
        show_auth_choice_screen()

    # Buttons
    btn_frame = tk.Frame(outer, bg="#f0f4f8")
    btn_frame.pack(pady=15)
    make_button(btn_frame, "🔑  Login",
                on_login, color="#38a169").pack(side="left", padx=8)
    make_button(btn_frame, "← Back",
                go_back, color="#718096").pack(side="left", padx=8)

    # Enter key triggers login
    root.bind("<Return>", lambda e: on_login())


# ============================================================
# REGISTER SCREEN
# ============================================================
# New user creates an account.
# Validation checks (in order):
#   1. No empty fields
#   2. Username length 6-10
#   3. Username not already taken
#   4. Valid email format
#   5. Password meets requirements
# If all pass → hash password → save to database → success message
# ============================================================

def show_register_screen():
    clear_window()

    outer = tk.Frame(root, bg="#f0f4f8")
    outer.pack(expand=True, fill="both", padx=60, pady=30)

    make_label(outer, "📝 Create Account", font_size=18, bold=True, color="#2b6cb0").pack(pady=(10, 20))

    # Form card
    card = tk.Frame(outer, bg="white", relief="solid", bd=1)
    card.pack(fill="x", padx=20, pady=10)
    card.columnconfigure(1, weight=1)

    fields = [
        ("Username:", False),   # (label text, is_password?)
        ("Email:", False),
        ("Password:", True),
    ]

    entries = []
    for i, (label_text, is_pass) in enumerate(fields):
        tk.Label(card, text=label_text, font=("Segoe UI", 10, "bold"),
                 bg="white", fg="#4a5568").grid(row=i, column=0, sticky="w",
                                                padx=20, pady=(20 if i == 0 else 8, 8))
        entry = make_entry(card, show="*" if is_pass else None, width=35)
        entry.grid(row=i, column=1, padx=20, pady=(20 if i == 0 else 8, 8), sticky="ew")
        entries.append(entry)

    username_entry, email_entry, password_entry = entries

    # Password requirements hint shown below form
    hint_frame = tk.Frame(outer, bg="#fffbeb", relief="solid", bd=1)
    hint_frame.pack(fill="x", padx=20, pady=5)
    tk.Label(
        hint_frame,
        text="🔒 Password must be 8+ chars with 1 uppercase, 1 number, 1 symbol (e.g. Secure*123)",
        font=("Segoe UI", 9), bg="#fffbeb", fg="#744210", wraplength=500, pady=8
    ).pack()

    msg_label = tk.Label(outer, text="", font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red", wraplength=450)
    msg_label.pack(pady=8)

    def on_register():
        """
        Validates all fields in order and registers the user if valid.
        """
        username = username_entry.get().strip()
        email = email_entry.get().strip()
        password = password_entry.get()

        # Check no fields are empty
        if not username or not email or not password:
            msg_label.config(text="❌ Please fill in all fields.", fg="red")
            return

        # Check username length
        if not is_valid_username(username):
            msg_label.config(text="❌ Username must be 6 to 10 characters long.", fg="red")
            return

        # Check username not taken
        if username_exists(username):
            msg_label.config(text="❌ Username already taken. Please choose another.", fg="red")
            return

        # Check email format
        if not is_valid_email(email):
            msg_label.config(text="❌ Please enter a valid email address.", fg="red")
            return

        # Check password strength
        if not is_valid_password(password):
            msg_label.config(
                text="❌ Password must have 8+ chars, 1 uppercase, 1 number, 1 symbol.",
                fg="red"
            )
            return

        # All checks passed — register the user
        success, message = register_user(username, email, password)
        if success:
            msg_label.config(text=message, fg="green")
        else:
            msg_label.config(text=message, fg="red")

    btn_frame = tk.Frame(outer, bg="#f0f4f8")
    btn_frame.pack(pady=15)
    make_button(btn_frame, "📝  Register", on_register, color="#3182ce").pack(side="left", padx=8)

    def go_back():
        root.unbind("<Return>")       # ← Remove the Enter binding first
        show_auth_choice_screen()     # ← Then navigate away

    make_button(
        btn_frame, "← Back",
        go_back,                      # ← Use go_back not show_auth_choice_screen directly
        color="#718096"
    ).pack(side="left", padx=8)


# ============================================================
# MAIN MENU
# ============================================================
# Shown after successful login.
# Displays:
#   - Welcome message with username, email, today's date
#   - Streak count and motivational message
#   - 7 feature buttons (one per app section)
# ============================================================

def show_main_menu(user):
    global current_user
    current_user = user   # Save logged-in user globally for other screens to access

    clear_window()

    user_id   = user[0]
    username  = user[1]
    email     = user[2]
    today     = datetime.today().strftime("%A, %d %B %Y")

    # Read streak from DB (already updated during login — don't update again here)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT streak_count FROM users WHERE id = ?", (user_id,))
        streak_count = cursor.fetchone()[0] or 0

    # Pick motivational message based on streak length
    if streak_count == 0:
        motivation = "🚀 Start your streak today!"
    elif streak_count == 1:
        motivation = "🔥 Streak started! Come back tomorrow!"
    elif streak_count <= 5:
        motivation = "🔥 You're on fire! Keep it going!"
    elif streak_count <= 10:
        motivation = "🔥 Amazing! You're unstoppable!"
    else:
        motivation = "🔥 Streak master! Keep pushing!"

    # --- Header section ---
    header = tk.Frame(root, bg="#2b6cb0", pady=15)
    header.pack(fill="x")

    tk.Label(header, text=f"👋 Welcome, {username}!",
             font=("Segoe UI", 16, "bold"), fg="white", bg="#2b6cb0").pack()
    tk.Label(header, text=f"{email}  |  {today}",
             font=("Segoe UI", 9), fg="#bee3f8", bg="#2b6cb0").pack(pady=2)
    tk.Label(header, text=f"🔥 Streak: {streak_count} days  —  {motivation}",
             font=("Segoe UI", 10, "italic"), fg="#fefcbf", bg="#2b6cb0").pack(pady=4)

    # --- Feature buttons ---
    body = tk.Frame(root, bg="#f0f4f8")
    body.pack(expand=True, fill="both", padx=50, pady=20)

    make_label(body, "What would you like to do?", font_size=12,
               bold=True, color="#2d3748").pack(pady=(10, 15))

    # Each tuple: (button label, function to call)
    # lambda b=btn_func: b() is used to avoid the common closure bug
    # where all lambdas would call the same last function
    features = [
        ("💳  Account Balance",        lambda: show_account_balance(user_id)),
        ("📊  Budgets",                lambda: show_budgets(user_id)),
        ("💸  Add Transaction",        lambda: show_add_transaction(user_id)),
        ("🔁  Recurring Transactions", lambda: show_recurring_transactions(user_id)),
        ("🔄  Subscriptions",          lambda: show_add_subscription(user_id)),
        ("🎯  Wishlist",               lambda: show_wishlist(user_id)),
        ("📈  Dashboard",              lambda: show_dashboard(user_id)),
        ("🏅  Badges",                 lambda: show_badges(user_id)),
        ("⚙️  Settings",               lambda: show_settings(user_id)),
    ]

    for label, cmd in features:
        make_button(body, label, cmd, width=28).pack(pady=5)

    # Logout button at bottom
    ttk.Separator(body, orient="horizontal").pack(fill="x", pady=15)
    make_button(body, "🚪  Logout", show_auth_choice_screen,
                color="#e53e3e", width=28).pack(pady=5)

# ============================================================
# ACCOUNT BALANCE SCREEN
# ============================================================
# Shows all accounts user has created.
# Each account shows: name, balance, notes.
# Max 5 accounts per user (enforced here).
# Buttons: Add Account, Delete Account, Back.
# ============================================================
def show_account_balance(user_id):
    clear_window()

    # ── Header ──────────────────────────────────────────────
    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(
        header,
        text="💳 Account Balance",
        font=("Segoe UI", 16, "bold"),
        fg="white", bg="#2b6cb0"
    ).pack()

    # ── Scrollable body ──────────────────────────────────────
    body = make_scrollable_frame(root)
    sym  = get_currency(user_id)

    accounts = view_accounts(user_id)

    if not accounts:
        # Empty state
        empty_frame = tk.Frame(body, bg="#f0f4f8")
        empty_frame.pack(pady=40)
        tk.Label(
            empty_frame,
            text="💳",
            font=("Segoe UI", 36),
            bg="#f0f4f8"
        ).pack()
        tk.Label(
            empty_frame,
            text="No accounts yet.",
            font=("Segoe UI", 13, "bold"),
            bg="#f0f4f8", fg="#2d3748"
        ).pack(pady=(5, 2))
        tk.Label(
            empty_frame,
            text="Add an account to start tracking your money.",
            font=("Segoe UI", 10),
            bg="#f0f4f8", fg="#718096"
        ).pack()

    # ── Account cards ─────────────────────────────────────────
    for account in accounts:
        # account = (id, account_name, balance, notes)
        account_id   = account[0]
        account_name = account[1]
        balance      = account[2]
        notes        = account[3] or "None"

        # Colour code based on balance
        if balance < 0:
            card_bg      = "#fff5f5"   # Red tint — negative balance
            border_color = "#fc8181"
            balance_color = "#e53e3e"
            balance_icon  = "⚠️"
        elif balance == 0:
            card_bg       = "#fffbeb"  # Yellow tint — zero balance
            border_color  = "#f6ad55"
            balance_color = "#dd6b20"
            balance_icon  = "⚠️"
        else:
            card_bg       = "#f0fff4"  # Green tint — positive balance
            border_color  = "#68d391"
            balance_color = "#276749"
            balance_icon  = "✅"

        # ── Card ─────────────────────────────────────────────
        card = tk.Frame(
            body,
            bg=card_bg,
            relief="solid", bd=1,
            highlightbackground=border_color,
            highlightthickness=2
        )
        card.pack(fill="x", padx=20, pady=8)

        # ── Card top row — name and balance ──────────────────
        top_row = tk.Frame(card, bg=card_bg)
        top_row.pack(fill="x", padx=12, pady=(10, 4))

        # Left — account name
        tk.Label(
            top_row,
            text=f"🏦  {account_name}",
            font=("Segoe UI", 12, "bold"),
            bg=card_bg, fg="#2d3748"
        ).pack(side="left")

        # Right — balance with colour
        tk.Label(
            top_row,
            text=f"{balance_icon}  {sym}{balance:,.2f}",
            font=("Segoe UI", 12, "bold"),
            bg=card_bg, fg=balance_color
        ).pack(side="right")

        # ── Notes row ────────────────────────────────────────
        notes_row = tk.Frame(card, bg=card_bg)
        notes_row.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(
            notes_row,
            text=f"📝  Notes: {notes}",
            font=("Segoe UI", 9, "italic"),
            bg=card_bg, fg="#718096"
        ).pack(side="left")

        # ── Action buttons row ────────────────────────────────
        # Three buttons: Edit, Adjust Balance, Delete
        action_row = tk.Frame(card, bg=card_bg)
        action_row.pack(anchor="e", padx=10, pady=(0, 8))

        # Edit button — opens edit screen for name and notes
        make_button(
            action_row, "✏️ Edit",
            lambda aid=account_id: show_edit_account(user_id, aid),
            color="#3182ce", width=12
        ).pack(side="left", padx=3)

        # Adjust Balance button — opens balance adjustment screen
        make_button(
            action_row, "💰 Adjust Balance",
            lambda aid=account_id, aname=account_name: show_adjust_balance(
                user_id, aid, aname
            ),
            color="#805ad5", width=16
        ).pack(side="left", padx=3)

        # Delete button
        make_button(
            action_row, "🗑️ Delete",
            lambda aid=account_id, aname=account_name: confirm_delete_account(
                user_id, aid, aname
            ),
            color="#e53e3e", width=10
        ).pack(side="left", padx=3)

    # ── Bottom buttons ────────────────────────────────────────
    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=15)

    if len(accounts) < 5:
        make_button(
            btn_frame, "➕ Add Account",
            lambda: show_add_account(user_id),
            color="#38a169"
        ).pack(side="left", padx=5)
    else:
        tk.Label(
            body,
            text="⚠️ Maximum 5 accounts reached.",
            font=("Segoe UI", 9),
            bg="#f0f4f8", fg="#e53e3e"
        ).pack()

    make_button(
        btn_frame, "← Back to Menu",
        lambda: show_main_menu(current_user),
        color="#718096"
    ).pack(side="left", padx=5)

def confirm_delete_account(user_id, account_id, account_name):
    """
    Confirmation dialog before deleting an account.
    Warns user that all transactions linked to this
    account will lose their account reference.
    """
    confirmed = messagebox.askyesno(
        "Confirm Delete",
        f"Delete account '{account_name}'?\n\n"
        f"⚠️ This cannot be undone.\n"
        f"Transactions linked to this account will\n"
        f"no longer have an account reference."
    )
    if confirmed:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM accounts WHERE id = ? AND user_id = ?",
                (account_id, user_id)
            )
            conn.commit()
        show_account_balance(user_id)


def show_edit_account(user_id, account_id):
    """
    Edit screen for account name and notes only.
    Balance is handled separately via show_adjust_balance
    to maintain a proper audit trail.
    """
    clear_window()

    # Load existing account data
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT account_name, balance, notes FROM accounts WHERE id = ? AND user_id = ?",
            (account_id, user_id)
        )
        row = cursor.fetchone()

    if not row:
        messagebox.showerror("Error", "Account not found.")
        show_account_balance(user_id)
        return

    old_name, old_balance, old_notes = row
    old_notes = old_notes or ""
    sym       = get_currency(user_id)

    # ── Header ───────────────────────────────────────────────
    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(
        header,
        text="✏️ Edit Account",
        font=("Segoe UI", 16, "bold"),
        fg="white", bg="#2b6cb0"
    ).pack()

    body = make_scrollable_frame(root)

    # ── Info note ─────────────────────────────────────────────
    # Explain why balance is not editable here
    note_frame = tk.Frame(body, bg="#ebf8ff", relief="solid", bd=1)
    note_frame.pack(fill="x", padx=20, pady=(10, 5))
    tk.Label(
        note_frame,
        text=(
            "ℹ️ You can edit the account name and notes here.\n"
            "To adjust the balance, use the 💰 Adjust Balance button\n"
            "on the accounts screen — this keeps a proper record."
        ),
        font=("Segoe UI", 9, "italic"),
        bg="#ebf8ff", fg="#2c5282",
        wraplength=430, justify="left",
        pady=8, padx=8
    ).pack()

    # ── Current balance display (read only) ───────────────────
    bal_frame = tk.Frame(body, bg="white", relief="solid", bd=1)
    bal_frame.pack(fill="x", padx=20, pady=5)
    tk.Label(
        bal_frame,
        text=f"Current Balance:  {sym}{old_balance:,.2f}",
        font=("Segoe UI", 11, "bold"),
        bg="white", fg="#2b6cb0",
        pady=8
    ).pack()

    # ── Account name field ────────────────────────────────────
    tk.Label(
        body,
        text="Account Name:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20, pady=(10, 0))

    name_entry = make_entry(body, width=35)
    name_entry.insert(0, old_name)       # Pre-fill existing name
    name_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Notes field ───────────────────────────────────────────
    tk.Label(
        body,
        text="Notes (optional):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    notes_entry = make_entry(body, width=35)
    notes_entry.insert(0, old_notes)     # Pre-fill existing notes
    notes_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Message label ─────────────────────────────────────────
    msg_label = tk.Label(
        body, text="",
        font=("Segoe UI", 10),
        bg="#f0f4f8", fg="red",
        wraplength=400
    )
    msg_label.pack(padx=20, pady=5)

    def on_save():
        new_name  = name_entry.get().strip()
        new_notes = notes_entry.get().strip()

        # Validate name not empty
        if not new_name:
            msg_label.config(
                text="❌ Account name cannot be empty.", fg="red")
            return

        # Check for duplicate name — but allow keeping the same name
        existing = view_accounts(user_id)
        for acc in existing:
            if acc[1] == new_name and acc[0] != account_id:
                msg_label.config(
                    text="❌ Another account already has this name.",
                    fg="red")
                return

        # Save changes
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''UPDATE accounts
                   SET account_name = ?, notes = ?
                   WHERE id = ? AND user_id = ?''',
                (new_name, new_notes, account_id, user_id)
            )
            conn.commit()

        msg_label.config(
            text="✅ Account updated successfully!", fg="green")
        root.after(1000, lambda: show_account_balance(user_id))

    # ── Buttons ───────────────────────────────────────────────
    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=10, padx=20, anchor="w")

    make_button(
        btn_frame, "✅ Save Changes",
        on_save, color="#38a169"
    ).pack(side="left", padx=5)

    make_button(
        btn_frame, "← Back",
        lambda: show_account_balance(user_id),
        color="#718096"
    ).pack(side="left", padx=5)


def show_adjust_balance(user_id, account_id, account_name):
    """
    Dedicated screen to adjust an account's balance.
    Creates a real transaction record for the adjustment
    so there is always an audit trail of why balance changed.
    """
    clear_window()

    # Load current balance
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT balance FROM accounts WHERE id = ? AND user_id = ?",
            (account_id, user_id)
        )
        row = cursor.fetchone()

    if not row:
        messagebox.showerror("Error", "Account not found.")
        show_account_balance(user_id)
        return

    current_balance = row[0]
    sym             = get_currency(user_id)

    # ── Header ───────────────────────────────────────────────
    header = tk.Frame(root, bg="#805ad5", pady=12)
    header.pack(fill="x")

    tk.Label(
        header,
        text="💰 Adjust Balance",
        font=("Segoe UI", 16, "bold"),
        fg="white", bg="#805ad5"
    ).pack()

    tk.Label(
        header,
        text=f"Account: {account_name}",
        font=("Segoe UI", 10),
        fg="#e9d8fd", bg="#805ad5"
    ).pack()

    # ── Pinned button bar ─────────────────────────────────────
    # IMPORTANT: Pack btn_bar BEFORE body
    # In tkinter, side="bottom" only works if packed
    # before the widget that fills remaining space
    btn_bar = tk.Frame(root, bg="#f0f4f8", pady=10)
    btn_bar.pack(side="bottom", fill="x", padx=20)

    # ── Scrollable body ───────────────────────────────────────
    # Packed AFTER btn_bar so it fills the space between
    # the header and the button bar
    body = make_scrollable_frame(root)

    # ── Explanation note ──────────────────────────────────────
    note_frame = tk.Frame(body, bg="#faf5ff", relief="solid", bd=1)
    note_frame.pack(fill="x", padx=20, pady=(10, 5))

    tk.Label(
        note_frame,
        text=(
            "ℹ️ Balance adjustments are recorded as transactions\n"
            "so you always have a history of every balance change.\n"
            "Example reasons: bank fee, found cash, correction."
        ),
        font=("Segoe UI", 9, "italic"),
        bg="#faf5ff", fg="#553c9a",
        wraplength=430, justify="left",
        pady=8, padx=8
    ).pack()

    # ── Current balance display ───────────────────────────────
    bal_frame = tk.Frame(body, bg="white", relief="solid", bd=1)
    bal_frame.pack(fill="x", padx=20, pady=5)

    tk.Label(
        bal_frame,
        text=f"Current Balance:  {sym}{current_balance:,.2f}",
        font=("Segoe UI", 12, "bold"),
        bg="white", fg="#2b6cb0",
        pady=10
    ).pack()

    # ── Adjustment type ───────────────────────────────────────
    tk.Label(
        body,
        text="Adjustment Type:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20, pady=(10, 0))

    tk.Label(
        body,
        text="Add money = income adjustment  |  Remove money = expense adjustment",
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8", fg="#718096"
    ).pack(anchor="w", padx=20)

    adj_type_var = tk.StringVar(value="income")
    type_frame   = tk.Frame(body, bg="#f0f4f8")
    type_frame.pack(anchor="w", padx=20, pady=(4, 10))

    tk.Radiobutton(
        type_frame,
        text="➕ Add to balance (income)",
        variable=adj_type_var,
        value="income",
        bg="#f0f4f8",
        font=("Segoe UI", 10)
    ).pack(side="left")

    tk.Radiobutton(
        type_frame,
        text="➖ Remove from balance (expense)",
        variable=adj_type_var,
        value="expense",
        bg="#f0f4f8",
        font=("Segoe UI", 10)
    ).pack(side="left", padx=10)

    # ── Adjustment amount ─────────────────────────────────────
    tk.Label(
        body,
        text=f"Adjustment Amount ({sym}):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    amount_entry = make_entry(body, width=20)
    amount_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Reason field ──────────────────────────────────────────
    tk.Label(
        body,
        text="Reason for adjustment:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    tk.Label(
        body,
        text="e.g. Bank fee, Found cash, Correction, Interest earned",
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8", fg="#718096"
    ).pack(anchor="w", padx=20)

    reason_entry = make_entry(body, width=40)
    reason_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Live preview label ────────────────────────────────────
    preview_label = tk.Label(
        body,
        text=f"New balance will be:  {sym}{current_balance:,.2f}",
        font=("Segoe UI", 11, "bold"),
        bg="#f0f4f8", fg="#2b6cb0"
    )
    preview_label.pack(anchor="w", padx=20, pady=5)

    # ── Message label ─────────────────────────────────────────
    msg_label = tk.Label(
        body, text="",
        font=("Segoe UI", 10),
        bg="#f0f4f8", fg="red",
        wraplength=400
    )
    msg_label.pack(padx=20, pady=5)

    # ── Helper functions ──────────────────────────────────────
    # All defined AFTER widgets so they can reference them

    def update_preview(*args):
        """Updates the preview label as user types."""
        try:
            adj_amount = float(amount_entry.get().strip())
            if adj_type_var.get() == "income":
                new_bal = current_balance + adj_amount
            else:
                new_bal = current_balance - adj_amount
            color = "#276749" if new_bal >= 0 else "#e53e3e"
            preview_label.config(
                text=f"New balance will be:  {sym}{new_bal:,.2f}",
                fg=color
            )
        except ValueError:
            # If amount is not a valid number yet just show current balance
            preview_label.config(
                text=f"New balance will be:  {sym}{current_balance:,.2f}",
                fg="#2b6cb0"
            )

    # ── FIXED: Use trace_add instead of trace ─────────────────
    # trace("w", ...) crashes on Python 3.14 / Tcl 9
    # trace_add("write", ...) is the correct modern syntax
    amount_entry.bind("<KeyRelease>", update_preview)
    adj_type_var.trace_add("write", update_preview)   # ← FIXED

    def on_confirm():
        adj_type = adj_type_var.get()
        reason   = reason_entry.get().strip()

        # Validate amount
        try:
            adj_amount = float(amount_entry.get().strip())
        except ValueError:
            msg_label.config(
                text="❌ Amount must be a valid number.", fg="red")
            return

        if adj_amount <= 0:
            msg_label.config(
                text="❌ Amount must be greater than 0.", fg="red")
            return

        # Reason is required for audit trail
        if not reason:
            msg_label.config(
                text="❌ Please enter a reason for the adjustment.",
                fg="red")
            return

        now = datetime.now()

        with get_db() as conn:
            cursor = conn.cursor()

            # Create Balance Adjustment category if it doesnt exist
            adj_category = "Balance Adjustment"
            cursor.execute(
                "SELECT 1 FROM categories WHERE user_id = ? AND type = ? AND name = ?",
                (user_id, adj_type, adj_category)
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO categories (user_id, type, name) VALUES (?, ?, ?)",
                    (user_id, adj_type, adj_category)
                )

            # Insert as a real transaction with reason as notes
            cursor.execute(
                '''INSERT INTO transactions
                   (user_id, category, type, amount,
                    date, time, account_id, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, adj_category, adj_type,
                 adj_amount,
                 now.strftime("%Y-%m-%d"),
                 now.strftime("%H:%M"),
                 account_id,
                 f"Balance adjustment: {reason}")
            )

            # Update account balance
            if adj_type == "income":
                cursor.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                    (adj_amount, account_id)
                )
            else:
                cursor.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                    (adj_amount, account_id)
                )

            conn.commit()

        msg_label.config(
            text="✅ Balance adjusted and transaction recorded!",
            fg="green"
        )
        root.after(1200, lambda: show_account_balance(user_id))

    # ── Add buttons to the pinned button bar ──────────────────
    make_button(
        btn_bar, "✅ Confirm Adjustment",
        on_confirm, color="#805ad5"
    ).pack(side="left", padx=5)

    make_button(
        btn_bar, "← Back",
        lambda: show_account_balance(user_id),
        color="#718096"
    ).pack(side="left", padx=5)


def view_accounts(user_id):
    # Returns list of (id, account_name, balance, notes)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, account_name, balance, notes FROM accounts WHERE user_id = ?",
            (user_id,)
        )
        return cursor.fetchall()


def show_add_account(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="➕ Add Account", font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)

    # Account name field
    tk.Label(body, text="Account Name:", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    name_entry = make_entry(body)
    name_entry.pack(anchor="w", pady=(2, 10))

    # Balance field
    tk.Label(body, text="Starting Balance ($):", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    balance_entry = make_entry(body)
    balance_entry.pack(anchor="w", pady=(2, 10))

    # Notes field
    tk.Label(body, text="Notes (optional):", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    notes_entry = make_entry(body)
    notes_entry.pack(anchor="w", pady=(2, 10))

    msg_label = tk.Label(body, text="", font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red", wraplength=400)
    msg_label.pack(pady=5)

    def on_submit():
        name = name_entry.get().strip()
        notes = notes_entry.get().strip()

        # Validate account name not empty
        if not name:
            msg_label.config(text="❌ Account name cannot be empty.", fg="red")
            return

        # Validate balance is a valid number
        try:
            balance = float(balance_entry.get().strip())
        except ValueError:
            msg_label.config(text="❌ Balance must be a valid number.", fg="red")
            return

        if balance < 0:
            msg_label.config(text="❌ Balance cannot be negative.", fg="red")
            return

        # Check for duplicate account name
        existing = view_accounts(user_id)
        if name in [acc[1] for acc in existing]:
            msg_label.config(text="❌ Account name already exists.", fg="red")
            return

        # Save to database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO accounts (user_id, account_name, balance, notes) VALUES (?, ?, ?, ?)",
                (user_id, name, balance, notes)
            )
            conn.commit()

        # Check badges after account creation
        check_and_award_badges(user_id)

        msg_label.config(text="✅ Account added successfully!", fg="green")
        # Refresh account screen after short delay
        root.after(1000, lambda: show_account_balance(user_id))

    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=10)
    make_button(btn_frame, "✅ Save Account", on_submit, color="#38a169").pack(side="left", padx=5)
    make_button(btn_frame, "← Back", lambda: show_account_balance(user_id), color="#718096").pack(side="left", padx=5)



# ============================================================
# BUDGETS SCREEN
# ============================================================
# Budget tracks spending against a set limit.
# Timeframes: Daily, Weekly, Monthly, Yearly.
# Progress calculated dynamically from transactions table.
# Category: any expense category, or "General" (all expenses).
# Max 5 budgets per user.
# ============================================================
def show_budgets(user_id):
    clear_window()

    # ── Header ──────────────────────────────────────────────
    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(
        header,
        text="📊 Budgets",
        font=("Segoe UI", 16, "bold"),
        fg="white", bg="#2b6cb0"
    ).pack()

    # ── Scrollable body ──────────────────────────────────────
    body = make_scrollable_frame(root)

    budgets = view_budgets(user_id)
    sym     = get_currency(user_id)

    if not budgets:
        # Empty state message
        empty_frame = tk.Frame(body, bg="#f0f4f8")
        empty_frame.pack(pady=40)
        tk.Label(
            empty_frame,
            text="📊",
            font=("Segoe UI", 36),
            bg="#f0f4f8"
        ).pack()
        tk.Label(
            empty_frame,
            text="No budgets yet.",
            font=("Segoe UI", 13, "bold"),
            bg="#f0f4f8", fg="#2d3748"
        ).pack(pady=(5, 2))
        tk.Label(
            empty_frame,
            text="Add a budget to start tracking your spending.",
            font=("Segoe UI", 10),
            bg="#f0f4f8", fg="#718096"
        ).pack()

    # ── Budget cards ─────────────────────────────────────────
    for budget in budgets:
        budget_id = budget[0]
        budget_name = budget[2]
        timeframe = budget[3]
        category = budget[6]
        amount = budget[7]
        notes = budget[9] or ""

        # Use one reference date for this card's period and spending.
        today = datetime.today().date()

        period_start, period_end, days_left = get_budget_period(
            timeframe,
            reference_date=today
        )

        # period_end is exclusive. Display the last included day.
        display_end = period_end - timedelta(days=1)

        # Read the actual spending total rather than reconstructing
        # it from a percentage.
        (
            transactions,
            spent_amount,
            budget_limit,
            fetched_budget_name,
            fetched_category,
            fetched_timeframe,
            window_start
        ) = get_budget_transactions(
            budget_id,
            user_id,
            reference_date=today
        )

        progress = (
            (spent_amount / amount) * 100
            if amount > 0
            else 0
        )

        over_amount = max(spent_amount - amount, 0)
        remaining = max(amount - spent_amount, 0)

        # Determine severity from the actual monetary amounts.
        if spent_amount > amount:
            severity = "exceeded"
            header_bg = "#e53e3e"
            card_bg = "#fff5f5"
            border_color = "#fc8181"
            status_icon = "🔴"
            status_text = "EXCEEDED"
            status_color = "#e53e3e"

        elif spent_amount == amount:
            severity = "at_limit"
            header_bg = "#dd6b20"
            card_bg = "#fffbeb"
            border_color = "#f6ad55"
            status_icon = "🟡"
            status_text = "LIMIT REACHED"
            status_color = "#dd6b20"

        elif progress >= 80:
            severity = "warning"
            header_bg = "#dd6b20"
            card_bg = "#fffbeb"
            border_color = "#f6ad55"
            status_icon = "🟡"
            status_text = "APPROACHING LIMIT"
            status_color = "#dd6b20"

        else:
            severity = "ok"
            header_bg = "#276749"
            card_bg = "#f0fff4"
            border_color = "#68d391"
            status_icon = "🟢"
            status_text = "WITHIN LIMIT"
            status_color = "#276749"

        # ── Outer card ───────────────────────────────────────
        card = tk.Frame(
            body,
            bg=card_bg,
            relief="solid", bd=1,
            highlightbackground=border_color,
            highlightthickness=2
        )
        card.pack(fill="x", padx=20, pady=8)

        # ── Coloured card header strip ───────────────────────
        card_header = tk.Frame(card, bg=header_bg, pady=8)
        card_header.pack(fill="x")

        # Left side — budget name and status
        left_head = tk.Frame(card_header, bg=header_bg)
        left_head.pack(side="left", padx=12)

        tk.Label(
            left_head,
            text=f"📊  {budget_name}",
            font=("Segoe UI", 12, "bold"),
            bg=header_bg, fg="white"
        ).pack(anchor="w")

        tk.Label(
            left_head,
            text=f"{status_icon} {status_text}",
            font=("Segoe UI", 9, "bold"),
            bg=header_bg, fg="white"
        ).pack(anchor="w")

        # Right side — timeframe and category badge
        right_head = tk.Frame(card_header, bg=header_bg)
        right_head.pack(side="right", padx=12)

        tk.Label(
            right_head,
            text=f"⏱ {timeframe}",
            font=("Segoe UI", 9, "bold"),
            bg=header_bg, fg="white"
        ).pack(anchor="e")

        tk.Label(
            right_head,
            text=f"🏷 {category}",
            font=("Segoe UI", 9),
            bg=header_bg, fg="white"
        ).pack(anchor="e")

        # ── Money breakdown ───────────────────────────────────
        breakdown = tk.Frame(card, bg=card_bg)
        breakdown.pack(fill="x", padx=15, pady=(10, 5))

        # Three column layout for money figures
        # Column 1 = Limit, Column 2 = Spent, Column 3 = Over/Remaining
        cols = tk.Frame(breakdown, bg=card_bg)
        cols.pack(fill="x")

        # Helper to make one money column
        def make_money_col(parent, top_label,
                           amount_text, amount_color, bg):
            col = tk.Frame(parent, bg=bg)
            col.pack(side="left", expand=True)
            tk.Label(
                col,
                text=top_label,
                font=("Segoe UI", 8),
                bg=bg, fg="#718096"
            ).pack()
            tk.Label(
                col,
                text=amount_text,
                font=("Segoe UI", 11, "bold"),
                bg=bg, fg=amount_color
            ).pack()

        # Budget limit column — always neutral blue
        make_money_col(
            cols,
            "BUDGET LIMIT",
            f"{sym}{amount:,.2f}",
            "#2b6cb0",
            card_bg
        )

        # Vertical divider
        tk.Frame(cols, bg=border_color, width=1).pack(
            side="left", fill="y", padx=5
        )

        # Spent column — colour matches severity
        make_money_col(
            cols,
            "AMOUNT SPENT",
            f"{sym}{spent_amount:,.2f}",
            status_color,
            card_bg
        )

        # Vertical divider
        tk.Frame(cols, bg=border_color, width=1).pack(
            side="left", fill="y", padx=5
        )

        # Third column — Over by (if exceeded) or Remaining (if not)
        if severity == "exceeded":
            make_money_col(
                cols,
                "OVER BY",
                f"{sym}{over_amount:,.2f}",
                "#e53e3e",
                card_bg
            )
        else:
            make_money_col(
                cols,
                "REMAINING",
                f"{sym}{remaining:,.2f}",
                "#276749",
                card_bg
            )

        # ── Horizontal divider ────────────────────────────────
        ttk.Separator(
            breakdown, orient="horizontal"
        ).pack(fill="x", pady=8)

        # ── Progress bar ──────────────────────────────────────
        bar_info = tk.Frame(breakdown, bg=card_bg)
        bar_info.pack(fill="x")

        # Left label — percentage used
        tk.Label(
            bar_info,
            text=f"Used: {progress:.1f}%",
            font=("Segoe UI", 9, "bold"),
            bg=card_bg, fg=status_color
        ).pack(side="left")

        # Includes today because spending may still occur today.
        if days_left == 1:
            days_text = "Last day — includes today"
        else:
            days_text = f"{days_left} days left — includes today"

        days_color = "#718096"

        tk.Label(
            bar_info,
            text=days_text,
            font=("Segoe UI", 9),
            bg=card_bg, fg=days_color
        ).pack(side="right")

        # A conventional usage bar:
        # full width represents 100% of the budget.
        # Actual usage above 100% is shown by the percentage and
        # "Over by" amount, not by a misleading midpoint marker.
        usage_bar = ttk.Progressbar(
            breakdown,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            value=max(0, min(progress, 100))
        )
        usage_bar.pack(fill="x", pady=(4, 0))

        tk.Label(
            breakdown,
            text=(
                "Bar scale: 0–100% of the budget. "
                "Any overspend is shown in the amounts above."
            ),
            font=("Segoe UI", 8),
            bg=card_bg,
            fg="#718096",
            wraplength=500,
            justify="left"
        ).pack(anchor="w", pady=(3, 0))

        # ── Date info row ─────────────────────────────────────
        date_row = tk.Frame(card, bg=card_bg)
        date_row.pack(fill="x", padx=15, pady=(4, 4))

        tk.Label(
            date_row,
            text=(
                f"Calendar period: {period_start.isoformat()} "
                f"→ {display_end.isoformat()}\n"
                f"Recorded spending counted through: {today.isoformat()}"
            ),
            font=("Segoe UI", 8, "italic"),
            bg=card_bg,
            fg="#718096",
            justify="left"
        ).pack(anchor="w")

        tk.Label(
            card,
            text=(
                "The limit applies to the whole calendar period, including "
                "expenses recorded before this budget was created. "
                "It is not automatically prorated."
            ),
            font=("Segoe UI", 8, "italic"),
            bg=card_bg,
            fg="#718096",
            wraplength=550,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 6))

        # Display budget notes only if the user entered notes
        if notes:
            notes_row = tk.Frame(card, bg=card_bg)
            notes_row.pack(fill="x", padx=15, pady=(0, 4))

            tk.Label(
                notes_row,
                text=f"📝 Notes: {notes}",
                font=("Segoe UI", 9, "italic"),
                bg=card_bg,
                fg="#4a5568",
                wraplength=600,
                justify="left"
            ).pack(anchor="w")

        # ── Card action buttons ───────────────────────────────
        action_row = tk.Frame(card, bg=card_bg)
        action_row.pack(anchor="e", padx=10, pady=(0, 8))

        # View Spending button — opens spending breakdown popup
        make_button(
            action_row, "🔍 View Spending",
            lambda bid=budget_id: show_budget_spending(user_id, bid),
            color="#805ad5", width=16
        ).pack(side="left", padx=3)

        make_button(
            action_row, "✏️ Edit",
            lambda bid=budget_id: show_edit_budget(user_id, bid),
            color="#3182ce", width=10
        ).pack(side="left", padx=3)

        make_button(
            action_row, "🗑️ Delete",
            lambda bid=budget_id, bname=budget_name: confirm_delete_budget(
                user_id, bid, bname
            ),
            color="#e53e3e", width=10
        ).pack(side="left", padx=3)

    # ── Bottom buttons ────────────────────────────────────────
    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=15)

    if len(budgets) < 5:
        make_button(
            btn_frame, "➕ Add Budget",
            lambda: show_add_budget(user_id),
            color="#38a169"
        ).pack(side="left", padx=5)
    else:
        tk.Label(
            body,
            text="⚠️ Maximum 5 budgets reached.",
            font=("Segoe UI", 9),
            bg="#f0f4f8", fg="#e53e3e"
        ).pack()

    make_button(
        btn_frame, "← Back to Menu",
        lambda: show_main_menu(current_user),
        color="#718096"
    ).pack(side="left", padx=5)

def confirm_delete_budget(user_id, budget_id, budget_name):
    """
    Deletes a budget and its dependent monthly settings history.

    Past transactions and account balances remain unchanged.
    """
    # Read the current record instead of relying on a potentially
    # outdated name supplied by the budget card.
    with get_db() as conn:
        row = conn.execute(
            '''SELECT budget_name
               FROM budgets
               WHERE id = ? AND user_id = ?''',
            (budget_id, user_id)
        ).fetchone()

    if row is None:
        messagebox.showinfo(
            "Budget Not Found",
            "This budget no longer exists. The list will refresh.",
            parent=root
        )
        show_budgets(user_id)
        return

    current_name = row[0]

    confirmed = messagebox.askyesno(
        "Permanently Delete Budget",
        (
            f"Delete budget '{current_name}'?\n\n"
            "Its recorded monthly settings history will also be "
            "permanently deleted. It will no longer appear in the "
            "historical budget review.\n\n"
            "Past transactions and account balances will not change.\n"
            "Transactions remain available in normal Transaction History.\n\n"
            "This cannot be undone."
        ),
        parent=root
    )

    if not confirmed:
        return

    try:
        with get_db() as conn:
            conn.execute("BEGIN IMMEDIATE")

            cursor = conn.execute(
                '''DELETE FROM budgets
                   WHERE id = ? AND user_id = ?''',
                (budget_id, user_id)
            )
            deleted_count = cursor.rowcount

            # With foreign keys enabled, ON DELETE CASCADE removes
            # this budget's monthly history in the same transaction.
            conn.commit()

    except sqlite3.Error as error:
        messagebox.showerror(
            "Budget Deletion Failed",
            (
                "The deletion did not complete. Uncommitted database "
                "changes from this attempt were rolled back.\n\n"
                f"Details: {error}"
            ),
            parent=root
        )
        return

    if deleted_count == 0:
        messagebox.showinfo(
            "Budget Not Found",
            "The budget was already removed. The list will refresh.",
            parent=root
        )

    show_budgets(user_id)


def show_edit_budget(user_id, budget_id):
    """
    Edit screen for an existing budget.
    Lets user change name, amount, timeframe and category.
    """
    clear_window()

    # Load existing budget data to pre-fill the form
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT budget_name, timeframe, category, amount, notes
               FROM budgets
               WHERE id = ? AND user_id = ?''',
            (budget_id, user_id)
        )
        row = cursor.fetchone()

    if not row:
        messagebox.showerror("Error", "Budget not found.")
        show_budgets(user_id)
        return

    (old_name, old_timeframe, old_category,
     old_amount, old_notes) = row

    old_notes = old_notes or ""

    # ── Header ───────────────────────────────────────────────
    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(
        header,
        text="✏️ Edit Budget",
        font=("Segoe UI", 16, "bold"),
        fg="white", bg="#2b6cb0"
    ).pack()

    body = make_scrollable_frame(root)

    # ── Budget name ───────────────────────────────────────────
    tk.Label(
        body,
        text="Budget Name:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20, pady=(10, 0))

    name_entry = make_entry(body)
    name_entry.insert(0, old_name)     # Pre-fill with existing name
    name_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Timeframe ─────────────────────────────────────────────
    tk.Label(
        body,
        text="Timeframe:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    timeframe_var = tk.StringVar(value=old_timeframe)
    timeframe_dd = ttk.Combobox(
        body,
        textvariable=timeframe_var,
        values=["Daily", "Weekly", "Monthly", "Yearly"],
        state="readonly", width=28
    )
    timeframe_dd.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Amount limit ──────────────────────────────────────────
    sym = get_currency(user_id)
    tk.Label(
        body,
        text=f"Amount Limit ({sym}):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    amount_entry = make_entry(body)
    amount_entry.insert(0, str(old_amount))   # Pre-fill with existing amount
    amount_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Category ──────────────────────────────────────────────
    tk.Label(
        body,
        text="Category:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    # Horizontal frame for dropdown and button side by side
    cat_row = tk.Frame(body, bg="#f0f4f8")
    cat_row.pack(anchor="w", padx=20, pady=(2, 10))

    categories = get_expense_categories(user_id, include_all=True)
    # Older budgets may still contain the previous special value.
    if old_category == "General":
        old_category = ALL_EXPENSE_CATEGORIES
    category_var  = tk.StringVar(value=old_category)
    category_dd   = ttk.Combobox(
        cat_row,
        textvariable=category_var,
        values=categories,
        state="readonly", width=25
    )
    category_dd.pack(side="left")

    # Add Category button
    make_button(
        cat_row, "+ Add Category",
        lambda: open_add_category_popup(
            user_id, "expense", category_dd, category_var
        ),
        color="#3182ce", width=14
    ).pack(side="left", padx=6)

    # ── Budget notes ──────────────────────────────────────────
    tk.Label(
        body,
        text="Notes (optional):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20, pady=(2, 0))

    tk.Label(
        body,
        text="Describe the purpose or scope of this budget.",
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8",
        fg="#718096"
    ).pack(anchor="w", padx=20)

    notes_entry = tk.Text(
        body,
        height=3,
        width=45,
        font=("Segoe UI", 10),
        relief="solid",
        bd=1,
        wrap="word"
    )
    notes_entry.insert("1.0", old_notes)
    notes_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Info note ─────────────────────────────────────────────
    note_frame = tk.Frame(body, bg="#ebf8ff", relief="solid", bd=1)
    note_frame.pack(fill="x", padx=20, pady=5)
    tk.Label(
        note_frame,
        text=(
            "Budgets use calendar periods. Monthly amount and category "
            "changes apply to the entire CURRENT calendar month; "
            "previous recorded months remain unchanged. Repeated saves "
            "replace this month's settings, not create an edit-by-edit "
            "audit log. Monthly budgets with history cannot be changed "
            "to another timeframe."
        ),
        font=("Segoe UI", 9, "italic"),
        bg="#ebf8ff", fg="#2c5282",
        wraplength=420, pady=8
    ).pack()

    # ── Message label ─────────────────────────────────────────
    msg_label = tk.Label(
        body, text="",
        font=("Segoe UI", 10),
        bg="#f0f4f8", fg="red",
        wraplength=400
    )
    msg_label.pack(padx=20, pady=5)

    def on_save():  
        import math

        new_name      = name_entry.get().strip()
        new_timeframe = timeframe_var.get()
        new_category  = category_var.get()
        new_notes     = notes_entry.get("1.0", tk.END).strip()

        # Validate name
        if not new_name:
            msg_label.config(
                text="❌ Budget name cannot be empty.", fg="red")
            return

        # Validate amount
        try:
            new_amount = float(amount_entry.get().strip())
        except ValueError:
            msg_label.config(
                text="❌ Amount must be a valid number.", fg="red")
            return

        if not math.isfinite(new_amount) or new_amount <= 0:
            msg_label.config(
                text="❌ Amount must be a finite number greater than zero.",
                fg="red"
            )
            return

        # Refresh the stored snapshot using calendar boundaries.
        # This does not create a rolling period starting today.
        try:
            start_date, end_date, _ = get_budget_period(new_timeframe)
        except ValueError as error:
            msg_label.config(text=str(error), fg="red")
            return

        # Save the budget and its current-month history together.
        try:
            with get_db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                cursor = conn.cursor()

                current = cursor.execute(
                    '''SELECT timeframe
                       FROM budgets
                       WHERE id = ? AND user_id = ?''',
                    (budget_id, user_id)
                ).fetchone()

                if current is None:
                    raise ValueError("This budget no longer exists.")

                current_timeframe = current[0]

                history_exists = cursor.execute(
                    '''SELECT 1
                       FROM budget_monthly_history
                       WHERE budget_id = ? AND user_id = ?
                       LIMIT 1''',
                    (budget_id, user_id)
                ).fetchone() is not None

                if (
                    new_timeframe != "Monthly"
                    and (
                        current_timeframe == "Monthly"
                        or history_exists
                    )
                ):
                    raise ValueError(
                        "A monthly budget with tracked history cannot "
                        "be changed to another timeframe. Create a "
                        "separate budget instead."
                    )

                cursor.execute(
                    '''UPDATE budgets
                       SET budget_name = ?,
                           timeframe = ?,
                           category = ?,
                           amount = ?,
                           start_date = ?,
                           end_date = ?,
                           notes = ?
                       WHERE id = ? AND user_id = ?''',
                    (
                        new_name,
                        new_timeframe,
                        new_category,
                        new_amount,
                        start_date.isoformat(),
                        end_date.isoformat(),
                        new_notes,
                        budget_id,
                        user_id
                    )
                )

                record_monthly_budget_settings(
                    conn,
                    user_id,
                    budget_id
                )

                conn.commit()

        except (sqlite3.Error, ValueError) as error:
            msg_label.config(
                text=f"Could not update the budget: {error}",
                fg="red"
            )
            return

        msg_label.config(
            text="✅ Budget updated successfully!", fg="green")
        root.after(1000, lambda: show_budgets(user_id))

    # ── Buttons ───────────────────────────────────────────────
    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=10, padx=20, anchor="w")

    make_button(
        btn_frame, "✅ Save Changes",
        on_save, color="#38a169"
    ).pack(side="left", padx=5)

    make_button(
        btn_frame, "← Back",
        lambda: show_budgets(user_id),
        color="#718096"
    ).pack(side="left", padx=5)

def view_budgets(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM budgets WHERE user_id = ?", (user_id,))
        return cursor.fetchall()

def get_budget_period(timeframe, reference_date=None):
    """
    Returns calendar-period information for a budget.

    Returns:
        period_start: inclusive datetime.date
        period_end: exclusive datetime.date
        days_remaining: includes the reference day

    reference_date:
        Optional datetime.date used for testing or historical analysis.
        Defaults to today's local date.
    """
    if reference_date is None:
        reference_date = datetime.today().date()

    if timeframe == "Daily":
        period_start = reference_date
        period_end = period_start + timedelta(days=1)

    elif timeframe == "Weekly":
        period_start = reference_date - timedelta(
            days=reference_date.weekday()
        )
        period_end = period_start + timedelta(days=7)

    elif timeframe == "Monthly":
        period_start = reference_date.replace(day=1)
        period_end = period_start + relativedelta(months=1)

    elif timeframe == "Yearly":
        period_start = reference_date.replace(month=1, day=1)
        period_end = period_start + relativedelta(years=1)

    else:
        raise ValueError(
            f"Unsupported budget timeframe: {timeframe}"
        )

    days_remaining = (period_end - reference_date).days

    return period_start, period_end, days_remaining

def calculate_budget_progress(budget_id, user_id, reference_date=None):
    """
    Calculates uncapped budget usage using the same expenses
    returned by get_budget_transactions().
    """
    (
        transactions,
        total_spent,
        budget_limit,
        budget_name,
        category,
        timeframe,
        window_start
    ) = get_budget_transactions(
        budget_id,
        user_id,
        reference_date=reference_date
    )

    if not budget_name or budget_limit <= 0:
        return 0

    return (total_spent / budget_limit) * 100

def get_spending_comparison_periods(
    selected_year,
    selected_month,
    reference_date=None
):
    """
    Returns date ranges for a selected-month spending comparison.

    All ranges use an inclusive start and exclusive end.

    Current month:
        Compare equal numbers of elapsed days, limited by
        the previous month's length.

    Completed month:
        Compare both full calendar months.

    Future month:
        Raise ValueError.

    This function reads no database data.
    """
    from datetime import date

    if reference_date is None:
        reference_date = datetime.today().date()

    selected_start = date(selected_year, selected_month, 1)
    current_month_start = reference_date.replace(day=1)

    if selected_start > current_month_start:
        raise ValueError(
            "Spending comparisons are not available for future months."
        )

    previous_start = selected_start - relativedelta(months=1)
    selected_month_end = selected_start + relativedelta(months=1)

    is_current_month = selected_start == current_month_start

    if is_current_month:
        previous_month_days = (
            selected_start - previous_start
        ).days

        matched_days = min(
            reference_date.day,
            previous_month_days
        )

        selected_end = selected_start + timedelta(days=matched_days)
        previous_end = previous_start + timedelta(days=matched_days)
        comparison_mode = "matched_elapsed_days"

    else:
        selected_end = selected_month_end
        previous_end = selected_start
        comparison_mode = "full_months"

    selected_days = (selected_end - selected_start).days
    previous_days = (previous_end - previous_start).days

    return {
        "mode": comparison_mode,
        "as_of": reference_date.isoformat(),
        "selected_start": selected_start,
        "selected_end": selected_end,
        "previous_start": previous_start,
        "previous_end": previous_end,
        "selected_last_day": selected_end - timedelta(days=1),
        "previous_last_day": previous_end - timedelta(days=1),
        "selected_days": selected_days,
        "previous_days": previous_days,
        "equal_day_counts": selected_days == previous_days,
        "current_month_cutoff_limited": (
            is_current_month
            and selected_end - timedelta(days=1) < reference_date
        )
    }

def get_category_spending_recommendations(
    user_id,
    selected_year,
    selected_month,
    reference_date=None
):
    """
    Compares recorded expense totals by category.

    Returns:
        {
            "periods": comparison-period information,
            "recommendations": up to three spending increases,
            "invalid_amount_count": excluded invalid expense amounts
        }

    Reads data only. Does not change financial records.
    """
    import math
    from decimal import Decimal

    periods = get_spending_comparison_periods(
        selected_year,
        selected_month,
        reference_date=reference_date
    )

    invalid_amount_count = 0

    def collect_totals(conn, start, end):
        nonlocal invalid_amount_count

        rows = conn.execute(
            '''SELECT category, amount
               FROM transactions
               WHERE user_id = ?
                 AND type = 'expense'
                 AND date >= ?
                 AND date < ?''',
            (user_id, start.isoformat(), end.isoformat())
        ).fetchall()

        totals = {}

        for category, amount in rows:
            try:
                numeric_amount = float(amount)

                if (
                    not math.isfinite(numeric_amount)
                    or numeric_amount < 0
                ):
                    raise ValueError

                # Decimal avoids introducing extra binary-float
                # summation noise in this comparison.
                value = Decimal(str(amount))

            except (TypeError, ValueError, OverflowError):
                invalid_amount_count += 1
                continue

            # Category identity remains the stored category name.
            # Renamed or differently capitalised names are not merged.
            totals[category] = (
                totals.get(category, Decimal("0")) + value
            )

        return totals

    with get_db() as conn:
        # Both reads use the same database snapshot.
        conn.execute("BEGIN")

        selected_totals = collect_totals(
            conn,
            periods["selected_start"],
            periods["selected_end"]
        )

        previous_totals = collect_totals(
            conn,
            periods["previous_start"],
            periods["previous_end"]
        )

    increases = []

    categories = set(selected_totals) | set(previous_totals)

    for category in categories:
        selected_amount = selected_totals.get(
            category, Decimal("0")
        )
        previous_amount = previous_totals.get(
            category, Decimal("0")
        )
        increase = selected_amount - previous_amount

        if increase <= 0:
            continue

        percentage = (
            float((increase / previous_amount) * Decimal("100"))
            if previous_amount > 0
            else None
        )

        increases.append({
            "kind": "category_spending_increase",
            "category": category,
            "selected_amount": float(selected_amount),
            "previous_amount": float(previous_amount),
            "increase": float(increase),
            "percentage_increase": percentage,
            "has_previous_spending": previous_amount > 0,
            "suggestion": (
                "Consider reviewing the larger recorded expenses in "
                "this category and whether they fit your priorities."
            ),
            "limitation": (
                "An increase is not automatically a problem. "
                "Missing records, category-name changes, and one-off "
                "expenses can affect this comparison."
            )
        })

    increases.sort(
        key=lambda item: (
            -item["increase"],
            str(item["category"]).casefold()
        )
    )

    return {
        "periods": periods,
        "recommendations": increases[:3],
        "invalid_amount_count": invalid_amount_count
    }

def get_upcoming_expense_recommendations(user_id, reference_date=None):
    """
    Reads active expense schedules for a seven-day window.

    Window:
        reference_date through reference_date + 6 days, inclusive.

    Does not:
        - Generate transactions
        - Change next-due dates
        - Change account balances
        - Include scheduled income

    Returns account summaries, individual scheduled occurrences,
    and notices about incomplete or invalid schedule data.
    """
    import math

    if reference_date is None:
        reference_date = datetime.today().date()

    window_end = reference_date + timedelta(days=7)

    account_summaries = {}
    notices = []

    with get_db() as conn:
        # Read schedules and occurrence markers from one snapshot.
        conn.execute("BEGIN")

        rules = conn.execute(
            '''SELECT r.id, r.name, r.account_id, r.amount,
                      r.frequency, r.next_due_date, r.schedule_kind,
                      r.monthly_charge_days, r.schedule_start_date,
                      a.id, a.account_name, a.balance
               FROM recurring_transactions r
               LEFT JOIN accounts a
                 ON a.id = r.account_id AND a.user_id = r.user_id
               WHERE r.user_id = ?
                 AND r.is_active = 1
                 AND r.type = 'expense'
               ORDER BY r.id''',
            (user_id,)
        ).fetchall()

        processed = set(
            conn.execute(
                '''SELECT recurring_rule_id, scheduled_date
                   FROM processed_schedule_occurrences
                   WHERE user_id = ?
                     AND scheduled_date >= ?
                     AND scheduled_date < ?''',
                (
                    user_id,
                    reference_date.isoformat(),
                    window_end.isoformat()
                )
            ).fetchall()
        )

        linked_subscription_rules = {
            row[0]
            for row in conn.execute(
                '''SELECT recurring_rule_id
                   FROM subscriptions
                   WHERE user_id = ?
                     AND recurring_rule_id IS NOT NULL''',
                (user_id,)
            ).fetchall()
        }

        unlinked_count = conn.execute(
            '''SELECT COUNT(*)
               FROM subscriptions
               WHERE user_id = ? AND recurring_rule_id IS NULL''',
            (user_id,)
        ).fetchone()[0]

    if unlinked_count:
        notices.append(
            f"{unlinked_count} subscription(s) still need schedule setup "
            "and are excluded."
        )

    for rule in rules:
        (
            rule_id, name, account_id, stored_amount,
            frequency, next_due_text, schedule_kind,
            billing_days, start_date_text,
            found_account_id, account_name, stored_balance
        ) = rule

        if found_account_id is None:
            notices.append(
                f"'{name}' was excluded because its account is missing."
            )
            continue

        try:
            amount = float(stored_amount)
            balance = float(stored_balance)

            if (
                not math.isfinite(amount)
                or amount <= 0
                or not math.isfinite(balance)
            ):
                raise ValueError("Invalid amount or account balance.")

            due = datetime.strptime(
                next_due_text, "%Y-%m-%d"
            ).date()

            if schedule_kind == "subscription":
                if rule_id not in linked_subscription_rules:
                    raise ValueError("Missing linked subscription record.")

                start_date = datetime.strptime(
                    start_date_text, "%Y-%m-%d"
                ).date()

                due = next_subscription_billing_date(
                    billing_days,
                    max(due, start_date),
                    inclusive=True
                )

            elif schedule_kind != "recurring":
                raise ValueError("Unrecognised schedule type.")

            # Validate advancement even if the next date is outside
            # the requested window.
            advance_schedule_date(
                due, schedule_kind, frequency, billing_days
            )

            has_overdue_dates = due < reference_date
            iterations = 0
            occurrences = []

            # Advance using exactly the same date helper as the processor.
            # This preserves the processor's existing monthly behavior.
            while due < window_end:
                iterations += 1

                if iterations > 10000:
                    raise ValueError(
                        "Too many dates to inspect; review this schedule."
                    )

                if (
                    due >= reference_date
                    and (rule_id, due.isoformat()) not in processed
                ):
                    occurrences.append({
                        "rule_id": rule_id,
                        "name": name,
                        "scheduled_date": due.isoformat(),
                        "amount": amount,
                        "schedule_kind": schedule_kind
                    })

                following_due = advance_schedule_date(
                    due, schedule_kind, frequency, billing_days
                )

                if following_due <= due:
                    raise ValueError("Schedule dates did not advance.")

                due = following_due

        except (TypeError, ValueError, OverflowError) as error:
            notices.append(
                f"'{name}' was excluded: {error}"
            )
            continue

        if has_overdue_dates:
            notices.append(
                f"'{name}' has pending schedule dates before this window. "
                "Those dates are excluded from the upcoming total; "
                "account balances may not yet reflect their processing."
            )

        if not occurrences:
            continue

        if account_id not in account_summaries:
            account_summaries[account_id] = {
                "account_id": account_id,
                "account_name": account_name,
                "recorded_balance": balance,
                "scheduled_total": 0,
                "occurrences": []
            }

        summary = account_summaries[account_id]
        summary["occurrences"].extend(occurrences)

    for summary in account_summaries.values():
        summary["occurrences"].sort(
            key=lambda item: (
                item["scheduled_date"],
                item["name"].casefold(),
                item["rule_id"]
            )
        )

        summary["scheduled_total"] = sum(
            item["amount"] for item in summary["occurrences"]
        )

        summary["excess_over_recorded_balance"] = max(
            summary["scheduled_total"] - summary["recorded_balance"],
            0
        )

        summary["suggestion"] = (
            "Review this account before the scheduled dates. "
            "Scheduled expenses exceed its current recorded balance."
            if summary["scheduled_total"] > summary["recorded_balance"]
            else
            "Review these upcoming commitments before planning "
            "additional spending. A sufficient recorded balance does "
            "not establish affordability."
        )

    accounts = sorted(
        account_summaries.values(),
        key=lambda item: (
            -item["excess_over_recorded_balance"],
            item["account_name"].casefold(),
            item["account_id"]
        )
    )

    return {
        "window_start": reference_date.isoformat(),
        "window_last_day": (
            window_end - timedelta(days=1)
        ).isoformat(),
        "accounts": accounts,
        "notices": notices,
        "limitation": (
            "Based on active expense schedules and recorded account "
            "balances. Excludes scheduled income, pending dates before "
            "the window, unrecorded activity, and other future changes. "
            "This is not a complete cash-flow forecast."
        )
    }

def get_subscription_cost_review(user_id, reference_date=None):
    """
    Estimates unprocessed subscription expenses scheduled for
    the next calendar month, using current schedule settings.

    Reads data only. Does not process payments or change balances.
    """
    import math

    if reference_date is None:
        reference_date = datetime.today().date()

    month_start = (
        reference_date.replace(day=1) + relativedelta(months=1)
    )
    month_end = month_start + relativedelta(months=1)

    notices = []
    subscriptions = []

    with get_db() as conn:
        conn.execute("BEGIN")

        rows = conn.execute(
            '''SELECT
                   s.id, s.subscription_name, s.recurring_rule_id,
                   r.id, r.name, r.type, r.schedule_kind, r.is_active,
                   r.amount, r.monthly_charge_days,
                   r.schedule_start_date, r.next_due_date,
                   a.id, a.account_name
               FROM subscriptions s
               LEFT JOIN recurring_transactions r
                 ON r.id = s.recurring_rule_id
                AND r.user_id = s.user_id
               LEFT JOIN accounts a
                 ON a.id = r.account_id
                AND a.user_id = s.user_id
               WHERE s.user_id = ?
               ORDER BY s.id''',
            (user_id,)
        ).fetchall()

        processed = set(
            conn.execute(
                '''SELECT recurring_rule_id, scheduled_date
                   FROM processed_schedule_occurrences
                   WHERE user_id = ?
                     AND scheduled_date >= ?
                     AND scheduled_date < ?''',
                (
                    user_id,
                    month_start.isoformat(),
                    month_end.isoformat()
                )
            ).fetchall()
        )

    for row in rows:
        (
            sub_id, legacy_name, linked_rule_id,
            rule_id, rule_name, rule_type, schedule_kind, is_active,
            stored_amount, billing_days, start_text, next_due_text,
            account_id, account_name
        ) = row

        if linked_rule_id is None:
            notices.append(
                f"'{legacy_name}' needs schedule setup and is excluded."
            )
            continue

        if (
            rule_id is None
            or rule_type != "expense"
            or schedule_kind != "subscription"
        ):
            notices.append(
                f"'{legacy_name}' has an invalid schedule link "
                "and is excluded."
            )
            continue

        if not is_active:
            continue

        if account_id is None:
            notices.append(
                f"'{rule_name}' has no valid account and is excluded."
            )
            continue

        try:
            amount = float(stored_amount)

            if not math.isfinite(amount) or amount <= 0:
                raise ValueError("Invalid amount per occurrence.")

            start_date = datetime.strptime(
                start_text, "%Y-%m-%d"
            ).date()
            next_due = datetime.strptime(
                next_due_text, "%Y-%m-%d"
            ).date()

            # Do not invent occurrences earlier than the schedule's
            # start date or its current next-due boundary.
            candidate = next_subscription_billing_date(
                billing_days,
                max(month_start, start_date, next_due),
                inclusive=True
            )

            dates = []

            while candidate < month_end:
                if (rule_id, candidate.isoformat()) not in processed:
                    dates.append(candidate.isoformat())

                candidate = next_subscription_billing_date(
                    billing_days,
                    candidate,
                    inclusive=False
                )

        except (TypeError, ValueError, OverflowError) as error:
            notices.append(
                f"'{rule_name}' could not be evaluated: {error}"
            )
            continue

        subscriptions.append({
            "subscription_id": sub_id,
            "rule_id": rule_id,
            "name": rule_name,
            "account_name": account_name,
            "amount_per_occurrence": amount,
            "scheduled_dates": dates,
            "occurrence_count": len(dates),
            "scheduled_total": amount * len(dates)
        })

    subscriptions.sort(
        key=lambda item: (
            -item["scheduled_total"],
            item["name"].casefold(),
            item["subscription_id"]
        )
    )

    return {
        "period_start": month_start.isoformat(),
        "period_last_day": (
            month_end - timedelta(days=1)
        ).isoformat(),
        "evaluated_active_schedule_count": len(subscriptions),
        "occurrence_count": sum(
            item["occurrence_count"] for item in subscriptions
        ),
        "scheduled_total": sum(
            item["scheduled_total"] for item in subscriptions
        ),
        "subscriptions": subscriptions,
        "notices": notices,
        "suggestion": (
            "Consider reviewing whether these subscription plans "
            "still meet your needs before their scheduled dates."
        ),
        "limitation": (
            "An estimate using current active schedules and prices, "
            "not a provider invoice or a complete cash-flow forecast. "
            "Future price changes, cancellations, and schedule edits "
            "are unknown. The app does not measure subscription usage. "
            "Paused and unevaluable schedules are excluded."
        )
    }

def get_needs_wants_reflection(
    user_id,
    selected_year,
    selected_month,
    reference_date=None
):
    """
    Summarises recorded expenses by Need/Want classification
    for the selected report month.

    Rules:
    - Compares expenses only.
    - Treats 'unset' as unclassified, never as a Want.
    - For the current month, counts through today.
    - Reads data only.
    """
    import math
    from datetime import date
    from decimal import Decimal

    if reference_date is None:
        reference_date = datetime.today().date()

    period_start = date(selected_year, selected_month, 1)
    current_month_start = reference_date.replace(day=1)

    if period_start > current_month_start:
        raise ValueError(
            "Needs/Wants reflection is not available for future months."
        )

    month_end = period_start + relativedelta(months=1)

    # For the current month, count only through today.
    if period_start == current_month_start:
        spending_end = min(
            month_end,
            reference_date + timedelta(days=1)
        )
        counted_through = (spending_end - timedelta(days=1)).isoformat()
    else:
        spending_end = month_end
        counted_through = (month_end - timedelta(days=1)).isoformat()

    totals = {
        "need": Decimal("0"),
        "want": Decimal("0"),
        "unclassified": Decimal("0")
    }

    invalid_amount_count = 0

    with get_db() as conn:
        rows = conn.execute(
            '''SELECT amount, necessity
               FROM transactions
               WHERE user_id = ?
                 AND type = 'expense'
                 AND date >= ?
                 AND date < ?''',
            (
                user_id,
                period_start.isoformat(),
                spending_end.isoformat()
            )
        ).fetchall()

    for amount, necessity in rows:
        try:
            numeric = float(amount)

            if not math.isfinite(numeric) or numeric < 0:
                raise ValueError

            value = Decimal(str(amount))

        except (TypeError, ValueError, OverflowError):
            invalid_amount_count += 1
            continue

        if necessity == "need":
            totals["need"] += value
        elif necessity == "want":
            totals["want"] += value
        else:
            # Includes 'unset', NULL, or any unexpected value.
            totals["unclassified"] += value

    need_total = float(totals["need"])
    want_total = float(totals["want"])
    unclassified_total = float(totals["unclassified"])

    total_expenses = need_total + want_total + unclassified_total
    classified_total = need_total + want_total

    # Percentages of classified spending only.
    if classified_total > 0:
        need_percent = (need_total / classified_total) * 100
        want_percent = (want_total / classified_total) * 100
    else:
        need_percent = None
        want_percent = None

    return {
        "selected_year": selected_year,
        "selected_month": selected_month,
        "period_start": period_start.isoformat(),
        "period_last_day": (month_end - timedelta(days=1)).isoformat(),
        "counted_through": counted_through,
        "is_current_month": period_start == current_month_start,
        "need_total": need_total,
        "want_total": want_total,
        "unclassified_total": unclassified_total,
        "classified_total": classified_total,
        "total_expenses": total_expenses,
        "need_percent_of_classified": need_percent,
        "want_percent_of_classified": want_percent,
        "invalid_amount_count": invalid_amount_count,
        "suggestion": (
            "If you want to free up money for savings or goals, "
            "the Want expenses are usually the easiest to review first."
        ),
        "limitation": (
            "Covers recorded expenses only, by their Need/Want labels. "
            "Unclassified expenses are shown separately and are not "
            "counted as Wants. This is not a full 50/30/20 assessment, "
            "which also considers income, savings, and debt."
        )
    }

def get_repeated_spending_review(
    user_id,
    selected_year,
    selected_month,
    reference_date=None
):
    """
    Finds categories with at least five positive expense entries
    in the selected period.

    Returns up to three categories, ranked by recorded total.

    Reads data only. Does not infer impulse buying or wastefulness.
    """
    import math
    from datetime import date
    from decimal import Decimal

    if reference_date is None:
        reference_date = datetime.today().date()

    period_start = date(selected_year, selected_month, 1)
    current_month_start = reference_date.replace(day=1)

    if period_start > current_month_start:
        raise ValueError(
            "Repeated spending review is unavailable for future months."
        )

    period_end = period_start + relativedelta(months=1)

    if period_start == current_month_start:
        counted_end = min(
            period_end,
            reference_date + timedelta(days=1)
        )
    else:
        counted_end = period_end

    minimum_entries = 5
    invalid_amount_count = 0
    grouped = {}

    with get_db() as conn:
        rows = conn.execute(
            '''SELECT category, amount
               FROM transactions
               WHERE user_id = ?
                 AND type = 'expense'
                 AND date >= ?
                 AND date < ?''',
            (
                user_id,
                period_start.isoformat(),
                counted_end.isoformat()
            )
        ).fetchall()

    for category, amount in rows:
        try:
            numeric_amount = float(amount)

            if (
                not math.isfinite(numeric_amount)
                or numeric_amount < 0
            ):
                raise ValueError

            value = Decimal(str(amount))

        except (TypeError, ValueError, OverflowError):
            invalid_amount_count += 1
            continue

        # Zero-value entries do not represent a positive recorded cost.
        if value == 0:
            continue

        if category not in grouped:
            grouped[category] = {
                "count": 0,
                "total": Decimal("0")
            }

        grouped[category]["count"] += 1
        grouped[category]["total"] += value

    eligible = []

    for category, values in grouped.items():
        if values["count"] < minimum_entries:
            continue

        eligible.append({
            "category": category,
            "entry_count": values["count"],
            "total": values["total"],
            "average": values["total"] / Decimal(values["count"])
        })

    # Sort using Decimal totals before converting for display.
    eligible.sort(
        key=lambda item: (
            -item["total"],
            -item["entry_count"],
            str(item["category"]).casefold()
        )
    )

    reviews = [
        {
            "category": item["category"],
            "entry_count": item["entry_count"],
            "total": float(item["total"]),
            "average": float(item["average"]),
            "suggestion": (
                "Consider reviewing these entries for opportunities "
                "to reduce spending if that supports your priorities."
            )
        }
        for item in eligible[:3]
    ]

    return {
        "period_start": period_start.isoformat(),
        "period_last_day": (
            period_end - timedelta(days=1)
        ).isoformat(),
        "counted_through": (
            counted_end - timedelta(days=1)
        ).isoformat(),
        "minimum_entries": minimum_entries,
        "eligible_category_count": len(eligible),
        "reviews": reviews,
        "invalid_amount_count": invalid_amount_count,
        "limitation": (
            "Counts positive recorded expense entries, not verified "
            "purchases or spending habits. Repetition does not establish "
            "that expenses are unnecessary or impulsive. Split entries, "
            "scheduled payments, balance adjustments, missing records, "
            "and category naming can affect the result."
        )
    }

def get_data_quality_report(user_id, reference_date=None):
    """
    Collects data-quality issues that can affect insights.

    Reads data only. Does not modify any records.
    """
    import math
    from datetime import date

    if reference_date is None:
        reference_date = datetime.today().date()

    month_start = reference_date.replace(day=1)
    spending_end = reference_date + timedelta(days=1)

    issues = []

    with get_db() as conn:
        conn.execute("BEGIN")

        # Unclassified expenses in the current month, through today.
        unclassified = conn.execute(
            '''SELECT COUNT(*)
               FROM transactions
               WHERE user_id = ?
                 AND type = 'expense'
                 AND date >= ?
                 AND date < ?
                 AND (
                     necessity IS NULL
                     OR necessity NOT IN ('need', 'want')
                 )''',
            (
                user_id,
                month_start.isoformat(),
                spending_end.isoformat()
            )
        ).fetchone()[0]

        # Active schedules whose account is missing.
        missing_account = conn.execute(
            '''SELECT COUNT(*)
               FROM recurring_transactions r
               LEFT JOIN accounts a
                 ON a.id = r.account_id AND a.user_id = r.user_id
               WHERE r.user_id = ?
                 AND r.is_active = 1
                 AND a.id IS NULL''',
            (user_id,)
        ).fetchone()[0]

        # Subscriptions not yet linked to a shared schedule.
        unlinked_subscriptions = conn.execute(
            '''SELECT COUNT(*)
               FROM subscriptions
               WHERE user_id = ?
                 AND recurring_rule_id IS NULL''',
            (user_id,)
        ).fetchone()[0]

        budgets = conn.execute(
            '''SELECT budget_name, amount
               FROM budgets
               WHERE user_id = ?''',
            (user_id,)
        ).fetchall()

        accounts = conn.execute(
            '''SELECT account_name, balance
               FROM accounts
               WHERE user_id = ?''',
            (user_id,)
        ).fetchall()

    invalid_budget_count = 0
    for _name, amount in budgets:
        try:
            value = float(amount)
            if not math.isfinite(value) or value <= 0:
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            invalid_budget_count += 1

    negative_accounts = []
    for name, balance in accounts:
        try:
            value = float(balance)
            if math.isfinite(value) and value < 0:
                negative_accounts.append(name)
        except (TypeError, ValueError, OverflowError):
            # A non-numeric balance is itself a data problem.
            negative_accounts.append(name)

    if unclassified:
        issues.append({
            "key": "unclassified_expenses",
            "severity": "info",
            "title": "Unclassified expenses this month",
            "detail": (
                f"{unclassified} expense record(s) this month have no "
                "Need or Want classification. Classifying them makes the "
                "Needs/Wants reflection more complete."
            )
        })

    if missing_account:
        issues.append({
            "key": "schedules_missing_account",
            "severity": "warning",
            "title": "Active schedules without a valid account",
            "detail": (
                f"{missing_account} active schedule(s) have an unassigned, "
                "missing, or invalid account link. Review the schedules "
                "and assign a valid account before processing."
            )
        })

    if unlinked_subscriptions:
        issues.append({
            "key": "unlinked_subscriptions",
            "severity": "info",
            "title": "Subscriptions needing schedule setup",
            "detail": (
                f"{unlinked_subscriptions} subscription(s) are not linked "
                "to the shared scheduler and are excluded from scheduled "
                "expense guidance until set up."
            )
        })

    if invalid_budget_count:
        issues.append({
            "key": "invalid_budget_limits",
            "severity": "warning",
            "title": "Budgets with invalid limits",
            "detail": (
                f"{invalid_budget_count} budget(s) have a limit that is not "
                "a positive number. Budget guidance is skipped for them "
                "until the limit is corrected."
            )
        })

    if negative_accounts:
        shown = ", ".join(sorted(negative_accounts)[:5])
        more = len(negative_accounts) - 5

        detail = (
            "The following account(s) have a negative or unreadable "
            f"recorded balance: {shown}."
        )
        if more > 0:
            detail += f" ({more} more not shown.)"

        detail += (
            " This can result from recorded spending exceeding recorded "
            "income, or from missing income entries."
        )

        issues.append({
            "key": "negative_account_balances",
            "severity": "warning",
            "title": "Accounts with a negative recorded balance",
            "detail": detail
        })

    return {
        "as_of": reference_date.isoformat(),
        "issue_count": len(issues),
        "issues": issues,
        "limitation": (
            "Highlights detectable data issues only. A clean report does "
            "not prove your records are complete or correct. The app cannot "
            "detect expenses or income you did not record."
        )
    }

def initialise_monthly_budget_history(conn, reference_date=None):
    """
    Records a current-month baseline for monthly budgets that
    have no history at all.

    Does not create records for earlier months.
    Does not create a new snapshot every time the app starts.
    Uses the caller's transaction and does not commit.
    """
    import math

    if reference_date is None:
        reference_date = datetime.today().date()

    effective_month = reference_date.replace(day=1).isoformat()

    budgets = conn.execute(
        '''SELECT b.id, b.user_id, b.amount, b.category
           FROM budgets b
           WHERE b.timeframe = 'Monthly'
             AND NOT EXISTS (
                 SELECT 1
                 FROM budget_monthly_history h
                 WHERE h.budget_id = b.id
             )'''
    ).fetchall()

    for budget_id, user_id, stored_amount, category in budgets:
        try:
            amount = float(stored_amount)
            if not math.isfinite(amount) or amount <= 0:
                continue
        except (TypeError, ValueError, OverflowError):
            continue

        if user_id is None or not category or not category.strip():
            continue

        conn.execute(
            '''INSERT INTO budget_monthly_history
               (user_id, budget_id, effective_month, amount, category)
               VALUES (?, ?, ?, ?, ?)''',
            (
                user_id,
                budget_id,
                effective_month,
                amount,
                category.strip()
            )
        )

def record_monthly_budget_settings(
    conn,
    user_id,
    budget_id,
    reference_date=None
):
    """
    Records the current month's settings for a monthly budget.

    Uses the caller's existing connection so the history is saved
    in the same database transaction as the budget change.

    Returns the effective month, or None if the budget is not monthly.
    """
    import math

    if reference_date is None:
        reference_date = datetime.today().date()

    effective_month = reference_date.replace(day=1)

    budget = conn.execute(
        '''SELECT timeframe, amount, category
           FROM budgets
           WHERE id = ? AND user_id = ?''',
        (budget_id, user_id)
    ).fetchone()

    if budget is None:
        raise ValueError(
            "The budget could not be found for this user."
        )

    timeframe, stored_amount, category = budget

    # Settings history currently applies to monthly budgets only.
    if timeframe != "Monthly":
        return None

    try:
        amount = float(stored_amount)

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError

    except (TypeError, ValueError, OverflowError):
        raise ValueError(
            "The budget limit must be a finite amount greater than zero "
            "before its settings history can be recorded."
        ) from None

    category_text = (category or "").strip()

    if not category_text:
        raise ValueError(
            "The budget must have a category scope before its "
            "settings history can be recorded."
        )

    # Replace this month's settings without altering earlier months.
    conn.execute(
        '''INSERT INTO budget_monthly_history
               (user_id, budget_id, effective_month, amount, category)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(budget_id, effective_month)
           DO UPDATE SET
               amount = excluded.amount,
               category = excluded.category,
               user_id = excluded.user_id''',
        (
            user_id,
            budget_id,
            effective_month.isoformat(),
            amount,
            category_text
        )
    )

    return effective_month.isoformat()

def get_applicable_monthly_budget_settings(
    conn,
    user_id,
    budget_id,
    month_start_text
):
    """
    Finds the latest recorded monthly settings effective on or
    before the requested month.

    Uses the caller's connection to support a shared read snapshot.

    Returns:
        A settings dictionary, or None if no historical settings
        are known for that month.

    Does not fall back to the budget's current settings.
    Does not modify records or commit.
    """
    import math

    try:
        month_start = datetime.strptime(
            month_start_text, "%Y-%m-%d"
        ).date()

        if (
            month_start.day != 1
            or month_start.isoformat() != month_start_text
        ):
            raise ValueError

    except (TypeError, ValueError):
        raise ValueError(
            "The requested month must use YYYY-MM-01."
        ) from None

    # Verify ownership before looking up its history.
    budget = conn.execute(
        '''SELECT id
           FROM budgets
           WHERE id = ? AND user_id = ?''',
        (budget_id, user_id)
    ).fetchone()

    if budget is None:
        raise ValueError(
            "The budget could not be found for this user."
        )

    history = conn.execute(
        '''SELECT effective_month, amount, category
           FROM budget_monthly_history
           WHERE user_id = ?
             AND budget_id = ?
             AND effective_month <= ?
           ORDER BY effective_month DESC
           LIMIT 1''',
        (user_id, budget_id, month_start.isoformat())
    ).fetchone()

    if history is None:
        return None

    effective_month, stored_amount, category = history

    # Validate the selected snapshot instead of silently falling
    # back to a different snapshot if it is invalid.
    try:
        effective_date = datetime.strptime(
            effective_month, "%Y-%m-%d"
        ).date()

        if (
            effective_date.day != 1
            or effective_date.isoformat() != effective_month
        ):
            raise ValueError

        amount = float(stored_amount)

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError

        if not isinstance(category, str) or not category.strip():
            raise ValueError

    except (TypeError, ValueError, OverflowError):
        raise ValueError(
            "The applicable monthly budget history record contains "
            "invalid settings. It must be reviewed before comparison."
        ) from None

    # Preserve the saved category text for exact category matching.
    # Normalise only when checking the special all-expenses option.
    category_key = category.strip().casefold()

    includes_all = category_key in (
        "general",
        ALL_EXPENSE_CATEGORIES.casefold()
    )

    return {
        "budget_id": budget_id,
        "requested_month": month_start.isoformat(),
        "effective_month": effective_month,
        "amount": amount,
        "category": category,
        "includes_all_categories": includes_all,
        "carried_forward": effective_date < month_start
    }

def get_budget_month_expenses(user_id, budget_id, month_start_text):
    """
    Returns one month's expenses using its applicable recorded
    monthly budget settings.

    Raises ValueError when historical settings are unavailable.
    Reads data only.
    """
    import math
    from decimal import Decimal

    # The settings helper validates the month-start text.
    with get_db() as conn:
        conn.execute("BEGIN")

        settings = get_applicable_monthly_budget_settings(
            conn,
            user_id,
            budget_id,
            month_start_text
        )

        if settings is None:
            raise ValueError(
                "Historical budget settings are unavailable for this month. "
                "The app will not guess which category or limit applied. "
                "You can still review recorded transactions through "
                "normal Transaction History."
            )

        budget = conn.execute(
            '''SELECT budget_name
               FROM budgets
               WHERE id = ? AND user_id = ?''',
            (budget_id, user_id)
        ).fetchone()

        if budget is None:
            raise ValueError("The budget no longer exists.")

        month_start = datetime.strptime(
            settings["requested_month"], "%Y-%m-%d"
        ).date()
        month_end = month_start + relativedelta(months=1)

        query = '''
            SELECT t.date, t.time, t.category, t.amount,
                   t.notes, t.reference, t.necessity,
                   COALESCE(a.account_name, 'Missing account')
            FROM transactions t
            LEFT JOIN accounts a
              ON a.id = t.account_id
             AND a.user_id = t.user_id
            WHERE t.user_id = ?
              AND t.type = 'expense'
              AND t.date >= ?
              AND t.date < ?
        '''

        params = [
            user_id,
            month_start.isoformat(),
            month_end.isoformat()
        ]

        if not settings["includes_all_categories"]:
            query += " AND t.category = ?"
            params.append(settings["category"])

        query += " ORDER BY t.date ASC, t.time ASC, t.id ASC"

        rows = conn.execute(query, params).fetchall()

    transactions = []
    total = Decimal("0")
    invalid_amount_count = 0

    for row in rows:
        (
            tx_date, tx_time, tx_category, amount,
            notes, reference, necessity, account_name
        ) = row

        try:
            numeric_amount = float(amount)

            if (
                not math.isfinite(numeric_amount)
                or numeric_amount < 0
            ):
                raise ValueError

            value = Decimal(str(amount))

        except (TypeError, ValueError, OverflowError):
            invalid_amount_count += 1
            continue

        total += value

        transactions.append({
            "date": tx_date,
            "time": tx_time,
            "category": tx_category,
            "amount": float(value),
            "notes": notes or "",
            "reference": reference or "",
            "necessity": (
                necessity
                if necessity in ("need", "want")
                else "unclassified"
            ),
            "account_name": account_name
        })

    return {
        "budget_id": budget_id,
        "budget_name": budget[0],
        "category": settings["category"],
        "timeframe": "Monthly",
        "includes_all_categories": settings["includes_all_categories"],
        "applicable_limit": settings["amount"],
        "settings_effective_month": settings["effective_month"],
        "settings_carried_forward": settings["carried_forward"],
        "month_start": month_start.isoformat(),
        "month_last_day": (
            month_end - timedelta(days=1)
        ).isoformat(),
        "transactions": transactions,
        "entry_count": len(transactions),
        "total": float(total),
        "invalid_amount_count": invalid_amount_count,
        "limitation": (
            "Uses the recorded month-level category scope and limit "
            "applicable to this month. These settings are not an "
            "edit-by-edit audit log. Transactions are read as they "
            "exist now; later transaction edits or deletions can "
            "change historical spending totals."
        )
    }

def get_historical_budget_review(user_id, reference_date=None):
    """
    Reviews three completed months using recorded monthly budget settings.

    Months without recorded settings are reported as unknown rather than
    compared against current settings. Reads data only.
    """
    import math
    from decimal import Decimal

    if reference_date is None:
        reference_date = datetime.today().date()

    current_month_start = reference_date.replace(day=1)

    periods = []
    for months_back in (3, 2, 1):
        start = current_month_start - relativedelta(months=months_back)
        end = start + relativedelta(months=1)
        periods.append((start, end))

    reviews = []
    notices = []
    invalid_amount_count = 0
    valid_expenses = []

    with get_db() as conn:
        # Budgets, history and transactions share one read snapshot.
        conn.execute("BEGIN")

        budgets = conn.execute(
            '''SELECT id, budget_name
               FROM budgets
               WHERE user_id = ? AND timeframe = 'Monthly'
               ORDER BY budget_name COLLATE NOCASE, id''',
            (user_id,)
        ).fetchall()

        rows = conn.execute(
            '''SELECT category, amount, date
               FROM transactions
               WHERE user_id = ?
                 AND type = 'expense'
                 AND date >= ?
                 AND date < ?''',
            (
                user_id,
                periods[0][0].isoformat(),
                current_month_start.isoformat()
            )
        ).fetchall()

        for category, amount, tx_date in rows:
            try:
                numeric_amount = float(amount)

                if (
                    not math.isfinite(numeric_amount)
                    or numeric_amount < 0
                ):
                    raise ValueError

                valid_expenses.append(
                    (category, Decimal(str(amount)), tx_date)
                )

            except (TypeError, ValueError, OverflowError):
                invalid_amount_count += 1

        if invalid_amount_count:
            notices.append(
                f"{invalid_amount_count} expense record(s) with invalid "
                "amounts were excluded from the reviewed date range."
            )

        for budget_id, name in budgets:
            month_results = []
            months_known = 0
            months_above = 0

            for start, end in periods:
                start_text = start.isoformat()
                end_text = end.isoformat()

                try:
                    settings = get_applicable_monthly_budget_settings(
                        conn,
                        user_id,
                        budget_id,
                        start_text
                    )
                except ValueError as error:
                    settings = None

                    notices.append(
                        f"Budget '{name}' could not be compared for "
                        f"{start_text}: {error}"
                    )

                if settings is None:
                    month_results.append({
                        "period_start": start_text,
                        "period_last_day": (
                            end - timedelta(days=1)
                        ).isoformat(),
                        "settings_known": False,
                        "category": None,
                        "applicable_limit": None,
                        "settings_effective_month": None,
                        "settings_carried_forward": False,
                        "spent": None,
                        "valid_entry_count": 0,
                        "has_recorded_expenses": False,
                        "above_limit": False,
                        "difference_from_limit": None
                    })
                    continue

                months_known += 1

                includes_all = settings["includes_all_categories"]
                category = settings["category"]

                matching = [
                    amount
                    for tx_category, amount, tx_date in valid_expenses
                    if start_text <= tx_date < end_text
                    and (includes_all or tx_category == category)
                ]

                spent = sum(matching, Decimal("0"))
                limit = Decimal(str(settings["amount"]))
                difference = spent - limit
                above_limit = difference > 0

                if above_limit:
                    months_above += 1

                month_results.append({
                    "period_start": start_text,
                    "period_last_day": (
                        end - timedelta(days=1)
                    ).isoformat(),
                    "settings_known": True,
                    "category": category,
                    "applicable_limit": float(limit),
                    "settings_effective_month": settings["effective_month"],
                    "settings_carried_forward": settings["carried_forward"],
                    "spent": float(spent),
                    "valid_entry_count": len(matching),
                    "has_recorded_expenses": bool(matching),
                    "above_limit": above_limit,
                    "difference_from_limit": float(difference)
                })

            review_recommended = months_above >= 2

            if months_known == 0:
                suggestion = (
                    "No recorded monthly settings are available for these "
                    "months, so no limit comparison was performed."
                )
            elif review_recommended:
                suggestion = (
                    "Consider reviewing the contributing expenses and "
                    "whether your spending plan and current limit remain "
                    "appropriate. A higher limit is not automatically "
                    "affordable."
                )
            else:
                suggestion = (
                    "The repeated-above-limit review rule was not "
                    "triggered for the months with known settings. "
                    "This does not establish that the budget is "
                    "affordable or that the records are complete."
                )

            reviews.append({
                "budget_id": budget_id,
                "name": name,
                "months": month_results,
                "months_with_known_settings": months_known,
                "months_above_limit": months_above,
                "review_recommended": review_recommended,
                "suggestion": suggestion
            })

    reviews.sort(
        key=lambda item: (
            -item["months_above_limit"],
            -item["months_with_known_settings"],
            item["name"].casefold(),
            item["budget_id"]
        )
    )

    return {
        "as_of": reference_date.isoformat(),
        "reviewed_period_start": periods[0][0].isoformat(),
        "reviewed_period_last_day": (
            current_month_start - timedelta(days=1)
        ).isoformat(),
        "monthly_budget_count": len(budgets),
        "reviewed_month_count": len(periods),
        "reviews": reviews,
        "notices": notices,
        "trigger_month_count": 2,
        "limitation": (
            "Compares recorded expenses with the month-level limit and "
            "category recorded for each month. Months without recorded "
            "settings are excluded from comparison rather than assumed. "
            "Settings history is month-level, not an edit-by-edit audit "
            "log. Missing entries, category-name changes, and balance "
            "adjustments can affect results. No recorded expenses does "
            "not prove zero actual spending. Overlapping budgets are "
            "separate views of spending and must not be added together."
        )
    }

def get_budget_recommendations(user_id, reference_date=None):
    """
    Builds explainable recommendations for current calendar budgets.

    Reads data only:
    - Does not create transactions
    - Does not change balances or budget limits
    - Does not reserve money

    Returns a list of dictionaries for later Dashboard display.
    """
    import math
    from decimal import Decimal, ROUND_DOWN

    if reference_date is None:
        reference_date = datetime.today().date()

    recommendations = []

    for budget in view_budgets(user_id):
        budget_id = budget[0]

        (
            transactions,
            spent,
            limit,
            name,
            category,
            timeframe,
            window_start
        ) = get_budget_transactions(
            budget_id,
            user_id,
            reference_date=reference_date
        )

        if not name:
            continue

        # Avoid generating misleading advice from invalid stored amounts.
        if (
            not math.isfinite(limit)
            or limit <= 0
            or not math.isfinite(spent)
            or spent < 0
        ):
            continue

        period_start, period_end, days_remaining = get_budget_period(
            timeframe,
            reference_date=reference_date
        )

        remaining = max(limit - spent, 0)
        over = max(spent - limit, 0)
        daily_allowance = None

        if spent > limit:
            severity = "exceeded"
            title = f"{name}: review spending above the limit"
            suggestion = (
                "Review the transactions counted toward this budget "
                "and consider reducing further spending in this scope."
            )

        elif spent == limit:
            severity = "at_limit"
            title = f"{name}: budget limit reached"
            suggestion = (
                "There is no remaining allowance under this budget. "
                "Review upcoming expenses before recording further spending "
                "in this scope."
            )

        else:
            severity = "allowance"
            title = f"{name}: remaining daily allowance"

            # Round down to two decimal places so the displayed daily
            # amount does not round above the remaining allowance.
            daily_allowance = float(
                (
                    Decimal(str(remaining))
                    / Decimal(days_remaining)
                ).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_DOWN
                )
            )

            suggestion = (
                "Consider keeping average daily spending within the "
                "calculated allowance for the rest of this calendar period."
            )

        recommendations.append({
            "kind": "budget",
            "budget_id": budget_id,
            "title": title,
            "severity": severity,
            "name": name,
            "category": category,
            "timeframe": timeframe,
            "period_start": period_start.isoformat(),
            "period_last_day": (
                period_end - timedelta(days=1)
            ).isoformat(),
            "counted_through": reference_date.isoformat(),
            "limit": limit,
            "spent": spent,
            "remaining": remaining,
            "over": over,
            "days_remaining": days_remaining,
            "daily_allowance": daily_allowance,
            "transaction_count": len(transactions),
            "suggestion": suggestion,
            "limitation": (
                "Based on recorded expenses and the current budget limit. "
                "This is not an affordability assessment or a guarantee "
                "that upcoming expenses can be covered. Overlapping budgets "
                "are separate views of spending; do not add their daily "
                "allowances together."
            )
        })

    # Show exceeded budgets first, followed by reached limits.
    priority = {
        "exceeded": 0,
        "at_limit": 1,
        "allowance": 2
    }

    recommendations.sort(
        key=lambda item: (
            priority[item["severity"]],
            item["name"].casefold(),
            item["budget_id"]
        )
    )

    return recommendations

def show_budget_spending(user_id, budget_id):
    """
    Shows a popup listing all transactions that count
    toward the selected budget's progress.
    """
    # Use the same reference date for spending and period information.
    today = datetime.today().date()

    (
        transactions,
        total_spent,
        budget_limit,
        budget_name,
        category,
        timeframe,
        window_start
    ) = get_budget_transactions(
        budget_id,
        user_id,
        reference_date=today
    )

    if not budget_name:
        messagebox.showerror("Error", "Budget not found.")
        return

    period_start, period_end, days_remaining = get_budget_period(
        timeframe,
        reference_date=today
    )
    final_day = period_end - timedelta(days=1)

    sym      = get_currency(user_id)
    over     = max(total_spent - budget_limit, 0)
    remaining = max(budget_limit - total_spent, 0)
    progress = (total_spent / budget_limit * 100) if budget_limit else 0

    # ── Create popup ──────────────────────────────────────────
    popup = tk.Toplevel(root)
    popup.title(f"📊 {budget_name} — Spending Breakdown")
    popup.geometry("500x520")
    popup.resizable(False, False)
    popup.configure(bg="#f0f4f8")
    popup.transient(root)
    popup.grab_set()
    # Reserve the bottom controls before the expanding transaction list.
    btn_bar = tk.Frame(popup, bg="#f0f4f8", pady=10)
    btn_bar.pack(side="bottom", fill="x", padx=15)

    # ── Header ────────────────────────────────────────────────
    # Colour changes based on severity
    if total_spent > budget_limit:
        header_color = "#e53e3e"
        status_text = "BUDGET EXCEEDED"
    elif total_spent == budget_limit:
        header_color = "#dd6b20"
        status_text = "LIMIT REACHED"
    elif progress >= 80:
        header_color = "#dd6b20"
        status_text = "APPROACHING LIMIT"
    else:
        header_color = "#276749"
        status_text = "WITHIN LIMIT"

    header = tk.Frame(popup, bg=header_color, pady=10)
    header.pack(fill="x")

    tk.Label(
        header,
        text=f"📊 {budget_name}",
        font=("Segoe UI", 14, "bold"),
        bg=header_color, fg="white"
    ).pack()

    tk.Label(
        header,
        text=(
            f"{timeframe} | {category}\n"
            f"{status_text}\n"
            f"Calendar period: {period_start.isoformat()} "
            f"→ {final_day.isoformat()}\n"
            f"Recorded spending through: {today.isoformat()}"
        ),
        font=("Segoe UI", 9),
        bg=header_color,
        fg="white",
        wraplength=460,
        justify="center"
    ).pack(padx=10)

    # ── Summary strip ─────────────────────────────────────────
    summary = tk.Frame(popup, bg="white", relief="solid", bd=1)
    summary.pack(fill="x", padx=15, pady=8)

    summary_row = tk.Frame(summary, bg="white")
    summary_row.pack(pady=8)

    # Limit column
    lim_col = tk.Frame(summary_row, bg="white")
    lim_col.pack(side="left", expand=True)
    tk.Label(lim_col, text="LIMIT",
             font=("Segoe UI", 8), bg="white", fg="#718096").pack()
    tk.Label(lim_col, text=f"{sym}{budget_limit:,.2f}",
             font=("Segoe UI", 11, "bold"), bg="white", fg="#2b6cb0").pack()

    tk.Frame(summary_row, bg="#e2e8f0", width=1).pack(
        side="left", fill="y", padx=10)

    # Spent column
    spent_col = tk.Frame(summary_row, bg="white")
    spent_col.pack(side="left", expand=True)
    tk.Label(spent_col, text="SPENT",
             font=("Segoe UI", 8), bg="white", fg="#718096").pack()
    spent_color = (
        "#e53e3e"
        if total_spent > budget_limit
        else "#dd6b20"
        if progress >= 80
        else "#276749"
    )
    tk.Label(spent_col, text=f"{sym}{total_spent:,.2f}",
             font=("Segoe UI", 11, "bold"), bg="white", fg=spent_color).pack()

    tk.Frame(summary_row, bg="#e2e8f0", width=1).pack(
        side="left", fill="y", padx=10)

    # Over / Remaining column
    third_col = tk.Frame(summary_row, bg="white")
    third_col.pack(side="left", expand=True)
    if total_spent > budget_limit:
        tk.Label(third_col, text="OVER BY",
                 font=("Segoe UI", 8), bg="white", fg="#718096").pack()
        tk.Label(third_col, text=f"{sym}{over:,.2f}",
                 font=("Segoe UI", 11, "bold"), bg="white", fg="#e53e3e").pack()
    else:
        tk.Label(third_col, text="REMAINING",
                 font=("Segoe UI", 8), bg="white", fg="#718096").pack()
        tk.Label(third_col, text=f"{sym}{remaining:,.2f}",
                 font=("Segoe UI", 11, "bold"), bg="white", fg="#276749").pack()

    # ── Usage and transaction count ──────────────────────────
    tk.Label(
        popup,
        text=(
            f"Used: {progress:.1f}% | "
            f"Transactions counted: {len(transactions)}"
        ),
        font=("Segoe UI", 9, "italic"),
        bg="#f0f4f8",
        fg="#718096"
    ).pack(anchor="w", padx=15, pady=(0, 4))

    # ── Scrollable transaction list ───────────────────────────
    # Create a scrollable frame inside the popup
    scroll_outer = tk.Frame(popup, bg="#f0f4f8")
    scroll_outer.pack(fill="both", expand=True, padx=15)

    canvas = tk.Canvas(scroll_outer, bg="#f0f4f8", highlightthickness=0)
    scrollbar = ttk.Scrollbar(
        scroll_outer, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#f0f4f8")

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(event):
        try:
            if not canvas.winfo_exists():
                return

            direction = int(-1 * (event.delta / 120))
            if direction == 0:
                direction = -1 if event.delta > 0 else 1

            canvas.yview_scroll(direction, "units")

        except tk.TclError:
            return

    def enable_popup_scroll(event=None):
        try:
            if canvas.winfo_exists():
                root.bind_all("<MouseWheel>", _on_mousewheel)
        except tk.TclError:
            pass

    def disable_popup_scroll(event=None):
        root.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", enable_popup_scroll)
    canvas.bind("<Leave>", disable_popup_scroll)
    scroll_frame.bind("<Enter>", enable_popup_scroll)
    scroll_frame.bind("<Leave>", disable_popup_scroll)

    # ── Display each transaction ──────────────────────────────
    if not transactions:
        tk.Label(
            scroll_frame,
            text="No transactions found in this budget period.",
            font=("Segoe UI", 10),
            bg="#f0f4f8", fg="#718096"
        ).pack(pady=20)
    else:
        for tx in transactions:
            (tx_category, tx_amount, tx_date,
             tx_time, tx_notes, tx_reference, tx_necessity) = tx

            tx_notes     = tx_notes     or ""
            tx_reference = tx_reference or ""
            tx_necessity = tx_necessity or "unset"

            # Card for each transaction
            tx_card = tk.Frame(scroll_frame, bg="white", relief="solid", bd=1)
            tx_card.pack(fill="x", pady=3)

            # Top row — date, category, amount
            top = tk.Frame(tx_card, bg="white")
            top.pack(fill="x", padx=8, pady=(6, 2))

            tk.Label(
                top,
                text=f"{tx_date}  {tx_time}  |  {tx_category}",
                font=("Segoe UI", 9, "bold"),
                bg="white", fg="#2d3748"
            ).pack(side="left")

            tk.Label(
                top,
                text=f"-{sym}{tx_amount:,.2f}",
                font=("Segoe UI", 9, "bold"),
                bg="white", fg="#e53e3e"
            ).pack(side="right")

            # Necessity badge — only for expenses
            if tx_necessity in ("need", "want"):
                nec_bg   = "#e9d8fd" if tx_necessity == "want" else "#c6f6d5"
                nec_text = "🛍️ Want" if tx_necessity == "want" else "✅ Need"
                tk.Label(
                    top, text=nec_text,
                    font=("Segoe UI", 7, "bold"),
                    bg=nec_bg, fg="#2d3748",
                    relief="solid", bd=1, padx=3, pady=1
                ).pack(side="right", padx=5)

            # Notes row — only if notes exist
            if tx_notes:
                tk.Label(
                    tx_card,
                    text=f"📝  {tx_notes}",
                    font=("Segoe UI", 8, "italic"),
                    bg="white", fg="#4a5568",
                    wraplength=420, justify="left"
                ).pack(anchor="w", padx=8, pady=1)

            # Reference row — only if reference exists
            if tx_reference:
                tk.Label(
                    tx_card,
                    text=f"🔖  Ref: {tx_reference}",
                    font=("Segoe UI", 8),
                    bg="white", fg="#4a5568"
                ).pack(anchor="w", padx=8, pady=(1, 4))

            # Bottom padding
            tk.Frame(tx_card, bg="white", height=4).pack()

    # ── Close button ──────────────────────────────────────────

    def close_popup():
        # Remove the popup's global scrolling callback first.
        root.unbind_all("<MouseWheel>")
        popup.destroy()

    # Use the same cleanup if the user clicks the window's X button.
    popup.protocol("WM_DELETE_WINDOW", close_popup)

    make_button(
        btn_bar, "✖ Close",
        close_popup, color="#718096", width=12
    ).pack()

def get_budget_transactions(budget_id, user_id, reference_date=None):
    """
    Returns expenses counted toward a budget through reference_date.

    Defaults to today's local date.

    Preserves the existing seven-value return format:
        transactions, total_spent, budget_limit, budget_name,
        category, timeframe, window_start

    Each transaction contains:
        category, amount, date, time, notes, reference, necessity
    """
    if reference_date is None:
        reference_date = datetime.today().date()

    with get_db() as conn:
        cursor = conn.cursor()

        # Check both budget ID and ownership.
        cursor.execute(
            '''SELECT budget_name, category, amount, timeframe
               FROM budgets
               WHERE id = ? AND user_id = ?''',
            (budget_id, user_id)
        )
        budget = cursor.fetchone()

        if budget is None:
            return [], 0, 0, "", "", "", ""

        budget_name, category, budget_limit, timeframe = budget

        period_start, period_end, _ = get_budget_period(
            timeframe,
            reference_date
        )

        # Include the reference day, but exclude later dates.
        spending_end = min(
            period_end,
            reference_date + timedelta(days=1)
        )

        query = '''
            SELECT category, amount, date, time,
                   notes, reference, necessity
            FROM transactions
            WHERE user_id = ?
              AND type = 'expense'
              AND date >= ?
              AND date < ?
        '''

        params = [
            user_id,
            period_start.isoformat(),
            spending_end.isoformat()
        ]

        # Retain compatibility with the old "General" budget option.
        category_key = (category or "").strip().casefold()
        includes_all_categories = category_key in (
            "general",
            ALL_EXPENSE_CATEGORIES.casefold()
        )

        if not includes_all_categories:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY date DESC, time DESC, id DESC"

        cursor.execute(query, params)
        transactions = cursor.fetchall()

        total_spent = sum(
            transaction[1] for transaction in transactions
        )

    return (
        transactions,
        total_spent,
        budget_limit,
        budget_name,
        category,
        timeframe,
        period_start.isoformat()
    )

def get_expense_categories(user_id, include_all=False):
    """
    Returns the user's expense categories.

    include_all=False:
        Returns only real expense categories.
        Used by subscriptions and recurring transactions.

    include_all=True:
        Also includes the special "All Expense Categories" option.
        Used only by budgets.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT name
               FROM categories
               WHERE user_id = ? AND type = 'expense'
               ORDER BY name COLLATE NOCASE''',
            (user_id,)
        )
        categories = [row[0] for row in cursor.fetchall()]

    if include_all:
        # Put the special budget option first.
        categories.insert(0, ALL_EXPENSE_CATEGORIES)

    return categories


def show_add_budget(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="➕ Add Budget", font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)

    # Budget name
    tk.Label(body, text="Budget Name:", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    name_entry = make_entry(body)
    name_entry.pack(anchor="w", pady=(2, 10))

    # Timeframe dropdown
    tk.Label(body, text="Timeframe:", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    timeframe_var = tk.StringVar(value="Monthly")
    timeframe_dd = ttk.Combobox(body, textvariable=timeframe_var,
                                values=["Daily", "Weekly", "Monthly", "Yearly"],
                                state="readonly", width=28)
    timeframe_dd.pack(anchor="w", pady=(2, 10))

    # Show the period before the user enters a budget limit.
    period_info = tk.Label(
        body,
        text="",
        font=("Segoe UI", 9),
        bg="#ebf8ff",
        fg="#2c5282",
        wraplength=500,
        justify="left",
        padx=10,
        pady=8
    )
    period_info.pack(anchor="w", pady=(0, 10))

    def update_budget_period_preview(*args):
        try:
            period_start, period_end, days_remaining = get_budget_period(
                timeframe_var.get()
            )

            # The helper returns an exclusive end.
            # Show the final included day to the user.
            final_day = period_end - timedelta(days=1)

            period_info.config(
                text=(
                    f"Current calendar period: "
                    f"{period_start.strftime('%d %b %Y')} – "
                    f"{final_day.strftime('%d %b %Y')}\n"
                    f"Days remaining, including today: {days_remaining}\n\n"
                    "Includes expenses already recorded in this period. "
                    "The limit applies to the whole period and is not "
                    "automatically prorated."
                )
            )
        except ValueError as error:
            period_info.config(text=str(error))

    timeframe_var.trace_add("write", update_budget_period_preview)
    update_budget_period_preview()

    # Amount
    sym = get_currency(user_id)

    tk.Label(
        body,
        text=f"Amount Limit ({sym}):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w")
    amount_entry = make_entry(body)
    amount_entry.pack(anchor="w", pady=(2, 10))

    # Category dropdown with Add Category button
    tk.Label(body, text="Category:", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")

    # Horizontal frame to hold dropdown and button side by side
    cat_row = tk.Frame(body, bg="#f0f4f8")
    cat_row.pack(anchor="w", pady=(2, 10))

    categories = get_expense_categories(user_id, include_all=True)
    category_var = tk.StringVar(
        value=categories[0] if categories else ALL_EXPENSE_CATEGORIES
    )
    category_dd = ttk.Combobox(cat_row, textvariable=category_var,
                               values=categories, state="readonly", width=25)
    category_dd.pack(side="left")

    # Add Category button — expense categories only for budgets
    make_button(
        cat_row, "+ Add Category",
        lambda: open_add_category_popup(
            user_id, "expense", category_dd, category_var
        ),
        color="#3182ce", width=14
    ).pack(side="left", padx=6)

     # ── Budget notes ──────────────────────────────────────────
    tk.Label(
        body,
        text="Notes (optional):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", pady=(2, 0))

    tk.Label(
        body,
        text="Describe the purpose or scope of this budget.",
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8",
        fg="#718096"
    ).pack(anchor="w")

    notes_entry = tk.Text(
        body,
        height=3,
        width=45,
        font=("Segoe UI", 10),
        relief="solid",
        bd=1,
        wrap="word"
    )
    notes_entry.pack(anchor="w", pady=(2, 10))

    msg_label = tk.Label(body, text="", font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red", wraplength=400)
    msg_label.pack(pady=5)

    def on_submit():
        import math

        name = name_entry.get().strip()
        timeframe = timeframe_var.get()
        category = category_var.get()
        notes = notes_entry.get("1.0", tk.END).strip()

        if not name:
            msg_label.config(text="❌ Budget name cannot be empty.", fg="red")
            return

        try:
            amount = float(amount_entry.get().strip())
        except ValueError:
            msg_label.config(text="❌ Amount must be a valid number.", fg="red")
            return

        if not math.isfinite(amount) or amount <= 0:
            msg_label.config(
                text="❌ Amount must be a finite number greater than zero.",
                fg="red"
            )
            return

        # Store a snapshot of the current calendar period.
        # end_date is exclusive: it is not a counted spending date.
        try:
            start_date, end_date, _ = get_budget_period(timeframe)
        except ValueError as error:
            msg_label.config(text=str(error), fg="red")
            return

        try:
            with get_db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                cursor = conn.cursor()

                cursor.execute(
                    '''INSERT INTO budgets
                       (user_id, budget_name, timeframe, start_date,
                        end_date, category, amount, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        user_id,
                        name,
                        timeframe,
                        start_date.isoformat(),
                        end_date.isoformat(),
                        category,
                        amount,
                        notes
                    )
                )

                new_budget_id = cursor.lastrowid

                record_monthly_budget_settings(
                    conn,
                    user_id,
                    new_budget_id
                )

                conn.commit()

        except (sqlite3.Error, ValueError) as error:
            msg_label.config(
                text=f"Could not save the budget: {error}",
                fg="red"
            )
            return

        check_and_award_badges(user_id)
        msg_label.config(text="✅ Budget added!", fg="green")
        root.after(1000, lambda: show_budgets(user_id))

    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=10)
    make_button(btn_frame, "✅ Save Budget", on_submit, color="#38a169").pack(side="left", padx=5)
    make_button(btn_frame, "← Back", lambda: show_budgets(user_id), color="#718096").pack(side="left", padx=5)



# ============================================================
# TRANSACTIONS SCREEN
# ============================================================
# User records income or expense here.
# Each transaction:
#   - belongs to an account (updates balance automatically)
#   - has a category (user-created)
#   - has type: 'income' or 'expense'
#   - date/time recorded automatically
# ============================================================
def show_add_transaction(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="💸 Add Transaction", font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)

    sym = get_currency(user_id)

    # --- Transaction type toggle ---
    tk.Label(body, text="Transaction Type:", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w", padx=20, pady=(10, 0))
    type_var = tk.StringVar(value="income")
    type_frame = tk.Frame(body, bg="#f0f4f8")
    type_frame.pack(anchor="w", padx=20, pady=(2, 10))
    tk.Radiobutton(type_frame, text="Income", variable=type_var,
                   value="income", bg="#f0f4f8",
                   font=("Segoe UI", 10),
                   command=lambda: refresh_categories()).pack(side="left")
    tk.Radiobutton(type_frame, text="Expense", variable=type_var,
                   value="expense", bg="#f0f4f8",
                   font=("Segoe UI", 10),
                   command=lambda: refresh_categories()).pack(side="left", padx=10)

    # --- Category dropdown ---
    tk.Label(body, text="Category:", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w", padx=20)
    category_var = tk.StringVar()
    category_dd = ttk.Combobox(body, textvariable=category_var,
                               state="readonly", width=28)
    category_dd.pack(anchor="w", padx=20, pady=(2, 6))

    # --- Add new category inline ---
    new_cat_frame = tk.Frame(body, bg="#f0f4f8")
    new_cat_frame.pack(anchor="w", padx=20, pady=(0, 10))
    new_cat_entry = make_entry(new_cat_frame, width=20)
    new_cat_entry.pack(side="left")

    # msg_label defined early so on_add_category can reference it
    msg_label = tk.Label(body, text="", font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red", wraplength=400)

    def on_add_category():
        new_cat = new_cat_entry.get().strip()
        if not new_cat:
            msg_label.config(text="❌ Category name cannot be empty.", fg="red")
            return
        tx_type = type_var.get()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM categories WHERE user_id = ? AND type = ? AND name = ?",
                (user_id, tx_type, new_cat)
            )
            if cursor.fetchone():
                msg_label.config(text="❌ Category already exists.", fg="red")
                return
            cursor.execute(
                "INSERT INTO categories (user_id, type, name) VALUES (?, ?, ?)",
                (user_id, tx_type, new_cat)
            )
            conn.commit()
        new_cat_entry.delete(0, tk.END)
        msg_label.config(text="✅ Category added.", fg="green")
        refresh_categories()
        category_var.set(new_cat)

    make_button(new_cat_frame, "+ Add Category",
                on_add_category, color="#3182ce", width=14).pack(side="left", padx=6)

    # --- Amount ---
    tk.Label(body, text=f"Amount ({sym}):", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w", padx=20)
    amount_entry = make_entry(body)
    amount_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # --- Account dropdown ---
    tk.Label(body, text="Account:", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w", padx=20)
    accounts = view_accounts(user_id)
    account_options = {
        f"{acc[1]} | Balance: {sym}{acc[2]:,.2f}": acc[0]
        for acc in accounts
    }
    account_var = tk.StringVar(
        value=list(account_options.keys())[0] if account_options else ""
    )
    account_dd = ttk.Combobox(body, textvariable=account_var,
                              values=list(account_options.keys()),
                              state="readonly", width=35)
    account_dd.pack(anchor="w", padx=20, pady=(2, 10))

    # --- Notes / Remarks ---
    # Multi-line text box for describing the transaction
    # e.g. "Lunch at McDonalds with family"
    tk.Label(body, text="Notes / Remarks (optional):",
             font=("Segoe UI", 10, "bold"), bg="#f0f4f8").pack(anchor="w", padx=20)
    tk.Label(body,
             text="Describe what this transaction was for",
             font=("Segoe UI", 8, "italic"),
             bg="#f0f4f8", fg="#718096").pack(anchor="w", padx=20)
    notes_entry = tk.Text(body, height=3, width=45,
                          font=("Segoe UI", 10),
                          relief="solid", bd=1, wrap="word")
    notes_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # --- Reference Number ---
    # Receipt, invoice or bank reference number
    # e.g. "Receipt #INV-2024-001" or "Bank Ref: TXN123456"
    tk.Label(body, text="Reference / Receipt No. (optional):",
             font=("Segoe UI", 10, "bold"), bg="#f0f4f8").pack(anchor="w", padx=20)
    tk.Label(body,
             text="Bank reference, receipt number, invoice ID etc.",
             font=("Segoe UI", 8, "italic"),
             bg="#f0f4f8", fg="#718096").pack(anchor="w", padx=20)
    reference_entry = make_entry(body, width=35)
    reference_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # --- Tags ---
    # Short comma separated labels for filtering later
    # e.g. "work, reimbursable, urgent"
    tk.Label(body, text="Tags (optional):",
             font=("Segoe UI", 10, "bold"), bg="#f0f4f8").pack(anchor="w", padx=20)
    tk.Label(body,
             text="Comma separated e.g. work, personal, emergency",
             font=("Segoe UI", 8, "italic"),
             bg="#f0f4f8", fg="#718096").pack(anchor="w", padx=20)
    tags_entry = make_entry(body, width=35)
    tags_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # --- Necessity Rating ---
    # Was this spending a Need or a Want?
    # Only relevant for expense transactions
    # Hidden for income — set to "unset" automatically
    tk.Label(body, text="Necessity (for expenses only):",
             font=("Segoe UI", 10, "bold"), bg="#f0f4f8").pack(anchor="w", padx=20)
    tk.Label(body,
             text="Was this expense a need or a want?",
             font=("Segoe UI", 8, "italic"),
             bg="#f0f4f8", fg="#718096").pack(anchor="w", padx=20)
    necessity_var = tk.StringVar(value="unset")
    necessity_frame = tk.Frame(body, bg="#f0f4f8")
    necessity_frame.pack(anchor="w", padx=20, pady=(2, 10))
    tk.Radiobutton(necessity_frame, text="✅ Need",
                   variable=necessity_var, value="need",
                   bg="#f0f4f8", font=("Segoe UI", 10)).pack(side="left")
    tk.Radiobutton(necessity_frame, text="🛍️ Want",
                   variable=necessity_var, value="want",
                   bg="#f0f4f8", font=("Segoe UI", 10)).pack(side="left", padx=10)
    tk.Radiobutton(necessity_frame, text="— Not set",
                   variable=necessity_var, value="unset",
                   bg="#f0f4f8", font=("Segoe UI", 10)).pack(side="left")

    # msg_label placed after all fields
    msg_label.pack(padx=20, pady=5)

    def refresh_categories():
        tx_type = type_var.get()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM categories WHERE user_id = ? AND type = ?",
                (user_id, tx_type)
            )
            cats = [row[0] for row in cursor.fetchall()]
        category_dd["values"] = cats
        if cats:
            category_var.set(cats[0])
        else:
            category_var.set("")

    refresh_categories()

    def on_submit():
        category = category_var.get()
        tx_type  = type_var.get()

        if not category:
            msg_label.config(
                text="❌ Please select or add a category.", fg="red")
            return

        if not account_options:
            msg_label.config(
                text="❌ No accounts found. Add an account first.", fg="red")
            return

        try:
            amount = float(amount_entry.get().strip())
        except ValueError:
            msg_label.config(
                text="❌ Amount must be a valid number.", fg="red")
            return

        if amount <= 0:
            msg_label.config(
                text="❌ Amount must be greater than 0.", fg="red")
            return

        # Get new fields
        # tk.Text uses get("1.0", tk.END) — "1.0" means line 1 char 0
        notes     = notes_entry.get("1.0", tk.END).strip()
        reference = reference_entry.get().strip()
        tags_raw  = tags_entry.get().strip()

        # For income transactions force necessity to unset
        # necessity only meaningful for expenses
        if tx_type == "income":
            necessity = "unset"
        else:
            necessity = necessity_var.get()

        account_id = account_options[account_var.get()]
        now = datetime.now()

        with get_db() as conn:
            cursor = conn.cursor()

            # Insert transaction with all new fields
            cursor.execute(
                '''INSERT INTO transactions
                   (user_id, category, type, amount, date, time,
                    account_id, notes, reference, necessity)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, category, tx_type, amount,
                 now.strftime("%Y-%m-%d"), now.strftime("%H:%M"),
                 account_id, notes, reference, necessity)
            )

            # Get the id of the transaction just inserted
            # so we can link tags to it
            transaction_id = cursor.lastrowid

            # Update account balance
            if tx_type == "income":
                cursor.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                    (amount, account_id)
                )
            else:
                cursor.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                    (amount, account_id)
                )

            # Save tags if user entered any
            # Split by comma, strip whitespace, skip empty strings
            if tags_raw:
                MAX_TAG_LENGTH = 30   # Each tag max 30 characters
                MAX_TAGS = 10         # Max 10 tags per transaction

                # Build tag list — skip any tag over 30 characters
                tag_list = [
                    t.strip()
                    for t in tags_raw.split(",")
                    if t.strip() and len(t.strip()) <= MAX_TAG_LENGTH
                ]

                # Only keep the first 10 tags
                tag_list = tag_list[:MAX_TAGS]

                for tag in tag_list:
                    cursor.execute(
                        '''INSERT INTO tags (transaction_id, user_id, tag_name)
                           VALUES (?, ?, ?)''',
                        (transaction_id, user_id, tag)
                    )

            conn.commit()

        check_and_award_badges(user_id)
        msg_label.config(
            text="✅ Transaction added successfully!", fg="green")

        # Clear all fields after successful submit
        amount_entry.delete(0, tk.END)
        notes_entry.delete("1.0", tk.END)
        reference_entry.delete(0, tk.END)
        tags_entry.delete(0, tk.END)
        necessity_var.set("unset")

        # Check budgets after transaction
        root.after(600, lambda: show_budget_alert_popup(
            user_id, check_budget_alerts(user_id)
        ))

    # --- Nav buttons ---
    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=8, padx=20, anchor="w")
    make_button(btn_frame, "✅ Submit",
                on_submit, color="#38a169").pack(side="left", padx=5)
    make_button(btn_frame, "📋 Category List",
                lambda: show_category_list(user_id),
                color="#3182ce").pack(side="left", padx=5)
    make_button(btn_frame, "🕐 Transaction History",
                lambda: show_transaction_history(user_id),
                color="#3182ce").pack(side="left", padx=5)
    make_button(btn_frame, "← Back to Menu",
                lambda: show_main_menu(current_user),
                color="#718096").pack(side="left", padx=5)



def show_category_list(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")

    tk.Label(
        header,
        text="📋 Category List",
        font=("Segoe UI", 16, "bold"),
        fg="white",
        bg="#2b6cb0"
    ).pack()

    # Reserve space for navigation before adding scrollable content.
    btn_bar = tk.Frame(root, bg="#f0f4f8", pady=10)
    btn_bar.pack(side="bottom", fill="x", padx=20)

    body = make_scrollable_frame(root)

    # Load each category's ID, type and name.
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT id, type, name
               FROM categories
               WHERE user_id = ?
               ORDER BY type, name COLLATE NOCASE, id''',
            (user_id,)
        )
        categories = cursor.fetchall()

    income_cats = [
        row for row in categories if row[1] == "income"
    ]
    expense_cats = [
        row for row in categories if row[1] == "expense"
    ]

    # ── Income categories ────────────────────────────────────
    tk.Label(
        body,
        text="💚 Income Categories",
        font=("Segoe UI", 11, "bold"),
        bg="#f0f4f8",
        fg="#276749"
    ).pack(anchor="w", padx=20, pady=(10, 4))

    if income_cats:
        for category_id, category_type, category_name in income_cats:
            tk.Label(
                body,
                text=f"  • {category_name}",
                font=("Segoe UI", 10),
                bg="#f0f4f8"
            ).pack(anchor="w", padx=30)
    else:
        tk.Label(
            body,
            text="No income categories yet.",
            font=("Segoe UI", 10),
            bg="#f0f4f8",
            fg="#718096"
        ).pack(anchor="w", padx=30)

    # ── Expense categories ───────────────────────────────────
    tk.Label(
        body,
        text="🔴 Expense Categories",
        font=("Segoe UI", 11, "bold"),
        bg="#f0f4f8",
        fg="#9b2c2c"
    ).pack(anchor="w", padx=20, pady=(15, 4))

    if expense_cats:
        for category_id, category_type, category_name in expense_cats:
            tk.Label(
                body,
                text=f"  • {category_name}",
                font=("Segoe UI", 10),
                bg="#f0f4f8"
            ).pack(anchor="w", padx=30)
    else:
        tk.Label(
            body,
            text="No expense categories yet.",
            font=("Segoe UI", 10),
            bg="#f0f4f8",
            fg="#718096"
        ).pack(anchor="w", padx=30)

    # ── Category selection ────────────────────────────────────
    tk.Label(
        body,
        text="Delete a Category:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20, pady=(20, 4))

    # Keep the records and labels in the same order.
    # dropdown.current() lets us retrieve the exact selected record.
    category_labels = [
        f"{category_type.capitalize()} — {category_name}"
        for category_id, category_type, category_name in categories
    ]

    dropdown = ttk.Combobox(
        body,
        values=category_labels,
        state="readonly",
        width=38
    )
    dropdown.pack(anchor="w", padx=20, pady=(0, 8))

    if categories:
        dropdown.current(0)

    tk.Label(
        body,
        text=(
            "Deleting a category removes it from future category lists.\n"
            "Existing transactions, budgets and scheduled rules are not changed."
        ),
        font=("Segoe UI", 9, "italic"),
        bg="#f0f4f8",
        fg="#718096",
        wraplength=500,
        justify="left"
    ).pack(anchor="w", padx=20, pady=(0, 8))

    msg_label = tk.Label(
        body,
        text="",
        font=("Segoe UI", 10),
        bg="#f0f4f8",
        fg="red",
        wraplength=500
    )
    msg_label.pack(anchor="w", padx=20)

    def on_delete():
        selected_index = dropdown.current()

        if selected_index < 0:
            msg_label.config(
                text="❌ Select a category first.",
                fg="red"
            )
            return

        category_id, category_type, category_name = categories[selected_index]

        confirmed = messagebox.askyesno(
            "Confirm Category Deletion",
            (
                f"Delete {category_type} category '{category_name}'?\n\n"
                "It will be removed from future category lists.\n"
                "Existing transactions, budgets and scheduled rules "
                "will remain unchanged."
            ),
            parent=root
        )

        if not confirmed:
            return

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''DELETE FROM categories
                       WHERE id = ? AND user_id = ?''',
                    (category_id, user_id)
                )
                deleted_count = cursor.rowcount
                conn.commit()
        except sqlite3.Error:
            msg_label.config(
                text="❌ Could not delete the category. Please try again.",
                fg="red"
            )
            return

        if deleted_count == 0:
            messagebox.showinfo(
                "Category Not Found",
                "This category no longer exists. The list will refresh.",
                parent=root
            )

        show_category_list(user_id)

    # ── Fixed bottom buttons ──────────────────────────────────
    delete_button = make_button(
        btn_bar,
        "🗑️ Delete Selected",
        on_delete,
        color="#e53e3e"
    )
    delete_button.pack(side="left", padx=5)

    if not categories:
        delete_button.config(state="disabled")

    make_button(
        btn_bar,
        "← Back",
        lambda: show_add_transaction(user_id),
        color="#718096"
    ).pack(side="left", padx=5)


def show_transaction_history(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="🕐 Transaction History", font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)
    sym = get_currency(user_id)

    # --- Filter controls card ---
    filter_card = tk.Frame(body, bg="white", relief="solid", bd=1)
    filter_card.pack(fill="x", padx=20, pady=10)

    tk.Label(filter_card, text="🔍 Filter Transactions",
             font=("Segoe UI", 10, "bold"), bg="white").pack(
             anchor="w", padx=10, pady=(8, 4))

    # Row 1 — date range
    row1 = tk.Frame(filter_card, bg="white")
    row1.pack(anchor="w", padx=10, pady=4)

    tk.Label(row1, text="From:", font=("Segoe UI", 10),
             bg="white").pack(side="left")
    start_entry = make_entry(row1, width=12)
    start_entry.pack(side="left", padx=5)
    # Pre-fill with first day of current month
    start_entry.insert(0, datetime.today().replace(day=1).strftime("%Y-%m-%d"))

    tk.Label(row1, text="To:", font=("Segoe UI", 10),
             bg="white").pack(side="left", padx=(10, 0))
    end_entry = make_entry(row1, width=12)
    end_entry.pack(side="left", padx=5)
    # Pre-fill with today
    end_entry.insert(0, datetime.today().strftime("%Y-%m-%d"))

    # Row 2 — keyword search
    row2 = tk.Frame(filter_card, bg="white")
    row2.pack(anchor="w", padx=10, pady=4)

    tk.Label(row2, text="Search notes / tags / reference:",
             font=("Segoe UI", 10), bg="white").pack(side="left")
    search_entry = make_entry(row2, width=25)
    search_entry.pack(side="left", padx=5)

    # Row 3 — type and necessity filters
    row3 = tk.Frame(filter_card, bg="white")
    row3.pack(anchor="w", padx=10, pady=(4, 10))

    tk.Label(row3, text="Type:", font=("Segoe UI", 10),
             bg="white").pack(side="left")
    type_filter_var = tk.StringVar(value="all")
    for label, val in [("All", "all"), ("Income", "income"), ("Expense", "expense")]:
        tk.Radiobutton(row3, text=label, variable=type_filter_var,
                       value=val, bg="white",
                       font=("Segoe UI", 9)).pack(side="left", padx=3)

    tk.Label(row3, text="  Necessity:", font=("Segoe UI", 10),
             bg="white").pack(side="left", padx=(10, 0))
    necessity_filter_var = tk.StringVar(value="all")
    for label, val in [("All", "all"), ("Need", "need"),
                       ("Want", "want"), ("Unset", "unset")]:
        tk.Radiobutton(row3, text=label, variable=necessity_filter_var,
                       value=val, bg="white",
                       font=("Segoe UI", 9)).pack(side="left", padx=3)

    # Results area — cleared and rebuilt on each fetch
    results_frame = tk.Frame(body, bg="#f0f4f8")
    results_frame.pack(fill="x", padx=20, pady=5)

    msg_label = tk.Label(body, text="", font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red")
    msg_label.pack()

    def fetch():
        # Clear previous results
        for widget in results_frame.winfo_children():
            widget.destroy()

        start   = start_entry.get().strip()
        end     = end_entry.get().strip()
        keyword = search_entry.get().strip().lower()
        type_f  = type_filter_var.get()
        nec_f   = necessity_filter_var.get()

        # Validate date format
        try:
            datetime.strptime(start, "%Y-%m-%d")
            datetime.strptime(end, "%Y-%m-%d")
        except ValueError:
            msg_label.config(
                text="❌ Use format YYYY-MM-DD for dates.", fg="red")
            return

        with get_db() as conn:
            cursor = conn.cursor()

            # Build query dynamically based on type filter
            # Base query fetches all new fields including
            # notes, reference, necessity
            base_query = '''
                SELECT t.id, t.type, t.category, t.amount,
                       t.date, t.time, a.account_name,
                       t.notes, t.reference, t.necessity
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.user_id = ?
                AND t.date BETWEEN ? AND ?
            '''
            params = [user_id, start, end]

            # Add type filter if not "all"
            if type_f != "all":
                base_query += " AND t.type = ?"
                params.append(type_f)

            # Add necessity filter if not "all"
            if nec_f != "all":
                base_query += " AND t.necessity = ?"
                params.append(nec_f)

            base_query += " ORDER BY t.date DESC, t.time DESC"

            cursor.execute(base_query, params)
            transactions = cursor.fetchall()

            # Fetch tags for each transaction
            tx_tags = {}
            for tx in transactions:
                cursor.execute(
                    "SELECT tag_name FROM tags WHERE transaction_id = ?",
                    (tx[0],)
                )
                tx_tags[tx[0]] = [row[0] for row in cursor.fetchall()]

        if not transactions:
            tk.Label(results_frame,
                     text="No transactions found.",
                     font=("Segoe UI", 10),
                     bg="#f0f4f8", fg="#718096").pack(pady=10)
            return

        # Apply keyword filter on notes, tags, reference
        if keyword:
            filtered = []
            for tx in transactions:
                notes     = (tx[7] or "").lower()
                tags_str  = " ".join(tx_tags.get(tx[0], [])).lower()
                reference = (tx[8] or "").lower()
                if (keyword in notes or
                        keyword in tags_str or
                        keyword in reference):
                    filtered.append(tx)
            transactions = filtered

        if not transactions:
            tk.Label(results_frame,
                     text="No transactions match your search.",
                     font=("Segoe UI", 10),
                     bg="#f0f4f8", fg="#718096").pack(pady=10)
            return

        msg_label.config(text="")

        # --- Summary bar ---
        total_income  = sum(tx[3] for tx in transactions
                            if tx[1] == "income")
        total_expense = sum(tx[3] for tx in transactions
                            if tx[1] == "expense")
        needs_total   = sum(tx[3] for tx in transactions
                            if tx[1] == "expense" and tx[9] == "need")
        wants_total   = sum(tx[3] for tx in transactions
                            if tx[1] == "expense" and tx[9] == "want")

        summary = tk.Frame(results_frame, bg="white",
                           relief="solid", bd=1)
        summary.pack(fill="x", pady=(0, 8))
        tk.Label(summary,
                 text=(f"  Found {len(transactions)} transaction(s)  |  "
                       f"Income: {sym}{total_income:,.2f}  |  "
                       f"Expenses: {sym}{total_expense:,.2f}  |  "
                       f"Needs: {sym}{needs_total:,.2f}  |  "
                       f"Wants: {sym}{wants_total:,.2f}"),
                 font=("Segoe UI", 9, "bold"),
                 bg="white", fg="#2d3748").pack(
                 anchor="w", padx=10, pady=6)

        # --- Transaction cards ---
        for tx in transactions:
            (tx_id, tx_type, category, amount,
             date, time, account_name,
             notes, reference, necessity) = tx

            tags      = tx_tags.get(tx_id, [])
            color     = "#f0fff4" if tx_type == "income" else "#fff5f5"
            prefix    = "+" if tx_type == "income" else "-"

            card = tk.Frame(results_frame, bg=color,
                            relief="solid", bd=1)
            card.pack(fill="x", pady=3)

            # Top row — main transaction info
            top_row = tk.Frame(card, bg=color)
            top_row.pack(fill="x", padx=8, pady=(6, 2))

            tk.Label(top_row,
                     text=(f"{date}  {time}  |  "
                           f"{category}  |  "
                           f"{prefix}{sym}{amount:,.2f}  |  "
                           f"{account_name}"),
                     font=("Segoe UI", 9, "bold"),
                     bg=color, fg="#2d3748").pack(side="left")

            # Necessity badge — only show for expenses
            if tx_type == "expense" and necessity != "unset":
                nec_color = "#e9d8fd" if necessity == "want" else "#c6f6d5"
                nec_text  = "🛍️ Want" if necessity == "want" else "✅ Need"
                tk.Label(top_row, text=nec_text,
                         font=("Segoe UI", 8, "bold"),
                         bg=nec_color, fg="#2d3748",
                         relief="solid", bd=1,
                         padx=4, pady=1).pack(side="right", padx=4)

            # Notes row — only show if notes exist
            if notes:
                notes_row = tk.Frame(card, bg=color)
                notes_row.pack(fill="x", padx=8, pady=1)
                tk.Label(notes_row,
                         text=f"📝  {notes}",
                         font=("Segoe UI", 9, "italic"),
                         bg=color, fg="#4a5568",
                         wraplength=500,
                         justify="left").pack(anchor="w")

            # Reference row — only show if reference exists
            if reference:
                ref_row = tk.Frame(card, bg=color)
                ref_row.pack(fill="x", padx=8, pady=1)
                tk.Label(ref_row,
                         text=f"🔖  Ref: {reference}",
                         font=("Segoe UI", 9),
                         bg=color, fg="#4a5568").pack(anchor="w")

            # Tags row — only show if tags exist
            if tags:
                tags_row = tk.Frame(card, bg=color)
                tags_row.pack(fill="x", padx=8, pady=(1, 4))
                for tag in tags:
                    tk.Label(tags_row,
                             text=f"#{tag}",
                             font=("Segoe UI", 8, "bold"),
                             bg="#ebf8ff", fg="#2b6cb0",
                             relief="solid", bd=1,
                             padx=4, pady=1).pack(
                             side="left", padx=2)

            # Action buttons row
            action_row = tk.Frame(card, bg=color)
            action_row.pack(anchor="e", padx=8, pady=(0, 6))

            def make_delete(tid=tx_id, amt=amount, ttype=tx_type):
                def on_delete():
                    with get_db() as conn2:
                        cursor2 = conn2.cursor()
                        cursor2.execute(
                            "SELECT account_id FROM transactions WHERE id = ?",
                            (tid,)
                        )
                        row2 = cursor2.fetchone()
                        if row2:
                            account_id = row2[0]
                            if ttype == "income":
                                cursor2.execute(
                                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                                    (amt, account_id)
                                )
                            else:
                                cursor2.execute(
                                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                                    (amt, account_id)
                                )
                            # Delete tags first then transaction
                            cursor2.execute(
                                "DELETE FROM tags WHERE transaction_id = ?",
                                (tid,)
                            )
                            cursor2.execute(
                                "DELETE FROM transactions WHERE id = ?",
                                (tid,)
                            )
                            conn2.commit()
                    fetch()
                return on_delete

            make_button(action_row, "🗑️ Delete",
                        make_delete(),
                        color="#e53e3e", width=10).pack(
                        side="right", padx=4, pady=2)
            make_button(action_row, "✏️ Edit",
                        lambda tid=tx_id: show_edit_transaction(user_id, tid),
                        color="#3182ce", width=10).pack(
                        side="right", padx=2, pady=2)

    # --- Bottom buttons ---
    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=8, padx=20, anchor="w")
    make_button(btn_frame, "🔍 Fetch Transactions",
                fetch, color="#3182ce").pack(side="left", padx=5)
    make_button(btn_frame, "📥 Export to CSV",
                lambda: export_transactions_to_csv(user_id),
                color="#38a169").pack(side="left", padx=5)
    make_button(btn_frame, "← Back",
                lambda: show_add_transaction(user_id),
                color="#718096").pack(side="left", padx=5)


# ============================================================
# SUBSCRIPTIONS SCREEN
# ============================================================
# Subscriptions = recurring charges (Netflix, Spotify etc.)
# User sets: name, category, amount, charge dates (day numbers)
# e.g. charge_dates = "1, 15" means charges on 1st and 15th
# of every month.
# Subscription expenses are generated by the shared recurring processor.
# if today matches a charge date.
# Max 5 subscriptions.
# ============================================================

# ============================================================
# CURRENCY HELPERS
# ============================================================
# get_currency() is called everywhere money is displayed.
# It returns the symbol the user has chosen e.g. "$", "£".
#
# If user has no setting saved yet, it defaults to "$" (USD)
# and creates a settings row for them automatically.
#
# Supported currencies list can be extended easily —
# just add more entries to the CURRENCIES dict below.
# ============================================================

# Dictionary of supported currencies
# Format: "CODE — Name": "symbol"
CURRENCIES = {
    "USD — US Dollar":          "$",
    "EUR — Euro":               "€",
    "GBP — British Pound":      "£",
    "JPY — Japanese Yen":       "¥",
    "MYR — Malaysian Ringgit":  "RM",
    "SGD — Singapore Dollar":   "S$",
    "AUD — Australian Dollar":  "A$",
    "CAD — Canadian Dollar":    "C$",
    "INR — Indian Rupee":       "₹",
    "PHP — Philippine Peso":    "₱",
    "IDR — Indonesian Rupiah":  "Rp",
    "THB — Thai Baht":          "฿",
    "KRW — South Korean Won":   "₩",
    "CNY — Chinese Yuan":       "¥",
    "AED — UAE Dirham":         "د.إ",
    "SAR — Saudi Riyal":        "﷼",
    "BRL — Brazilian Real":     "R$",
    "ZAR — South African Rand": "R",
    "CHF — Swiss Franc":        "Fr",
    "HKD — Hong Kong Dollar":   "HK$",
}

# Special budget option that includes spending from every expense category.
# This is not stored as a normal user-created category.
ALL_EXPENSE_CATEGORIES = "All Expense Categories"

# Delete user data in this exact order:
# child records first, then the records they reference.
USER_DATA_DELETE_ORDER = (
    "tags",
    "processed_schedule_occurrences",
    "transactions",
    "subscriptions",
    "recurring_transactions",
    "budgets",
    "categories",
    "wishlist",
    "badges",
    "settings",
    "accounts",
)

def get_currency(user_id):
    """
    Returns the currency symbol for the user.
    Creates a default USD setting if none exists yet.
    Call this anywhere you display a money amount.

    Usage example:
        symbol = get_currency(user_id)
        label = f"Balance: {symbol}{amount:,.2f}"
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT currency_symbol FROM settings WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()

        if row:
            return row[0]
        else:
            # No settings row yet — create default USD
            cursor.execute(
                '''INSERT INTO settings (user_id, currency_symbol, currency_name)
                   VALUES (?, ?, ?)''',
                (user_id, "$", "USD")
            )
            conn.commit()
            return "$"


def save_currency(user_id, symbol, name):
    """
    Saves the user's chosen currency to the settings table.
    Uses INSERT OR REPLACE so it works whether row
    already exists or not.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO settings (user_id, currency_symbol, currency_name)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
               currency_symbol = excluded.currency_symbol,
               currency_name = excluded.currency_name''',
            (user_id, symbol, name)
        )
        conn.commit()

def advance_schedule_date(
    current_date,
    schedule_kind,
    frequency,
    monthly_charge_days
):
    """Returns the date strictly after the current occurrence."""
    if schedule_kind == "subscription":
        return next_subscription_billing_date(
            monthly_charge_days,
            current_date,
            inclusive=False
        )

    if schedule_kind != "recurring":
        raise ValueError(
            f"Unsupported schedule kind: {schedule_kind}"
        )

    if frequency == "Daily":
        return current_date + timedelta(days=1)

    if frequency == "Weekly":
        return current_date + timedelta(weeks=1)

    if frequency == "Monthly":
        return current_date + relativedelta(months=1)

    if frequency == "Yearly":
        return current_date + relativedelta(years=1)

    raise ValueError(
        f"Unsupported recurring frequency: {frequency}"
    )
# ============================================================
# RECURRING TRANSACTIONS
# ============================================================
# Recurring transactions auto-add themselves on login
# when their next_due_date has arrived or passed.
#
# Frequencies supported:
#   Daily   — adds every day
#   Weekly  — adds every 7 days
#   Monthly — adds same date each month
#   Yearly  — adds same date each year
#
# How it works on login:
#   1. process_recurring_transactions() runs
#   2. Finds all active recurring transactions where
#      next_due_date <= today
#   3. Inserts them as real transactions
#   4. Updates account balance
#   5. Calculates and saves the new next_due_date
#
# User can:
#   - Add new recurring transactions
#   - View existing ones
#   - Pause/resume them
#   - Delete them
# ============================================================

def process_recurring_transactions(user_id):
    """
    Called automatically on login.
    Uses a while loop to catch up ALL missed occurrences
    not just the most recent one.
    Example: offline 5 days with daily recurring = 5 transactions added
    """
    today = datetime.today().date()
    today_str = today.strftime("%Y-%m-%d")

    with get_db() as conn:
        # Serialize schedule processing before reading due rules.
        # If another writer is active, SQLite may wait or report
        # "database is locked" rather than process concurrently.
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.cursor()

        # Get all active recurring transactions that are due
        # Also fetch notes, tags and necessity from the recurring rule
        cursor.execute(
            '''SELECT id, account_id, type, category, amount,
                      frequency, next_due_date, name,
                      notes, tags, necessity,
                      schedule_kind, monthly_charge_days,
                      schedule_start_date
               FROM recurring_transactions
               WHERE user_id = ? AND is_active = 1
               AND next_due_date <= ?''',
            (user_id, today_str)
        )
        due_items = cursor.fetchall()

        for item in due_items:
            (rec_id, account_id, tx_type, category,
             amount, frequency, next_due_date_str, name,
             notes, tags, necessity,
             schedule_kind, monthly_charge_days,
             schedule_start_date) = item

            # Fallback for rows created before columns existed
            notes     = notes     or ""
            tags      = tags      or ""
            necessity = necessity or "unset"

            # Ordinary recurring rules have no subscription ID.
            linked_subscription_id = None

            if schedule_kind == "subscription":
                # Find the subscription associated with this shared rule.
                cursor.execute(
                    '''SELECT id
                       FROM subscriptions
                       WHERE user_id = ? AND recurring_rule_id = ?''',
                    (user_id, rec_id)
                )
                linked_subscription = cursor.fetchone()

                if linked_subscription is None:
                    raise ValueError(
                        f"Subscription rule {rec_id} has no linked "
                        "subscription record. No expense was generated "
                        "for this rule."
                    )

                linked_subscription_id = linked_subscription[0]

            next_due = datetime.strptime(
                next_due_date_str, "%Y-%m-%d"
            ).date()

            # Subscription schedules must have an explicit start date
            # and must represent expenses.
            if schedule_kind == "subscription":
                if tx_type != "expense":
                    raise ValueError(
                        f"Subscription rule {rec_id} must be an expense."
                    )

                if not schedule_start_date:
                    raise ValueError(
                        f"Subscription rule {rec_id} is missing its start date."
                    )

                start_date = datetime.strptime(
                    schedule_start_date, "%Y-%m-%d"
                ).date()

                # Never generate an occurrence before the schedule begins.
                search_from = max(next_due, start_date)

                # Also ensure next_due falls on a valid billing day.
                next_due = next_subscription_billing_date(
                    monthly_charge_days,
                    search_from,
                    inclusive=True
                )

            # Keep looping until next_due is in the future
            # This catches ALL missed dates not just one
            while next_due <= today:
                occurrence_date = next_due.strftime("%Y-%m-%d")

                # Calculate the following date before writing this occurrence.
                following_due = advance_schedule_date(
                    next_due,
                    schedule_kind,
                    frequency,
                    monthly_charge_days
                )

                cursor.execute(
                    '''SELECT 1
                       FROM processed_schedule_occurrences
                       WHERE user_id = ?
                         AND recurring_rule_id = ?
                         AND scheduled_date = ?''',
                    (user_id, rec_id, occurrence_date)
                )

                if cursor.fetchone() is not None:
                    # Already processed, including occurrences whose
                    # transaction has since been deleted.
                    next_due = following_due
                    continue

                # This marker is committed together with the transaction
                # and balance update below.
                cursor.execute(
                    '''INSERT INTO processed_schedule_occurrences
                       (user_id, recurring_rule_id, scheduled_date)
                       VALUES (?, ?, ?)''',
                    (user_id, rec_id, occurrence_date)
                )

                # Income transactions should not have a Need/Want rating.
                transaction_necessity = (
                    necessity
                    if tx_type == "expense"
                    and necessity in ("need", "want", "unset")
                    else "unset"
                )

                # Label the generated record according to its schedule kind.
                source_label = (
                    "Subscription"
                    if schedule_kind == "subscription"
                    else "Recurring"
                )

                transaction_notes = f"{source_label}: {name}"
                if notes:
                    transaction_notes += f" | {notes}"

                # A subscription expense stores both IDs:
                # - recurring_rule_id for shared recurring history
                # - subscription_id for subscription payment history
                cursor.execute(
                    '''INSERT INTO transactions
                       (user_id, category, type, amount,
                        date, time, account_id, notes, necessity,
                        recurring_rule_id, subscription_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        user_id,
                        category,
                        tx_type,
                        amount,
                        next_due.strftime("%Y-%m-%d"),
                        "00:00",
                        account_id,
                        transaction_notes,
                        transaction_necessity,
                        rec_id,
                        linked_subscription_id
                    )
                )

                # Get the id of the transaction just inserted
                # so we can save tags to it
                new_tx_id = cursor.lastrowid

                # Save tags from the recurring rule to this transaction
                if tags:
                    MAX_TAG_LENGTH = 30
                    MAX_TAGS       = 10
                    tag_list = [
                        t.strip()
                        for t in tags.split(",")
                        if t.strip() and len(t.strip()) <= MAX_TAG_LENGTH
                    ]
                    tag_list = tag_list[:MAX_TAGS]
                    for tag in tag_list:
                        cursor.execute(
                            '''INSERT INTO tags
                               (transaction_id, user_id, tag_name)
                               VALUES (?, ?, ?)''',
                            (new_tx_id, user_id, tag)
                        )

                # Keep a readable automatic tag for keyword searches.
                # History will use recurring_rule_id, not this tag.
                auto_tag = f"auto:{name}"

                cursor.execute(
                    '''INSERT INTO tags
                       (transaction_id, user_id, tag_name)
                       SELECT ?, ?, ?
                       WHERE NOT EXISTS (
                           SELECT 1
                           FROM tags
                           WHERE transaction_id = ?
                             AND user_id = ?
                             AND tag_name = ?
                       )''',
                    (
                        new_tx_id,
                        user_id,
                        auto_tag,
                        new_tx_id,
                        user_id,
                        auto_tag
                    )
                )

                # Update account balance
                if tx_type == "income":
                    cursor.execute(
                        "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                        (amount, account_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                        (amount, account_id)
                    )

                # Advance after successfully recording this occurrence.
                next_due = following_due

            # After all catch-up done save the new next due date
            cursor.execute(
                '''UPDATE recurring_transactions
                   SET next_due_date = ?, last_processed = ?
                   WHERE id = ?''',
                (next_due.strftime("%Y-%m-%d"), today_str, rec_id)
            )

        conn.commit()

def show_recurring_transactions(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="🔁 Recurring Transactions",
             font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)

    # Fetch all recurring transactions for this user
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT r.id, r.name, r.type, r.category,
                      r.amount, r.frequency, r.next_due_date,
                      r.is_active, a.account_name,
                      r.notes, r.tags, r.necessity,
                      r.schedule_kind, r.monthly_charge_days
               FROM recurring_transactions r
               LEFT JOIN accounts a
                 ON r.account_id = a.id
                AND a.user_id = r.user_id
               WHERE r.user_id = ?
               ORDER BY r.next_due_date ASC, r.id ASC''',
            (user_id,)
        )
        items = cursor.fetchall()

    if not items:
        tk.Label(body,
                 text="No recurring transactions yet. Add one below!",
                 font=("Segoe UI", 10),
                 bg="#f0f4f8", fg="#718096").pack(pady=10)
    else:
        tk.Label(
            body,
            text=(
                "Active schedules are checked at login. "
                "Subscriptions shown here are the same schedules "
                "shown in the Subscriptions section."
            ),
            font=("Segoe UI", 9, "italic"),
            bg="#f0f4f8",
            fg="#718096",
            wraplength=550,
            justify="left"
        ).pack(padx=20, pady=(5, 10))

        for item in items:
            (rec_id, name, tx_type, category,
             amount, frequency, next_due,
             is_active, account_name,
             notes, tags, necessity,
             schedule_kind, monthly_charge_days) = item

            account_name = account_name or "Missing account — needs attention"

            # Fallback for rows created before new columns existed
            notes     = notes     or ""
            tags      = tags      or ""
            necessity = necessity or "unset"

            # Card colour — grey if paused, white if active
            card_bg = "white" if is_active else "#f7fafc"
            status_text = "🟢 Active" if is_active else "⏸️ Paused"
            prefix = "+" if tx_type == "income" else "-"

            card = tk.Frame(body, bg=card_bg, relief="solid", bd=1)
            card.pack(fill="x", padx=20, pady=5)

            # Top row — name and status
            top = tk.Frame(card, bg=card_bg)
            top.pack(fill="x", padx=10, pady=(8, 2))
            tk.Label(top, text=f"🔁 {name}",
                     font=("Segoe UI", 11, "bold"),
                     bg=card_bg).pack(side="left")
            tk.Label(top, text=status_text,
                     font=("Segoe UI", 9),
                     bg=card_bg, fg="#718096").pack(side="right")

            # Describe the actual schedule pattern.
            if schedule_kind == "subscription":
                kind_label = "Subscription"
                schedule_label = (
                    f"Monthly billing days: {monthly_charge_days}"
                )
            else:
                kind_label = (
                    "Recurring Income"
                    if tx_type == "income"
                    else "Recurring Expense"
                )
                schedule_label = f"Frequency: {frequency}"

            sym = get_currency(user_id)

            tk.Label(
                card,
                text=(
                    f"{kind_label}\n"
                    f"{schedule_label}\n"
                    f"Category: {category}\n"
                    f"Current amount per occurrence: "
                    f"{prefix}{sym}{amount:,.2f}\n"
                    f"Account: {account_name}\n"
                    f"Next scheduled date: {next_due}"
                ),
                font=("Segoe UI", 9),
                bg=card_bg,
                fg="#4a5568",
                wraplength=550,
                justify="left"
            ).pack(anchor="w", padx=10)

            # Notes row — only show if notes exist
            if notes:
                tk.Label(card,
                         text=f"📝  {notes}",
                         font=("Segoe UI", 8, "italic"),
                         bg=card_bg, fg="#4a5568",
                         wraplength=500, justify="left"
                         ).pack(anchor="w", padx=10, pady=(1, 0))

            # Necessity badge — only show for expense recurring transactions
            if tx_type == "expense" and necessity != "unset":
                nec_bg   = "#e9d8fd" if necessity == "want" else "#c6f6d5"
                nec_text = "🛍️ Want" if necessity == "want" else "✅ Need"
                tk.Label(card,
                         text=nec_text,
                         font=("Segoe UI", 8, "bold"),
                         bg=nec_bg, fg="#2d3748",
                         relief="solid", bd=1,
                         padx=4, pady=1
                         ).pack(anchor="w", padx=10, pady=(2, 0))

            # Tags row — only show if tags exist
            if tags:
                tags_row = tk.Frame(card, bg=card_bg)
                tags_row.pack(anchor="w", padx=10, pady=(2, 0))
                for tag in tags.split(","):
                    tag = tag.strip()
                    if tag:
                        tk.Label(
                            tags_row,
                            text=f"#{tag}",
                            font=("Segoe UI", 8, "bold"),
                            bg="#ebf8ff", fg="#2b6cb0",
                            relief="solid", bd=1,
                            padx=4, pady=1
                        ).pack(side="left", padx=2)

            # ── Action buttons ────────────────────────────────
            history_row = tk.Frame(card, bg=card_bg)
            history_row.pack(anchor="w", padx=10, pady=(6, 2))

            make_button(
                history_row,
                "View History",
                lambda rid=rec_id, rname=name: show_recurring_history(
                    user_id, rid, rname
                ),
                color="#805ad5",
                width=16
            ).pack(side="left", padx=3)

            btn_row = tk.Frame(card, bg=card_bg)
            btn_row.pack(anchor="w", padx=10, pady=(2, 8))

            make_button(
                btn_row,
                "Edit",
                lambda rid=rec_id: show_edit_recurring(user_id, rid),
                color="#3182ce",
                width=10
            ).pack(side="left", padx=3)

            make_button(
                btn_row,
                "Pause" if is_active else "Resume",
                lambda rid=rec_id, target=(0 if is_active else 1):
                    toggle_recurring(user_id, rid, target),
                color="#dd6b20" if is_active else "#38a169",
                width=10
            ).pack(side="left", padx=3)

            make_button(
                btn_row,
                "Delete",
                lambda rid=rec_id: delete_recurring(user_id, rid),
                color="#e53e3e",
                width=10
            ).pack(side="left", padx=3)

    # Bottom buttons
    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=10)
    make_button(btn_frame, "➕ Add Recurring",
                lambda: show_add_recurring(user_id),
                color="#38a169").pack(side="left", padx=5)
    make_button(btn_frame, "← Back to Menu",
                lambda: show_main_menu(current_user),
                color="#718096").pack(side="left", padx=5)


def show_add_recurring(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="➕ Add Recurring Transaction",
             font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)

    # Name
    tk.Label(body, text="Name (e.g. Monthly Salary):",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    name_entry = make_entry(body)
    name_entry.pack(anchor="w", pady=(2, 10))

    # Transaction type
    tk.Label(body, text="Type:",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    type_var = tk.StringVar(value="income")
    type_frame = tk.Frame(body, bg="#f0f4f8")
    type_frame.pack(anchor="w", pady=(2, 10))
    tk.Radiobutton(type_frame, text="Income",
                   variable=type_var, value="income",
                   bg="#f0f4f8", font=("Segoe UI", 10),
                   command=lambda: refresh_cats()).pack(side="left")
    tk.Radiobutton(type_frame, text="Expense",
                   variable=type_var, value="expense",
                   bg="#f0f4f8", font=("Segoe UI", 10),
                   command=lambda: refresh_cats()).pack(side="left", padx=10)

    # Category dropdown with Add Category button
    tk.Label(body, text="Category:",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")

    # Horizontal frame for dropdown and button
    cat_row = tk.Frame(body, bg="#f0f4f8")
    cat_row.pack(anchor="w", pady=(2, 10))

    category_var = tk.StringVar()
    category_dd = ttk.Combobox(cat_row, textvariable=category_var,
                               state="readonly", width=25)
    category_dd.pack(side="left")

    # Add Category button — uses the currently selected type
    # (income or expense) so it adds the correct category type
    make_button(
        cat_row, "+ Add Category",
        lambda: open_add_category_popup(
            user_id, type_var.get(), category_dd, category_var
        ),
        color="#3182ce", width=14
    ).pack(side="left", padx=6)

    def refresh_cats():
        tx_type = type_var.get()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM categories WHERE user_id = ? AND type = ?",
                (user_id, tx_type)
            )
            cats = [row[0] for row in cursor.fetchall()]
        category_dd["values"] = cats
        if cats:
            category_var.set(cats[0])
        else:
            category_var.set("")

    refresh_cats()

    # Amount
    tk.Label(body, text="Amount ($):",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    amount_entry = make_entry(body)
    amount_entry.pack(anchor="w", pady=(2, 10))

    # Frequency
    tk.Label(body, text="Frequency:",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    freq_var = tk.StringVar(value="Monthly")
    freq_dd = ttk.Combobox(body, textvariable=freq_var,
                           values=["Daily", "Weekly", "Monthly", "Yearly"],
                           state="readonly", width=20)
    freq_dd.pack(anchor="w", pady=(2, 10))

    # ── Notes field ───────────────────────────────────────────
    tk.Label(body, text="Notes (optional):",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    tk.Label(body,
             text="e.g. Monthly rent for apartment — included in each transaction",
             font=("Segoe UI", 8, "italic"),
             bg="#f0f4f8", fg="#718096").pack(anchor="w")
    notes_entry = make_entry(body, width=40)
    notes_entry.pack(anchor="w", pady=(2, 10))

    # ── Tags field ────────────────────────────────────────────
    tk.Label(body, text="Tags (optional):",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    tk.Label(body,
             text="Comma separated e.g. fixed-cost, household, work",
             font=("Segoe UI", 8, "italic"),
             bg="#f0f4f8", fg="#718096").pack(anchor="w")
    tags_entry = make_entry(body, width=40)
    tags_entry.pack(anchor="w", pady=(2, 10))

    # ── Necessity field ───────────────────────────────────────
    # Only relevant for expense recurring transactions
    # Income recurring transactions will always save as "unset"
    tk.Label(body, text="Necessity (for expenses only):",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    tk.Label(body,
             text="Is this recurring expense a need or a want?",
             font=("Segoe UI", 8, "italic"),
             bg="#f0f4f8", fg="#718096").pack(anchor="w")
    necessity_var = tk.StringVar(value="unset")
    necessity_frame = tk.Frame(body, bg="#f0f4f8")
    necessity_frame.pack(anchor="w", pady=(2, 10))
    tk.Radiobutton(necessity_frame, text="✅ Need",
                   variable=necessity_var, value="need",
                   bg="#f0f4f8", font=("Segoe UI", 10)).pack(side="left")
    tk.Radiobutton(necessity_frame, text="🛍️ Want",
                   variable=necessity_var, value="want",
                   bg="#f0f4f8", font=("Segoe UI", 10)).pack(side="left", padx=10)
    tk.Radiobutton(necessity_frame, text="— Not set",
                   variable=necessity_var, value="unset",
                   bg="#f0f4f8", font=("Segoe UI", 10)).pack(side="left")

    # Start date
    tk.Label(body, text="Start Date (YYYY-MM-DD):",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    start_entry = make_entry(body)
    # Pre-fill with today's date
    start_entry.insert(0, datetime.today().strftime("%Y-%m-%d"))
    start_entry.pack(anchor="w", pady=(2, 10))

    # Account
    tk.Label(body, text="Account:",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    accounts = view_accounts(user_id)
    sym = get_currency(user_id)          # ← Add this line
    account_options = {
        f"{acc[1]} | Balance: {sym}{acc[2]:,.2f}": acc[0]  # ← Use sym
        for acc in accounts
    }
    account_var = tk.StringVar(
        value=list(account_options.keys())[0] if account_options else ""
    )
    account_dd = ttk.Combobox(body, textvariable=account_var,
                              values=list(account_options.keys()),
                              state="readonly", width=35)
    account_dd.pack(anchor="w", pady=(2, 10))

    msg_label = tk.Label(body, text="",
                         font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red", wraplength=400)
    msg_label.pack(pady=5)

    def on_submit():
        name       = name_entry.get().strip()
        tx_type    = type_var.get()
        category   = category_var.get()
        frequency  = freq_var.get()
        start      = start_entry.get().strip()
        account_id = account_options.get(account_var.get())
        notes      = notes_entry.get().strip()
        tags_raw   = tags_entry.get().strip()

        # For income recurring transactions force necessity to unset
        if tx_type == "income":
            necessity = "unset"
        else:
            necessity = necessity_var.get()

        # Validate name
        if not name:
            msg_label.config(
                text="❌ Please enter a name.", fg="red")
            return

        # Validate category
        if not category:
            msg_label.config(
                text="❌ Please select a category.", fg="red")
            return

        # Validate account
        if not account_id:
            msg_label.config(
                text="❌ Please select an account.", fg="red")
            return

        # Validate amount
        try:
            amount = float(amount_entry.get().strip())
        except ValueError:
            msg_label.config(
                text="❌ Amount must be a valid number.", fg="red")
            return

        if amount <= 0:
            msg_label.config(
                text="❌ Amount must be greater than 0.", fg="red")
            return

        # Validate start date format
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
        except ValueError:
            msg_label.config(
                text="❌ Date must be in YYYY-MM-DD format.", fg="red")
            return

        # Save to database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO recurring_transactions
                   (user_id, account_id, type, category,
                    amount, frequency, next_due_date, name,
                    notes, tags, necessity)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, account_id, tx_type, category,
                 amount, frequency,
                 start_date.strftime("%Y-%m-%d"), name,
                 notes, tags_raw, necessity)
            )
            conn.commit()

        msg_label.config(
            text="✅ Recurring transaction added!", fg="green")
        root.after(1000, lambda: show_recurring_transactions(user_id))

    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=10)
    make_button(btn_frame, "✅ Save",
                on_submit, color="#38a169").pack(side="left", padx=5)
    make_button(btn_frame, "← Back",
                lambda: show_recurring_transactions(user_id),
                color="#718096").pack(side="left", padx=5)

def show_edit_recurring(user_id, rec_id):
    """
    Edit screen for a recurring transaction.
    Allows editing name, type, category, amount,
    frequency, next due date and account.
    Pre-fills all fields with existing values.
    """
    # Subscriptions must use their specialised editor.
    # Do this before clearing the current screen.
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT schedule_kind
               FROM recurring_transactions
               WHERE id = ? AND user_id = ?''',
            (rec_id, user_id)
        )
        schedule_row = cursor.fetchone()

        cursor.execute(
            '''SELECT id
               FROM subscriptions
               WHERE recurring_rule_id = ? AND user_id = ?''',
            (rec_id, user_id)
        )
        subscription_row = cursor.fetchone()

    if schedule_row is None:
        messagebox.showerror(
            "Not Found",
            "This recurring schedule no longer exists.",
            parent=root
        )
        return

    schedule_kind = schedule_row[0]

    if schedule_kind == "subscription":
        if subscription_row is None:
            messagebox.showerror(
                "Invalid Schedule Link",
                "This subscription schedule has no linked subscription record.",
                parent=root
            )
            return

        show_edit_subscription(user_id, subscription_row[0])
        return

    if schedule_kind != "recurring" or subscription_row is not None:
        messagebox.showerror(
            "Invalid Schedule",
            "The schedule type or subscription link is inconsistent. "
            "Nothing was changed.",
            parent=root
        )
        return
    
    clear_window()

    # Load existing recurring transaction data
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT name, type, category, amount,
                      frequency, next_due_date, account_id,
                      notes, tags, necessity
               FROM recurring_transactions
               WHERE id = ? AND user_id = ?''',
            (rec_id, user_id)
        )
        row = cursor.fetchone()

    if not row:
        messagebox.showerror("Error", "Recurring transaction not found.")
        show_recurring_transactions(user_id)
        return

    (old_name, old_type, old_category, old_amount,
     old_frequency, old_next_due, old_account_id,
     old_notes, old_tags, old_necessity) = row

    # Fallback for rows created before new columns existed
    old_notes     = old_notes     or ""
    old_tags      = old_tags      or ""
    old_necessity = old_necessity or "unset"

    sym = get_currency(user_id)

    # ── Header ───────────────────────────────────────────────
    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")

    tk.Label(
        header,
        text="✏️ Edit Recurring Transaction",
        font=("Segoe UI", 16, "bold"),
        fg="white", bg="#2b6cb0"
    ).pack()

    tk.Label(
        header,
        text=f"Editing: {old_name}",
        font=("Segoe UI", 10),
        fg="#bee3f8", bg="#2b6cb0"
    ).pack()

    # ── Pinned button bar — packed BEFORE body ────────────────
    btn_bar = tk.Frame(root, bg="#f0f4f8", pady=10)
    btn_bar.pack(side="bottom", fill="x", padx=20)

    # ── Scrollable body ───────────────────────────────────────
    body = make_scrollable_frame(root)

    # ── Name ──────────────────────────────────────────────────
    tk.Label(
        body,
        text="Name:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20, pady=(10, 0))

    name_entry = make_entry(body, width=35)
    name_entry.insert(0, old_name)       # Pre-fill existing name
    name_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Transaction type ──────────────────────────────────────
    tk.Label(
        body,
        text="Type:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    type_var   = tk.StringVar(value=old_type)
    type_frame = tk.Frame(body, bg="#f0f4f8")
    type_frame.pack(anchor="w", padx=20, pady=(2, 10))

    tk.Radiobutton(
        type_frame,
        text="Income",
        variable=type_var,
        value="income",
        bg="#f0f4f8",
        font=("Segoe UI", 10),
        command=lambda: refresh_cats()
    ).pack(side="left")

    tk.Radiobutton(
        type_frame,
        text="Expense",
        variable=type_var,
        value="expense",
        bg="#f0f4f8",
        font=("Segoe UI", 10),
        command=lambda: refresh_cats()
    ).pack(side="left", padx=10)

    # ── Category ──────────────────────────────────────────────
    tk.Label(
        body,
        text="Category:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    # Horizontal frame for dropdown and button
    cat_row = tk.Frame(body, bg="#f0f4f8")
    cat_row.pack(anchor="w", padx=20, pady=(2, 10))

    category_var = tk.StringVar(value=old_category)
    category_dd  = ttk.Combobox(
        cat_row,
        textvariable=category_var,
        state="readonly",
        width=25
    )
    category_dd.pack(side="left")

    # Add Category button — uses currently selected type
    make_button(
        cat_row, "+ Add Category",
        lambda: open_add_category_popup(
            user_id, type_var.get(), category_dd, category_var
        ),
        color="#3182ce", width=14
    ).pack(side="left", padx=6)

    def refresh_cats():
        """Refreshes category dropdown based on selected type."""
        tx_type = type_var.get()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM categories WHERE user_id = ? AND type = ?",
                (user_id, tx_type)
            )
            cats = [row[0] for row in cursor.fetchall()]
        category_dd["values"] = cats
        if old_category in cats:
            category_var.set(old_category)  # Keep existing if still valid
        elif cats:
            category_var.set(cats[0])
        else:
            category_var.set("")

    refresh_cats()

    # ── Amount ────────────────────────────────────────────────
    tk.Label(
        body,
        text=f"Amount ({sym}):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    amount_entry = make_entry(body, width=20)
    amount_entry.insert(0, str(old_amount))  # Pre-fill existing amount
    amount_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Frequency ─────────────────────────────────────────────
    tk.Label(
        body,
        text="Frequency:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    freq_var = tk.StringVar(value=old_frequency)
    freq_dd  = ttk.Combobox(
        body,
        textvariable=freq_var,
        values=["Daily", "Weekly", "Monthly", "Yearly"],
        state="readonly",
        width=20
    )
    freq_dd.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Notes field ───────────────────────────────────────────
    tk.Label(
        body,
        text="Notes (optional):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)
    tk.Label(
        body,
        text="e.g. Monthly rent for apartment",
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8", fg="#718096"
    ).pack(anchor="w", padx=20)
    notes_entry = make_entry(body, width=40)
    notes_entry.insert(0, old_notes)   # Pre-fill existing notes
    notes_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Tags field ────────────────────────────────────────────
    tk.Label(
        body,
        text="Tags (optional):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)
    tk.Label(
        body,
        text="Comma separated e.g. fixed-cost, household",
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8", fg="#718096"
    ).pack(anchor="w", padx=20)
    tags_entry = make_entry(body, width=40)
    tags_entry.insert(0, old_tags)     # Pre-fill existing tags
    tags_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Necessity field ───────────────────────────────────────
    tk.Label(
        body,
        text="Necessity (for expenses only):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)
    necessity_var = tk.StringVar(value=old_necessity)
    necessity_frame = tk.Frame(body, bg="#f0f4f8")
    necessity_frame.pack(anchor="w", padx=20, pady=(2, 10))
    tk.Radiobutton(
        necessity_frame, text="✅ Need",
        variable=necessity_var, value="need",
        bg="#f0f4f8", font=("Segoe UI", 10)
    ).pack(side="left")
    tk.Radiobutton(
        necessity_frame, text="🛍️ Want",
        variable=necessity_var, value="want",
        bg="#f0f4f8", font=("Segoe UI", 10)
    ).pack(side="left", padx=10)
    tk.Radiobutton(
        necessity_frame, text="— Not set",
        variable=necessity_var, value="unset",
        bg="#f0f4f8", font=("Segoe UI", 10)
    ).pack(side="left")

    # ── Next due date ─────────────────────────────────────────
    tk.Label(
        body,
        text="Next Due Date (YYYY-MM-DD):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    tk.Label(
        body,
        text="Change this to correct when the next transaction fires.",
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8", fg="#718096"
    ).pack(anchor="w", padx=20)

    due_entry = make_entry(body, width=20)
    due_entry.insert(0, old_next_due)    # Pre-fill existing due date
    due_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Account dropdown ──────────────────────────────────────
    tk.Label(
        body,
        text="Account:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    accounts       = view_accounts(user_id)
    account_options = {
        f"{acc[1]} | Balance: {sym}{acc[2]:,.2f}": acc[0]
        for acc in accounts
    }

    # Find the label for the currently linked account
    old_account_label = next(
        (k for k, v in account_options.items()
         if v == old_account_id), ""
    )

    account_var = tk.StringVar(value=old_account_label)
    account_dd  = ttk.Combobox(
        body,
        textvariable=account_var,
        values=list(account_options.keys()),
        state="readonly",
        width=35
    )
    account_dd.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Info note ─────────────────────────────────────────────
    note_frame = tk.Frame(body, bg="#ebf8ff", relief="solid", bd=1)
    note_frame.pack(fill="x", padx=20, pady=5)

    tk.Label(
        note_frame,
        text=(
            "ℹ️ Changes take effect from the next due date onwards.\n"
            "Past transactions already added will not be affected."
        ),
        font=("Segoe UI", 9, "italic"),
        bg="#ebf8ff", fg="#2c5282",
        wraplength=430, justify="left",
        pady=8, padx=8
    ).pack()

    # ── Message label ─────────────────────────────────────────
    msg_label = tk.Label(
        body, text="",
        font=("Segoe UI", 10),
        bg="#f0f4f8", fg="red",
        wraplength=400
    )
    msg_label.pack(padx=20, pady=5)

    # ── Save function ─────────────────────────────────────────
    def on_save():
        new_name      = name_entry.get().strip()
        new_type      = type_var.get()
        new_category  = category_var.get()
        new_frequency = freq_var.get()
        new_due       = due_entry.get().strip()
        new_account   = account_options.get(account_var.get())
        new_notes     = notes_entry.get().strip()
        new_tags      = tags_entry.get().strip()

        # For income recurring transactions force necessity to unset
        if new_type == "income":
            new_necessity = "unset"
        else:
            new_necessity = necessity_var.get()

        # Validate name
        if not new_name:
            msg_label.config(
                text="❌ Name cannot be empty.", fg="red")
            return

        # Validate category
        if not new_category:
            msg_label.config(
                text="❌ Please select a category.", fg="red")
            return

        # Validate account
        if not new_account:
            msg_label.config(
                text="❌ Please select an account.", fg="red")
            return

        # Validate amount
        try:
            new_amount = float(amount_entry.get().strip())
        except ValueError:
            msg_label.config(
                text="❌ Amount must be a valid number.", fg="red")
            return

        if new_amount <= 0:
            msg_label.config(
                text="❌ Amount must be greater than 0.", fg="red")
            return

        # Validate next due date format
        try:
            datetime.strptime(new_due, "%Y-%m-%d")
        except ValueError:
            msg_label.config(
                text="❌ Date must be in YYYY-MM-DD format.", fg="red")
            return

        # Save all changes to database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''UPDATE recurring_transactions
                   SET name          = ?,
                       type          = ?,
                       category      = ?,
                       amount        = ?,
                       frequency     = ?,
                       next_due_date = ?,
                       account_id    = ?,
                       notes         = ?,
                       tags          = ?,
                       necessity     = ?
                   WHERE id = ? AND user_id = ?''',
                (new_name, new_type, new_category,
                 new_amount, new_frequency,
                 new_due, new_account,
                 new_notes, new_tags, new_necessity,
                 rec_id, user_id)
            )
            conn.commit()

        msg_label.config(
            text="✅ Recurring transaction updated!", fg="green")
        root.after(1000, lambda: show_recurring_transactions(user_id))

    # ── Add buttons to pinned bar ─────────────────────────────
    make_button(
        btn_bar, "✅ Save Changes",
        on_save, color="#38a169"
    ).pack(side="left", padx=5)

    make_button(
        btn_bar, "← Back",
        lambda: show_recurring_transactions(user_id),
        color="#718096"
    ).pack(side="left", padx=5)

def show_recurring_history(user_id, rec_id, rec_name):
    """
    Displays surviving transactions linked to a recurring rule by ID.

    Each transaction is displayed using its own saved income/expense
    type, rather than the rule's current type.
    """
    sym = get_currency(user_id)

    # Load the recurring rule details
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT type, category, amount, frequency, is_active
               FROM recurring_transactions
               WHERE id = ? AND user_id = ?''',
            (rec_id, user_id)
        )
        rec_row = cursor.fetchone()

    if not rec_row:
        messagebox.showerror("Error", "Recurring transaction not found.")
        return

    rec_type, rec_category, rec_amount, rec_frequency, is_active = rec_row

    # Fetch transactions generated by this specific recurring rule.
    # Matching uses the stable recurring_rule_id, so renaming the
    # rule does not hide its earlier generated transactions.
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT t.date, t.time, t.amount, t.notes,
                      t.reference, t.necessity,
                      COALESCE(a.account_name, 'Missing account'),
                      t.type
               FROM transactions t
               LEFT JOIN accounts a
                 ON t.account_id = a.id
                AND a.user_id = t.user_id
               WHERE t.user_id = ?
                 AND t.recurring_rule_id = ?
               ORDER BY t.date DESC, t.time DESC, t.id DESC''',
            (user_id, rec_id)
        )
        history = cursor.fetchall()

    # Use each recorded transaction's type for historical totals.
    total_income = sum(
        record[2] for record in history if record[7] == "income"
    )
    total_expenses = sum(
        record[2] for record in history if record[7] == "expense"
    )
    net_recorded = total_income - total_expenses

    # These describe the current rule only.
    prefix = "+" if rec_type == "income" else "-"
    status_text = "Active" if is_active else "Paused"

    # ── Create popup ──────────────────────────────────────────
    popup = tk.Toplevel(root)
    popup.title(f"🔍 {rec_name} — History")
    popup.geometry("500x520")
    popup.resizable(False, False)
    popup.configure(bg="#f0f4f8")
    popup.transient(root)
    popup.grab_set()
    # Reserve bottom space before packing the expanding history area.
    btn_bar = tk.Frame(popup, bg="#f0f4f8", pady=10)
    btn_bar.pack(side="bottom", fill="x", padx=15)

    # ── Header ────────────────────────────────────────────────
    header = tk.Frame(popup, bg="#805ad5", pady=10)
    header.pack(fill="x")

    tk.Label(
        header,
        text=f"🔁 {rec_name}",
        font=("Segoe UI", 14, "bold"),
        bg="#805ad5", fg="white"
    ).pack()

    tk.Label(
        header,
        text=f"{rec_frequency}  |  {rec_category}  |  {status_text}",
        font=("Segoe UI", 9),
        bg="#805ad5", fg="#e9d8fd"
    ).pack()

    # ── Summary ───────────────────────────────────────────────
    summary = tk.Frame(popup, bg="white", relief="solid", bd=1)
    summary.pack(fill="x", padx=15, pady=8)

    summary_values = [
        (
            "Recorded income",
            f"{sym}{total_income:,.2f}",
            "#276749"
        ),
        (
            "Recorded expenses",
            f"{sym}{total_expenses:,.2f}",
            "#c53030"
        ),
        (
            "Net recorded",
            f"{'-' if net_recorded < 0 else '+'}"
            f"{sym}{abs(net_recorded):,.2f}",
            "#276749" if net_recorded >= 0 else "#c53030"
        ),
        (
            "Recorded transactions",
            str(len(history)),
            "#2b6cb0"
        ),
        (
            "Current amount per occurrence",
            f"{prefix}{sym}{rec_amount:,.2f}",
            "#2d3748"
        )
    ]

    for label, value, color in summary_values:
        row = tk.Frame(summary, bg="white")
        row.pack(fill="x", padx=10, pady=2)

        tk.Label(
            row,
            text=f"{label}:",
            font=("Segoe UI", 9),
            bg="white",
            fg="#4a5568"
        ).pack(side="left")

        tk.Label(
            row,
            text=value,
            font=("Segoe UI", 9, "bold"),
            bg="white",
            fg=color
        ).pack(side="right")

    # ── Info note ─────────────────────────────────────────────
    tk.Label(
        popup,
        text=(
            "ℹ️ Showing transactions generated by this recurring rule.\n"
            "Occurrences created before this update may not appear here."
        ),
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8", fg="#718096",
        justify="left"
    ).pack(anchor="w", padx=15, pady=(0, 4))

    # ── Scrollable history list ───────────────────────────────
    scroll_outer = tk.Frame(popup, bg="#f0f4f8")
    scroll_outer.pack(fill="both", expand=True, padx=15)

    canvas    = tk.Canvas(scroll_outer, bg="#f0f4f8", highlightthickness=0)
    scrollbar = ttk.Scrollbar(
        scroll_outer, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#f0f4f8")

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(event):
        try:
            if not canvas.winfo_exists():
                return

            direction = int(-1 * (event.delta / 120))
            if direction == 0:
                direction = -1 if event.delta > 0 else 1

            canvas.yview_scroll(direction, "units")

        except tk.TclError:
            return

    def enable_popup_scroll(event=None):
        try:
            if canvas.winfo_exists():
                root.bind_all("<MouseWheel>", _on_mousewheel)
        except tk.TclError:
            pass

    def disable_popup_scroll(event=None):
        root.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", enable_popup_scroll)
    canvas.bind("<Leave>", disable_popup_scroll)
    scroll_frame.bind("<Enter>", enable_popup_scroll)
    scroll_frame.bind("<Leave>", disable_popup_scroll)

    # ── Display each transaction ──────────────────────────────
    if not history:
        tk.Label(
            scroll_frame,
            text=(
                "No linked transactions are currently available.\n"
                "Older unlinked or deleted transactions are not shown."
            ),
            font=("Segoe UI", 10),
            bg="#f0f4f8", fg="#718096",
            justify="center"
        ).pack(pady=20)
    else:
        for record in history:
            (tx_date, tx_time, tx_amount,
             tx_notes, tx_reference, tx_necessity,
             tx_account, recorded_type) = record

            tx_prefix = "+" if recorded_type == "income" else "-"
            tx_color = (
                "#276749"
                if recorded_type == "income"
                else "#e53e3e"
            )

            tx_notes     = tx_notes     or ""
            tx_reference = tx_reference or ""
            tx_necessity = tx_necessity or "unset"

            # Card for each transaction
            tx_card = tk.Frame(scroll_frame, bg="white", relief="solid", bd=1)
            tx_card.pack(fill="x", pady=3)

            # Top row — date, time, account, amount
            top = tk.Frame(tx_card, bg="white")
            top.pack(fill="x", padx=8, pady=(6, 2))

            tk.Label(
                top,
                text=f"{tx_date}  {tx_time}  |  {tx_account}",
                font=("Segoe UI", 9, "bold"),
                bg="white", fg="#2d3748"
            ).pack(side="left")

            tk.Label(
                top,
                text=(
                    f"{recorded_type.capitalize()} "
                    f"{tx_prefix}{sym}{tx_amount:,.2f}"
                ),
                font=("Segoe UI", 9, "bold"),
                bg="white",
                fg=tx_color
            ).pack(side="right")

            # Necessity badge — only for expense recurring transactions
            if (
                recorded_type == "expense"
                and tx_necessity in ("need", "want")
            ):
                nec_bg   = "#e9d8fd" if tx_necessity == "want" else "#c6f6d5"
                nec_text = "🛍️ Want" if tx_necessity == "want" else "✅ Need"
                tk.Label(
                    top, text=nec_text,
                    font=("Segoe UI", 7, "bold"),
                    bg=nec_bg, fg="#2d3748",
                    relief="solid", bd=1, padx=3, pady=1
                ).pack(side="right", padx=5)

            # Notes row — only if notes exist
            if tx_notes:
                tk.Label(
                    tx_card,
                    text=f"📝  {tx_notes}",
                    font=("Segoe UI", 8, "italic"),
                    bg="white", fg="#4a5568",
                    wraplength=420, justify="left"
                ).pack(anchor="w", padx=8, pady=1)

            # Reference row — only if reference exists
            if tx_reference:
                tk.Label(
                    tx_card,
                    text=f"🔖  Ref: {tx_reference}",
                    font=("Segoe UI", 8),
                    bg="white", fg="#4a5568"
                ).pack(anchor="w", padx=8, pady=(1, 4))

            # Bottom padding
            tk.Frame(tx_card, bg="white", height=4).pack()

    # ── Close button ──────────────────────────────────────────

    def close_popup():
        # Remove the popup's global scrolling callback first.
        root.unbind_all("<MouseWheel>")
        popup.destroy()

    # Use the same cleanup if the user clicks the window's X button.
    popup.protocol("WM_DELETE_WINDOW", close_popup)

    make_button(
        btn_bar, "✖ Close",
        close_popup, color="#718096", width=12
    ).pack()

def toggle_recurring(user_id, rec_id, new_status, on_complete=None):
    """
    Pauses a schedule or resumes it from an explicitly confirmed date.

    Resuming does not automatically catch up dates before the
    confirmed next-due date.
    """
    from tkinter import simpledialog

    def refresh_screen():
        if on_complete is not None:
            on_complete()
        else:
            show_recurring_transactions(user_id)

    if new_status not in (0, 1):
        messagebox.showerror(
            "Invalid Status",
            "Schedule status must be active or paused.",
            parent=root
        )
        return

    with get_db() as conn:
        row = conn.execute(
            '''SELECT name, schedule_kind, is_active,
                      next_due_date, monthly_charge_days,
                      schedule_start_date
               FROM recurring_transactions
               WHERE id = ? AND user_id = ?''',
            (rec_id, user_id)
        ).fetchone()

    if row is None:
        messagebox.showerror(
            "Not Found",
            "This schedule no longer exists.",
            parent=root
        )
        return

    (
        name,
        schedule_kind,
        old_status,
        old_next_due,
        billing_days,
        start_date_text
    ) = row

    if old_status == new_status:
        refresh_screen()
        return

    if new_status == 0:
        confirmed = messagebox.askyesno(
            "Pause Schedule",
            (
                f"Pause '{name}'?\n\n"
                "No new occurrences will be recorded while paused.\n"
                "Past transactions and account balances will not change.\n\n"
                "When resuming, you will confirm a new next-due date."
            ),
            parent=root
        )

        if not confirmed:
            return

        proposed_due = old_next_due

    else:
        today = datetime.today().date()

        try:
            if schedule_kind == "subscription":
                start_date = datetime.strptime(
                    start_date_text, "%Y-%m-%d"
                ).date()

                next_date = next_subscription_billing_date(
                    billing_days,
                    max(today, start_date),
                    inclusive=True
                )

            elif schedule_kind == "recurring":
                entered_date = simpledialog.askstring(
                    "Resume Recurring Schedule",
                    (
                        f"Enter the next due date for '{name}'.\n"
                        "Use YYYY-MM-DD, today or a future date.\n\n"
                        "Earlier pending dates will not be caught up."
                    ),
                    initialvalue=today.isoformat(),
                    parent=root
                )

                if entered_date is None:
                    return

                entered_date = entered_date.strip()
                next_date = datetime.strptime(
                    entered_date, "%Y-%m-%d"
                ).date()

                if (
                    next_date.isoformat() != entered_date
                    or next_date < today
                ):
                    raise ValueError(
                        "Choose today or a future date using YYYY-MM-DD."
                    )

            else:
                raise ValueError("The schedule type is not recognised.")

        except (TypeError, ValueError, OverflowError) as error:
            messagebox.showerror(
                "Cannot Resume",
                f"Check the schedule dates and billing settings.\n\n{error}",
                parent=root
            )
            return

        proposed_due = next_date.isoformat()

        confirmed = messagebox.askyesno(
            "Confirm Resume",
            (
                f"Resume '{name}'?\n\n"
                f"Next scheduled date: {proposed_due}\n\n"
                "Any pending occurrences before that date will be skipped.\n"
                "No transactions or balance changes are made by resuming.\n\n"
                "If the next date is today, it becomes eligible for "
                "processing at the next login."
            ),
            parent=root
        )

        if not confirmed:
            return

    try:
        with get_db() as conn:
            conn.execute("BEGIN IMMEDIATE")

            # Refuse to overwrite schedule state changed since this
            # confirmation was prepared.
            current = conn.execute(
                '''SELECT name, schedule_kind, is_active,
                          next_due_date, monthly_charge_days,
                          schedule_start_date
                   FROM recurring_transactions
                   WHERE id = ? AND user_id = ?''',
                (rec_id, user_id)
            ).fetchone()

            if current != row:
                raise ValueError(
                    "The schedule changed while this dialog was open. "
                    "Please refresh and try again."
                )

            conn.execute(
                '''UPDATE recurring_transactions
                   SET is_active = ?, next_due_date = ?
                   WHERE id = ? AND user_id = ?''',
                (new_status, proposed_due, rec_id, user_id)
            )
            conn.commit()

    except (sqlite3.Error, ValueError) as error:
        messagebox.showerror(
            "Could Not Update Schedule",
            str(error),
            parent=root
        )
        return

    refresh_screen()


def delete_recurring(user_id, rec_id):
    """
    Deletes an ordinary recurring rule, or a subscription and its rule.

    Past transactions and account balances remain unchanged.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT name, schedule_kind
               FROM recurring_transactions
               WHERE id = ? AND user_id = ?''',
            (rec_id, user_id)
        )
        rule = cursor.fetchone()

        cursor.execute(
            '''SELECT id
               FROM subscriptions
               WHERE recurring_rule_id = ? AND user_id = ?''',
            (rec_id, user_id)
        )
        subscription = cursor.fetchone()

    if rule is None:
        messagebox.showinfo(
            "Not Found",
            "This recurring schedule no longer exists.",
            parent=root
        )
        show_recurring_transactions(user_id)
        return

    name, schedule_kind = rule

    if schedule_kind == "subscription":
        if subscription is None:
            messagebox.showerror(
                "Invalid Subscription Link",
                (
                    "This subscription schedule has no linked subscription "
                    "record. Nothing was deleted.\n\n"
                    "Please resolve the broken link before continuing."
                ),
                parent=root
            )
            return

        confirmation_text = (
            f"Delete subscription schedule '{name}'?\n\n"
            "The linked subscription will also be removed from "
            "the Subscriptions screen.\n\n"
            "Past transactions and account balances will not change.\n"
            "Past expenses remain in Transaction History."
        )

    elif schedule_kind == "recurring":
        if subscription is not None:
            messagebox.showerror(
                "Invalid Schedule Link",
                (
                    "This ordinary recurring rule is unexpectedly linked "
                    "to a subscription. Nothing was deleted."
                ),
                parent=root
            )
            return

        confirmation_text = (
            f"Delete recurring schedule '{name}'?\n\n"
            "Past transactions and account balances will not change."
        )

    else:
        messagebox.showerror(
            "Invalid Schedule",
            "The schedule type is not recognised. Nothing was deleted.",
            parent=root
        )
        return

    if not messagebox.askyesno(
        "Confirm Delete",
        confirmation_text,
        parent=root
    ):
        return

    try:
        if schedule_kind == "subscription":
            delete_subscription_and_schedule(
                user_id,
                subscription[0]
            )
        else:
            with get_db() as conn:
                conn.execute(
                    '''DELETE FROM recurring_transactions
                       WHERE id = ? AND user_id = ?
                         AND schedule_kind = 'recurring' ''',
                    (rec_id, user_id)
                )
                conn.commit()

    except (sqlite3.Error, ValueError) as error:
        messagebox.showerror(
            "Deletion Failed",
            str(error),
            parent=root
        )
        return

    show_recurring_transactions(user_id)

# ============================================================
# EXPORT TRANSACTIONS TO CSV
# ============================================================
# Exports all transactions for the logged-in user
# into a .csv file that can be opened in Excel or
# Google Sheets.
#
# Steps:
#   1. Ask user where to save the file using a
#      file dialog box (like a normal Save As window)
#   2. Fetch all transactions from database
#   3. Write them into the CSV file using pandas
#   4. Show success or error message
#
# filedialog.asksaveasfilename() opens a native Windows
# Save As dialog — user picks folder and filename.
# ============================================================

def export_transactions_to_csv(user_id):
    from tkinter import filedialog

    file_path = filedialog.asksaveasfilename(
        title="Save Transactions As",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile="transactions_export"
    )

    if not file_path:
        return

    with get_db() as conn:
        cursor = conn.cursor()
        # Updated query to include new fields
        

        # Fetch tags for each transaction separately
        # We need transaction id to get tags so run
        # a second query to get ids alongside data
        cursor.execute(
            '''SELECT
                t.id,
                t.date,
                t.time,
                t.type,
                t.category,
                t.amount,
                a.account_name,
                t.notes,
                t.reference,
                t.necessity
               FROM transactions t
               JOIN accounts a ON t.account_id = a.id
               WHERE t.user_id = ?
               ORDER BY t.date DESC, t.time DESC''',
            (user_id,)
        )
        full_rows = cursor.fetchall()

        # Build tags lookup dictionary
        tx_tags = {}
        for row in full_rows:
            tx_id = row[0]
            cursor.execute(
                "SELECT tag_name FROM tags WHERE transaction_id = ?",
                (tx_id,)
            )
            tag_list = [r[0] for r in cursor.fetchall()]
            tx_tags[tx_id] = ", ".join(tag_list) if tag_list else ""

    if not full_rows:
        messagebox.showinfo(
            "No Data",
            "No transactions found to export."
        )
        return

    # Build rows for DataFrame including tags
    export_data = []
    for row in full_rows:
        (tx_id, date, time, tx_type, category,
         amount, account_name, notes,
         reference, necessity) = row

        export_data.append({
            "Date":              date,
            "Time":              time,
            "Type":              tx_type,
            "Category":          category,
            "Amount":            amount,
            "Signed Amount":     amount if tx_type == "income" else -amount,
            "Account":           account_name,
            "Notes":             notes or "",
            "Reference":         reference or "",
            "Necessity":         necessity or "unset",
            "Tags":              tx_tags.get(tx_id, "")
        })

    df = pd.DataFrame(export_data)

    try:
        df.to_csv(file_path, index=False)
        messagebox.showinfo(
            "✅ Export Successful",
            f"Transactions exported successfully!\n\nSaved to:\n{file_path}"
        )
    except Exception as e:
        messagebox.showerror(
            "❌ Export Failed",
            f"Could not save file.\n\nError: {str(e)}"
        )


# ============================================================
# EDIT TRANSACTION
# ============================================================
# Allows user to correct a transaction's category, amount,
# type and account after it was already saved.
# When edited:
#   - Old amount is reversed on the old account balance
#   - New amount is applied to the new account balance
# ============================================================

def show_edit_transaction(user_id, transaction_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="✏️ Edit Transaction",
             font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)

    # Load existing transaction data to pre-fill the form
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT type, category, amount, account_id,
                      notes, reference, necessity
               FROM transactions WHERE id = ? AND user_id = ?''',
            (transaction_id, user_id)
        )
        tx = cursor.fetchone()

        # Fetch existing tags for this transaction
        cursor.execute(
            "SELECT tag_name FROM tags WHERE transaction_id = ?",
            (transaction_id,)
        )
        existing_tags = ", ".join(
            [row[0] for row in cursor.fetchall()]
        )

    if not tx:
        tk.Label(body, text="❌ Transaction not found.",
                 font=("Segoe UI", 10),
                 bg="#f0f4f8", fg="red").pack(padx=20, pady=10)
        make_button(body, "← Back",
                    lambda: show_transaction_history(user_id),
                    color="#718096").pack(pady=10)
        return

    # Unpack existing values
    (old_type, old_category, old_amount,
     old_account_id, old_notes,
     old_reference, old_necessity) = tx

    # Fallback for rows created before new columns existed
    old_notes     = old_notes     or ""
    old_reference = old_reference or ""
    old_necessity = old_necessity or "unset"

    # --- Transaction type ---
    tk.Label(body, text="Transaction Type:",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w", padx=20, pady=(10, 0))
    type_var = tk.StringVar(value=old_type)
    type_frame = tk.Frame(body, bg="#f0f4f8")
    type_frame.pack(anchor="w", padx=20, pady=(2, 10))
    tk.Radiobutton(type_frame, text="Income",
                   variable=type_var, value="income",
                   bg="#f0f4f8", font=("Segoe UI", 10),
                   command=lambda: refresh_categories()).pack(side="left")
    tk.Radiobutton(type_frame, text="Expense",
                   variable=type_var, value="expense",
                   bg="#f0f4f8", font=("Segoe UI", 10),
                   command=lambda: refresh_categories()).pack(
                   side="left", padx=10)

    # --- Category dropdown ---
    tk.Label(body, text="Category:",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w", padx=20)
    category_var = tk.StringVar(value=old_category)
    category_dd = ttk.Combobox(body, textvariable=category_var,
                               state="readonly", width=28)
    category_dd.pack(anchor="w", padx=20, pady=(2, 10))

    def refresh_categories():
        tx_type = type_var.get()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM categories WHERE user_id = ? AND type = ?",
                (user_id, tx_type)
            )
            cats = [row[0] for row in cursor.fetchall()]
        category_dd["values"] = cats
        if cats:
            category_var.set(cats[0])
        else:
            category_var.set("")

    refresh_categories()
    # Restore old category after refresh
    category_var.set(old_category)

    # --- Amount ---
    sym = get_currency(user_id)
    tk.Label(body, text=f"Amount ({sym}):",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w", padx=20)
    amount_entry = make_entry(body)
    amount_entry.insert(0, str(old_amount))
    amount_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # --- Account dropdown ---
    tk.Label(body, text="Account:",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w", padx=20)
    accounts = view_accounts(user_id)
    account_options = {
        f"{acc[1]} | Balance: {sym}{acc[2]:,.2f}": acc[0]
        for acc in accounts
    }
    old_account_label = next(
        (k for k, v in account_options.items()
         if v == old_account_id), ""
    )
    account_var = tk.StringVar(value=old_account_label)
    account_dd = ttk.Combobox(body, textvariable=account_var,
                              values=list(account_options.keys()),
                              state="readonly", width=35)
    account_dd.pack(anchor="w", padx=20, pady=(2, 10))

    # --- Notes ---
    tk.Label(body, text="Notes / Remarks (optional):",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w", padx=20)
    notes_entry = tk.Text(body, height=3, width=45,
                          font=("Segoe UI", 10),
                          relief="solid", bd=1, wrap="word")
    # Pre-fill with existing notes
    notes_entry.insert("1.0", old_notes)
    notes_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # --- Reference ---
    tk.Label(body, text="Reference / Receipt No. (optional):",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w", padx=20)
    reference_entry = make_entry(body, width=35)
    # Pre-fill with existing reference
    reference_entry.insert(0, old_reference)
    reference_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # --- Tags ---
    tk.Label(body, text="Tags (optional):",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w", padx=20)
    tk.Label(body,
             text="Comma separated e.g. work, personal, emergency",
             font=("Segoe UI", 8, "italic"),
             bg="#f0f4f8", fg="#718096").pack(anchor="w", padx=20)
    tags_entry = make_entry(body, width=35)
    # Pre-fill with existing tags
    tags_entry.insert(0, existing_tags)
    tags_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # --- Necessity ---
    tk.Label(body, text="Necessity (for expenses only):",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w", padx=20)
    necessity_var = tk.StringVar(value=old_necessity)
    necessity_frame = tk.Frame(body, bg="#f0f4f8")
    necessity_frame.pack(anchor="w", padx=20, pady=(2, 10))
    tk.Radiobutton(necessity_frame, text="✅ Need",
                   variable=necessity_var, value="need",
                   bg="#f0f4f8",
                   font=("Segoe UI", 10)).pack(side="left")
    tk.Radiobutton(necessity_frame, text="🛍️ Want",
                   variable=necessity_var, value="want",
                   bg="#f0f4f8",
                   font=("Segoe UI", 10)).pack(side="left", padx=10)
    tk.Radiobutton(necessity_frame, text="— Not set",
                   variable=necessity_var, value="unset",
                   bg="#f0f4f8",
                   font=("Segoe UI", 10)).pack(side="left")

    msg_label = tk.Label(body, text="",
                         font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red", wraplength=400)
    msg_label.pack(padx=20, pady=5)

    def on_save():
        new_type     = type_var.get()
        new_category = category_var.get()
        new_account  = account_options.get(account_var.get())
        new_notes     = notes_entry.get("1.0", tk.END).strip()
        new_reference = reference_entry.get().strip()
        new_tags_raw  = tags_entry.get().strip()
        new_necessity = (
            "unset" if new_type == "income"
            else necessity_var.get()
        )

        if not new_category:
            msg_label.config(
                text="❌ Please select a category.", fg="red")
            return

        if not new_account:
            msg_label.config(
                text="❌ Please select an account.", fg="red")
            return

        try:
            new_amount = float(amount_entry.get().strip())
        except ValueError:
            msg_label.config(
                text="❌ Amount must be a valid number.", fg="red")
            return

        if new_amount <= 0:
            msg_label.config(
                text="❌ Amount must be greater than 0.", fg="red")
            return

        with get_db() as conn:
            cursor = conn.cursor()

            # Step 1 — Reverse old balance effect
            if old_type == "income":
                cursor.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                    (old_amount, old_account_id)
                )
            else:
                cursor.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                    (old_amount, old_account_id)
                )

            # Step 2 — Apply new balance effect
            if new_type == "income":
                cursor.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                    (new_amount, new_account)
                )
            else:
                cursor.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                    (new_amount, new_account)
                )

            # Step 3 — Update transaction record
            # including all new fields
            cursor.execute(
                '''UPDATE transactions
                   SET type = ?, category = ?, amount = ?,
                       account_id = ?, notes = ?,
                       reference = ?, necessity = ?
                   WHERE id = ? AND user_id = ?''',
                (new_type, new_category, new_amount,
                 new_account, new_notes,
                 new_reference, new_necessity,
                 transaction_id, user_id)
            )

            # Step 4 — Update tags
            # Delete old tags first then insert new ones
            cursor.execute(
                "DELETE FROM tags WHERE transaction_id = ?",
                (transaction_id,)
            )
            if new_tags_raw:
                MAX_TAG_LENGTH = 30   # Each tag max 30 characters
                MAX_TAGS = 10         # Max 10 tags per transaction

                # Build tag list — skip any tag over 30 characters
                tag_list = [
                    t.strip()
                    for t in new_tags_raw.split(",")
                    if t.strip() and len(t.strip()) <= MAX_TAG_LENGTH
                ]

                # Only keep the first 10 tags
                tag_list = tag_list[:MAX_TAGS]

                for tag in tag_list:
                    cursor.execute(
                        '''INSERT INTO tags
                           (transaction_id, user_id, tag_name)
                           VALUES (?, ?, ?)''',
                        (transaction_id, user_id, tag)
                    )

            conn.commit()

        msg_label.config(
            text="✅ Transaction updated successfully!", fg="green")
        root.after(1000, lambda: show_transaction_history(user_id))

    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=10, padx=20, anchor="w")
    make_button(btn_frame, "✅ Save Changes",
                on_save, color="#38a169").pack(side="left", padx=5)
    make_button(btn_frame, "← Back",
                lambda: show_transaction_history(user_id),
                color="#718096").pack(side="left", padx=5)



def update_transaction(transaction_id, user_id,
                       old_type, old_amount, old_account_id,
                       new_type, new_category, new_amount, new_account_id):
    """
    Updates a transaction and adjusts account balances correctly.

    Step 1: Reverse the OLD transaction's effect on old account
            e.g. if it was income +100, subtract 100 back
    Step 2: Apply the NEW transaction's effect on new account
            e.g. if new type is expense -50, subtract 50
    Step 3: Update the transaction record in the database
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Step 1 — Reverse old transaction effect on old account
        if old_type == "income":
            cursor.execute(
                "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                (old_amount, old_account_id)
            )
        else:
            cursor.execute(
                "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                (old_amount, old_account_id)
            )

        # Step 2 — Apply new transaction effect on new account
        if new_type == "income":
            cursor.execute(
                "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                (new_amount, new_account_id)
            )
        else:
            cursor.execute(
                "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                (new_amount, new_account_id)
            )

        # Step 3 — Update the transaction record itself
        cursor.execute(
            '''UPDATE transactions
               SET type = ?, category = ?, amount = ?, account_id = ?
               WHERE id = ? AND user_id = ?''',
            (new_type, new_category, new_amount, new_account_id,
             transaction_id, user_id)
        )
        conn.commit()

def show_add_subscription(user_id):
    import math

    clear_window()
    sym = get_currency(user_id)

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(
        header,
        text="🔄 Add Subscription",
        font=("Segoe UI", 16, "bold"),
        fg="white",
        bg="#2b6cb0"
    ).pack()

    # Reserve space for buttons before creating the scrollable body.
    btn_bar = tk.Frame(root, bg="#f0f4f8", pady=10)
    btn_bar.pack(side="bottom", fill="x", padx=10)

    body = make_scrollable_frame(root)

    def field_label(text):
        tk.Label(
            body,
            text=text,
            font=("Segoe UI", 10, "bold"),
            bg="#f0f4f8"
        ).pack(anchor="w", padx=20, pady=(8, 2))

    field_label("Subscription Name:")
    name_entry = make_entry(body, width=35)
    name_entry.pack(anchor="w", padx=20)

    field_label("Expense Category:")
    cat_row = tk.Frame(body, bg="#f0f4f8")
    cat_row.pack(anchor="w", padx=20)

    categories = get_expense_categories(user_id)
    category_var = tk.StringVar(
        value=categories[0] if categories else ""
    )
    category_dd = ttk.Combobox(
        cat_row,
        textvariable=category_var,
        values=categories,
        state="readonly",
        width=25
    )
    category_dd.pack(side="left")

    make_button(
        cat_row,
        "+ Add Category",
        lambda: open_add_category_popup(
            user_id, "expense", category_dd, category_var
        ),
        color="#3182ce",
        width=14
    ).pack(side="left", padx=6)

    field_label("Monthly Billing Days (for example 1,15):")
    dates_entry = make_entry(body)
    dates_entry.pack(anchor="w", padx=20)

    tk.Label(
        body,
        text="Days that do not exist in a month are skipped.",
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8",
        fg="#718096"
    ).pack(anchor="w", padx=20)

    field_label("Start Recording From (YYYY-MM-DD):")
    start_entry = make_entry(body)
    start_entry.insert(0, datetime.today().strftime("%Y-%m-%d"))
    start_entry.pack(anchor="w", padx=20)

    tk.Label(
        body,
        text=(
            "A past start date records missed billing occurrences. "
            "This can reduce your in-app account balance."
        ),
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8",
        fg="#718096",
        wraplength=500,
        justify="left"
    ).pack(anchor="w", padx=20)

    field_label(f"Amount Per Occurrence ({sym}):")
    amount_entry = make_entry(body)
    amount_entry.pack(anchor="w", padx=20)

    field_label("Notes (optional):")
    notes_entry = make_entry(body, width=40)
    notes_entry.pack(anchor="w", padx=20)

    field_label("Necessity:")
    necessity_var = tk.StringVar(value="unset")
    necessity_frame = tk.Frame(body, bg="#f0f4f8")
    necessity_frame.pack(anchor="w", padx=20)

    for label, value in [
        ("Need", "need"),
        ("Want", "want"),
        ("Not set", "unset")
    ]:
        tk.Radiobutton(
            necessity_frame,
            text=label,
            variable=necessity_var,
            value=value,
            bg="#f0f4f8",
            font=("Segoe UI", 10)
        ).pack(side="left", padx=(0, 10))

    field_label("Account:")
    accounts = view_accounts(user_id)

    # Include the ID in each label to avoid ambiguous account labels.
    account_options = {
        f"{acc[1]} (ID {acc[0]}) | {sym}{acc[2]:,.2f}": acc[0]
        for acc in accounts
    }
    account_var = tk.StringVar(
        value=next(iter(account_options), "")
    )
    account_dd = ttk.Combobox(
        body,
        textvariable=account_var,
        values=list(account_options),
        state="readonly",
        width=45
    )
    account_dd.pack(anchor="w", padx=20)

    msg_label = tk.Label(
        body,
        text="",
        font=("Segoe UI", 10),
        bg="#f0f4f8",
        fg="red",
        wraplength=500,
        justify="left"
    )
    msg_label.pack(anchor="w", padx=20, pady=12)

    saved = False

    def on_submit():
        nonlocal saved

        if saved:
            return

        name = name_entry.get().strip()
        category = category_var.get().strip()
        account_id = account_options.get(account_var.get())
        notes = notes_entry.get().strip()
        necessity = necessity_var.get()

        if not name:
            msg_label.config(
                text="Please enter a subscription name.", fg="red"
            )
            return

        if not category:
            msg_label.config(
                text="Please select or add an expense category.", fg="red"
            )
            return

        if account_id is None:
            msg_label.config(
                text="Please select an account.", fg="red"
            )
            return

        try:
            amount = float(amount_entry.get().strip())
            if not math.isfinite(amount) or amount <= 0:
                raise ValueError
        except (ValueError, OverflowError):
            msg_label.config(
                text="Amount must be a finite number greater than zero.",
                fg="red"
            )
            return

        if necessity not in ("need", "want", "unset"):
            msg_label.config(text="Invalid necessity selection.", fg="red")
            return

        try:
            start_text = start_entry.get().strip()
            start_date = datetime.strptime(
                start_text, "%Y-%m-%d"
            ).date()

            if start_date.isoformat() != start_text:
                raise ValueError

            # The helper validates the full billing-day input.
            first_due = next_subscription_billing_date(
                dates_entry.get().strip(),
                start_date,
                inclusive=True
            )

            billing_days = ",".join(
                str(day)
                for day in sorted({
                    int(part.strip())
                    for part in dates_entry.get().split(",")
                })
            )
        except ValueError:
            msg_label.config(
                text=(
                    "Use YYYY-MM-DD for the start date and billing days "
                    "from 1 to 31 separated by commas."
                ),
                fg="red"
            )
            return

        today = datetime.today().date()

        # Count and preview the occurrences that would be recorded now.
        due_count = 0
        preview_due = first_due

        while preview_due <= today:
            due_count += 1
            preview_due = next_subscription_billing_date(
                billing_days, preview_due, inclusive=False
            )

        if due_count:
            confirmed = messagebox.askyesno(
                "Confirm Scheduled Expenses",
                (
                    f"This new schedule will record {due_count} "
                    f"expense(s), totaling {sym}{amount * due_count:,.2f}, "
                    f"on the selected account.\n\n"
                    "This only changes records and balances inside this app; "
                    "it does not pay the provider.\n\n"
                    "Do not continue if these payments are already recorded "
                    "manually or through another recurring schedule.\n\n"
                    "Continue?"
                ),
                parent=root
            )
            if not confirmed:
                return

        try:
            with get_db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT COUNT(*) FROM subscriptions WHERE user_id = ?",
                    (user_id,)
                )
                if cursor.fetchone()[0] >= 5:
                    msg_label.config(
                        text="Maximum 5 subscriptions reached.", fg="red"
                    )
                    return

                cursor.execute(
                    '''SELECT 1 FROM subscriptions
                       WHERE user_id = ?
                         AND subscription_name = ? COLLATE NOCASE''',
                    (user_id, name)
                )
                if cursor.fetchone():
                    msg_label.config(
                        text="A subscription with this name already exists.",
                        fg="red"
                    )
                    return

                # Recheck ownership and category existence at save time.
                cursor.execute(
                    "SELECT 1 FROM accounts WHERE id = ? AND user_id = ?",
                    (account_id, user_id)
                )
                if not cursor.fetchone():
                    msg_label.config(
                        text="The selected account no longer exists.",
                        fg="red"
                    )
                    return

                cursor.execute(
                    '''SELECT 1 FROM categories
                       WHERE user_id = ? AND type = 'expense' AND name = ?''',
                    (user_id, category)
                )
                if not cursor.fetchone():
                    msg_label.config(
                        text="Please select an existing expense category.",
                        fg="red"
                    )
                    return

                cursor.execute(
                    '''INSERT INTO recurring_transactions
                       (user_id, account_id, type, category, amount,
                        frequency, next_due_date, name, is_active,
                        notes, tags, necessity, schedule_kind,
                        monthly_charge_days, schedule_start_date)
                       VALUES (?, ?, 'expense', ?, ?, 'Monthly', ?, ?, 1,
                               ?, '', ?, 'subscription', ?, ?)''',
                    (
                        user_id,
                        account_id,
                        category,
                        amount,
                        first_due.isoformat(),
                        name,
                        notes,
                        necessity,
                        billing_days,
                        start_date.isoformat()
                    )
                )
                rule_id = cursor.lastrowid

                cursor.execute(
                    '''INSERT INTO subscriptions
                       (user_id, subscription_name, category, amount,
                        charge_dates, notes, necessity, recurring_rule_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        user_id,
                        name,
                        category,
                        amount,
                        billing_days,
                        notes,
                        necessity,
                        rule_id
                    )
                )
                conn.commit()

        except sqlite3.Error as error:
            msg_label.config(
                text=f"Could not save the subscription: {error}",
                fg="red"
            )
            return

        # Saving succeeded. Never let a processing failure cause the
        # user to accidentally submit the same subscription again.
        saved = True
        save_button.config(state="disabled")

        try:
            # This processes ALL due rules for this user, not only the new one.
            process_recurring_transactions(user_id)
        except (sqlite3.Error, ValueError, OverflowError) as error:
            messagebox.showwarning(
                "Subscription Saved — Processing Incomplete",
                (
                    "The subscription and its schedule were saved.\n"
                    "Do not add it again.\n\n"
                    "Due-schedule processing did not complete. "
                    "Review the error before retrying processing:\n\n"
                    f"{error}"
                ),
                parent=root
            )
        else:
            messagebox.showinfo(
                "Subscription Saved",
                (
                    "The subscription and shared schedule were saved.\n"
                    "Due schedules have been checked."
                ),
                parent=root
            )

        show_subscription_list(user_id)

    save_button = make_button(
        btn_bar,
        "Save Subscription",
        on_submit,
        color="#38a169",
        width=18
    )
    save_button.pack(side="left", padx=4)

    make_button(
        btn_bar,
        "View Subscriptions",
        lambda: show_subscription_list(user_id),
        color="#3182ce",
        width=18
    ).pack(side="left", padx=4)

    make_button(
        btn_bar,
        "Back",
        lambda: show_main_menu(current_user),
        color="#718096",
        width=10
    ).pack(side="left", padx=4)

def link_existing_subscription_schedule(
    user_id, sub_id, account_id, start_date_text
):
    """
    Creates a shared schedule for an existing unlinked subscription.

    Does not generate expenses or change account balances.
    The caller must obtain explicit user confirmation before calling.

    Returns:
        (new_rule_id, first_due_date)
    """
    import math

    try:
        start_date = datetime.strptime(
            start_date_text.strip(), "%Y-%m-%d"
        ).date()

        if start_date.isoformat() != start_date_text.strip():
            raise ValueError
    except (AttributeError, TypeError, ValueError):
        raise ValueError(
            "Use YYYY-MM-DD for the start date."
        ) from None

    if account_id is None:
        raise ValueError("Please select an account.")

    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()

        cursor.execute(
            '''SELECT subscription_name, category, amount,
                      charge_dates, notes, necessity, recurring_rule_id
               FROM subscriptions
               WHERE id = ? AND user_id = ?''',
            (sub_id, user_id)
        )
        subscription = cursor.fetchone()

        if subscription is None:
            raise ValueError("The subscription no longer exists.")

        (
            name, category, stored_amount, charge_days,
            notes, necessity, existing_rule_id
        ) = subscription

        if existing_rule_id is not None:
            raise ValueError(
                "This subscription already has a schedule. "
                "Refresh the list instead of setting it up again."
            )

        if not name or not name.strip():
            raise ValueError(
                "Edit the subscription details and enter a name first."
            )

        try:
            amount = float(stored_amount)
            if not math.isfinite(amount) or amount <= 0:
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            raise ValueError(
                "Edit the subscription amount first. "
                "It must be a finite number greater than zero."
            ) from None

        cursor.execute(
            '''SELECT 1 FROM accounts
               WHERE id = ? AND user_id = ?''',
            (account_id, user_id)
        )
        if cursor.fetchone() is None:
            raise ValueError(
                "The selected account does not belong to this user "
                "or no longer exists."
            )

        cursor.execute(
            '''SELECT 1 FROM categories
               WHERE user_id = ? AND type = 'expense' AND name = ?''',
            (user_id, category)
        )
        if cursor.fetchone() is None:
            raise ValueError(
                "Edit the subscription and select an existing "
                "expense category before setting up its schedule."
            )

        first_due = next_subscription_billing_date(
            charge_days,
            start_date,
            inclusive=True
        )

        normalised_days = ",".join(
            str(day)
            for day in sorted({
                int(part.strip()) for part in charge_days.split(",")
            })
        )

        if necessity not in ("need", "want", "unset"):
            necessity = "unset"

        cursor.execute(
            '''INSERT INTO recurring_transactions
               (user_id, account_id, type, category, amount,
                frequency, next_due_date, name, is_active,
                notes, tags, necessity, schedule_kind,
                monthly_charge_days, schedule_start_date)
               VALUES (?, ?, 'expense', ?, ?, 'Monthly', ?, ?, 1,
                       ?, '', ?, 'subscription', ?, ?)''',
            (
                user_id,
                account_id,
                category,
                amount,
                first_due.isoformat(),
                name,
                notes or "",
                necessity,
                normalised_days,
                start_date.isoformat()
            )
        )
        rule_id = cursor.lastrowid

        cursor.execute(
            '''UPDATE subscriptions
               SET recurring_rule_id = ?,
                   charge_dates = ?,
                   necessity = ?
               WHERE id = ? AND user_id = ?
                 AND recurring_rule_id IS NULL''',
            (
                rule_id,
                normalised_days,
                necessity,
                sub_id,
                user_id
            )
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "The subscription changed during setup. "
                "Nothing was saved; refresh and try again."
            )

        conn.commit()

    return rule_id, first_due.isoformat()

def show_subscription_schedule_setup(user_id, sub_id):
    """
    Sets up a shared schedule for an older, unlinked subscription.

    Saving creates the schedule but does not process expenses.
    Due occurrences are processed at the next login.
    """
    with get_db() as conn:
        subscription = conn.execute(
            '''SELECT subscription_name, category, amount,
                      charge_dates, recurring_rule_id
               FROM subscriptions
               WHERE id = ? AND user_id = ?''',
            (sub_id, user_id)
        ).fetchone()

    if subscription is None:
        messagebox.showerror(
            "Not Found", "Subscription no longer exists.", parent=root
        )
        return

    name, category, amount, charge_days, linked_rule_id = subscription

    if linked_rule_id is not None:
        messagebox.showinfo(
            "Already Set Up",
            "This subscription already has a shared schedule.",
            parent=root
        )
        show_subscription_list(user_id)
        return

    clear_window()
    sym = get_currency(user_id)

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")

    tk.Label(
        header,
        text="Set Up Subscription Schedule",
        font=("Segoe UI", 16, "bold"),
        bg="#2b6cb0",
        fg="white"
    ).pack()

    btn_bar = tk.Frame(root, bg="#f0f4f8", pady=10)
    btn_bar.pack(side="bottom", fill="x", padx=20)

    body = make_scrollable_frame(root)

    tk.Label(
        body,
        text=(
            f"Subscription: {name}\n"
            f"Category: {category}\n"
            f"Amount per occurrence: {sym}{amount:,.2f}\n"
            f"Monthly billing days: {charge_days}"
        ),
        font=("Segoe UI", 10),
        bg="#f0f4f8",
        fg="#2d3748",
        justify="left",
        wraplength=500
    ).pack(anchor="w", padx=20, pady=15)

    tk.Label(
        body,
        text=(
            "Choose when this app should begin recording expenses—not "
            "necessarily when the subscription originally began.\n\n"
            "A past start date can create catch-up expenses at the next login. "
            "Do not include dates whose payments are already recorded manually "
            "or through another recurring schedule.\n\n"
            "Days that do not exist in a month are skipped."
        ),
        font=("Segoe UI", 9),
        bg="#f0f4f8",
        fg="#718096",
        justify="left",
        wraplength=500
    ).pack(anchor="w", padx=20, pady=(0, 12))

    tk.Label(
        body,
        text="Account:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    accounts = view_accounts(user_id)
    account_options = {
        f"{acc[1]} (ID {acc[0]}) | {sym}{acc[2]:,.2f}": acc[0]
        for acc in accounts
    }

    # Require an explicit choice rather than guessing the account.
    account_var = tk.StringVar(value="")
    account_dd = ttk.Combobox(
        body,
        textvariable=account_var,
        values=list(account_options),
        state="readonly",
        width=45
    )
    account_dd.pack(anchor="w", padx=20, pady=(3, 12))

    tk.Label(
        body,
        text="Start Recording From (YYYY-MM-DD):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    start_entry = make_entry(body, width=25)
    start_entry.insert(0, datetime.today().strftime("%Y-%m-%d"))
    start_entry.pack(anchor="w", padx=20, pady=(3, 12))

    checked_var = tk.BooleanVar(value=False)

    tk.Checkbutton(
        body,
        text=(
            "I checked that this payment is not already scheduled elsewhere "
            "and that the selected dates will not duplicate recorded expenses."
        ),
        variable=checked_var,
        bg="#f0f4f8",
        font=("Segoe UI", 9),
        wraplength=500,
        justify="left",
        anchor="w"
    ).pack(anchor="w", padx=20, pady=8)

    msg_label = tk.Label(
        body,
        text="",
        font=("Segoe UI", 10),
        bg="#f0f4f8",
        fg="red",
        wraplength=500,
        justify="left"
    )
    msg_label.pack(anchor="w", padx=20, pady=10)

    saved = False

    def on_save():
        nonlocal saved
        import math

        if saved:
            return

        account_id = account_options.get(account_var.get())

        if account_id is None:
            msg_label.config(text="Please select an account.")
            return

        if not checked_var.get():
            msg_label.config(
                text="Please check for duplicate schedules and expenses first."
            )
            return

        try:
            start_text = start_entry.get().strip()
            start_date = datetime.strptime(
                start_text, "%Y-%m-%d"
            ).date()

            if start_date.isoformat() != start_text:
                raise ValueError("Use YYYY-MM-DD for the start date.")

            preview_amount = float(amount)
            if not math.isfinite(preview_amount) or preview_amount <= 0:
                raise ValueError(
                    "Edit the subscription amount before setting up its schedule."
                )

            first_due = next_subscription_billing_date(
                charge_days, start_date, inclusive=True
            )

            today = datetime.today().date()
            due_count = 0
            candidate = first_due

            while candidate <= today:
                due_count += 1
                candidate = next_subscription_billing_date(
                    charge_days, candidate, inclusive=False
                )

        except (TypeError, ValueError, OverflowError) as error:
            msg_label.config(text=f"Check the schedule settings: {error}")
            return

        confirmed = messagebox.askyesno(
            "Confirm Schedule Setup",
            (
                f"Subscription: {name}\n"
                f"Account: {account_var.get()}\n"
                f"Start recording from: {start_text}\n"
                f"First scheduled date: {first_due.isoformat()}\n\n"
                f"Occurrences due as of today: {due_count}\n"
                f"Total due as of today: "
                f"{sym}{preview_amount * due_count:,.2f}\n\n"
                "Saving activates the schedule but does not record expenses "
                "immediately. Processing happens at the next login. "
                "Additional dates may become due before then.\n\n"
                "This records expenses inside the app; it does not pay "
                "the provider.\n\nContinue?"
            ),
            parent=root
        )

        if not confirmed:
            return

        try:
            # Refuse to use an outdated preview if the subscription
            # details changed while this screen was open.
            with get_db() as conn:
                current = conn.execute(
                    '''SELECT subscription_name, category, amount,
                              charge_dates, recurring_rule_id
                       FROM subscriptions
                       WHERE id = ? AND user_id = ?''',
                    (sub_id, user_id)
                ).fetchone()

            if current != subscription:
                raise ValueError(
                    "The subscription changed while this screen was open. "
                    "Return to the list and reopen setup."
                )

            link_existing_subscription_schedule(
                user_id, sub_id, account_id, start_text
            )

        except (sqlite3.Error, ValueError, OverflowError) as error:
            msg_label.config(text=f"Could not set up schedule: {error}")
            return

        saved = True
        save_button.config(state="disabled")

        messagebox.showinfo(
            "Schedule Activated",
            (
                "The subscription is now linked to a shared schedule.\n\n"
                "No expenses were generated by saving setup. "
                "Due occurrences will be checked at the next login."
            ),
            parent=root
        )
        show_subscription_list(user_id)

    save_button = make_button(
        btn_bar,
        "Activate Schedule",
        on_save,
        color="#38a169",
        width=18
    )
    save_button.pack(side="left", padx=5)

    make_button(
        btn_bar,
        "Back",
        lambda: show_subscription_list(user_id),
        color="#718096",
        width=12
    ).pack(side="left", padx=5)

def show_subscription_list(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")

    tk.Label(
        header,
        text="📋 Subscription List",
        font=("Segoe UI", 16, "bold"),
        fg="white",
        bg="#2b6cb0"
    ).pack()

    # Reserve navigation space before adding the scrolling content.
    btn_bar = tk.Frame(root, bg="#f0f4f8", pady=10)
    btn_bar.pack(side="bottom", fill="x", padx=20)

    body = make_scrollable_frame(root)
    sym = get_currency(user_id)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT
                   s.id,
                   s.subscription_name,
                   s.category,
                   s.amount,
                   s.charge_dates,
                   s.notes,
                   s.necessity,
                   s.recurring_rule_id,
                   r.id,
                   r.name,
                   r.category,
                   r.amount,
                   r.monthly_charge_days,
                   r.notes,
                   r.necessity,
                   r.next_due_date,
                   r.schedule_start_date,
                   r.is_active,
                   r.type,
                   r.schedule_kind,
                   a.id,
                   a.account_name
               FROM subscriptions s
               LEFT JOIN recurring_transactions r
                 ON r.id = s.recurring_rule_id
                AND r.user_id = s.user_id
               LEFT JOIN accounts a
                 ON a.id = r.account_id
                AND a.user_id = s.user_id
               WHERE s.user_id = ?
               ORDER BY s.subscription_name COLLATE NOCASE, s.id''',
            (user_id,)
        )
        subscriptions = cursor.fetchall()

    if not subscriptions:
        tk.Label(
            body,
            text="No subscriptions yet.",
            font=("Segoe UI", 13, "bold"),
            bg="#f0f4f8",
            fg="#2d3748"
        ).pack(pady=(35, 5))

        tk.Label(
            body,
            text="Add a subscription to schedule expense recording at login.",
            font=("Segoe UI", 10),
            bg="#f0f4f8",
            fg="#718096",
            wraplength=500
        ).pack(padx=20)

    for sub in subscriptions:
        (
            sub_id,
            legacy_name,
            legacy_category,
            legacy_amount,
            legacy_days,
            legacy_notes,
            legacy_necessity,
            linked_rule_id,
            found_rule_id,
            rule_name,
            rule_category,
            rule_amount,
            rule_days,
            rule_notes,
            rule_necessity,
            next_due,
            start_date,
            is_active,
            rule_type,
            schedule_kind,
            found_account_id,
            account_name
        ) = sub

        is_unlinked = linked_rule_id is None

        # A link must point to this user's subscription expense rule
        # and a valid account before scheduling controls are offered.
        valid_link = (
            not is_unlinked
            and found_rule_id is not None
            and rule_type == "expense"
            and schedule_kind == "subscription"
            and found_account_id is not None
        )

        if valid_link:
            # The recurring rule is the authoritative source.
            name = rule_name
            category = rule_category
            amount = rule_amount
            billing_days = rule_days
            notes = rule_notes or ""
            necessity = rule_necessity or "unset"

            status_text = "Active" if is_active else "Paused"
            status_color = "#276749" if is_active else "#975a16"

        else:
            # Preserve visibility of older or broken records.
            name = legacy_name
            category = legacy_category
            amount = legacy_amount
            billing_days = legacy_days
            notes = legacy_notes or ""
            necessity = legacy_necessity or "unset"

            if is_unlinked:
                status_text = "Schedule setup required"
                status_color = "#975a16"
            else:
                status_text = "Schedule link needs attention"
                status_color = "#c53030"

        card = tk.Frame(body, bg="white", relief="solid", bd=1)
        card.pack(fill="x", padx=20, pady=8)

        tk.Label(
            card,
            text=f"🔄 {name}",
            font=("Segoe UI", 12, "bold"),
            bg="white",
            fg="#2d3748",
            wraplength=550,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(10, 2))

        tk.Label(
            card,
            text=status_text,
            font=("Segoe UI", 10, "bold"),
            bg="white",
            fg=status_color
        ).pack(anchor="w", padx=12, pady=(0, 6))

        tk.Label(
            card,
            text=(
                f"Category: {category}\n"
                f"Current amount per occurrence: {sym}{amount:,.2f}\n"
                f"Monthly billing days: {billing_days}"
            ),
            font=("Segoe UI", 10),
            bg="white",
            fg="#4a5568",
            justify="left",
            wraplength=550
        ).pack(anchor="w", padx=12)

        if valid_link:
            tk.Label(
                card,
                text=(
                    f"Account: {account_name}\n"
                    f"Start recording from: {start_date}\n"
                    f"Next scheduled date: {next_due}"
                ),
                font=("Segoe UI", 10),
                bg="white",
                fg="#4a5568",
                justify="left",
                wraplength=550
            ).pack(anchor="w", padx=12, pady=(4, 0))

            if is_active:
                explanation = (
                    "Due occurrences are checked at login. "
                    "This app records expenses; it does not pay the provider."
                )
            else:
                explanation = (
                    "No new occurrences are recorded while this schedule "
                    "is paused. Resume requires confirmation of the next date."
                )

        elif is_unlinked:
            explanation = (
                "This older subscription is not connected to the shared "
                "scheduler. Use Set Up Schedule to choose its account "
                "and recording start date. Check for existing duplicate "
                "schedules before activating it."
            )

        else:
            explanation = (
                "The linked rule is missing, has an unexpected type, "
                "or has no valid account. Scheduling controls are unavailable. "
                "Do not add a replacement without first checking the existing "
                "rule, because it may still be active."
            )

        tk.Label(
            card,
            text=explanation,
            font=("Segoe UI", 9, "italic"),
            bg="white",
            fg="#718096",
            wraplength=550,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(6, 4))

        if notes:
            tk.Label(
                card,
                text=f"📝 {notes}",
                font=("Segoe UI", 9, "italic"),
                bg="white",
                fg="#4a5568",
                wraplength=550,
                justify="left"
            ).pack(anchor="w", padx=12, pady=(0, 4))

        if necessity in ("need", "want"):
            tk.Label(
                card,
                text="Need" if necessity == "need" else "Want",
                font=("Segoe UI", 8, "bold"),
                bg="#c6f6d5" if necessity == "need" else "#e9d8fd",
                fg="#2d3748",
                padx=5,
                pady=2
            ).pack(anchor="w", padx=12, pady=(0, 6))

        # Put history on its own row to avoid overcrowding.
        history_row = tk.Frame(card, bg="white")
        history_row.pack(anchor="w", padx=8, pady=(2, 2))

        make_button(
            history_row,
            "View Payments",
            lambda sid=sub_id, sname=name: show_subscription_payments(
                user_id, sid, sname
            ),
            color="#805ad5",
            width=16
        ).pack(side="left", padx=3)

        action_row = tk.Frame(card, bg="white")
        action_row.pack(anchor="w", padx=8, pady=(2, 10))

        if valid_link:
            make_button(
                action_row,
                "Edit",
                lambda sid=sub_id: show_edit_subscription(user_id, sid),
                color="#3182ce",
                width=10
            ).pack(side="left", padx=3)

            make_button(
                action_row,
                "Pause" if is_active else "Resume",
                lambda rid=linked_rule_id, target=(0 if is_active else 1):
                    toggle_recurring(
                        user_id,
                        rid,
                        target,
                        on_complete=lambda: show_subscription_list(user_id)
                    ),
                color="#dd6b20" if is_active else "#38a169",
                width=10
            ).pack(side="left", padx=3)

        elif is_unlinked:
            make_button(
                action_row,
                "Set Up Schedule",
                lambda sid=sub_id: show_subscription_schedule_setup(
                    user_id, sid
                ),
                color="#38a169",
                width=16
            ).pack(side="left", padx=3)

            make_button(
                action_row,
                "Edit Details",
                lambda sid=sub_id: show_edit_subscription(user_id, sid),
                color="#3182ce",
                width=12
            ).pack(side="left", padx=3)

        make_button(
            action_row,
            "Delete",
            lambda sid=sub_id, sname=name: confirm_delete_subscription(
                user_id, sid, sname
            ),
            color="#e53e3e",
            width=10
        ).pack(side="left", padx=3)

    if len(subscriptions) < 5:
        make_button(
            btn_bar,
            "Add Subscription",
            lambda: show_add_subscription(user_id),
            color="#38a169",
            width=18
        ).pack(side="left", padx=5)
    else:
        tk.Label(
            body,
            text="Maximum 5 subscriptions reached.",
            font=("Segoe UI", 9),
            bg="#f0f4f8",
            fg="#c53030"
        ).pack(anchor="w", padx=20, pady=8)

    make_button(
        btn_bar,
        "Back to Menu",
        lambda: show_main_menu(current_user),
        color="#718096",
        width=18
    ).pack(side="left", padx=5)

def delete_subscription_and_schedule(user_id, sub_id):
    """
    Deletes a subscription and its linked recurring schedule together.

    Preserves:
    - Past transactions
    - Account balances
    - Processed-occurrence markers

    Returns True if the subscription existed, otherwise False.
    """
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()

        cursor.execute(
            '''SELECT recurring_rule_id
               FROM subscriptions
               WHERE id = ? AND user_id = ?''',
            (sub_id, user_id)
        )
        row = cursor.fetchone()

        if row is None:
            return False

        rule_id = row[0]

        # Check the link before deleting either record.
        if rule_id is not None:
            cursor.execute(
                '''SELECT user_id, schedule_kind
                   FROM recurring_transactions
                   WHERE id = ?''',
                (rule_id,)
            )
            rule = cursor.fetchone()

            # A missing rule can be cleaned up by removing its
            # dangling subscription record.
            # A conflicting existing rule must not be deleted.
            if rule is not None:
                owner_id, schedule_kind = rule

                if (
                    owner_id != user_id
                    or schedule_kind != "subscription"
                ):
                    raise ValueError(
                        "The subscription has an invalid schedule link. "
                        "Nothing was deleted."
                    )

        # Remove the subscription first, then its schedule.
        cursor.execute(
            '''DELETE FROM subscriptions
               WHERE id = ? AND user_id = ?''',
            (sub_id, user_id)
        )

        if rule_id is not None:
            cursor.execute(
                '''DELETE FROM recurring_transactions
                   WHERE id = ? AND user_id = ?
                     AND schedule_kind = 'subscription' ''',
                (rule_id, user_id)
            )

        conn.commit()
        return True

def confirm_delete_subscription(user_id, sub_id, sub_name):
    """
    Deletes a subscription and its linked schedule after confirmation.
    Does not delete or reverse past transactions.
    """
    confirmed = messagebox.askyesno(
        "Delete Subscription",
        (
            f"Delete subscription '{sub_name}'?\n\n"
            "Its linked recurring schedule will also be deleted, "
            "so it will stop generating future expenses.\n\n"
            "Past transactions and account balances will not change.\n"
            "Past expenses remain in Transaction History.\n\n"
            "This cannot be undone."
        ),
        parent=root
    )

    if not confirmed:
        return

    try:
        deleted = delete_subscription_and_schedule(user_id, sub_id)
    except (sqlite3.Error, ValueError) as error:
        messagebox.showerror(
            "Deletion Failed",
            str(error),
            parent=root
        )
        return

    if not deleted:
        messagebox.showinfo(
            "Subscription Not Found",
            "This subscription no longer exists. The list will refresh.",
            parent=root
        )

    show_subscription_list(user_id)

def show_subscription_payments(user_id, sub_id, sub_name):
    """
    Shows a popup listing all past transactions recorded
    for a specific subscription.

    Matches transactions by category name — since subscriptions
    currently store category as a name string and transactions
    also store category as a name string, we match on that.
    """
    sym = get_currency(user_id)

    # First get the subscription details
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT category, amount, charge_dates
               FROM subscriptions
               WHERE id = ? AND user_id = ?''',
            (sub_id, user_id)
        )
        sub_row = cursor.fetchone()

    if not sub_row:
        messagebox.showerror("Error", "Subscription not found.")
        return

    sub_category, sub_amount, charge_dates = sub_row

    # Fetch only transactions generated by THIS subscription
    # using the stable subscription_id link — not the category
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT t.date, t.time, t.amount, t.notes,
                      t.reference, t.necessity, a.account_name
               FROM transactions t
               JOIN accounts a ON t.account_id = a.id
               WHERE t.user_id = ?
               AND t.subscription_id = ?
               ORDER BY t.date DESC, t.time DESC''',
            (user_id, sub_id)
        )
        payments = cursor.fetchall()

    total_paid = sum(p[2] for p in payments)

    # ── Create popup ──────────────────────────────────────────
    popup = tk.Toplevel(root)
    popup.title(f"🔍 {sub_name} — Payment History")
    popup.geometry("500x520")
    popup.resizable(False, False)
    popup.configure(bg="#f0f4f8")
    popup.transient(root)
    popup.grab_set()

    # ── Header ────────────────────────────────────────────────
    header = tk.Frame(popup, bg="#805ad5", pady=10)
    header.pack(fill="x")

    tk.Label(
        header,
        text=f"🔍 {sub_name}",
        font=("Segoe UI", 14, "bold"),
        bg="#805ad5", fg="white"
    ).pack()

    tk.Label(
        header,
        text=f"Category: {sub_category}  |  "
             f"Charge Days: {charge_dates}",
        font=("Segoe UI", 9),
        bg="#805ad5", fg="#e9d8fd"
    ).pack()

    # ── Summary strip ─────────────────────────────────────────
    summary = tk.Frame(popup, bg="white", relief="solid", bd=1)
    summary.pack(fill="x", padx=15, pady=8)

    summary_row = tk.Frame(summary, bg="white")
    summary_row.pack(pady=8)

    # Total paid column
    total_col = tk.Frame(summary_row, bg="white")
    total_col.pack(side="left", expand=True)
    tk.Label(total_col, text="TOTAL PAID",
             font=("Segoe UI", 8), bg="white", fg="#718096").pack()
    tk.Label(total_col, text=f"{sym}{total_paid:,.2f}",
             font=("Segoe UI", 11, "bold"), bg="white", fg="#805ad5").pack()

    tk.Frame(summary_row, bg="#e2e8f0", width=1).pack(
        side="left", fill="y", padx=10)

    # Payment count column
    count_col = tk.Frame(summary_row, bg="white")
    count_col.pack(side="left", expand=True)
    tk.Label(count_col, text="PAYMENTS",
             font=("Segoe UI", 8), bg="white", fg="#718096").pack()
    tk.Label(count_col, text=str(len(payments)),
             font=("Segoe UI", 11, "bold"), bg="white", fg="#2b6cb0").pack()

    tk.Frame(summary_row, bg="#e2e8f0", width=1).pack(
        side="left", fill="y", padx=10)

    # Amount per charge column
    per_col = tk.Frame(summary_row, bg="white")
    per_col.pack(side="left", expand=True)
    tk.Label(per_col, text="PER CHARGE",
             font=("Segoe UI", 8), bg="white", fg="#718096").pack()
    tk.Label(per_col, text=f"{sym}{sub_amount:,.2f}",
             font=("Segoe UI", 11, "bold"), bg="white", fg="#2d3748").pack()

    # ── Info note ─────────────────────────────────────────────
    tk.Label(
        popup,
        text=(
            "ℹ️ Showing charges generated by this subscription.\n"
            "Charges created before this update may not appear here."
        ),
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8", fg="#718096",
        justify="left"
    ).pack(anchor="w", padx=15, pady=(0, 4))

    # ── Scrollable payment list ───────────────────────────────
    scroll_outer = tk.Frame(popup, bg="#f0f4f8")
    scroll_outer.pack(fill="both", expand=True, padx=15)

    canvas = tk.Canvas(scroll_outer, bg="#f0f4f8", highlightthickness=0)
    scrollbar = ttk.Scrollbar(
        scroll_outer, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#f0f4f8")

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(event):
        try:
            if not canvas.winfo_exists():
                return

            direction = int(-1 * (event.delta / 120))
            if direction == 0:
                direction = -1 if event.delta > 0 else 1

            canvas.yview_scroll(direction, "units")

        except tk.TclError:
            return

    def enable_popup_scroll(event=None):
        try:
            if canvas.winfo_exists():
                root.bind_all("<MouseWheel>", _on_mousewheel)
        except tk.TclError:
            pass

    def disable_popup_scroll(event=None):
        root.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", enable_popup_scroll)
    canvas.bind("<Leave>", disable_popup_scroll)
    scroll_frame.bind("<Enter>", enable_popup_scroll)
    scroll_frame.bind("<Leave>", disable_popup_scroll)

    # ── Display each payment ──────────────────────────────────
    if not payments:
        tk.Label(
            scroll_frame,
            text="No payments recorded yet for this subscription.",
            font=("Segoe UI", 10),
            bg="#f0f4f8", fg="#718096"
        ).pack(pady=20)
    else:
        for payment in payments:
            (pay_date, pay_time, pay_amount,
             pay_notes, pay_reference, pay_necessity, pay_account) = payment

            pay_notes     = pay_notes     or ""
            pay_reference = pay_reference or ""
            pay_necessity = pay_necessity or "unset"

            # Card for each payment
            pay_card = tk.Frame(scroll_frame, bg="white", relief="solid", bd=1)
            pay_card.pack(fill="x", pady=3)

            # Top row — date, time, amount
            top = tk.Frame(pay_card, bg="white")
            top.pack(fill="x", padx=8, pady=(6, 2))

            tk.Label(
                top,
                text=f"{pay_date}  {pay_time}  |  {pay_account}",
                font=("Segoe UI", 9, "bold"),
                bg="white", fg="#2d3748"
            ).pack(side="left")

            tk.Label(
                top,
                text=f"-{sym}{pay_amount:,.2f}",
                font=("Segoe UI", 9, "bold"),
                bg="white", fg="#e53e3e"
            ).pack(side="right")

            # Necessity badge
            if pay_necessity != "unset":
                nec_bg   = "#e9d8fd" if pay_necessity == "want" else "#c6f6d5"
                nec_text = "🛍️ Want" if pay_necessity == "want" else "✅ Need"
                tk.Label(
                    top, text=nec_text,
                    font=("Segoe UI", 7, "bold"),
                    bg=nec_bg, fg="#2d3748",
                    relief="solid", bd=1, padx=3, pady=1
                ).pack(side="right", padx=5)

            # Notes row
            if pay_notes:
                tk.Label(
                    pay_card,
                    text=f"📝  {pay_notes}",
                    font=("Segoe UI", 8, "italic"),
                    bg="white", fg="#4a5568",
                    wraplength=420, justify="left"
                ).pack(anchor="w", padx=8, pady=1)

            # Reference row
            if pay_reference:
                tk.Label(
                    pay_card,
                    text=f"🔖  Ref: {pay_reference}",
                    font=("Segoe UI", 8),
                    bg="white", fg="#4a5568"
                ).pack(anchor="w", padx=8, pady=(1, 4))

            # Bottom padding
            tk.Frame(pay_card, bg="white", height=4).pack()

    # ── Close button ──────────────────────────────────────────
    btn_bar = tk.Frame(popup, bg="#f0f4f8", pady=10)
    btn_bar.pack(fill="x", padx=15)

    def close_popup():
        # Remove the popup's global scrolling callback first.
        root.unbind_all("<MouseWheel>")
        popup.destroy()

    # Use the same cleanup if the user clicks the window's X button.
    popup.protocol("WM_DELETE_WINDOW", close_popup)

    make_button(
        btn_bar, "✖ Close",
        close_popup, color="#718096", width=12
    ).pack()

def update_linked_subscription(
    user_id,
    sub_id,
    name,
    category,
    amount_text,
    billing_days_text,
    account_id,
    notes,
    necessity
):
    """
    Updates a linked subscription and its shared schedule atomically.

    Does not generate transactions or change account balances.
    Preserves start date, active/paused status, tags and past records.

    Returns the saved next-due date as YYYY-MM-DD.
    Raises ValueError for invalid input or an unsafe edit.
    """
    import math

    name = name.strip()
    category = category.strip()
    notes = notes.strip()

    if not name:
        raise ValueError("Please enter a subscription name.")

    if not category:
        raise ValueError("Please select an expense category.")

    if account_id is None:
        raise ValueError("Please select an account.")

    if necessity not in ("need", "want", "unset"):
        raise ValueError("Please select a valid necessity rating.")

    try:
        amount = float(amount_text)
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        raise ValueError(
            "Amount must be a finite number greater than zero."
        ) from None

    today = datetime.today().date()

    # Validate billing days using the same rules as the processor.
    next_subscription_billing_date(
        billing_days_text,
        today,
        inclusive=True
    )

    billing_days = ",".join(
        str(day)
        for day in sorted({
            int(part.strip())
            for part in billing_days_text.split(",")
        })
    )

    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()

        cursor.execute(
            '''SELECT recurring_rule_id
               FROM subscriptions
               WHERE id = ? AND user_id = ?''',
            (sub_id, user_id)
        )
        subscription = cursor.fetchone()

        if subscription is None:
            raise ValueError("The subscription no longer exists.")

        rule_id = subscription[0]

        if rule_id is None:
            raise ValueError(
                "This older subscription has no shared schedule yet. "
                "Complete schedule setup before using this editor."
            )

        cursor.execute(
            '''SELECT type, schedule_kind, next_due_date,
                      monthly_charge_days, schedule_start_date
               FROM recurring_transactions
               WHERE id = ? AND user_id = ?''',
            (rule_id, user_id)
        )
        rule = cursor.fetchone()

        if rule is None:
            raise ValueError(
                "The linked schedule no longer exists."
            )

        (
            rule_type,
            schedule_kind,
            old_next_due_text,
            old_billing_days_text,
            start_date_text
        ) = rule

        if rule_type != "expense" or schedule_kind != "subscription":
            raise ValueError(
                "The linked schedule is not a valid subscription expense."
            )

        try:
            old_next_due = datetime.strptime(
                old_next_due_text, "%Y-%m-%d"
            ).date()

            start_date = datetime.strptime(
                start_date_text, "%Y-%m-%d"
            ).date()

            # Validate and normalise the existing billing days too.
            next_subscription_billing_date(
                old_billing_days_text,
                old_next_due,
                inclusive=True
            )

            old_billing_days = ",".join(
                str(day)
                for day in sorted({
                    int(part.strip())
                    for part in old_billing_days_text.split(",")
                })
            )
        except (TypeError, ValueError):
            raise ValueError(
                "The existing schedule has invalid dates or billing days. "
                "Nothing was changed."
            ) from None

        if old_next_due <= today:
            raise ValueError(
                "This schedule has an occurrence due today or earlier. "
                "For an active schedule, process outstanding occurrences "
                "under the old settings before editing. "
                "For a paused schedule, its outstanding-date policy must "
                "be resolved before editing. Nothing was changed."
            )

        # Keep the next date when billing days are unchanged.
        # Otherwise, the new billing pattern begins tomorrow or on the
        # original start date, whichever is later.
        if billing_days == old_billing_days:
            next_due = old_next_due
        else:
            next_due = next_subscription_billing_date(
                billing_days,
                max(today + timedelta(days=1), start_date),
                inclusive=True
            )

        cursor.execute(
            '''SELECT 1 FROM accounts
               WHERE id = ? AND user_id = ?''',
            (account_id, user_id)
        )
        if cursor.fetchone() is None:
            raise ValueError(
                "The selected account no longer exists."
            )

        cursor.execute(
            '''SELECT 1 FROM categories
               WHERE user_id = ? AND type = 'expense' AND name = ?''',
            (user_id, category)
        )
        if cursor.fetchone() is None:
            raise ValueError(
                "Please select an existing expense category."
            )

        cursor.execute(
            '''SELECT 1 FROM subscriptions
               WHERE user_id = ?
                 AND id != ?
                 AND subscription_name = ? COLLATE NOCASE''',
            (user_id, sub_id, name)
        )
        if cursor.fetchone() is not None:
            raise ValueError(
                "Another subscription already has this name."
            )

        cursor.execute(
            '''UPDATE recurring_transactions
               SET name = ?,
                   category = ?,
                   amount = ?,
                   monthly_charge_days = ?,
                   next_due_date = ?,
                   account_id = ?,
                   notes = ?,
                   necessity = ?
               WHERE id = ? AND user_id = ?''',
            (
                name,
                category,
                amount,
                billing_days,
                next_due.isoformat(),
                account_id,
                notes,
                necessity,
                rule_id,
                user_id
            )
        )

        # Keep the legacy display fields synchronised until all list
        # screens read the authoritative schedule directly.
        cursor.execute(
            '''UPDATE subscriptions
               SET subscription_name = ?,
                   category = ?,
                   amount = ?,
                   charge_dates = ?,
                   notes = ?,
                   necessity = ?
               WHERE id = ? AND user_id = ?''',
            (
                name,
                category,
                amount,
                billing_days,
                notes,
                necessity,
                sub_id,
                user_id
            )
        )

        conn.commit()

    return next_due.isoformat()

def show_edit_subscription(user_id, sub_id):
    """
    Edits a subscription through its shared recurring schedule.

    Older, unlinked subscriptions are routed to the legacy editor.
    """
    # Read the link before changing the current screen.
    with get_db() as conn:
        subscription = conn.execute(
            '''SELECT recurring_rule_id
               FROM subscriptions
               WHERE id = ? AND user_id = ?''',
            (sub_id, user_id)
        ).fetchone()

        if subscription is not None and subscription[0] is not None:
            rule = conn.execute(
                '''SELECT name, category, amount, monthly_charge_days,
                          account_id, notes, necessity, next_due_date,
                          schedule_start_date, is_active, type, schedule_kind
                   FROM recurring_transactions
                   WHERE id = ? AND user_id = ?''',
                (subscription[0], user_id)
            ).fetchone()
        else:
            rule = None

    if subscription is None:
        messagebox.showerror(
            "Not Found",
            "This subscription no longer exists.",
            parent=root
        )
        return

    if subscription[0] is None:
        show_edit_unlinked_subscription(user_id, sub_id)
        return

    if rule is None:
        messagebox.showerror(
            "Invalid Schedule Link",
            "The subscription's linked schedule could not be found.",
            parent=root
        )
        return

    (
        old_name,
        old_category,
        old_amount,
        old_days,
        old_account_id,
        old_notes,
        old_necessity,
        old_next_due_text,
        start_date_text,
        is_active,
        rule_type,
        schedule_kind
    ) = rule

    if rule_type != "expense" or schedule_kind != "subscription":
        messagebox.showerror(
            "Invalid Schedule",
            "The linked rule is not a subscription expense.",
            parent=root
        )
        return

    try:
        old_next_due = datetime.strptime(
            old_next_due_text, "%Y-%m-%d"
        ).date()
        start_date = datetime.strptime(
            start_date_text, "%Y-%m-%d"
        ).date()

        # Validate the existing billing-day settings.
        next_subscription_billing_date(
            old_days, old_next_due, inclusive=True
        )
        normalised_old_days = ",".join(
            str(day)
            for day in sorted({
                int(part.strip()) for part in old_days.split(",")
            })
        )
    except (TypeError, ValueError):
        messagebox.showerror(
            "Invalid Schedule",
            "The existing schedule contains invalid dates or billing days. "
            "Nothing was changed.",
            parent=root
        )
        return

    clear_window()
    sym = get_currency(user_id)
    saved = False

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")

    tk.Label(
        header,
        text="Edit Subscription",
        font=("Segoe UI", 16, "bold"),
        bg="#2b6cb0",
        fg="white"
    ).pack()

    tk.Label(
        header,
        text=f"Editing: {old_name}",
        font=("Segoe UI", 10),
        bg="#2b6cb0",
        fg="#bee3f8"
    ).pack()

    # Reserve space for navigation before the scrolling content.
    btn_bar = tk.Frame(root, bg="#f0f4f8", pady=10)
    btn_bar.pack(side="bottom", fill="x", padx=20)

    body = make_scrollable_frame(root)

    def field_label(text):
        tk.Label(
            body,
            text=text,
            font=("Segoe UI", 10, "bold"),
            bg="#f0f4f8"
        ).pack(anchor="w", padx=20, pady=(10, 2))

    status = "Active" if is_active else "Paused"

    tk.Label(
        body,
        text=(
            f"Status: {status}\n"
            f"Start date: {start_date_text}\n"
            f"Current next billing date: {old_next_due_text}"
        ),
        font=("Segoe UI", 10),
        bg="#f0f4f8",
        fg="#2d3748",
        justify="left"
    ).pack(anchor="w", padx=20, pady=10)

    field_label("Subscription Name:")
    name_entry = make_entry(body, width=35)
    name_entry.insert(0, old_name)
    name_entry.pack(anchor="w", padx=20)

    field_label("Expense Category:")
    cat_row = tk.Frame(body, bg="#f0f4f8")
    cat_row.pack(anchor="w", padx=20)

    categories = get_expense_categories(user_id)

    # Display the stored value even if the category was deleted.
    # Saving still requires an existing expense category.
    category_var = tk.StringVar(value=old_category)
    category_dd = ttk.Combobox(
        cat_row,
        textvariable=category_var,
        values=categories,
        state="readonly",
        width=25
    )
    category_dd.pack(side="left")

    make_button(
        cat_row,
        "+ Add Category",
        lambda: open_add_category_popup(
            user_id, "expense", category_dd, category_var
        ),
        color="#3182ce",
        width=14
    ).pack(side="left", padx=6)

    field_label(f"Amount Per Occurrence ({sym}):")
    amount_entry = make_entry(body, width=20)
    amount_entry.insert(0, str(old_amount))
    amount_entry.pack(anchor="w", padx=20)

    field_label("Monthly Billing Days (for example 1,15):")
    days_var = tk.StringVar(value=normalised_old_days)
    days_entry = tk.Entry(
        body,
        textvariable=days_var,
        width=30,
        font=("Segoe UI", 10),
        relief="solid",
        bd=1
    )
    days_entry.pack(anchor="w", padx=20)

    tk.Label(
        body,
        text=(
            "If billing days change, the new pattern begins tomorrow "
            "or on the original start date, whichever is later.\n"
            "Days that do not exist in a month are skipped."
        ),
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8",
        fg="#718096",
        wraplength=500,
        justify="left"
    ).pack(anchor="w", padx=20, pady=(3, 0))

    preview_label = tk.Label(
        body,
        text="",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8",
        fg="#2b6cb0"
    )
    preview_label.pack(anchor="w", padx=20, pady=6)

    field_label("Account:")
    accounts = view_accounts(user_id)
    account_options = {
        f"{acc[1]} (ID {acc[0]}) | {sym}{acc[2]:,.2f}": acc[0]
        for acc in accounts
    }

    old_account_label = next(
        (
            label for label, account_id in account_options.items()
            if account_id == old_account_id
        ),
        ""
    )

    account_var = tk.StringVar(value=old_account_label)
    account_dd = ttk.Combobox(
        body,
        textvariable=account_var,
        values=list(account_options),
        state="readonly",
        width=45
    )
    account_dd.pack(anchor="w", padx=20)

    field_label("Notes (optional):")
    notes_entry = make_entry(body, width=40)
    notes_entry.insert(0, old_notes or "")
    notes_entry.pack(anchor="w", padx=20)

    field_label("Necessity:")
    necessity_var = tk.StringVar(
        value=old_necessity
        if old_necessity in ("need", "want", "unset")
        else "unset"
    )
    necessity_frame = tk.Frame(body, bg="#f0f4f8")
    necessity_frame.pack(anchor="w", padx=20)

    for label, value in [
        ("Need", "need"),
        ("Want", "want"),
        ("Not set", "unset")
    ]:
        tk.Radiobutton(
            necessity_frame,
            text=label,
            variable=necessity_var,
            value=value,
            font=("Segoe UI", 10),
            bg="#f0f4f8"
        ).pack(side="left", padx=(0, 10))

    tk.Label(
        body,
        text=(
            "Saving does not generate expenses or change account balances.\n"
            "Past transactions, the start date, and active/paused status "
            "are preserved."
        ),
        font=("Segoe UI", 9, "italic"),
        bg="#f0f4f8",
        fg="#2c5282",
        wraplength=500,
        justify="left"
    ).pack(anchor="w", padx=20, pady=12)

    msg_label = tk.Label(
        body,
        text="",
        font=("Segoe UI", 10),
        bg="#f0f4f8",
        fg="red",
        wraplength=500,
        justify="left"
    )
    msg_label.pack(anchor="w", padx=20, pady=(0, 10))

    def calculate_preview():
        today = datetime.today().date()

        if old_next_due <= today:
            raise ValueError(
                "An occurrence is due today or earlier. "
                "Resolve outstanding dates before editing."
            )

        raw_days = days_var.get().strip()

        # Validate before normalising.
        next_subscription_billing_date(
            raw_days, today, inclusive=True
        )

        normalised_days = ",".join(
            str(day)
            for day in sorted({
                int(part.strip()) for part in raw_days.split(",")
            })
        )

        if normalised_days == normalised_old_days:
            next_due = old_next_due
        else:
            next_due = next_subscription_billing_date(
                normalised_days,
                max(today + timedelta(days=1), start_date),
                inclusive=True
            )

        return normalised_days, next_due

    def update_preview(*args):
        try:
            _, next_due = calculate_preview()
        except ValueError as error:
            preview_label.config(
                text=str(error),
                fg="#c53030"
            )
        else:
            preview_label.config(
                text=f"Next billing date after saving: {next_due.isoformat()}",
                fg="#2b6cb0"
            )

    days_var.trace_add("write", update_preview)
    update_preview()

    def on_save():
        nonlocal saved

        if saved:
            return

        try:
            billing_days, preview_due = calculate_preview()
        except ValueError as error:
            msg_label.config(text=str(error), fg="red")
            return

        confirmed = messagebox.askyesno(
            "Confirm Subscription Changes",
            (
                f"Save changes to '{name_entry.get().strip()}'?\n\n"
                f"Next billing date: {preview_due.isoformat()}\n"
                f"Status remains: {status}\n\n"
                "If billing days changed, the old future billing pattern "
                "will be replaced by the new pattern.\n"
                "Past transactions and account balances will not change."
            ),
            parent=root
        )

        if not confirmed:
            return

        try:
            saved_next_due = update_linked_subscription(
                user_id=user_id,
                sub_id=sub_id,
                name=name_entry.get(),
                category=category_var.get(),
                amount_text=amount_entry.get(),
                billing_days_text=billing_days,
                account_id=account_options.get(account_var.get()),
                notes=notes_entry.get(),
                necessity=necessity_var.get()
            )
        except (sqlite3.Error, ValueError, OverflowError) as error:
            msg_label.config(
                text=f"Could not save: {error}",
                fg="red"
            )
            return

        saved = True
        save_button.config(state="disabled")

        messagebox.showinfo(
            "Subscription Updated",
            (
                "The subscription and shared schedule were updated.\n\n"
                f"Next billing date: {saved_next_due}\n"
                "Past transactions and account balances were not changed."
            ),
            parent=root
        )
        show_subscription_list(user_id)

    save_button = make_button(
        btn_bar,
        "Save Changes",
        on_save,
        color="#38a169"
    )
    save_button.pack(side="left", padx=5)

    make_button(
        btn_bar,
        "Back",
        lambda: show_subscription_list(user_id),
        color="#718096"
    ).pack(side="left", padx=5)

    # Outstanding occurrences must be resolved under the old settings.
    if old_next_due <= datetime.today().date():
        save_button.config(state="disabled")

        if is_active:
            explanation = (
                "Editing is blocked because an occurrence is due today "
                "or earlier. Log out and log in to process due schedules "
                "under their existing settings, then reopen this editor. "
                "Login processes all due schedules for your user."
            )
        else:
            explanation = (
                "This paused schedule has outstanding dates. "
                "Editing remains blocked until we implement the explicit "
                "resume-date policy. Saving will not silently skip dates "
                "or resume the subscription."
            )

        msg_label.config(text=explanation, fg="red")

def show_edit_unlinked_subscription(user_id, sub_id):
    """
    Edit screen for a subscription.
    Allows editing name, category, amount and charge dates.
    """
    # Temporary safety guard.
    # Remove this guard when the shared-schedule editor is implemented.
    with get_db() as conn:
        row = conn.execute(
            '''SELECT recurring_rule_id
               FROM subscriptions
               WHERE id = ? AND user_id = ?''',
            (sub_id, user_id)
        ).fetchone()

    if row is None:
        messagebox.showerror(
            "Not Found",
            "This subscription no longer exists.",
            parent=root
        )
        return

    if row[0] is not None:
        messagebox.showinfo(
            "Shared Schedule Editing Not Yet Enabled",
            (
                "This subscription uses a shared recurring schedule.\n\n"
                "Editing is temporarily blocked until the shared-schedule "
                "editor is installed, so the two records cannot "
                "become inconsistent.\n\n"
                "Nothing has been changed."
            ),
            parent=root
        )
        return
    
    clear_window()

    # Load existing subscription data
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT subscription_name, category, amount,
                      charge_dates, notes, necessity
               FROM subscriptions WHERE id = ? AND user_id = ?''',
            (sub_id, user_id)
        )
        row = cursor.fetchone()

    if not row:
        messagebox.showerror("Error", "Subscription not found.")
        show_subscription_list(user_id)
        return

    (old_name, old_category, old_amount,
     old_dates, old_notes, old_necessity) = row

    # Fallback for rows created before new columns existed
    old_notes     = old_notes     or ""
    old_necessity = old_necessity or "unset"

    sym = get_currency(user_id)

    # ── Header ───────────────────────────────────────────────
    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")

    tk.Label(
        header,
        text="✏️ Edit Subscription",
        font=("Segoe UI", 16, "bold"),
        fg="white", bg="#2b6cb0"
    ).pack()

    tk.Label(
        header,
        text=f"Editing: {old_name}",
        font=("Segoe UI", 10),
        fg="#bee3f8", bg="#2b6cb0"
    ).pack()

    # ── Pinned button bar — packed BEFORE body ────────────────
    btn_bar = tk.Frame(root, bg="#f0f4f8", pady=10)
    btn_bar.pack(side="bottom", fill="x", padx=20)

    # ── Scrollable body ───────────────────────────────────────
    body = make_scrollable_frame(root)

    # ── Subscription name ─────────────────────────────────────
    tk.Label(
        body,
        text="Subscription Name:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20, pady=(10, 0))

    name_entry = make_entry(body, width=35)
    name_entry.insert(0, old_name)       # Pre-fill existing name
    name_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Category ──────────────────────────────────────────────
    tk.Label(
        body,
        text="Category:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    categories   = get_expense_categories(user_id)
    category_var = tk.StringVar(
        value=old_category if old_category in categories else (
            categories[0] if categories else "General"
        )
    )
    category_dd = ttk.Combobox(
        body,
        textvariable=category_var,
        values=categories,
        state="readonly",
        width=28
    )
    category_dd.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Charge dates ──────────────────────────────────────────
    tk.Label(
        body,
        text="Charge Dates (comma separated day numbers e.g. 1,15):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    dates_entry = make_entry(body, width=35)
    dates_entry.insert(0, old_dates)     # Pre-fill existing charge dates
    dates_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Amount ────────────────────────────────────────────────
    tk.Label(
        body,
        text=f"Amount ({sym}):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    tk.Label(
        body,
        text="e.g. Netflix raised its price — update the amount here.",
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8", fg="#718096"
    ).pack(anchor="w", padx=20)

    amount_entry = make_entry(body, width=20)
    amount_entry.insert(0, str(old_amount))  # Pre-fill existing amount
    amount_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Notes field ───────────────────────────────────────────
    tk.Label(
        body,
        text="Notes (optional):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)
    tk.Label(
        body,
        text="e.g. Student plan, Annual billing, Shared with family",
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8", fg="#718096"
    ).pack(anchor="w", padx=20)
    notes_entry = make_entry(body, width=40)
    notes_entry.insert(0, old_notes)   # Pre-fill existing notes
    notes_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Necessity field ───────────────────────────────────────
    tk.Label(
        body,
        text="Necessity:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)
    necessity_var = tk.StringVar(value=old_necessity)
    necessity_frame = tk.Frame(body, bg="#f0f4f8")
    necessity_frame.pack(anchor="w", padx=20, pady=(2, 10))
    tk.Radiobutton(
        necessity_frame, text="✅ Need",
        variable=necessity_var, value="need",
        bg="#f0f4f8", font=("Segoe UI", 10)
    ).pack(side="left")
    tk.Radiobutton(
        necessity_frame, text="🛍️ Want",
        variable=necessity_var, value="want",
        bg="#f0f4f8", font=("Segoe UI", 10)
    ).pack(side="left", padx=10)
    tk.Radiobutton(
        necessity_frame, text="— Not set",
        variable=necessity_var, value="unset",
        bg="#f0f4f8", font=("Segoe UI", 10)
    ).pack(side="left")

    # ── Info note ─────────────────────────────────────────────
    note_frame = tk.Frame(body, bg="#ebf8ff", relief="solid", bd=1)
    note_frame.pack(fill="x", padx=20, pady=5)
    tk.Label(
        note_frame,
        text=(
            "ℹ️ These changes only affect FUTURE charges.\n"
            "Past transactions already recorded will not be changed."
        ),
        font=("Segoe UI", 9, "italic"),
        bg="#ebf8ff", fg="#2c5282",
        wraplength=430, justify="left",
        pady=8, padx=8
    ).pack()

    # ── Message label ─────────────────────────────────────────
    msg_label = tk.Label(
        body, text="",
        font=("Segoe UI", 10),
        bg="#f0f4f8", fg="red",
        wraplength=400
    )
    msg_label.pack(padx=20, pady=5)

    # ── Save function ─────────────────────────────────────────
    def on_save():
        new_name      = name_entry.get().strip()
        new_category  = category_var.get()
        new_dates     = dates_entry.get().strip()
        new_notes     = notes_entry.get().strip()
        new_necessity = necessity_var.get()

        # Validate name
        if not new_name:
            msg_label.config(
                text="❌ Subscription name cannot be empty.", fg="red")
            return

        # Validate amount
        try:
            new_amount = float(amount_entry.get().strip())
        except ValueError:
            msg_label.config(
                text="❌ Amount must be a valid number.", fg="red")
            return

        if new_amount <= 0:
            msg_label.config(
                text="❌ Amount must be greater than 0.", fg="red")
            return

        # Validate charge dates
        try:
            date_list = [int(d.strip()) for d in new_dates.split(",")]
            if not all(1 <= d <= 31 for d in date_list):
                raise ValueError
        except ValueError:
            msg_label.config(
                text="❌ Charge dates must be numbers between 1 and 31 "
                     "separated by commas.",
                fg="red"
            )
            return

        # Check for duplicate name — but allow keeping the same name
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT id FROM subscriptions
                   WHERE user_id = ? AND subscription_name = ?''',
                (user_id, new_name)
            )
            existing = cursor.fetchone()
            if existing and existing[0] != sub_id:
                msg_label.config(
                    text="❌ Another subscription already has this name.",
                    fg="red")
                return

            # Save changes
            cursor.execute(
                '''UPDATE subscriptions
                   SET subscription_name = ?, category = ?,
                       amount = ?, charge_dates = ?,
                       notes = ?, necessity = ?
                   WHERE id = ? AND user_id = ?''',
                (new_name, new_category, new_amount,
                 new_dates, new_notes, new_necessity,
                 sub_id, user_id)
            )
            conn.commit()

        msg_label.config(
            text="✅ Subscription updated!", fg="green")
        root.after(1000, lambda: show_subscription_list(user_id))

    # ── Add buttons to pinned bar ─────────────────────────────
    make_button(
        btn_bar, "✅ Save Changes",
        on_save, color="#38a169"
    ).pack(side="left", padx=5)

    make_button(
        btn_bar, "← Back",
        lambda: show_subscription_list(user_id),
        color="#718096"
    ).pack(side="left", padx=5)

def next_subscription_billing_date(charge_days, from_date, inclusive=True):
    """
    Returns the next valid subscription billing date.

    charge_days:
        Comma-separated day numbers, for example "1,15".

    from_date:
        A datetime.date value from which to search.

    inclusive=True:
        Allows from_date itself if it is a billing date.

    inclusive=False:
        Returns a billing date strictly after from_date.

    Policy:
        Days that do not exist in a month are skipped.
        Duplicate billing days are counted only once.
    """
    try:
        parts = charge_days.split(",")

        # Reject empty entries such as "1,,15" or "15,".
        if not parts or any(not part.strip() for part in parts):
            raise ValueError

        days = sorted({
            int(part.strip()) for part in parts
        })

        if not days or any(day < 1 or day > 31 for day in days):
            raise ValueError

    except (AttributeError, TypeError, ValueError):
        raise ValueError(
            "Billing days must be numbers from 1 to 31 "
            "separated by commas, for example 1,15."
        ) from None

    # Begin with the month containing from_date.
    month_start = from_date.replace(day=1)

    while True:
        last_day = monthrange(
            month_start.year,
            month_start.month
        )[1]

        for day in days:
            # Skip days that do not exist in this month.
            if day > last_day:
                continue

            candidate = month_start.replace(day=day)

            if candidate > from_date:
                return candidate

            if inclusive and candidate == from_date:
                return candidate

        # No suitable date remains this month: try the next month.
        if month_start.year == 9999 and month_start.month == 12:
            raise ValueError(
                "No later billing date is available within the supported dates."
            )

        month_start = month_start + relativedelta(months=1)





# ============================================================
# WISHLIST SCREEN
# ============================================================
# Wishlist = savings goal tracker (piggy bank concept).
# User adds items with a price target.
# They fund items separately — progress bar tracks % saved.
# 100% = fully funded, ready to purchase.
# Wishlist funding does NOT touch account balances —
# it is a separate virtual savings tracker.
# Max 5 wishlist items per user.
# ============================================================

def show_wishlist(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="🎯 Wishlist", font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)

    # Explanation note
    tk.Label(
        body,
        text="💡 Fund items separately from your accounts. Once 100% funded, they're ready to buy!",
        font=("Segoe UI", 9, "italic"), bg="#f0f4f8", fg="#718096",
        wraplength=500
    ).pack(pady=(5, 10))

    items = view_wishlist(user_id)

    if not items:
        tk.Label(body, text="No wishlist items yet. Add one below!",
                 font=("Segoe UI", 10), bg="#f0f4f8", fg="#718096").pack(pady=10)

    # ── Display each wishlist item as a card ──────────────────
    sym = get_currency(user_id)

    for item in items:
        # item columns: id, user_id, item_name, price, notes, link, progress
        item_id   = item[0]
        item_name = item[2]
        price     = float(item[3])
        notes     = item[4] or "None"
        link      = item[5] or "None"
        progress  = float(item[6]) if item[6] else 0.0

        card = tk.Frame(body, bg="white", relief="solid", bd=1)
        card.pack(fill="x", padx=20, pady=6)

        tk.Label(card, text=f"🎯 {item_name}",
                 font=("Segoe UI", 11, "bold"), bg="white").pack(
            anchor="w", padx=10, pady=(8, 2))

        tk.Label(card,
                 text=f"Price: {sym}{price:,.2f}  |  Notes: {notes}  |  Link: {link}",
                 font=("Segoe UI", 9), bg="white",
                 fg="#4a5568").pack(anchor="w", padx=10)

        # Progress bar drawn on canvas
        bar_canvas = tk.Canvas(card, width=400, height=16,
                               bg="#e2e8f0", highlightthickness=0)
        bar_canvas.pack(anchor="w", padx=10, pady=4)
        fill_width = int((min(progress, 100) / 100) * 400)
        bar_color = "#48bb78" if progress < 100 else "#3182ce"
        bar_canvas.create_rectangle(0, 0, fill_width, 16,
                                    fill=bar_color, outline="")

        # Status text below bar
        if progress >= 100:
            status_text = f"Progress: {progress:.1f}%  🎉 Fully funded! Ready to buy!"
            status_color = "#3182ce"
        else:
            status_text = f"Progress: {progress:.1f}%"
            status_color = "#276749"

        tk.Label(card, text=status_text,
                 font=("Segoe UI", 9), bg="white",
                 fg=status_color).pack(anchor="w", padx=10, pady=(0, 4))

        # ── Per-card action buttons ─────────────────────────────
        action_row = tk.Frame(card, bg="white")
        action_row.pack(anchor="e", padx=10, pady=(0, 8))

        # Edit button — opens edit screen for this specific item
        make_button(
            action_row, "✏️ Edit",
            lambda iid=item_id: show_edit_wishlist(user_id, iid),
            color="#3182ce", width=10
        ).pack(side="left", padx=3)

        # Fund button — only show if not fully funded
        if progress < 100:
            make_button(
                action_row, "💰 Fund",
                lambda iid=item_id, iname=item_name: show_fund_wishlist_item(
                    user_id, iid, iname
                ),
                color="#805ad5", width=10
            ).pack(side="left", padx=3)

        # Delete button
        make_button(
            action_row, "🗑️ Delete",
            lambda iid=item_id, iname=item_name: confirm_delete_wishlist_item(
                user_id, iid, iname
            ),
            color="#e53e3e", width=10
        ).pack(side="left", padx=3)

    # ── Bottom buttons ────────────────────────────────────────
    # Fund, Edit, Delete moved to per-card buttons above
    # Only Add and Back remain here
    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=15)

    if len(items) < 5:
        make_button(
            btn_frame, "➕ Add Item",
            lambda: show_add_wishlist(user_id),
            color="#38a169"
        ).pack(side="left", padx=5)
    else:
        tk.Label(
            body,
            text="⚠️ Maximum 5 wishlist items reached.",
            font=("Segoe UI", 9),
            bg="#f0f4f8", fg="#e53e3e"
        ).pack()

    make_button(
        btn_frame, "← Back to Menu",
        lambda: show_main_menu(current_user),
        color="#718096"
    ).pack(side="left", padx=5)

def confirm_delete_wishlist_item(user_id, item_id, item_name):
    """
    Confirmation dialog before deleting a wishlist item.
    """
    confirmed = messagebox.askyesno(
        "Confirm Delete",
        f"Delete wishlist item '{item_name}'?\n\nThis cannot be undone."
    )
    if confirmed:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM wishlist WHERE id = ? AND user_id = ?",
                (item_id, user_id)
            )
            conn.commit()
        show_wishlist(user_id)


def show_edit_wishlist(user_id, item_id):
    """
    Edit screen for a wishlist item.
    Allows editing name, price, notes and link.
    Progress is NOT editable here — use Fund button instead
    to keep funding history consistent.
    """
    clear_window()

    # Load existing item data
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT item_name, price, notes, link, progress
               FROM wishlist WHERE id = ? AND user_id = ?''',
            (item_id, user_id)
        )
        row = cursor.fetchone()

    if not row:
        messagebox.showerror("Error", "Wishlist item not found.")
        show_wishlist(user_id)
        return

    old_name, old_price, old_notes, old_link, old_progress = row
    old_notes = old_notes or ""
    old_link  = old_link or ""
    sym       = get_currency(user_id)

    # ── Header ───────────────────────────────────────────────
    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")

    tk.Label(
        header,
        text="✏️ Edit Wishlist Item",
        font=("Segoe UI", 16, "bold"),
        fg="white", bg="#2b6cb0"
    ).pack()

    tk.Label(
        header,
        text=f"Editing: {old_name}",
        font=("Segoe UI", 10),
        fg="#bee3f8", bg="#2b6cb0"
    ).pack()

    # ── Pinned button bar — packed BEFORE body ────────────────
    btn_bar = tk.Frame(root, bg="#f0f4f8", pady=10)
    btn_bar.pack(side="bottom", fill="x", padx=20)

    # ── Scrollable body ───────────────────────────────────────
    body = make_scrollable_frame(root)

    # ── Current progress display (read only) ──────────────────
    progress_frame = tk.Frame(body, bg="white", relief="solid", bd=1)
    progress_frame.pack(fill="x", padx=20, pady=(10, 5))

    tk.Label(
        progress_frame,
        text=f"Current Funding Progress: {old_progress:.1f}%",
        font=("Segoe UI", 11, "bold"),
        bg="white", fg="#2b6cb0",
        pady=8
    ).pack()

    note_frame = tk.Frame(body, bg="#ebf8ff", relief="solid", bd=1)
    note_frame.pack(fill="x", padx=20, pady=5)
    tk.Label(
        note_frame,
        text=(
            "ℹ️ To fund this item, use the 💰 Fund button on the\n"
            "wishlist screen — this keeps your funding history intact."
        ),
        font=("Segoe UI", 9, "italic"),
        bg="#ebf8ff", fg="#2c5282",
        wraplength=430, justify="left",
        pady=8, padx=8
    ).pack()

    # ── Item name ─────────────────────────────────────────────
    tk.Label(
        body,
        text="Item Name:",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20, pady=(10, 0))

    name_entry = make_entry(body, width=35)
    name_entry.insert(0, old_name)       # Pre-fill existing name
    name_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Price ─────────────────────────────────────────────────
    tk.Label(
        body,
        text=f"Price ({sym}):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    tk.Label(
        body,
        text="⚠️ Changing the price will recalculate your funding percentage.",
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8", fg="#dd6b20"
    ).pack(anchor="w", padx=20)

    price_entry = make_entry(body, width=20)
    price_entry.insert(0, str(old_price))  # Pre-fill existing price
    price_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Notes ─────────────────────────────────────────────────
    tk.Label(
        body,
        text="Notes (optional):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    notes_entry = make_entry(body, width=40)
    notes_entry.insert(0, old_notes)     # Pre-fill existing notes
    notes_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Link ──────────────────────────────────────────────────
    tk.Label(
        body,
        text="Link (optional):",
        font=("Segoe UI", 10, "bold"),
        bg="#f0f4f8"
    ).pack(anchor="w", padx=20)

    link_entry = make_entry(body, width=40)
    link_entry.insert(0, old_link)       # Pre-fill existing link
    link_entry.pack(anchor="w", padx=20, pady=(2, 10))

    # ── Message label ─────────────────────────────────────────
    msg_label = tk.Label(
        body, text="",
        font=("Segoe UI", 10),
        bg="#f0f4f8", fg="red",
        wraplength=400
    )
    msg_label.pack(padx=20, pady=5)

    # ── Save function ─────────────────────────────────────────
    def on_save():
        new_name  = name_entry.get().strip()
        new_notes = notes_entry.get().strip()
        new_link  = link_entry.get().strip()

        # Validate name
        if not new_name:
            msg_label.config(
                text="❌ Item name cannot be empty.", fg="red")
            return

        # Validate price
        try:
            new_price = float(price_entry.get().strip())
        except ValueError:
            msg_label.config(
                text="❌ Price must be a valid number.", fg="red")
            return

        if new_price <= 0:
            msg_label.config(
                text="❌ Price must be greater than 0.", fg="red")
            return

        # ── Recalculate progress if price changed ──────────────
        # Progress is stored as a percentage, but it was based
        # on the OLD price. If price changes, we need to recalculate
        # how much money was actually funded and reapply it
        # to the new price so the funded AMOUNT stays accurate.
        old_funded_amount = (old_progress / 100) * old_price
        new_progress = min((old_funded_amount / new_price) * 100, 100)

        # Save changes to database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''UPDATE wishlist
                   SET item_name = ?, price = ?, notes = ?,
                       link = ?, progress = ?
                   WHERE id = ? AND user_id = ?''',
                (new_name, new_price, new_notes, new_link,
                 new_progress, item_id, user_id)
            )
            conn.commit()

        msg_label.config(
            text="✅ Wishlist item updated!", fg="green")
        root.after(1000, lambda: show_wishlist(user_id))

    # ── Add buttons to pinned bar ─────────────────────────────
    make_button(
        btn_bar, "✅ Save Changes",
        on_save, color="#38a169"
    ).pack(side="left", padx=5)

    make_button(
        btn_bar, "← Back",
        lambda: show_wishlist(user_id),
        color="#718096"
    ).pack(side="left", padx=5)

def view_wishlist(user_id):
    """Returns all wishlist items for the user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM wishlist WHERE user_id = ?", (user_id,))
        return cursor.fetchall()


def show_add_wishlist(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="➕ Add Wishlist Item", font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)

    # Build form fields
    field_labels = [
        ("Item Name:", "name"),
        ("Price ($):", "price"),
        ("Notes (optional):", "notes"),
        ("Link (optional):", "link")
    ]
    entries = {}
    for label_text, key in field_labels:
        tk.Label(body, text=label_text, font=("Segoe UI", 10, "bold"),
                 bg="#f0f4f8").pack(anchor="w")
        entry = make_entry(body)
        entry.pack(anchor="w", pady=(2, 10))
        entries[key] = entry

    msg_label = tk.Label(body, text="", font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red", wraplength=400)
    msg_label.pack(pady=5)

    def on_submit():
        name  = entries["name"].get().strip()
        notes = entries["notes"].get().strip()
        link  = entries["link"].get().strip()

        # Validate name
        if not name:
            msg_label.config(text="❌ Item name cannot be empty.", fg="red")
            return

        # Validate price
        try:
            price = float(entries["price"].get().strip())
        except ValueError:
            msg_label.config(text="❌ Price must be a valid number.", fg="red")
            return

        if price <= 0:
            msg_label.config(text="❌ Price must be greater than 0.", fg="red")
            return

        # Save to database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO wishlist (user_id, item_name, price, notes, link)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, name, price, notes, link)
            )
            conn.commit()

        # Check if first wishlist badge should be awarded
        check_and_award_badges(user_id)

        msg_label.config(text="✅ Item added successfully!", fg="green")
        root.after(1000, lambda: show_wishlist(user_id))

    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=10)
    make_button(btn_frame, "✅ Save Item",
                on_submit, color="#38a169").pack(side="left", padx=5)
    make_button(btn_frame, "← Back",
                lambda: show_wishlist(user_id),
                color="#718096").pack(side="left", padx=5)


def show_fund_wishlist(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="💰 Fund Wishlist Item", font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)

    items = view_wishlist(user_id)

    if not items:
        tk.Label(body, text="No wishlist items to fund.",
                 font=("Segoe UI", 10), bg="#f0f4f8").pack(pady=10)
        make_button(body, "← Back",
                    lambda: show_wishlist(user_id),
                    color="#718096").pack()
        return

    # Dropdown of wishlist items
    item_names = [item[2] for item in items]
    selected = tk.StringVar(value=item_names[0])

    tk.Label(body, text="Select Item:", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    dropdown = ttk.Combobox(body, textvariable=selected,
                            values=item_names, state="readonly", width=28)
    dropdown.pack(anchor="w", pady=(2, 10))

    # Amount to fund
    tk.Label(body, text="Amount to Fund ($):", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    amount_entry = make_entry(body)
    amount_entry.pack(anchor="w", pady=(2, 10))

    msg_label = tk.Label(body, text="", font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red", wraplength=400)
    msg_label.pack(pady=5)

    def on_fund():
        chosen = selected.get()

        # Find the selected item from list
        item = next((i for i in items if i[2] == chosen), None)
        if not item:
            msg_label.config(text="❌ Item not found.", fg="red")
            return

        # Unpack item columns
        # item = (id, user_id, item_name, price, notes, link, progress)
        item_id  = item[0]
        price    = float(item[3])
        progress = float(item[6]) if item[6] else 0.0

        # Cannot fund an already fully funded item
        if progress >= 100:
            msg_label.config(text="❌ This item is already fully funded.", fg="red")
            return

        # Validate funding amount
        try:
            amount = float(amount_entry.get().strip())
        except ValueError:
            msg_label.config(text="❌ Amount must be a valid number.", fg="red")
            return

        if amount <= 0:
            msg_label.config(text="❌ Amount must be greater than 0.", fg="red")
            return

        # Calculate new progress percentage
        # Formula: progress += (amount_funded / total_price) * 100
        new_progress = progress + (amount / price) * 100

        # Cap progress at 100%
        if new_progress > 100:
            new_progress = 100

        # Save updated progress to database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE wishlist SET progress = ? WHERE id = ? AND user_id = ?",
                (new_progress, item_id, user_id)
            )
            conn.commit()

        msg_label.config(
            text=f"✅ Funded! New progress: {new_progress:.1f}%",
            fg="green"
        )
        root.after(1200, lambda: show_wishlist(user_id))

    # Submit button — properly connected this time (was missing in original code)
    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=10)
    make_button(btn_frame, "💰 Fund Item",
                on_fund, color="#38a169").pack(side="left", padx=5)
    make_button(btn_frame, "← Back",
                lambda: show_wishlist(user_id),
                color="#718096").pack(side="left", padx=5)

def show_fund_wishlist_item(user_id, item_id, item_name):
    """
    Pre-selected version of fund wishlist screen.
    Called from per-card Fund button — jumps straight
    to the chosen item without needing the dropdown.
    """
    clear_window()

    header = tk.Frame(root, bg="#805ad5", pady=12)
    header.pack(fill="x")
    tk.Label(
        header, text="💰 Fund Wishlist Item",
        font=("Segoe UI", 16, "bold"),
        fg="white", bg="#805ad5"
    ).pack()
    tk.Label(
        header, text=f"Item: {item_name}",
        font=("Segoe UI", 10),
        fg="#e9d8fd", bg="#805ad5"
    ).pack()

    # ── Pinned button bar ──────────────────────────────────────
    btn_bar = tk.Frame(root, bg="#f0f4f8", pady=10)
    btn_bar.pack(side="bottom", fill="x", padx=20)

    body = make_scrollable_frame(root)
    sym  = get_currency(user_id)

    # Load item data
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT price, progress FROM wishlist WHERE id = ? AND user_id = ?",
            (item_id, user_id)
        )
        row = cursor.fetchone()

    if not row:
        messagebox.showerror("Error", "Item not found.")
        show_wishlist(user_id)
        return

    price, progress = row
    price    = float(price)
    progress = float(progress) if progress else 0.0

    # Current progress display
    bal_frame = tk.Frame(body, bg="white", relief="solid", bd=1)
    bal_frame.pack(fill="x", padx=20, pady=10)
    tk.Label(
        bal_frame,
        text=f"Current Progress: {progress:.1f}%  |  Price: {sym}{price:,.2f}",
        font=("Segoe UI", 11, "bold"),
        bg="white", fg="#2b6cb0", pady=10
    ).pack()

    tk.Label(
        body, text=f"Amount to Fund ({sym}):",
        font=("Segoe UI", 10, "bold"), bg="#f0f4f8"
    ).pack(anchor="w", padx=20, pady=(10, 0))

    amount_entry = make_entry(body, width=20)
    amount_entry.pack(anchor="w", padx=20, pady=(2, 10))

    msg_label = tk.Label(
        body, text="", font=("Segoe UI", 10),
        bg="#f0f4f8", fg="red", wraplength=400
    )
    msg_label.pack(padx=20, pady=5)

    def on_fund():
        if progress >= 100:
            msg_label.config(
                text="❌ This item is already fully funded.", fg="red")
            return

        try:
            amount = float(amount_entry.get().strip())
        except ValueError:
            msg_label.config(
                text="❌ Amount must be a valid number.", fg="red")
            return

        if amount <= 0:
            msg_label.config(
                text="❌ Amount must be greater than 0.", fg="red")
            return

        new_progress = progress + (amount / price) * 100
        if new_progress > 100:
            new_progress = 100

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE wishlist SET progress = ? WHERE id = ? AND user_id = ?",
                (new_progress, item_id, user_id)
            )
            conn.commit()

        msg_label.config(
            text=f"✅ Funded! New progress: {new_progress:.1f}%",
            fg="green"
        )
        root.after(1200, lambda: show_wishlist(user_id))

    make_button(
        btn_bar, "💰 Fund Item",
        on_fund, color="#805ad5"
    ).pack(side="left", padx=5)

    make_button(
        btn_bar, "← Back",
        lambda: show_wishlist(user_id),
        color="#718096"
    ).pack(side="left", padx=5)

def render_budget_recommendations(parent, user_id, reference_date=None):
    """
    Displays current budget recommendations in the supplied frame.

    Reads financial data only. Does not generate transactions,
    change balances, or adjust budget limits.
    """
    if reference_date is None:
        reference_date = datetime.today().date()

    section = tk.Frame(parent, bg="#ebf8ff", relief="solid", bd=1)
    section.pack(fill="x", pady=10)

    tk.Label(
        section,
        text="Financial Insights & Suggestions",
        font=("Segoe UI", 13, "bold"),
        bg="#ebf8ff",
        fg="#2b6cb0"
    ).pack(anchor="w", padx=12, pady=(12, 4))

    tk.Label(
        section,
        text=(
            f"Current budget guidance as of {reference_date.isoformat()}.\n"
            "This section is independent of the report month selected above. "
            "It uses recorded expenses through today."
        ),
        font=("Segoe UI", 9),
        bg="#ebf8ff",
        fg="#4a5568",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 8))

    try:
        recommendations = get_budget_recommendations(
            user_id,
            reference_date=reference_date
        )
    except (sqlite3.Error, ValueError, OverflowError) as error:
        tk.Label(
            section,
            text=(
                "Budget suggestions could not be calculated.\n"
                f"Details: {error}"
            ),
            font=("Segoe UI", 10),
            bg="#ebf8ff",
            fg="#c53030",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 12))
        return

    if not recommendations:
        tk.Label(
            section,
            text=(
                "No budget suggestions are available. "
                "Create a calendar budget with a valid positive limit "
                "to enable this guidance."
            ),
            font=("Segoe UI", 10),
            bg="#ebf8ff",
            fg="#718096",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 12))
        return

    sym = get_currency(user_id)

    colors = {
        "exceeded": "#c53030",
        "at_limit": "#975a16",
        "allowance": "#2b6cb0"
    }

    for insight in recommendations:
        card = tk.Frame(section, bg="white", relief="solid", bd=1)
        card.pack(fill="x", padx=12, pady=5)

        color = colors[insight["severity"]]

        tk.Label(
            card,
            text=insight["title"],
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg=color,
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(10, 4))

        tk.Label(
            card,
            text=(
                f"{insight['timeframe']} | {insight['category']}\n"
                f"Calendar period: {insight['period_start']} "
                f"→ {insight['period_last_day']}\n"
                f"Budget limit: {sym}{insight['limit']:,.2f}\n"
                f"Recorded spending: {sym}{insight['spent']:,.2f}"
            ),
            font=("Segoe UI", 9),
            bg="white",
            fg="#4a5568",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10)

        if insight["severity"] == "allowance":
            days = insight["days_remaining"]
            day_label = "day" if days == 1 else "days"

            explanation = (
                f"Remaining: {sym}{insight['remaining']:,.2f}\n"
                f"{days} {day_label} remaining, including today.\n"
                f"Suggested average daily allowance: "
                f"{sym}{insight['daily_allowance']:,.2f}\n\n"
                f"Calculation: remaining budget ÷ {days} {day_label}; "
                "rounded down to two decimal places."
            )

        elif insight["severity"] == "at_limit":
            explanation = (
                "Remaining: "
                f"{sym}{insight['remaining']:,.2f}\n"
                "Recorded spending has reached the current budget limit."
            )

        else:
            explanation = (
                f"Over the limit by: {sym}{insight['over']:,.2f}"
            )

        tk.Label(
            card,
            text=explanation,
            font=("Segoe UI", 10, "bold"),
            bg="white",
            fg=color,
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(6, 4))

        tk.Label(
            card,
            text=insight["suggestion"],
            font=("Segoe UI", 9),
            bg="white",
            fg="#2d3748",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 6))

        if insight["transaction_count"] == 0:
            tk.Label(
                card,
                text=(
                    "No matching expense entries were found. "
                    "Check that your records are complete before "
                    "relying on this allowance."
                ),
                font=("Segoe UI", 8, "italic"),
                bg="white",
                fg="#975a16",
                wraplength=570,
                justify="left"
            ).pack(anchor="w", padx=10, pady=(0, 6))

        make_button(
            card,
            "View Spending",
            lambda bid=insight["budget_id"]: show_budget_spending(
                user_id, bid
            ),
            color="#805ad5",
            width=16
        ).pack(anchor="w", padx=10, pady=(0, 10))

    tk.Label(
        section,
        text=(
            "Rule-based guidance, not an affordability assessment. "
            "It does not reserve funds or subtract upcoming scheduled "
            "expenses. Missing entries can change the results. "
            "Overlapping budgets are separate views of spending: "
            "do not add their allowances together. "
            "Displayed amounts are rounded."
        ),
        font=("Segoe UI", 8, "italic"),
        bg="#ebf8ff",
        fg="#718096",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(6, 12))

def render_category_spending_recommendations(
    parent,
    user_id,
    selected_year,
    selected_month,
    reference_date=None
):
    """
    Displays expense comparisons for the selected report month.

    Reads data only. Does not generate transactions or change balances.
    """
    section = tk.Frame(parent, bg="#f7fafc", relief="solid", bd=1)
    section.pack(fill="x", pady=10)

    tk.Label(
        section,
        text="Selected-Period Spending Insights",
        font=("Segoe UI", 12, "bold"),
        bg="#f7fafc",
        fg="#2b6cb0"
    ).pack(anchor="w", padx=12, pady=(10, 4))

    try:
        result = get_category_spending_recommendations(
            user_id,
            selected_year,
            selected_month,
            reference_date=reference_date
        )
    except (sqlite3.Error, ValueError, OverflowError) as error:
        tk.Label(
            section,
            text=f"Spending comparisons are unavailable: {error}",
            font=("Segoe UI", 9),
            bg="#f7fafc",
            fg="#c53030",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 10))
        return

    periods = result["periods"]
    recommendations = result["recommendations"]
    sym = get_currency(user_id)

    selected_range = (
        f"{periods['selected_start'].isoformat()} "
        f"→ {periods['selected_last_day'].isoformat()}"
    )
    previous_range = (
        f"{periods['previous_start'].isoformat()} "
        f"→ {periods['previous_last_day'].isoformat()}"
    )

    tk.Label(
        section,
        text=(
            f"Selected period: {selected_range}\n"
            f"Comparison period: {previous_range}"
        ),
        font=("Segoe UI", 9),
        bg="#f7fafc",
        fg="#4a5568",
        justify="left",
        wraplength=600
    ).pack(anchor="w", padx=12, pady=(0, 6))

    if periods["mode"] == "matched_elapsed_days":
        comparison_note = (
            f"Comparing {periods['selected_days']} days in each month."
        )

        if periods["current_month_cutoff_limited"]:
            comparison_note += (
                " The previous month is shorter, so the selected-month "
                "comparison stops before today to keep the day counts equal."
            )
    else:
        comparison_note = (
            "Comparing completed calendar months: "
            f"{periods['selected_days']} days versus "
            f"{periods['previous_days']} days."
        )

        if not periods["equal_day_counts"]:
            comparison_note += (
                " Different month lengths can contribute to a change "
                "in total spending."
            )

    tk.Label(
        section,
        text=comparison_note,
        font=("Segoe UI", 8, "italic"),
        bg="#f7fafc",
        fg="#718096",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 8))

    if result["invalid_amount_count"]:
        tk.Label(
            section,
            text=(
                f"Data-quality notice: "
                f"{result['invalid_amount_count']} expense record(s) "
                "with invalid amounts were excluded."
            ),
            font=("Segoe UI", 9),
            bg="#f7fafc",
            fg="#975a16",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

    if not recommendations:
        tk.Label(
            section,
            text=(
                "No category spending increases were found in the "
                "valid expense records for these ranges. This may also "
                "occur when there are no recorded expenses."
            ),
            font=("Segoe UI", 10),
            bg="#f7fafc",
            fg="#4a5568",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 10))

    for insight in recommendations:
        card = tk.Frame(section, bg="white", relief="solid", bd=1)
        card.pack(fill="x", padx=12, pady=5)

        category = insight["category"]
        category_label = (
            str(category)
            if category is not None and str(category).strip()
            else "Unnamed category"
        )

        tk.Label(
            card,
            text=f"{category_label}: recorded spending increased",
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg="#2d3748",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(10, 4))

        percentage = insight["percentage_increase"]

        if percentage is None:
            change_text = (
                f"Increase in recorded amount: "
                f"{sym}{insight['increase']:,.2f}\n"
                "No positive spending total was recorded in the comparison "
                "period; a percentage increase is not calculated."
            )
        else:
            change_text = (
                f"Increase: {sym}{insight['increase']:,.2f} "
                f"({percentage:.1f}%)"
            )

        tk.Label(
            card,
            text=(
                f"Selected period: {sym}{insight['selected_amount']:,.2f}\n"
                f"Previous period: {sym}{insight['previous_amount']:,.2f}\n"
                f"{change_text}"
            ),
            font=("Segoe UI", 10),
            bg="white",
            fg="#4a5568",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10)

        tk.Label(
            card,
            text=insight["suggestion"],
            font=("Segoe UI", 9),
            bg="white",
            fg="#2d3748",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(6, 10))

    tk.Label(
        section,
        text=(
            "Showing up to three increases, ranked by monetary difference. "
            "Increased spending is not automatically a problem. "
            "Missing entries, changed category names, one-off purchases, "
            "and expenses recorded as balance adjustments can affect results. "
            "This comparison does not measure affordability."
        ),
        font=("Segoe UI", 8, "italic"),
        bg="#f7fafc",
        fg="#718096",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(6, 12))

def render_upcoming_expense_recommendations(
    parent,
    user_id,
    reference_date=None
):
    """
    Displays upcoming expense guidance for seven calendar days.

    Independent of the selected Dashboard report month.
    Reads data only.
    """
    if reference_date is None:
        reference_date = datetime.today().date()

    section = tk.Frame(
        parent,
        bg="#faf5ff",
        relief="solid",
        bd=1
    )
    section.pack(fill="x", pady=10)

    tk.Label(
        section,
        text="Upcoming Scheduled Expenses",
        font=("Segoe UI", 12, "bold"),
        bg="#faf5ff",
        fg="#553c9a"
    ).pack(anchor="w", padx=12, pady=(10, 4))

    try:
        result = get_upcoming_expense_recommendations(
            user_id,
            reference_date=reference_date
        )
    except (sqlite3.Error, ValueError, OverflowError) as error:
        tk.Label(
            section,
            text=f"Upcoming expenses could not be calculated: {error}",
            font=("Segoe UI", 9),
            bg="#faf5ff",
            fg="#c53030",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 12))
        return

    sym = get_currency(user_id)

    tk.Label(
        section,
        text=(
            f"{result['window_start']} → {result['window_last_day']}\n"
            "Seven calendar days, including today. "
            "Independent of the report month selected above."
        ),
        font=("Segoe UI", 9),
        bg="#faf5ff",
        fg="#4a5568",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 8))

    if result["notices"]:
        notice_frame = tk.Frame(section, bg="#fffbeb")
        notice_frame.pack(fill="x", padx=12, pady=(0, 8))

        tk.Label(
            notice_frame,
            text="Schedule and data notices",
            font=("Segoe UI", 9, "bold"),
            bg="#fffbeb",
            fg="#975a16"
        ).pack(anchor="w", padx=8, pady=(6, 2))

        for notice in result["notices"]:
            tk.Label(
                notice_frame,
                text=f"• {notice}",
                font=("Segoe UI", 9),
                bg="#fffbeb",
                fg="#975a16",
                wraplength=560,
                justify="left"
            ).pack(anchor="w", padx=8, pady=(0, 5))

    if not result["accounts"]:
        tk.Label(
            section,
            text=(
                "No unprocessed scheduled expense occurrences were found "
                "in this window among the schedules that could be evaluated. "
                "This does not mean there will be no expenses."
            ),
            font=("Segoe UI", 10),
            bg="#faf5ff",
            fg="#4a5568",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 10))

    for account in result["accounts"]:
        card = tk.Frame(section, bg="white", relief="solid", bd=1)
        card.pack(fill="x", padx=12, pady=5)

        exceeds_balance = (
            account["scheduled_total"] > account["recorded_balance"]
        )
        emphasis_color = "#c53030" if exceeds_balance else "#553c9a"

        balance = account["recorded_balance"]
        balance_text = (
            f"{'-' if balance < 0 else ''}{sym}{abs(balance):,.2f}"
        )

        tk.Label(
            card,
            text=account["account_name"],
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg="#2d3748",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(10, 4))

        tk.Label(
            card,
            text=(
                f"Current recorded balance: {balance_text}\n"
                f"Scheduled expenses in this window: "
                f"{sym}{account['scheduled_total']:,.2f}"
            ),
            font=("Segoe UI", 10),
            bg="white",
            fg="#4a5568",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10)

        if exceeds_balance:
            tk.Label(
                card,
                text=(
                    "Scheduled expenses exceed the current recorded "
                    f"balance by "
                    f"{sym}{account['excess_over_recorded_balance']:,.2f}."
                ),
                font=("Segoe UI", 10, "bold"),
                bg="white",
                fg=emphasis_color,
                wraplength=570,
                justify="left"
            ).pack(anchor="w", padx=10, pady=(6, 2))

        tk.Label(
            card,
            text=account["suggestion"],
            font=("Segoe UI", 9),
            bg="white",
            fg=emphasis_color,
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(4, 8))

        # Keep the Dashboard compact. Totals still include every
        # occurrence, even if only the first five are listed here.
        visible_occurrences = account["occurrences"][:5]

        for occurrence in visible_occurrences:
            kind = (
                "Subscription"
                if occurrence["schedule_kind"] == "subscription"
                else "Recurring expense"
            )

            tk.Label(
                card,
                text=(
                    f"{occurrence['scheduled_date']} | "
                    f"{occurrence['name']} | "
                    f"{sym}{occurrence['amount']:,.2f}\n"
                    f"{kind}"
                ),
                font=("Segoe UI", 9),
                bg="white",
                fg="#4a5568",
                wraplength=570,
                justify="left"
            ).pack(anchor="w", padx=10, pady=(0, 6))

        hidden_count = (
            len(account["occurrences"]) - len(visible_occurrences)
        )

        if hidden_count > 0:
            tk.Label(
                card,
                text=(
                    f"{hidden_count} additional occurrence(s) are "
                    "included in the total but not listed here."
                ),
                font=("Segoe UI", 8, "italic"),
                bg="white",
                fg="#718096",
                wraplength=570,
                justify="left"
            ).pack(anchor="w", padx=10, pady=(0, 8))

    tk.Label(
        section,
        text=result["limitation"],
        font=("Segoe UI", 8, "italic"),
        bg="#faf5ff",
        fg="#718096",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(6, 8))

    make_button(
        section,
        "View All Schedules",
        lambda: show_recurring_transactions(user_id),
        color="#805ad5",
        width=20
    ).pack(anchor="w", padx=12, pady=(0, 12))

def render_subscription_cost_review(
    parent,
    user_id,
    reference_date=None
):
    """
    Displays next-calendar-month subscription commitments.

    Reads data only. Independent of the selected report month.
    """
    if reference_date is None:
        reference_date = datetime.today().date()

    section = tk.Frame(
        parent,
        bg="#fffaf0",
        relief="solid",
        bd=1
    )
    section.pack(fill="x", pady=10)

    tk.Label(
        section,
        text="Subscription Cost Review",
        font=("Segoe UI", 12, "bold"),
        bg="#fffaf0",
        fg="#975a16"
    ).pack(anchor="w", padx=12, pady=(10, 4))

    try:
        result = get_subscription_cost_review(
            user_id,
            reference_date=reference_date
        )
    except (sqlite3.Error, ValueError, OverflowError) as error:
        tk.Label(
            section,
            text=f"Subscription costs could not be calculated: {error}",
            font=("Segoe UI", 9),
            bg="#fffaf0",
            fg="#c53030",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 12))
        return

    sym = get_currency(user_id)

    tk.Label(
        section,
        text=(
            f"Next calendar month: {result['period_start']} "
            f"→ {result['period_last_day']}\n"
            f"Based on schedule settings as of "
            f"{reference_date.isoformat()}.\n"
            "Independent of the report month selected above."
        ),
        font=("Segoe UI", 9),
        bg="#fffaf0",
        fg="#4a5568",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 8))

    if result["notices"]:
        notice_frame = tk.Frame(section, bg="#fffbeb")
        notice_frame.pack(fill="x", padx=12, pady=(0, 8))

        tk.Label(
            notice_frame,
            text="Excluded or incomplete subscription records",
            font=("Segoe UI", 9, "bold"),
            bg="#fffbeb",
            fg="#975a16"
        ).pack(anchor="w", padx=8, pady=(6, 3))

        for notice in result["notices"]:
            tk.Label(
                notice_frame,
                text=f"• {notice}",
                font=("Segoe UI", 9),
                bg="#fffbeb",
                fg="#975a16",
                wraplength=560,
                justify="left"
            ).pack(anchor="w", padx=8, pady=(0, 5))

    tk.Label(
        section,
        text=(
            "Active schedules successfully evaluated: "
            f"{result['evaluated_active_schedule_count']}\n"
            "Unprocessed occurrences scheduled in this period: "
            f"{result['occurrence_count']}\n"
            "Total scheduled expenses: "
            f"{sym}{result['scheduled_total']:,.2f}"
        ),
        font=("Segoe UI", 10, "bold"),
        bg="#fffaf0",
        fg="#2d3748",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 8))

    if not result["subscriptions"]:
        tk.Label(
            section,
            text=(
                "No active subscription schedules could be evaluated. "
                "Check the notices above and the Subscriptions screen. "
                "This does not establish that you have no subscription costs."
            ),
            font=("Segoe UI", 9),
            bg="#fffaf0",
            fg="#718096",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

    for subscription in result["subscriptions"]:
        card = tk.Frame(section, bg="white", relief="solid", bd=1)
        card.pack(fill="x", padx=12, pady=5)

        tk.Label(
            card,
            text=subscription["name"],
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg="#2d3748",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(10, 4))

        if subscription["scheduled_dates"]:
            date_text = ", ".join(subscription["scheduled_dates"])
        else:
            date_text = "No unprocessed occurrences in this period."

        tk.Label(
            card,
            text=(
                f"Account: {subscription['account_name']}\n"
                f"Current amount per occurrence: "
                f"{sym}{subscription['amount_per_occurrence']:,.2f}\n"
                f"Occurrence count: {subscription['occurrence_count']}\n"
                f"Scheduled total: "
                f"{sym}{subscription['scheduled_total']:,.2f}\n"
                f"Dates: {date_text}"
            ),
            font=("Segoe UI", 9),
            bg="white",
            fg="#4a5568",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 10))

    tk.Label(
        section,
        text=result["suggestion"],
        font=("Segoe UI", 10, "bold"),
        bg="#fffaf0",
        fg="#975a16",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(8, 6))

    tk.Label(
        section,
        text=(
            result["limitation"]
            + " This total may overlap with the seven-day upcoming-expense "
              "section; do not add the two totals together."
        ),
        font=("Segoe UI", 8, "italic"),
        bg="#fffaf0",
        fg="#718096",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 8))

    make_button(
        section,
        "Review Subscriptions",
        lambda: show_subscription_list(user_id),
        color="#dd6b20",
        width=22
    ).pack(anchor="w", padx=12, pady=(0, 12))

def render_needs_wants_reflection(
    parent,
    user_id,
    selected_year,
    selected_month,
    reference_date=None
):
    """
    Displays Need/Want expense information for the selected month.

    Reads data only. Does not change classifications or balances.
    """
    section = tk.Frame(
        parent,
        bg="#f0fff4",
        relief="solid",
        bd=1
    )
    section.pack(fill="x", pady=10)

    tk.Label(
        section,
        text="Selected-Period Needs/Wants Reflection",
        font=("Segoe UI", 12, "bold"),
        bg="#f0fff4",
        fg="#276749"
    ).pack(anchor="w", padx=12, pady=(10, 4))

    try:
        result = get_needs_wants_reflection(
            user_id,
            selected_year,
            selected_month,
            reference_date=reference_date
        )
    except (sqlite3.Error, ValueError, OverflowError) as error:
        tk.Label(
            section,
            text=f"Needs/Wants reflection is unavailable: {error}",
            font=("Segoe UI", 9),
            bg="#f0fff4",
            fg="#c53030",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 12))
        return

    sym = get_currency(user_id)

    tk.Label(
        section,
        text=(
            f"Selected calendar month: {result['period_start']} "
            f"→ {result['period_last_day']}\n"
            f"Recorded expenses counted through: "
            f"{result['counted_through']}"
        ),
        font=("Segoe UI", 9),
        bg="#f0fff4",
        fg="#4a5568",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 8))

    if result["invalid_amount_count"]:
        tk.Label(
            section,
            text=(
                f"Data-quality notice: "
                f"{result['invalid_amount_count']} expense record(s) "
                "with invalid amounts were excluded."
            ),
            font=("Segoe UI", 9),
            bg="#f0fff4",
            fg="#975a16",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

    totals = [
        ("Needs", result["need_total"], "#276749"),
        ("Wants", result["want_total"], "#805ad5"),
        ("Unclassified", result["unclassified_total"], "#975a16"),
        ("Total valid recorded expenses", result["total_expenses"], "#2d3748")
    ]

    for label, amount, color in totals:
        tk.Label(
            section,
            text=f"{label}: {sym}{amount:,.2f}",
            font=("Segoe UI", 10, "bold"),
            bg="#f0fff4",
            fg=color,
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=2)

    if result["classified_total"] > 0:
        tk.Label(
            section,
            text=(
                f"Among classified expenses only "
                f"({sym}{result['classified_total']:,.2f}):\n"
                f"Needs: {result['need_percent_of_classified']:.1f}%\n"
                f"Wants: {result['want_percent_of_classified']:.1f}%"
            ),
            font=("Segoe UI", 9),
            bg="#f0fff4",
            fg="#4a5568",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(8, 4))

    elif result["total_expenses"] > 0:
        tk.Label(
            section,
            text=(
                "No positive expense amount has been classified "
                "as Need or Want, so a classified spending split "
                "cannot be calculated."
            ),
            font=("Segoe UI", 9),
            bg="#f0fff4",
            fg="#718096",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(8, 4))

    else:
        tk.Label(
            section,
            text=(
                "No positive valid expense total was found for this range. "
                "This does not establish that no real spending occurred."
            ),
            font=("Segoe UI", 9),
            bg="#f0fff4",
            fg="#718096",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(8, 4))

    # Provide a review suggestion only when Wants are actually recorded.
    if result["want_total"] > 0:
        tk.Label(
            section,
            text=(
                "If you want to make room for savings or other goals, "
                "consider reviewing expenses you labelled as Wants. "
                "Decide which, if any, can reasonably be reduced."
            ),
            font=("Segoe UI", 10),
            bg="#f0fff4",
            fg="#276749",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(6, 4))

    if result["unclassified_total"] > 0:
        tk.Label(
            section,
            text=(
                "Consider reviewing unclassified expenses to make this "
                "reflection more complete. Unclassified entries include "
                "Not set and any unrecognised stored classification."
            ),
            font=("Segoe UI", 9),
            bg="#f0fff4",
            fg="#975a16",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(4, 6))

    tk.Label(
        section,
        text=(
            result["limitation"]
            + " The percentages above use classified expenses, not income. "
              "They must not be compared directly with the 50/30/20 "
              "income-allocation guideline. Labels are user supplied, "
              "and expenses such as balance adjustments may be included."
        ),
        font=("Segoe UI", 8, "italic"),
        bg="#f0fff4",
        fg="#718096",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(6, 12))

def render_repeated_spending_review(
    parent,
    user_id,
    selected_year,
    selected_month,
    reference_date=None
):
    """
    Displays categories with frequently recorded expense entries
    for the selected report month.

    Reads data only.
    """
    section = tk.Frame(
        parent,
        bg="#fff5f7",
        relief="solid",
        bd=1
    )
    section.pack(fill="x", pady=10)

    tk.Label(
        section,
        text="Selected-Period Repeated Spending Review",
        font=("Segoe UI", 12, "bold"),
        bg="#fff5f7",
        fg="#97266d"
    ).pack(anchor="w", padx=12, pady=(10, 4))

    try:
        result = get_repeated_spending_review(
            user_id,
            selected_year,
            selected_month,
            reference_date=reference_date
        )
    except (sqlite3.Error, ValueError, OverflowError) as error:
        tk.Label(
            section,
            text=f"Repeated spending review is unavailable: {error}",
            font=("Segoe UI", 9),
            bg="#fff5f7",
            fg="#c53030",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 12))
        return

    sym = get_currency(user_id)
    minimum = result["minimum_entries"]

    tk.Label(
        section,
        text=(
            f"Selected calendar month: {result['period_start']} "
            f"→ {result['period_last_day']}\n"
            f"Expense entries counted through: "
            f"{result['counted_through']}"
        ),
        font=("Segoe UI", 9),
        bg="#fff5f7",
        fg="#4a5568",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 6))

    tk.Label(
        section,
        text=(
            f"Showing categories with at least {minimum} positive "
            "expense entries, ranked by recorded total. "
            f"The {minimum}-entry threshold is an application setting, "
            "not a financial standard."
        ),
        font=("Segoe UI", 8, "italic"),
        bg="#fff5f7",
        fg="#718096",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 8))

    if result["invalid_amount_count"]:
        tk.Label(
            section,
            text=(
                "Data-quality notice: "
                f"{result['invalid_amount_count']} expense record(s) "
                "with invalid amounts were excluded."
            ),
            font=("Segoe UI", 9),
            bg="#fff5f7",
            fg="#975a16",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

    reviews = result["reviews"]

    if not reviews:
        tk.Label(
            section,
            text=(
                f"No category reached {minimum} positive expense entries "
                "in this period. This does not mean spending was low."
            ),
            font=("Segoe UI", 10),
            bg="#fff5f7",
            fg="#4a5568",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 10))

    for review in reviews:
        card = tk.Frame(section, bg="white", relief="solid", bd=1)
        card.pack(fill="x", padx=12, pady=5)

        category = review["category"]
        category_label = (
            str(category)
            if category is not None and str(category).strip()
            else "Unnamed category"
        )

        entry_word = (
            "entry" if review["entry_count"] == 1 else "entries"
        )

        tk.Label(
            card,
            text=f"{category_label}: frequently recorded expenses",
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg="#2d3748",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(10, 4))

        tk.Label(
            card,
            text=(
                f"Recorded entries: {review['entry_count']} {entry_word}\n"
                f"Recorded total: {sym}{review['total']:,.2f}\n"
                f"Average per entry: {sym}{review['average']:,.2f}"
            ),
            font=("Segoe UI", 10),
            bg="white",
            fg="#4a5568",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10)

        tk.Label(
            card,
            text=review["suggestion"],
            font=("Segoe UI", 9),
            bg="white",
            fg="#2d3748",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(6, 10))

    if result["eligible_category_count"] > len(reviews):
        hidden = result["eligible_category_count"] - len(reviews)

        tk.Label(
            section,
            text=(
                f"{hidden} additional category(ies) also reached the "
                "entry threshold but are not listed here."
            ),
            font=("Segoe UI", 8, "italic"),
            bg="#fff5f7",
            fg="#718096",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 6))

    tk.Label(
        section,
        text=result["limitation"],
        font=("Segoe UI", 8, "italic"),
        bg="#fff5f7",
        fg="#718096",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(4, 12))

def render_data_quality_panel(parent, user_id, reference_date=None):
    """
    Displays current-data quality notices.

    Reads data only. Does not modify or auto-correct records.
    """
    if reference_date is None:
        reference_date = datetime.today().date()

    section = tk.Frame(
        parent,
        bg="#edf2f7",
        relief="solid",
        bd=1
    )
    section.pack(fill="x", pady=10)

    tk.Label(
        section,
        text="Data Quality Review",
        font=("Segoe UI", 12, "bold"),
        bg="#edf2f7",
        fg="#2d3748"
    ).pack(anchor="w", padx=12, pady=(10, 4))

    try:
        report = get_data_quality_report(
            user_id,
            reference_date=reference_date
        )
    except (sqlite3.Error, ValueError, OverflowError) as error:
        tk.Label(
            section,
            text=f"Data quality review is unavailable: {error}",
            font=("Segoe UI", 9),
            bg="#edf2f7",
            fg="#c53030",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 12))
        return

    tk.Label(
        section,
        text=(
            f"As of {report['as_of']}.\n"
            "Checks are informational and apply to your financial data "
            "inside the app."
        ),
        font=("Segoe UI", 9),
        bg="#edf2f7",
        fg="#4a5568",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 8))

    if not report["issues"]:
        tk.Label(
            section,
            text=(
                "No detectable data issues were found. "
                "This does not establish that your records are complete, "
                "because the app cannot detect transactions you did not record."
            ),
            font=("Segoe UI", 10),
            bg="#edf2f7",
            fg="#2d3748",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 12))
        return

    severity_colors = {
        "info": "#2b6cb0",
        "warning": "#c05621",
        "error": "#c53030"
    }

    screen_actions = {
        "unclassified_expenses": (
            "Review Transactions",
            lambda: show_add_transaction(user_id)
        ),
        "schedules_missing_account": (
            "Review Schedules",
            lambda: show_recurring_transactions(user_id)
        ),
        "unlinked_subscriptions": (
            "Review Subscriptions",
            lambda: show_subscription_list(user_id)
        ),
        "invalid_budget_limits": (
            "Review Budgets",
            lambda: show_budgets(user_id)
        ),
        "negative_account_balances": (
            "Review Accounts",
            lambda: show_account_balance(user_id)
        )
    }

    for issue in report["issues"]:
        card = tk.Frame(section, bg="white", relief="solid", bd=1)
        card.pack(fill="x", padx=12, pady=5)

        color = severity_colors.get(issue["severity"], "#2d3748")

        tk.Label(
            card,
            text=issue["title"],
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg=color,
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(10, 4))

        tk.Label(
            card,
            text=issue["detail"],
            font=("Segoe UI", 10),
            bg="white",
            fg="#4a5568",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 8))

        action = screen_actions.get(issue["key"])

        if action is not None:
            label, callback = action

            make_button(
                card,
                label,
                callback,
                color="#4a5568",
                width=22
            ).pack(anchor="w", padx=10, pady=(0, 10))

    tk.Label(
        section,
        text=report["limitation"],
        font=("Segoe UI", 8, "italic"),
        bg="#edf2f7",
        fg="#718096",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(6, 12))

def show_historical_budget_expenses(user_id, budget_id, month_start_text):
    """
    Displays matching recorded expenses for one historical month.

    Reads data only. Does not edit transactions or balances.
    """
    try:
        detail = get_budget_month_expenses(
            user_id,
            budget_id,
            month_start_text
        )
    except (sqlite3.Error, ValueError, OverflowError) as error:
        messagebox.showerror(
            "Historical Expenses Unavailable",
            str(error),
            parent=root
        )
        return

    sym = get_currency(user_id)

    popup = tk.Toplevel(root)
    popup.title("Historical Budget Expenses")
    popup.geometry("700x600")
    popup.minsize(520, 420)
    popup.configure(bg="#f0f4f8")
    popup.transient(root)

    def close_popup():
        popup.destroy()

    popup.protocol("WM_DELETE_WINDOW", close_popup)
    popup.bind("<Escape>", lambda event: close_popup())

    # Reserve footer space before adding the expanding table.
    footer = tk.Frame(popup, bg="#f0f4f8", pady=8)
    footer.pack(side="bottom", fill="x", padx=15)

    tk.Label(
        footer,
        text=(
            "Read-only view. Select a row to see its notes and reference. "
            "Data is read when this window opens; refresh the Dashboard "
            "after changing financial records."
        ),
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8",
        fg="#718096",
        wraplength=650,
        justify="left"
    ).pack(anchor="w", pady=(0, 6))

    make_button(
        footer,
        "Close",
        close_popup,
        color="#718096",
        width=12
    ).pack()

    header = tk.Frame(popup, bg="#2b6cb0", pady=10)
    header.pack(fill="x")

    tk.Label(
        header,
        text=detail["budget_name"],
        font=("Segoe UI", 14, "bold"),
        bg="#2b6cb0",
        fg="white",
        wraplength=650
    ).pack(padx=10)

    tk.Label(
        header,
        text=(
            f"{detail['month_start']} → {detail['month_last_day']}\n"
            f"Recorded monthly category scope: {detail['category']}"
        ),
        font=("Segoe UI", 9),
        bg="#2b6cb0",
        fg="white",
        wraplength=650
    ).pack(padx=10)

    summary = tk.Frame(popup, bg="white", relief="solid", bd=1)
    summary.pack(fill="x", padx=15, pady=8)

    summary_text = (
        f"Valid recorded expenses: {detail['entry_count']}\n"
        f"Recorded total: {sym}{detail['total']:,.2f}"
    )

    summary_text += (
        f"\nApplicable recorded monthly limit: "
        f"{sym}{detail['applicable_limit']:,.2f}"
        f"\nSettings effective from: "
        f"{detail['settings_effective_month']}"
    )

    if detail["settings_carried_forward"]:
        summary_text += (
            "\nThese settings carry forward from an earlier month."
        )

    tk.Label(
        summary,
        text=summary_text,
        font=("Segoe UI", 10, "bold"),
        bg="white",
        fg="#2d3748",
        justify="left"
    ).pack(anchor="w", padx=10, pady=8)

    tk.Label(
        popup,
        text=detail["limitation"],
        font=("Segoe UI", 8, "italic"),
        bg="#f0f4f8",
        fg="#718096",
        wraplength=650,
        justify="left"
    ).pack(anchor="w", padx=15, pady=(0, 6))

    if detail["invalid_amount_count"]:
        tk.Label(
            popup,
            text=(
                f"{detail['invalid_amount_count']} matching expense "
                "record(s) with invalid amounts were excluded."
            ),
            font=("Segoe UI", 9),
            bg="#f0f4f8",
            fg="#975a16",
            wraplength=650,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 6))

    # Reserve space for selected-row details above the footer.
    selected_detail = tk.Label(
        popup,
        text="Select an expense to inspect its notes and reference.",
        font=("Segoe UI", 9),
        bg="#f0f4f8",
        fg="#4a5568",
        wraplength=650,
        justify="left",
        anchor="w"
    )
    selected_detail.pack(
        side="bottom",
        fill="x",
        padx=15,
        pady=6
    )

    table_frame = tk.Frame(popup, bg="#f0f4f8")
    table_frame.pack(
        fill="both",
        expand=True,
        padx=15,
        pady=(0, 6)
    )
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    columns = (
        "date", "time", "category", "amount", "account", "necessity"
    )

    table = ttk.Treeview(
        table_frame,
        columns=columns,
        show="headings",
        selectmode="browse",
        height=8
    )

    headings = {
        "date": "Date",
        "time": "Time",
        "category": "Category",
        "amount": "Expense",
        "account": "Account",
        "necessity": "Classification"
    }

    widths = {
        "date": 100,
        "time": 65,
        "category": 140,
        "amount": 110,
        "account": 150,
        "necessity": 110
    }

    for column in columns:
        table.heading(column, text=headings[column])
        table.column(
            column,
            width=widths[column],
            minwidth=60,
            anchor="e" if column == "amount" else "w"
        )

    vertical = ttk.Scrollbar(
        table_frame,
        orient="vertical",
        command=table.yview
    )
    horizontal = ttk.Scrollbar(
        table_frame,
        orient="horizontal",
        command=table.xview
    )

    table.configure(
        yscrollcommand=vertical.set,
        xscrollcommand=horizontal.set
    )

    table.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")

    records_by_row = {}

    for index, transaction in enumerate(detail["transactions"]):
        row_id = str(index)
        records_by_row[row_id] = transaction

        table.insert(
            "",
            "end",
            iid=row_id,
            values=(
                transaction["date"],
                transaction["time"],
                transaction["category"],
                f"{sym}{transaction['amount']:,.2f}",
                transaction["account_name"],
                transaction["necessity"].capitalize()
            )
        )

    def show_selected_details(event=None):
        selection = table.selection()

        if not selection:
            return

        transaction = records_by_row[selection[0]]

        selected_detail.config(
            text=(
                f"Notes: {transaction['notes'] or 'None'}\n"
                f"Reference: {transaction['reference'] or 'None'}"
            )
        )

    table.bind("<<TreeviewSelect>>", show_selected_details)

    if not detail["transactions"]:
        selected_detail.config(
            text=(
                "No valid recorded expenses matched this budget "
                "for the selected month. This does not prove "
                "no real spending occurred."
            )
        )

    # No global mouse-wheel binding is installed by this popup.
    # The table has its own scrollbars and native widget scrolling.
    popup.wait_visibility()
    popup.grab_set()


def render_historical_budget_review(
    parent,
    user_id,
    reference_date=None
):
    """
    Displays completed-month spending against recorded monthly settings.

    Reads data only.
    """
    if reference_date is None:
        reference_date = datetime.today().date()

    section = tk.Frame(parent, bg="#f7fafc", relief="solid", bd=1)
    section.pack(fill="x", pady=10)

    tk.Label(
        section,
        text="Past Spending vs Recorded Monthly Limits",
        font=("Segoe UI", 12, "bold"),
        bg="#f7fafc",
        fg="#2c5282"
    ).pack(anchor="w", padx=12, pady=(10, 4))

    try:
        report = get_historical_budget_review(
            user_id,
            reference_date=reference_date
        )
    except (sqlite3.Error, ValueError, OverflowError) as error:
        tk.Label(
            section,
            text=f"Historical budget review is unavailable: {error}",
            font=("Segoe UI", 9),
            bg="#f7fafc",
            fg="#c53030",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 12))
        return

    sym = get_currency(user_id)
    trigger_count = report["trigger_month_count"]
    month_count = report["reviewed_month_count"]

    tk.Label(
        section,
        text=(
            f"Completed months reviewed: "
            f"{report['reviewed_period_start']} "
            f"→ {report['reviewed_period_last_day']}\n"
            f"Monthly budgets found: {report['monthly_budget_count']}\n"
            "Independent of the report month selected above."
        ),
        font=("Segoe UI", 9),
        bg="#f7fafc",
        fg="#4a5568",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 6))

    tk.Label(
        section,
        text=(
            "Each month is compared with the limit and category recorded "
            "for that month. Months without recorded settings are not "
            "compared. A review is suggested when at least "
            f"{trigger_count} month(s) with known settings were above "
            "their applicable limits. This is an application rule, "
            "not a financial standard."
        ),
        font=("Segoe UI", 8, "italic"),
        bg="#f7fafc",
        fg="#718096",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 8))

    if report["notices"]:
        notice_frame = tk.Frame(section, bg="#fffbeb")
        notice_frame.pack(fill="x", padx=12, pady=(0, 8))

        tk.Label(
            notice_frame,
            text="Excluded records and comparison notices",
            font=("Segoe UI", 9, "bold"),
            bg="#fffbeb",
            fg="#975a16"
        ).pack(anchor="w", padx=8, pady=(6, 3))

        for notice in report["notices"]:
            tk.Label(
                notice_frame,
                text=f"• {notice}",
                font=("Segoe UI", 9),
                bg="#fffbeb",
                fg="#975a16",
                wraplength=560,
                justify="left"
            ).pack(anchor="w", padx=8, pady=(0, 5))

    if not report["reviews"]:
        tk.Label(
            section,
            text=(
                "No monthly budgets were available to review. "
                "Weekly, daily, and yearly budgets are not included."
            ),
            font=("Segoe UI", 10),
            bg="#f7fafc",
            fg="#4a5568",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 12))
        return

    for review in report["reviews"]:
        card = tk.Frame(section, bg="white", relief="solid", bd=1)
        card.pack(fill="x", padx=12, pady=5)

        highlight = (
            "#c05621"
            if review["review_recommended"]
            else "#2d3748"
        )

        tk.Label(
            card,
            text=review["name"],
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg=highlight,
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(10, 2))

        tk.Label(
            card,
            text=(
                f"Months with recorded settings: "
                f"{review['months_with_known_settings']} of {month_count}\n"
                f"Months above their applicable limits: "
                f"{review['months_above_limit']}"
            ),
            font=("Segoe UI", 10),
            bg="white",
            fg="#4a5568",
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 6))

        for month in review["months"]:
            period_text = (
                f"{month['period_start']} → {month['period_last_day']}"
            )

            if not month["settings_known"]:
                tk.Label(
                    card,
                    text=(
                        f"{period_text}\n"
                        "Historical budget settings unavailable.\n"
                        "This month is excluded from the limit comparison."
                    ),
                    font=("Segoe UI", 9),
                    bg="white",
                    fg="#718096",
                    wraplength=570,
                    justify="left"
                ).pack(anchor="w", padx=10, pady=(0, 10))
                continue

            difference = month["difference_from_limit"]

            if not month["has_recorded_expenses"]:
                comparison = (
                    "No recorded expenses matched this month's category "
                    "scope. This does not prove no spending occurred."
                )
                month_color = "#718096"

            elif month["above_limit"]:
                comparison = (
                    f"{sym}{difference:,.2f} above the applicable limit"
                )
                month_color = "#c05621"

            elif difference == 0:
                comparison = "Exactly at the applicable limit"
                month_color = "#975a16"

            else:
                comparison = (
                    f"{sym}{abs(difference):,.2f} below the applicable limit"
                )
                month_color = "#276749"

            month_text = (
                f"{period_text}\n"
                f"Recorded category scope: {month['category']}\n"
                f"Applicable limit: "
                f"{sym}{month['applicable_limit']:,.2f}\n"
                f"Recorded spending: {sym}{month['spent']:,.2f} "
                f"({month['valid_entry_count']} entries)\n"
                f"{comparison}"
            )

            if month["settings_carried_forward"]:
                month_text += (
                    "\nSettings carried forward from "
                    f"{month['settings_effective_month']}."
                )

            tk.Label(
                card,
                text=month_text,
                font=("Segoe UI", 9),
                bg="white",
                fg=month_color,
                wraplength=570,
                justify="left"
            ).pack(anchor="w", padx=10, pady=(0, 5))

            make_button(
                card,
                "View Expenses",
                lambda bid=review["budget_id"],
                       month_start=month["period_start"]:
                    show_historical_budget_expenses(
                        user_id,
                        bid,
                        month_start
                    ),
                color="#805ad5",
                width=16
            ).pack(anchor="w", padx=10, pady=(0, 10))

        tk.Label(
            card,
            text=review["suggestion"],
            font=("Segoe UI", 9),
            bg="white",
            fg=highlight,
            wraplength=570,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(4, 8))

        make_button(
            card,
            "Review Budgets",
            lambda: show_budgets(user_id),
            color="#3182ce",
            width=18
        ).pack(anchor="w", padx=10, pady=(0, 10))

    tk.Label(
        section,
        text=report["limitation"],
        font=("Segoe UI", 8, "italic"),
        bg="#f7fafc",
        fg="#718096",
        wraplength=600,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(4, 12))

# ============================================================
# DASHBOARD SCREEN
# ============================================================
# Shows a summary of transactions for a selected month.
# Displays:
#   - A table of all transactions (using pandas DataFrame)
#   - A pie chart: Income vs Expense distribution
#   - A line chart: Income and Expense trend over time
#
# Charts are embedded inside the tkinter window using
# FigureCanvasTkAgg — no separate window pops up.
# ============================================================

def show_dashboard(user_id):
    clear_window()
    award_dashboard_access_badge(user_id)

    background = "#f0f4f8"

    # ── Fixed header ─────────────────────────────────────────
    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")

    tk.Label(
        header,
        text="📈 Dashboard",
        font=("Segoe UI", 16, "bold"),
        fg="white",
        bg="#2b6cb0"
    ).pack()

    # ── Fixed footer: reserve space before expanding content ─
    footer = tk.Frame(root, bg=background, pady=8)
    footer.pack(side="bottom", fill="x", padx=15)

    make_button(
        footer,
        "← Back to Menu",
        lambda: show_main_menu(current_user),
        color="#718096",
        width=18
    ).pack(side="left")

    # ── Report controls ──────────────────────────────────────
    controls = tk.Frame(root, bg=background)
    controls.pack(fill="x", padx=20, pady=10)

    months = [
        "January", "February", "March", "April",
        "May", "June", "July", "August",
        "September", "October", "November", "December"
    ]

    month_numbers = {
        name: index
        for index, name in enumerate(months, start=1)
    }

    today = datetime.today().date()
    month_var = tk.StringVar(value=months[today.month - 1])
    year_var = tk.StringVar(value=str(today.year))

    tk.Label(
        controls,
        text="Report month:",
        font=("Segoe UI", 10, "bold"),
        bg=background
    ).grid(row=0, column=0, sticky="w", padx=(0, 8))

    month_dd = ttk.Combobox(
        controls,
        textvariable=month_var,
        values=months,
        state="readonly",
        width=15
    )
    month_dd.grid(row=0, column=1, sticky="w", padx=(0, 12))

    tk.Label(
        controls,
        text="Year:",
        font=("Segoe UI", 10, "bold"),
        bg=background
    ).grid(row=0, column=2, sticky="w", padx=(0, 8))

    year_dd = ttk.Combobox(
        controls,
        textvariable=year_var,
        values=[
            str(year)
            for year in range(today.year - 2, today.year + 1)
        ],
        state="readonly",
        width=8
    )
    year_dd.grid(row=0, column=3, sticky="w")

    report_label = tk.Label(
        controls,
        text="",
        font=("Segoe UI", 9),
        bg=background,
        fg="#4a5568",
        justify="left",
        wraplength=650
    )
    report_label.grid(
        row=1,
        column=0,
        columnspan=4,
        sticky="w",
        pady=(8, 0)
    )

    # ── Tabs ─────────────────────────────────────────────────
    notebook = ttk.Notebook(root)
    notebook.pack(
        fill="both",
        expand=True,
        padx=15,
        pady=(0, 10)
    )

    overview_tab = tk.Frame(notebook, bg=background)
    period_tab = tk.Frame(notebook, bg=background)
    planning_tab = tk.Frame(notebook, bg=background)

    notebook.add(overview_tab, text="Overview")
    notebook.add(period_tab, text="Period Insights")
    notebook.add(planning_tab, text="Current Planning")

    # Each tab has its own scrollable content.
    overview_body = make_scrollable_frame(overview_tab)
    period_body = make_scrollable_frame(period_tab)
    planning_body = make_scrollable_frame(planning_tab)

    overview_results = tk.Frame(overview_body, bg=background)
    overview_results.pack(fill="x", padx=15, pady=10)

    period_results = tk.Frame(period_body, bg=background)
    period_results.pack(fill="x", padx=15, pady=10)

    planning_results = tk.Frame(planning_body, bg=background)
    planning_results.pack(fill="x", padx=15, pady=10)

    def clear_contents(frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def mark_selection_changed(event=None):
        report_label.config(
            text=(
                "Report selection changed. Click Refresh Dashboard "
                "to load the selected period. Current Planning uses "
                "today's date, independently of this selection."
            ),
            fg="#975a16"
        )

    month_dd.bind("<<ComboboxSelected>>", mark_selection_changed)
    year_dd.bind("<<ComboboxSelected>>", mark_selection_changed)

    def refresh_dashboard():
        selected_month = month_numbers[month_var.get()]
        selected_year = int(year_var.get())
        reference_date = datetime.today().date()

        # Read report data before clearing the current display.
        try:
            with get_db() as conn:
                transactions = conn.execute(
                    '''SELECT category, amount, type, date, time
                       FROM transactions
                       WHERE user_id = ?
                         AND strftime('%m', date) = ?
                         AND strftime('%Y', date) = ?
                       ORDER BY date ASC, time ASC, id ASC''',
                    (
                        user_id,
                        f"{selected_month:02d}",
                        str(selected_year)
                    )
                ).fetchall()

        except sqlite3.Error as error:
            messagebox.showerror(
                "Dashboard Refresh Failed",
                f"Could not load report transactions.\n\n{error}",
                parent=root
            )
            return

        clear_contents(overview_results)
        clear_contents(period_results)
        clear_contents(planning_results)

        selected_label = f"{month_var.get()} {selected_year}"

        report_label.config(
            text=(
                f"Loaded report: {selected_label}. "
                f"Current Planning refreshed as of "
                f"{reference_date.isoformat()}."
            ),
            fg="#4a5568"
        )

        # ── Overview ─────────────────────────────────────────
        tk.Label(
            overview_results,
            text=f"Recorded Overview — {selected_label}",
            font=("Segoe UI", 13, "bold"),
            bg=background,
            fg="#2b6cb0"
        ).pack(anchor="w", pady=(0, 6))

        tk.Label(
            overview_results,
            text=(
                "Shows records dated in the selected calendar month. "
                "Future-dated records, if present, are included here; "
                "current-period insight calculations exclude future dates."
            ),
            font=("Segoe UI", 9),
            bg=background,
            fg="#718096",
            wraplength=650,
            justify="left"
        ).pack(anchor="w", pady=(0, 8))

        sym = get_currency(user_id)

        total_income = sum(
            tx[1] for tx in transactions if tx[2] == "income"
        )
        total_expense = sum(
            tx[1] for tx in transactions if tx[2] == "expense"
        )
        net = total_income - total_expense

        summary = tk.Frame(
            overview_results,
            bg="white",
            relief="solid",
            bd=1
        )
        summary.pack(fill="x", pady=(0, 10))

        summary_rows = [
            ("Recorded income", total_income, "#276749"),
            ("Recorded expenses", total_expense, "#9b2c2c")
        ]

        for label, value, color in summary_rows:
            tk.Label(
                summary,
                text=f"{label}: {sym}{value:,.2f}",
                font=("Segoe UI", 11, "bold"),
                bg="white",
                fg=color
            ).pack(anchor="w", padx=12, pady=5)

        net_label = (
            "Recorded net surplus"
            if net >= 0
            else "Recorded net deficit"
        )

        tk.Label(
            summary,
            text=f"{net_label}: {sym}{abs(net):,.2f}",
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg="#276749" if net >= 0 else "#9b2c2c"
        ).pack(anchor="w", padx=12, pady=(5, 10))

        if transactions:
            # Charts now appear before the detailed table.
            generate_charts(
                transactions,
                overview_results,
                user_id
            )

            tk.Label(
                overview_results,
                text="Transaction Records",
                font=("Segoe UI", 11, "bold"),
                bg=background
            ).pack(anchor="w", pady=(10, 4))

            df = pd.DataFrame(
                transactions,
                columns=["Category", "Amount", "Type", "Date", "Time"]
            )

            table_text = scrolledtext.ScrolledText(
                overview_results,
                height=8,
                width=80,
                font=("Courier New", 9),
                wrap="none"
            )
            table_text.pack(fill="x")
            table_text.insert(tk.END, df.to_string(index=False))
            table_text.config(state="disabled")

        else:
            tk.Label(
                overview_results,
                text=f"No transactions found for {selected_label}.",
                font=("Segoe UI", 10),
                bg=background,
                fg="#718096"
            ).pack(anchor="w", pady=10)

        # ── Selected-period analysis ──────────────────────────
        tk.Label(
            period_results,
            text=f"Period Insights — {selected_label}",
            font=("Segoe UI", 13, "bold"),
            bg=background,
            fg="#2b6cb0"
        ).pack(anchor="w", pady=(0, 6))

        render_category_spending_recommendations(
            period_results,
            user_id,
            selected_year=selected_year,
            selected_month=selected_month,
            reference_date=reference_date
        )

        render_needs_wants_reflection(
            period_results,
            user_id,
            selected_year=selected_year,
            selected_month=selected_month,
            reference_date=reference_date
        )

        render_repeated_spending_review(
            period_results,
            user_id,
            selected_year=selected_year,
            selected_month=selected_month,
            reference_date=reference_date
        )

        # ── Current planning ─────────────────────────────────
        tk.Label(
            planning_results,
            text=f"Current Planning — {reference_date.isoformat()}",
            font=("Segoe UI", 13, "bold"),
            bg=background,
            fg="#2b6cb0"
        ).pack(anchor="w", pady=(0, 4))

        tk.Label(
            planning_results,
            text=(
                "Independent of the selected report month. "
                "Each section states its own planning or review period."
            ),
            font=("Segoe UI", 9),
            bg=background,
            fg="#718096",
            wraplength=650,
            justify="left"
        ).pack(anchor="w", pady=(0, 6))

        render_data_quality_panel(
            planning_results,
            user_id,
            reference_date=reference_date
        )
        render_budget_recommendations(
            planning_results,
            user_id,
            reference_date=reference_date
        )
        render_upcoming_expense_recommendations(
            planning_results,
            user_id,
            reference_date=reference_date
        )
        render_subscription_cost_review(
            planning_results,
            user_id,
            reference_date=reference_date
        )
        render_historical_budget_review(
            planning_results,
            user_id,
            reference_date=reference_date
        )

    make_button(
        footer,
        "Refresh Dashboard",
        refresh_dashboard,
        color="#3182ce",
        width=20
    ).pack(side="right")

    # Open on Overview and load the initial report automatically.
    notebook.select(overview_tab)
    refresh_dashboard()


def generate_charts(transactions, parent_frame, user_id):
    """
    Generates two charts embedded in the tkinter window:
    1. Pie chart  — Income vs Expense split
    2. Line chart — Income and Expense trend over selected month

    FigureCanvasTkAgg embeds matplotlib figures directly
    into a tkinter frame — no popup windows.
    """

    # Separate income and expense data
    income_amounts  = []
    income_dates    = []
    expense_amounts = []
    expense_dates   = []

    for tx in transactions:
        category, amount, tx_type, date, time = tx
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            continue

        if tx_type == "income":
            income_amounts.append(amount)
            income_dates.append(date_obj)
        else:
            expense_amounts.append(amount)
            expense_dates.append(date_obj)

    total_income  = sum(income_amounts)
    total_expense = sum(expense_amounts)

    # Nothing to chart if all zero
    if total_income == 0 and total_expense == 0:
        tk.Label(parent_frame, text="No chart data available.",
                 font=("Segoe UI", 10), bg="#f0f4f8").pack()
        return

    # Create figure with 2 subplots side by side
    # figsize = (width, height) in inches
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    fig.patch.set_facecolor("#f0f4f8")

    # --- Pie Chart (left) ---
    # Shows proportion of income vs expense
    sizes  = [total_income, total_expense]
    # Get the user's chosen currency symbol
    sym = get_currency(user_id)

    labels = [
        f"Income\n{sym}{total_income:,.2f}",     # ← Uses sym not $
        f"Expense\n{sym}{total_expense:,.2f}"     # ← Uses sym not $
    ]
    colors = ["#48bb78", "#fc8181"]

    # Filter out zero values so pie chart doesn't error
    filtered = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0]
    if filtered:
        f_sizes, f_labels, f_colors = zip(*filtered)
        ax1.pie(f_sizes, labels=f_labels, colors=f_colors,
                autopct="%1.1f%%", startangle=90)
    ax1.set_title("Income vs Expense", fontsize=11, fontweight="bold")
    ax1.axis("equal")

    # --- Line Chart (right) ---
    # Shows income and expense amounts plotted over dates
    ax2.set_facecolor("#ffffff")

    if income_dates and income_amounts:
        ax2.plot(income_dates, income_amounts,
                 label="Income", color="#48bb78",
                 marker="o", linewidth=2)

    if expense_dates and expense_amounts:
        ax2.plot(expense_dates, expense_amounts,
                 label="Expense", color="#fc8181",
                 marker="o", linewidth=2)

    # Format x-axis dates
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha="right")

    ax2.set_xlabel("Date", fontsize=9)
    ax2.set_ylabel("Amount ($)", fontsize=9)
    ax2.set_title("Income & Expense Trend", fontsize=11, fontweight="bold")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    # Embed chart into tkinter frame
    # Without FigureCanvasTkAgg, matplotlib would open a separate popup window
    chart_frame = tk.Frame(parent_frame, bg="#f0f4f8")
    chart_frame.pack(fill="both", expand=True, pady=10)

    canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    # Close figure after embedding to free memory
    plt.close(fig)


# ============================================================
# BADGES SCREEN
# ============================================================
# Shows all badges the user has earned.
# Each badge has:
#   - An icon and colour
#   - A name and description
#   - The date it was awarded
#
# Badges are awarded automatically when the user meets
# certain milestones (first account, 10 transactions, etc.)
# ============================================================

# Badge visual styles — maps badge name to display properties
badge_visuals = {
    "5 Day Streak":          {"color": "#c6f6d5", "icon": "🏅", "border": "#38a169"},
    "10 Day Streak":         {"color": "#bee3f8", "icon": "🏆", "border": "#3182ce"},
    "First Account Created": {"color": "#fefcbf", "icon": "💳", "border": "#d69e2e"},
    "5 Accounts Created":    {"color": "#e9d8fd", "icon": "💼", "border": "#805ad5"},
    "First Budget Created":  {"color": "#fed7d7", "icon": "📊", "border": "#e53e3e"},
    "5 Budgets Created":     {"color": "#feebc8", "icon": "📈", "border": "#dd6b20"},
    "10th Transaction":      {"color": "#fed7e2", "icon": "💸", "border": "#d53f8c"},
    "100th Transaction":     {"color": "#fefcbf", "icon": "💰", "border": "#d69e2e"},
    "First Wishlist Item":   {"color": "#c6f6d5", "icon": "📝", "border": "#38a169"},
    "First Dashboard Access":{"color": "#e2e8f0", "icon": "📊", "border": "#718096"},
}


def show_badges(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="🏅 Badges", font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT badge_name, badge_description, date_awarded FROM badges WHERE user_id = ?",
            (user_id,)
        )
        badges = cursor.fetchall()

    if not badges:
        tk.Label(body,
                 text="No badges earned yet.\nKeep using the app to unlock achievements!",
                 font=("Segoe UI", 10), bg="#f0f4f8", fg="#718096",
                 justify="center").pack(pady=20)
    else:
        tk.Label(body, text=f"You have earned {len(badges)} badge(s)!",
                 font=("Segoe UI", 11, "bold"), bg="#f0f4f8",
                 fg="#2b6cb0").pack(pady=(10, 5))

        # Display badges in a grid — 3 per row
        grid_frame = tk.Frame(body, bg="#f0f4f8")
        grid_frame.pack(padx=20, pady=5)

        for i, badge in enumerate(badges):
            badge_name, badge_desc, date_awarded = badge
            visual = badge_visuals.get(
                badge_name,
                {"color": "#e2e8f0", "icon": "⭐", "border": "#718096"}
            )

            # Badge card
            card = tk.Frame(
                grid_frame,
                bg=visual["color"],
                relief="solid", bd=2,
                highlightbackground=visual["border"],
                highlightthickness=2,
                width=180, height=140
            )
            # Place in grid — 3 columns
            row    = i // 3
            column = i % 3
            card.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
            card.grid_propagate(False)

            tk.Label(card, text=visual["icon"],
                     font=("Segoe UI", 28),
                     bg=visual["color"]).pack(pady=(10, 2))
            tk.Label(card, text=badge_name,
                     font=("Segoe UI", 9, "bold"),
                     bg=visual["color"], fg="#2d3748",
                     wraplength=160, justify="center").pack()
            tk.Label(card, text=badge_desc,
                     font=("Segoe UI", 8),
                     bg=visual["color"], fg="#4a5568",
                     wraplength=160, justify="center").pack(pady=2)
            tk.Label(card, text=f"📅 {date_awarded}",
                     font=("Segoe UI", 8, "italic"),
                     bg=visual["color"], fg="#718096").pack()

    make_button(body, "← Back to Menu",
                lambda: show_main_menu(current_user),
                color="#718096").pack(pady=15)


# ============================================================
# BADGE AWARDING LOGIC
# ============================================================
# These functions check milestones and insert badge records
# into the badges table if conditions are met.
#
# Safe whitelist used for entity names to prevent
# SQL injection (fixed from original code).
# ============================================================

ALLOWED_BADGE_ENTITIES = {"accounts", "budgets", "transactions", "wishlist"}


def award_badge(user_id, badge_name, badge_description, threshold, entity="accounts"):
    """
    Awards a badge if:
    1. User does not already have it
    2. Count of rows in entity table equals threshold

    entity must be in ALLOWED_BADGE_ENTITIES whitelist.
    """
    # Whitelist check — prevents SQL injection
    if entity not in ALLOWED_BADGE_ENTITIES:
        return

    with get_db() as conn:
        cursor = conn.cursor()

        # Check if badge already awarded
        cursor.execute(
            "SELECT COUNT(*) FROM badges WHERE user_id = ? AND badge_name = ?",
            (user_id, badge_name)
        )
        if cursor.fetchone()[0] > 0:
            return  # Already has badge — skip

        # Count rows in the relevant table
        # entity is safe — whitelisted above
        cursor.execute(
            f"SELECT COUNT(*) FROM {entity} WHERE user_id = ?",
            (user_id,)
        )
        count = cursor.fetchone()[0]

        # Award if threshold exactly met
        if count >= threshold:
            cursor.execute(
                '''INSERT INTO badges (user_id, badge_name, badge_description, date_awarded)
                   VALUES (?, ?, ?, ?)''',
                (user_id, badge_name, badge_description,
                 datetime.today().strftime("%Y-%m-%d"))
            )
            conn.commit()


def award_streak_badge(user_id, streak_count):
    """Awards streak badges at 5 and 10 day milestones."""

    # Decide which badge to try to give based on streak count
    # If streak is not high enough yet, do nothing
    if streak_count >= 10:
        badge_name = "10 Day Streak"
        badge_desc = "Awarded for logging in 10 consecutive days."
    elif streak_count >= 5:
        badge_name = "5 Day Streak"
        badge_desc = "Awarded for logging in 5 consecutive days."
    else:
        return  # Streak not high enough — exit the function

    # Now check if user already has this badge
    # We never want to give the same badge twice
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM badges WHERE user_id = ? AND badge_name = ?",
            (user_id, badge_name)
        )
        already_has_it = cursor.fetchone()[0] > 0

        if already_has_it:
            return  # They already have it — exit the function

        # If we reach here, they earned it and don't have it yet
        # So give them the badge
        cursor.execute(
            '''INSERT INTO badges
               (user_id, badge_name, badge_description, date_awarded)
               VALUES (?, ?, ?, ?)''',
            (user_id, badge_name, badge_desc,
             datetime.today().strftime("%Y-%m-%d"))
        )
        conn.commit()


def award_dashboard_access_badge(user_id):
    """
    Awards badge for first time visiting dashboard.
    Handled separately because it is not count-based —
    it triggers on the action of visiting the screen.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM badges WHERE user_id = ? AND badge_name = 'First Dashboard Access'",
            (user_id,)
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                '''INSERT INTO badges (user_id, badge_name, badge_description, date_awarded)
                   VALUES (?, ?, ?, ?)''',
                (user_id,
                 "First Dashboard Access",
                 "Awarded for visiting the dashboard for the first time.",
                 datetime.today().strftime("%Y-%m-%d"))
            )
            conn.commit()


def check_and_award_badges(user_id):
    """
    Central badge check called after every major action
    (login, account creation, transaction, etc.)
    Checks all badge conditions in one place.
    """
    # Streak badges
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT streak_count FROM users WHERE id = ?", (user_id,)
        )
        streak_count = cursor.fetchone()[0] or 0

    award_streak_badge(user_id, streak_count)

    # Account badges
    award_badge(
        user_id,
        "First Account Created",
        "Awarded for creating your first account.",
        1,
        "accounts"
    )
    award_badge(
        user_id,
        "5 Accounts Created",
        "Awarded for creating 5 accounts.",
        5,
        "accounts"
    )

    # Budget badges
    award_badge(
        user_id,
        "First Budget Created",
        "Awarded for creating your first budget.",
        1,
        "budgets"
    )
    award_badge(
        user_id,
        "5 Budgets Created",
        "Awarded for creating 5 budgets.",
        5,
        "budgets"
    )

    # Transaction badges
    award_badge(
        user_id,
        "10th Transaction",
        "Awarded for recording your 10th transaction.",
        10,
        "transactions"
    )
    award_badge(
        user_id,
        "100th Transaction",
        "Awarded for recording your 100th transaction.",
        100,
        "transactions"
    )

    # Wishlist badge
    award_badge(
        user_id,
        "First Wishlist Item",
        "Awarded for adding your first wishlist item.",
        1,
        "wishlist"
    )


# ============================================================
# OVERSPENDING ALERTS
# ============================================================
# Checks all budgets for the logged in user and
# shows a popup warning if any budget is:
#   - Over 80%  → Yellow warning
#   - Over 100% → Red exceeded alert
#
# Triggered in two places:
#   1. On login — catches anything that happened
#      since last login (e.g. subscriptions auto-charged)
#   2. After every transaction is added — immediate
#      feedback if a transaction pushes over the limit
#
# Uses a single popup window that lists ALL
# affected budgets at once so user is not
# spammed with multiple popups.
# ============================================================

def check_budget_alerts(user_id):
    """
    Returns alerts for budgets at 80% usage or above.

    Uses actual spending from the shared budget query.
    Distinguishes an exactly reached limit from an exceeded limit.
    """
    budgets = view_budgets(user_id)
    alerts = []
    today = datetime.today().date()

    for budget in budgets:
        budget_id = budget[0]

        (
            transactions,
            spent,
            limit,
            name,
            category,
            timeframe,
            window_start
        ) = get_budget_transactions(
            budget_id,
            user_id,
            reference_date=today
        )

        # Invalid limits cannot support a meaningful usage percentage.
        import math
        if (
            not name
            or not math.isfinite(limit)
            or limit <= 0
            or not math.isfinite(spent)
        ):
            continue

        progress = (spent / limit) * 100

        if spent > limit:
            severity = "exceeded"
        elif spent == limit:
            severity = "at_limit"
        elif progress >= 80:
            severity = "warning"
        else:
            continue

        period_start, period_end, _ = get_budget_period(
            timeframe,
            reference_date=today
        )

        alerts.append({
            "budget_id": budget_id,
            "name": name,
            "category": category,
            "timeframe": timeframe,
            "amount": limit,
            "spent": spent,
            "over": max(spent - limit, 0),
            "remaining": max(limit - spent, 0),
            "progress": progress,
            "severity": severity,
            "period_start": period_start.isoformat(),
            "period_last_day": (
                period_end - timedelta(days=1)
            ).isoformat(),
            "counted_through": today.isoformat()
        })

    return alerts

def show_budget_alert_popup(user_id, alerts):
    """
    Displays calendar-based budget alerts.

    Does not generate transactions or change balances.
    """
    if not alerts:
        return

    sym = get_currency(user_id)
    has_exceeded = any(
        alert["severity"] == "exceeded" for alert in alerts
    )

    popup = tk.Toplevel(root)
    popup.title("Budget Alerts")
    popup.geometry("560x600")
    popup.minsize(460, 420)
    popup.configure(bg="#f0f4f8")
    popup.transient(root)

    def close_popup():
        # The existing scrollable-frame helper uses a global
        # mouse-wheel binding. Clear it before destroying the canvas.
        root.unbind_all("<MouseWheel>")
        popup.destroy()

    def on_view_budgets():
        close_popup()
        show_budgets(user_id)

    popup.protocol("WM_DELETE_WINDOW", close_popup)

    # Reserve footer space before creating the expanding scroll area.
    footer = tk.Frame(popup, bg="#f0f4f8", pady=10)
    footer.pack(side="bottom", fill="x", padx=15)

    advice = (
        "Recorded spending exceeds one or more limits. "
        "Review the contributing transactions and your upcoming spending."
        if has_exceeded else
        "One or more budgets are near or at their limits. "
        "Review upcoming spending before adding further expenses."
    )

    tk.Label(
        footer,
        text=advice,
        font=("Segoe UI", 9, "italic"),
        bg="#f0f4f8",
        fg="#4a5568",
        wraplength=500,
        justify="left"
    ).pack(anchor="w", pady=(0, 8))

    button_row = tk.Frame(footer, bg="#f0f4f8")
    button_row.pack()

    make_button(
        button_row,
        "View Budgets",
        on_view_budgets,
        color="#3182ce",
        width=16
    ).pack(side="left", padx=5)

    make_button(
        button_row,
        "Dismiss",
        close_popup,
        color="#718096",
        width=12
    ).pack(side="left", padx=5)

    header_color = "#e53e3e" if has_exceeded else "#dd6b20"
    header = tk.Frame(popup, bg=header_color, pady=12)
    header.pack(fill="x")

    tk.Label(
        header,
        text="Budget Alerts",
        font=("Segoe UI", 15, "bold"),
        bg=header_color,
        fg="white"
    ).pack()

    tk.Label(
        header,
        text=f"{len(alerts)} budget(s) need your attention",
        font=("Segoe UI", 9),
        bg=header_color,
        fg="white"
    ).pack()

    alert_scroll = make_scrollable_frame(popup)

    status_labels = {
        "exceeded": "BUDGET EXCEEDED",
        "at_limit": "LIMIT REACHED",
        "warning": "APPROACHING LIMIT"
    }

    for alert in alerts:
        severity = alert["severity"]
        exceeded = severity == "exceeded"

        card_bg = "#fff5f5" if exceeded else "#fffbeb"
        status_color = "#c53030" if exceeded else "#975a16"

        card = tk.Frame(
            alert_scroll,
            bg=card_bg,
            relief="solid",
            bd=1
        )
        card.pack(fill="x", padx=15, pady=8)

        tk.Label(
            card,
            text=alert["name"],
            font=("Segoe UI", 12, "bold"),
            bg=card_bg,
            fg="#2d3748",
            wraplength=460,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(10, 2))

        tk.Label(
            card,
            text=status_labels[severity],
            font=("Segoe UI", 10, "bold"),
            bg=card_bg,
            fg=status_color
        ).pack(anchor="w", padx=12, pady=(0, 6))

        tk.Label(
            card,
            text=(
                f"{alert['timeframe']} | {alert['category']}\n"
                f"Calendar period: {alert['period_start']} "
                f"→ {alert['period_last_day']}\n"
                f"Recorded spending through: {alert['counted_through']}"
            ),
            font=("Segoe UI", 9),
            bg=card_bg,
            fg="#4a5568",
            wraplength=460,
            justify="left"
        ).pack(anchor="w", padx=12)

        values = [
            ("Budget limit", alert["amount"]),
            ("Recorded spending", alert["spent"]),
            (
                "Over by" if exceeded else "Remaining",
                alert["over"] if exceeded else alert["remaining"]
            )
        ]

        for label, value in values:
            tk.Label(
                card,
                text=f"{label}: {sym}{value:,.2f}",
                font=("Segoe UI", 10, "bold"),
                bg=card_bg,
                fg=status_color if label != "Budget limit" else "#2d3748"
            ).pack(anchor="w", padx=12, pady=2)

        tk.Label(
            card,
            text=f"Used: {alert['progress']:.1f}%",
            font=("Segoe UI", 9),
            bg=card_bg,
            fg="#4a5568"
        ).pack(anchor="w", padx=12, pady=(6, 2))

        ttk.Progressbar(
            card,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            value=max(0, min(alert["progress"], 100))
        ).pack(fill="x", padx=12, pady=(0, 4))

        tk.Label(
            card,
            text=(
                "Bar scale: 0–100%. "
                "Overspending is shown in the figures above."
            ),
            font=("Segoe UI", 8, "italic"),
            bg=card_bg,
            fg="#718096",
            wraplength=460,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 10))

    # Wait until the popup is visible before taking the modal grab.
    popup.wait_visibility()
    popup.grab_set()

# ============================================================
# SETTINGS SCREEN
# ============================================================
# Currently contains:
#   - Currency selector
# More settings can be added here later
# (dark mode, font size, default account etc.)
# ============================================================

def show_settings(user_id):
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="⚙️ Settings",
             font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)

    # --- Currency Section ---
    section = tk.Frame(body, bg="white", relief="solid", bd=1)
    section.pack(fill="x", pady=10)

    tk.Label(section, text="💱 Currency",
             font=("Segoe UI", 12, "bold"),
             bg="white", fg="#2d3748").pack(anchor="w", padx=15, pady=(12, 4))

    tk.Label(section,
             text="Choose the currency symbol displayed throughout the app.",
             font=("Segoe UI", 9),
             bg="white", fg="#718096").pack(anchor="w", padx=15, pady=(0, 10))

    # Get current setting to pre-select in dropdown
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT currency_symbol, currency_name FROM settings WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        current_symbol = row[0] if row else "$"
        current_name   = row[1] if row else "USD"

    # Find the full label for the current currency
    current_label = next(
        (k for k, v in CURRENCIES.items() if v == current_symbol),
        "USD — US Dollar"
    )

    tk.Label(section, text="Select Currency:",
             font=("Segoe UI", 10, "bold"),
             bg="white").pack(anchor="w", padx=15)

    currency_var = tk.StringVar(value=current_label)
    currency_dd = ttk.Combobox(
        section,
        textvariable=currency_var,
        values=list(CURRENCIES.keys()),
        state="readonly",
        width=35
    )
    currency_dd.pack(anchor="w", padx=15, pady=(4, 8))

    # Live preview — shows symbol as user selects
    preview_label = tk.Label(
        section,
        text=f"Preview: {current_symbol}1,000.00",
        font=("Segoe UI", 11, "bold"),
        bg="white", fg="#2b6cb0"
    )
    preview_label.pack(anchor="w", padx=15, pady=(0, 12))

    def on_currency_change(event=None):
        chosen = currency_var.get()
        symbol = CURRENCIES.get(chosen, "$")
        preview_label.config(text=f"Preview: {symbol}1,000.00")

    currency_dd.bind("<<ComboboxSelected>>", on_currency_change)

    msg_label = tk.Label(body, text="",
                         font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red")
    msg_label.pack(pady=5)

    def on_save():
        chosen = currency_var.get()
        symbol = CURRENCIES.get(chosen, "$")
        # Extract just the code e.g. "USD" from "USD — US Dollar"
        code   = chosen.split(" — ")[0]
        save_currency(user_id, symbol, code)
        msg_label.config(
            text=f"✅ Currency set to {code} ({symbol})",
            fg="green"
        )

    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=10)
    make_button(btn_frame, "✅ Save Settings",
                on_save, color="#38a169").pack(side="left", padx=5)
    make_button(btn_frame, "← Back to Menu",
                lambda: show_main_menu(current_user),
                color="#718096").pack(side="left", padx=5)
    
# ============================================================
# DB MANAGEMENT HELPERS
# ============================================================
# These replace the original Colab-only functions that used
# input() — which does not work in a GUI app.
#
# These are utility functions you can call from a Python
# console or add a hidden admin button for if needed.
# They are NOT shown in the main UI.
# ============================================================

def get_all_usernames():
    """Prints all registered usernames to console."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, email FROM users")
        users = cursor.fetchall()

    if users:
        print("Registered users:")
        for u in users:
            print(f"  - {u[0]}  ({u[1]})")
    else:
        print("No users found.")


def delete_user_by_username(username):
    """
    Permanently deletes a user and their data after confirmation.

    Intended for developer use in a running Tkinter application.
    All database deletions are committed together or rolled back.
    """
    username = username.strip()

    if not username:
        print("No username entered.")
        return False

    # Look up the user without holding a write transaction
    # while waiting for the confirmation dialog.
    with get_db() as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        ).fetchone()

    if user is None:
        print(f"User '{username}' not found.")
        return False

    user_id = user[0]

    confirmed = messagebox.askyesno(
        "Permanently Delete User",
        (
            f"Permanently delete user '{username}' and all their data?\n\n"
            "This includes accounts, transactions, subscriptions, "
            "recurring schedules, processed occurrences, budgets, "
            "categories, wishlist items, badges and settings.\n\n"
            "This cannot be undone."
        )
    )

    if not confirmed:
        print("Deletion cancelled.")
        return False

    try:
        with get_db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            # Confirm the same user still exists after the dialog.
            cursor.execute(
                "SELECT id FROM users WHERE id = ? AND username = ?",
                (user_id, username)
            )

            if cursor.fetchone() is None:
                print(
                    f"User '{username}' no longer exists. Nothing was deleted."
                )
                return False

            for table in USER_DATA_DELETE_ORDER:
                cursor.execute(
                    f'DELETE FROM "{table}" WHERE user_id = ?',
                    (user_id,)
                )

            cursor.execute(
                "DELETE FROM users WHERE id = ?",
                (user_id,)
            )

            conn.commit()

    except sqlite3.Error as error:
        # get_db() closes the connection on exit.
        # An uncommitted deletion transaction is rolled back.
        print(f"Could not delete user '{username}': {error}")
        messagebox.showerror(
            "User Deletion Failed",
            (
                "The deletion was not completed. "
                "Database changes from this attempt were rolled back.\n\n"
                f"Details: {error}"
            )
        )
        return False

    print(f"User '{username}' and their data were deleted successfully.")
    return True


# ============================================================
# APP RUNNER
# ============================================================
# This is the entry point of the entire application.
# When you run the file in VSCode, Python starts here.
#
# Order of operations:
#   1. create_db() — creates database file and tables
#                    if they don't already exist
#   2. launch_app() — opens the tkinter window and
#                     shows the auth choice screen
#
# The if __name__ == "__main__" guard means this code
# only runs when YOU run this file directly.
# It won't run if another file imports this file.
# ============================================================

if __name__ == "__main__":
    create_db()

    # ── Optional admin/dev tools ──────────────────────────
    # Run normally:
    #   python capstone_project_code.py
    #
    # Run dev tools:
    #   python capstone_project_code.py --admin
    #
    # This lets you inspect or clean up the database
    # without touching any code or commenting lines in/out
    # ─────────────────────────────────────────────────────
    if len(sys.argv) > 1 and sys.argv[1] == "--admin":
        print("\n=== ADMIN / DEV TOOLS ===")
        print("1 — List all registered users")
        print("2 — Delete a user by username")
        print("3 — Exit")
        print("─────────────────────────")

        choice = input("Choose an option (1/2/3): ").strip()

        if choice == "1":
            get_all_usernames()

        elif choice == "2":
            username = input("Enter username to delete: ").strip()
            if username:
                delete_user_by_username(username)
            else:
                print("❌ No username entered.")

        elif choice == "3":
            print("Exiting admin mode.")

        else:
            print("❌ Invalid option.")

    else:
        launch_app()   # ← Normal app launch