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
    # Step 1: Find user by username only (NOT password)
    # Step 2: Use verify_password() to check the password safely
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

    if user and verify_password(password, user[3]):
        update_streak(user[0])
        check_and_award_badges(user[0])
        # Auto-process any recurring transactions that are due
        process_recurring_transactions(user[0])
        # Schedule budget alert after main menu loads
        # root.after() delays the popup slightly so main menu
        # appears first before the popup shows on top
        root.after(800, lambda: show_budget_alert_popup(
            user[0], check_budget_alerts(user[0])
        ))
        return user
    return None

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

    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

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
        # Unpack all budget fields
        budget_id   = budget[0]
        budget_name = budget[2]
        timeframe   = budget[3]
        start_date  = budget[4]
        end_date    = budget[5]
        category    = budget[6]
        amount      = budget[7]   
        notes       = budget[9] or ""# The budget limit

        # Get progress (now uncapped — can exceed 100)
        progress = calculate_budget_progress(budget_id, user_id)

        # Calculate real money figures
        spent_amount = (progress / 100) * amount
        over_amount  = max(spent_amount - amount, 0)
        remaining    = max(amount - spent_amount, 0)

        # Calculate days remaining in budget period
        today    = datetime.today().date()
        try:
            end_dt   = datetime.strptime(end_date, "%Y-%m-%d").date()
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            days_left  = (end_dt - today).days
            total_days = (end_dt - start_dt).days
        except ValueError:
            days_left  = 0
            total_days = 0

        # Determine severity for colour coding
        if progress >= 100:
            severity     = "exceeded"
            header_bg    = "#e53e3e"   # Red
            card_bg      = "#fff5f5"   # Light red
            border_color = "#fc8181"
            status_icon  = "🔴"
            status_text  = "EXCEEDED"
            status_color = "#e53e3e"
        elif progress >= 80:
            severity     = "warning"
            header_bg    = "#dd6b20"   # Orange
            card_bg      = "#fffbeb"   # Light orange
            border_color = "#f6ad55"
            status_icon  = "🟡"
            status_text  = "APPROACHING LIMIT"
            status_color = "#dd6b20"
        else:
            severity     = "ok"
            header_bg    = "#276749"   # Green
            card_bg      = "#f0fff4"   # Light green
            border_color = "#68d391"
            status_icon  = "🟢"
            status_text  = "ON TRACK"
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

        # Right label — days remaining
        if days_left > 0:
            days_text  = f"⏰ {days_left} day(s) left"
            days_color = "#276749" if days_left > 7 else "#dd6b20"
        elif days_left == 0:
            days_text  = "⏰ Last day!"
            days_color = "#e53e3e"
        else:
            days_text  = "⏰ Period ended"
            days_color = "#718096"

        tk.Label(
            bar_info,
            text=days_text,
            font=("Segoe UI", 9),
            bg=card_bg, fg=days_color
        ).pack(side="right")

        # The progress bar canvas
        bar_canvas = tk.Canvas(
            breakdown,
            width=430, height=22,
            bg="#e2e8f0",
            highlightthickness=0
        )
        bar_canvas.pack(fill="x", pady=(4, 0))

        if severity == "exceeded":
            # Exceeded bar:
            # Split bar — left half shows "limit" zone in medium red
            # Right half shows "overspend" zone in dark red
            # White line in middle marks the budget limit point

            # Calculate where the limit sits proportionally
            # If progress = 715%, then limit is at 100/715 = 14% of the way
            # But we show it at the midpoint for clarity
            limit_x = 215   # Always show limit at midpoint

            # Left zone — "normal spend" up to limit
            bar_canvas.create_rectangle(
                0, 0, limit_x, 22,
                fill="#fc8181",   # Light red
                outline=""
            )

            # Right zone — overspend beyond limit
            bar_canvas.create_rectangle(
                limit_x, 0, 430, 22,
                fill="#e53e3e",   # Dark red
                outline=""
            )

            # White divider line at limit point
            bar_canvas.create_line(
                limit_x, 0, limit_x, 22,
                fill="white", width=3
            )

            # Text labels inside the bar zones
            bar_canvas.create_text(
                limit_x // 2, 11,
                text=f"Limit: {sym}{amount:,.2f}",
                font=("Segoe UI", 8, "bold"),
                fill="white"
            )
            bar_canvas.create_text(
                limit_x + (430 - limit_x) // 2, 11,
                text=f"Over: {sym}{over_amount:,.2f}",
                font=("Segoe UI", 8, "bold"),
                fill="white"
            )

        elif severity == "warning":
            # Warning bar — orange fill showing how much used
            fill_width = int((min(progress, 100) / 100) * 430)
            bar_canvas.create_rectangle(
                0, 0, fill_width, 22,
                fill="#f6ad55",   # Orange
                outline=""
            )
            # Show remaining space in lighter shade
            bar_canvas.create_rectangle(
                fill_width, 0, 430, 22,
                fill="#feebc8",   # Light orange
                outline=""
            )
            bar_canvas.create_text(
                fill_width // 2 if fill_width > 60 else 80, 11,
                text=f"{progress:.1f}% used",
                font=("Segoe UI", 8, "bold"),
                fill="white"
            )

        else:
            # OK bar — green fill
            fill_width = int((progress / 100) * 430)
            bar_canvas.create_rectangle(
                0, 0, fill_width, 22,
                fill="#48bb78",   # Green
                outline=""
            )
            bar_canvas.create_rectangle(
                fill_width, 0, 430, 22,
                fill="#c6f6d5",   # Light green
                outline=""
            )
            if fill_width > 60:
                bar_canvas.create_text(
                    fill_width // 2, 11,
                    text=f"{progress:.1f}% used",
                    font=("Segoe UI", 8, "bold"),
                    fill="white"
                )

        # ── Date info row ─────────────────────────────────────
        date_row = tk.Frame(card, bg=card_bg)
        date_row.pack(fill="x", padx=15, pady=(4, 4))

        tk.Label(
            date_row,
            text=f"📅 Period: {start_date}  →  {end_date}",
            font=("Segoe UI", 8, "italic"),
            bg=card_bg, fg="#718096"
        ).pack(side="left")

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
    Confirmation dialog before deleting a budget.
    Separated from show_budgets to keep it clean.
    """
    confirmed = messagebox.askyesno(
        "Confirm Delete",
        f"Delete budget '{budget_name}'?\n\nThis cannot be undone."
    )
    if confirmed:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM budgets WHERE id = ? AND user_id = ?",
                (budget_id, user_id)
            )
            conn.commit()
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
        text="ℹ️ Changing the timeframe will recalculate the end date from today.",
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

        if new_amount <= 0:
            msg_label.config(
                text="❌ Amount must be greater than 0.", fg="red")
            return

        # Recalculate end date based on new timeframe
        start_date = datetime.today().date()
        if new_timeframe == "Daily":
            end_date = start_date + timedelta(days=1)
        elif new_timeframe == "Weekly":
            end_date = start_date + timedelta(weeks=1)
        elif new_timeframe == "Monthly":
            end_date = start_date + relativedelta(months=1)
        elif new_timeframe == "Yearly":
            end_date = start_date + relativedelta(years=1)
        else:
            end_date = start_date

        # Save changes to database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''UPDATE budgets
                   SET budget_name = ?,
                       timeframe   = ?,
                       category    = ?,
                       amount      = ?,
                       start_date  = ?,
                       end_date    = ?,
                       notes       = ?
                   WHERE id = ? AND user_id = ?''',
                (
                    new_name,
                    new_timeframe,
                    new_category,
                    new_amount,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                    new_notes,
                    budget_id,
                    user_id
                )
            )
            conn.commit()

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


def calculate_budget_progress(budget_id, user_id):
    """
    Calculates % of budget spent.
    Looks at transactions in the current timeframe window only.
    e.g. Monthly budget only counts transactions this month.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT category, amount, timeframe, start_date FROM budgets WHERE id = ?",
            (budget_id,)
        )
        row = cursor.fetchone()
        if not row:
            return 0

        category, total_budget, timeframe, start_date = row
        today = datetime.today()

        # Determine window start based on timeframe
        if timeframe == "Daily":
            window_start = today.strftime("%Y-%m-%d")
        elif timeframe == "Weekly":
            window_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        elif timeframe == "Monthly":
            window_start = today.replace(day=1).strftime("%Y-%m-%d")
        elif timeframe == "Yearly":
            window_start = today.replace(month=1, day=1).strftime("%Y-%m-%d")
        else:
            window_start = start_date

        # General = all expense categories, else filter by specific category
        if category in ("General", ALL_EXPENSE_CATEGORIES):
            cursor.execute(
                "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'expense' AND date >= ?",
                (user_id, window_start)
            )
        else:
            cursor.execute(
                "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'expense' AND category = ? AND date >= ?",
                (user_id, category, window_start)
            )

        total_spent = cursor.fetchone()[0] or 0
        # Removed the min() cap here so alerts can detect over 100%
        return (total_spent / total_budget) * 100 if total_budget else 0

def show_budget_spending(user_id, budget_id):
    """
    Shows a popup listing all transactions that count
    toward the selected budget's progress.
    """
    # Fetch the data using our helper
    (transactions, total_spent, budget_limit,
     budget_name, category, timeframe, window_start) = get_budget_transactions(
        budget_id, user_id
    )

    if not budget_name:
        messagebox.showerror("Error", "Budget not found.")
        return

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

    # ── Header ────────────────────────────────────────────────
    # Colour changes based on severity
    if progress >= 100:
        header_color = "#e53e3e"
        status_text  = "EXCEEDED"
    elif progress >= 80:
        header_color = "#dd6b20"
        status_text  = "APPROACHING LIMIT"
    else:
        header_color = "#276749"
        status_text  = "ON TRACK"

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
        text=f"{timeframe}  |  {category}  |  Since {window_start}",
        font=("Segoe UI", 9),
        bg=header_color, fg="white"
    ).pack()

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
    spent_color = "#e53e3e" if progress >= 100 else "#dd6b20" if progress >= 80 else "#276749"
    tk.Label(spent_col, text=f"{sym}{total_spent:,.2f}",
             font=("Segoe UI", 11, "bold"), bg="white", fg=spent_color).pack()

    tk.Frame(summary_row, bg="#e2e8f0", width=1).pack(
        side="left", fill="y", padx=10)

    # Over / Remaining column
    third_col = tk.Frame(summary_row, bg="white")
    third_col.pack(side="left", expand=True)
    if progress >= 100:
        tk.Label(third_col, text="OVER BY",
                 font=("Segoe UI", 8), bg="white", fg="#718096").pack()
        tk.Label(third_col, text=f"{sym}{over:,.2f}",
                 font=("Segoe UI", 11, "bold"), bg="white", fg="#e53e3e").pack()
    else:
        tk.Label(third_col, text="REMAINING",
                 font=("Segoe UI", 8), bg="white", fg="#718096").pack()
        tk.Label(third_col, text=f"{sym}{remaining:,.2f}",
                 font=("Segoe UI", 11, "bold"), bg="white", fg="#276749").pack()

    # ── Transaction count label ───────────────────────────────
    tk.Label(
        popup,
        text=f"Transactions counted: {len(transactions)}",
        font=("Segoe UI", 9, "italic"),
        bg="#f0f4f8", fg="#718096"
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
            if tx_necessity != "unset":
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

def get_budget_transactions(budget_id, user_id):
    """
    Returns the exact list of expense transactions that
    contribute to a budget's progress calculation.

    Uses the same window_start logic as calculate_budget_progress
    so the numbers always match what the progress bar shows.

    Returns:
        - transactions: list of tuples
          (category, amount, date, time, notes, reference, necessity)
        - total_spent: total amount spent in the window
        - budget_limit: the budget's amount limit
        - budget_name: name of the budget
        - category: budget's category
        - timeframe: budget's timeframe
        - window_start: the date from which spending is counted
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get budget details
        cursor.execute(
            "SELECT budget_name, category, amount, timeframe, start_date FROM budgets WHERE id = ?",
            (budget_id,)
        )
        row = cursor.fetchone()

        if not row:
            return [], 0, 0, "", "", "", ""

        budget_name, category, budget_limit, timeframe, start_date = row
        today = datetime.today()

        # Determine window start — same logic as calculate_budget_progress
        if timeframe == "Daily":
            window_start = today.strftime("%Y-%m-%d")
        elif timeframe == "Weekly":
            window_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        elif timeframe == "Monthly":
            window_start = today.replace(day=1).strftime("%Y-%m-%d")
        elif timeframe == "Yearly":
            window_start = today.replace(month=1, day=1).strftime("%Y-%m-%d")
        else:
            window_start = start_date

        # Fetch matching transactions
        if category in ("General", ALL_EXPENSE_CATEGORIES):
            cursor.execute(
                '''SELECT category, amount, date, time, notes, reference, necessity
                   FROM transactions
                   WHERE user_id = ? AND type = 'expense' AND date >= ?
                   ORDER BY date DESC, time DESC''',
                (user_id, window_start)
            )
        else:
            cursor.execute(
                '''SELECT category, amount, date, time, notes, reference, necessity
                   FROM transactions
                   WHERE user_id = ? AND type = 'expense' AND category = ? AND date >= ?
                   ORDER BY date DESC, time DESC''',
                (user_id, category, window_start)
            )

        transactions = cursor.fetchall()
        total_spent  = sum(t[1] for t in transactions)

    return transactions, total_spent, budget_limit, budget_name, category, timeframe, window_start

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

        if amount <= 0:
            msg_label.config(text="❌ Amount must be greater than 0.", fg="red")
            return

        # Calculate start and end dates based on timeframe
        start_date = datetime.today().date()
        if timeframe == "Daily":
            end_date = start_date + timedelta(days=1)
        elif timeframe == "Weekly":
            end_date = start_date + timedelta(weeks=1)
        elif timeframe == "Monthly":
            end_date = start_date + relativedelta(months=1)
        elif timeframe == "Yearly":
            end_date = start_date + relativedelta(years=1)
        else:
            end_date = start_date

        with get_db() as conn:
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
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                    category,
                    amount,
                    notes
                )
            )
            conn.commit()

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
# process_subscription_transaction() auto-charges today
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

# Whitelist of tables allowed to be cleared when deleting a user
# If a table name is not in this set it will not be touched
ALLOWED_DELETE_TABLES = {
    "transactions",
    "accounts",
    "budgets",
    "categories",
    "subscriptions",
    "wishlist",
    "badges",
    "tags",
    "recurring_transactions",
    "settings"
}

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
                      r.notes, r.tags, r.necessity
               FROM recurring_transactions r
               JOIN accounts a ON r.account_id = a.id
               WHERE r.user_id = ?
               ORDER BY r.next_due_date ASC''',
            (user_id,)
        )
        items = cursor.fetchall()

    if not items:
        tk.Label(body,
                 text="No recurring transactions yet. Add one below!",
                 font=("Segoe UI", 10),
                 bg="#f0f4f8", fg="#718096").pack(pady=10)
    else:
        tk.Label(body,
                 text="✅ These transactions are added automatically when due.",
                 font=("Segoe UI", 9, "italic"),
                 bg="#f0f4f8", fg="#718096").pack(pady=(5, 10))

        for item in items:
            (rec_id, name, tx_type, category,
             amount, frequency, next_due,
             is_active, account_name,
             notes, tags, necessity) = item

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

            # Details row
            sym = get_currency(user_id)
            tk.Label(card,
                     text = f"{frequency}  |  {category}  |  "
                          f"{prefix}{sym}{amount:,.2f}  |  "
                          f"Account: {account_name}  |  "
                          f"Next due: {next_due}",
                     font=("Segoe UI", 9),
                     bg=card_bg, fg="#4a5568").pack(anchor="w", padx=10)

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

            # ── Action buttons row ────────────────────────────
            btn_row = tk.Frame(card, bg=card_bg)
            btn_row.pack(anchor="w", padx=10, pady=(4, 8))

            # View History button — shows all auto-generated transactions
            make_button(
                btn_row, "🔍 View History",
                lambda rid=rec_id, rname=name: show_recurring_history(
                    user_id, rid, rname
                ),
                color="#805ad5", width=16
            ).pack(side="left", padx=3)

            # Edit button — opens edit screen
            make_button(
                btn_row, "✏️ Edit",
                lambda rid=rec_id: show_edit_recurring(user_id, rid),
                color="#3182ce", width=10
            ).pack(side="left", padx=3)

            # Pause / Resume toggle button
            if is_active:
                make_button(
                    btn_row, "⏸️ Pause",
                    lambda rid=rec_id: toggle_recurring(user_id, rid, 0),
                    color="#dd6b20", width=10
                ).pack(side="left", padx=3)
            else:
                make_button(
                    btn_row, "▶️ Resume",
                    lambda rid=rec_id: toggle_recurring(user_id, rid, 1),
                    color="#38a169", width=10
                ).pack(side="left", padx=3)

            # Delete button
            make_button(
                btn_row, "🗑️ Delete",
                lambda rid=rec_id: delete_recurring(user_id, rid),
                color="#e53e3e", width=10
            ).pack(side="left", padx=3)

            # Pause / Resume toggle button
            if is_active:
                make_button(
                    btn_row, "⏸️ Pause",
                    lambda rid=rec_id: toggle_recurring(user_id, rid, 0),
                    color="#dd6b20", width=10
                ).pack(side="left", padx=3)
            else:
                make_button(
                    btn_row, "▶️ Resume",
                    lambda rid=rec_id: toggle_recurring(user_id, rid, 1),
                    color="#38a169", width=10
                ).pack(side="left", padx=3)

            # Delete button
            make_button(
                btn_row, "🗑️ Delete",
                lambda rid=rec_id: delete_recurring(user_id, rid),
                color="#e53e3e", width=10
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
    Shows a popup listing all transactions that were
    generated by a specific recurring transaction rule.

    Matches by searching for the auto tag 'auto:{name}'
    that is saved on every transaction created by
    process_recurring_transactions.
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
                      t.reference, t.necessity, a.account_name
               FROM transactions t
               JOIN accounts a ON t.account_id = a.id
               WHERE t.user_id = ?
               AND t.recurring_rule_id = ?
               ORDER BY t.date DESC, t.time DESC''',
            (user_id, rec_id)
        )
        history = cursor.fetchall()

    # Calculate totals
    total_amount = sum(h[2] for h in history)
    prefix       = "+" if rec_type == "income" else "-"
    type_color   = "#276749" if rec_type == "income" else "#e53e3e"
    status_text  = "🟢 Active" if is_active else "⏸️ Paused"

    # ── Create popup ──────────────────────────────────────────
    popup = tk.Toplevel(root)
    popup.title(f"🔍 {rec_name} — History")
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

    # ── Summary strip ─────────────────────────────────────────
    summary = tk.Frame(popup, bg="white", relief="solid", bd=1)
    summary.pack(fill="x", padx=15, pady=8)

    summary_row = tk.Frame(summary, bg="white")
    summary_row.pack(pady=8)

    # Total column
    total_col = tk.Frame(summary_row, bg="white")
    total_col.pack(side="left", expand=True)
    tk.Label(
        total_col, text="TOTAL RECORDED",
        font=("Segoe UI", 8), bg="white", fg="#718096"
    ).pack()
    tk.Label(
        total_col, text=f"{prefix}{sym}{total_amount:,.2f}",
        font=("Segoe UI", 11, "bold"), bg="white", fg=type_color
    ).pack()

    tk.Frame(summary_row, bg="#e2e8f0", width=1).pack(
        side="left", fill="y", padx=10)

    # Times fired column
    count_col = tk.Frame(summary_row, bg="white")
    count_col.pack(side="left", expand=True)
    tk.Label(
        count_col, text="TIMES FIRED",
        font=("Segoe UI", 8), bg="white", fg="#718096"
    ).pack()
    tk.Label(
        count_col, text=str(len(history)),
        font=("Segoe UI", 11, "bold"), bg="white", fg="#2b6cb0"
    ).pack()

    tk.Frame(summary_row, bg="#e2e8f0", width=1).pack(
        side="left", fill="y", padx=10)

    # Amount per fire column
    per_col = tk.Frame(summary_row, bg="white")
    per_col.pack(side="left", expand=True)
    tk.Label(
        per_col, text="PER OCCURRENCE",
        font=("Segoe UI", 8), bg="white", fg="#718096"
    ).pack()
    tk.Label(
        per_col, text=f"{prefix}{sym}{rec_amount:,.2f}",
        font=("Segoe UI", 11, "bold"), bg="white", fg="#2d3748"
    ).pack()

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
                "No transactions generated yet.\n"
                "This recurring rule has not fired."
            ),
            font=("Segoe UI", 10),
            bg="#f0f4f8", fg="#718096",
            justify="center"
        ).pack(pady=20)
    else:
        for record in history:
            (tx_date, tx_time, tx_amount,
             tx_notes, tx_reference, tx_necessity, tx_account) = record

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
                text=f"{prefix}{sym}{tx_amount:,.2f}",
                font=("Segoe UI", 9, "bold"),
                bg="white", fg=type_color
            ).pack(side="right")

            # Necessity badge — only for expense recurring transactions
            if tx_necessity != "unset":
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

def toggle_recurring(user_id, rec_id, new_status):
    """
    Pauses (0) or resumes (1) a recurring transaction.
    While paused it will not auto-fire on login.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE recurring_transactions SET is_active = ? WHERE id = ? AND user_id = ?",
            (new_status, rec_id, user_id)
        )
        conn.commit()
    show_recurring_transactions(user_id)


def delete_recurring(user_id, rec_id):
    """
    Permanently deletes a recurring transaction.
    Does NOT delete past transactions already added.
    """
    confirmed = messagebox.askyesno(
        "Confirm Delete",
        "Delete this recurring transaction?\n\n"
        "Past transactions already added will not be affected."
    )
    if confirmed:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM recurring_transactions WHERE id = ? AND user_id = ?",
                (rec_id, user_id)
            )
            conn.commit()
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
    clear_window()

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="🔄 Subscriptions", font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    body = make_scrollable_frame(root)  

    # Subscription name
    tk.Label(body, text="Subscription Name:", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    name_entry = make_entry(body)
    name_entry.pack(anchor="w", pady=(2, 10))

    # Category dropdown with Add Category button
    tk.Label(body, text="Category:", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")

    # Horizontal frame for dropdown and button
    cat_row = tk.Frame(body, bg="#f0f4f8")
    cat_row.pack(anchor="w", pady=(2, 10))

    categories = get_expense_categories(user_id)
    category_var = tk.StringVar(value=categories[0] if categories else "General")
    category_dd = ttk.Combobox(cat_row, textvariable=category_var,
                               values=categories, state="readonly", width=25)
    category_dd.pack(side="left")

    # Add Category button — expense categories only for subscriptions
    make_button(
        cat_row, "+ Add Category",
        lambda: open_add_category_popup(
            user_id, "expense", category_dd, category_var
        ),
        color="#3182ce", width=14
    ).pack(side="left", padx=6)

    # Charge dates
    tk.Label(body, text="Charge Dates (comma separated day numbers e.g. 1,15):",
             font=("Segoe UI", 10, "bold"), bg="#f0f4f8").pack(anchor="w")
    dates_entry = make_entry(body)
    dates_entry.pack(anchor="w", pady=(2, 10))

    # Amount
    tk.Label(body, text="Amount ($):", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    amount_entry = make_entry(body)
    amount_entry.pack(anchor="w", pady=(2, 10))

    # ── Notes field ───────────────────────────────────────────
    tk.Label(body, text="Notes (optional):",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    tk.Label(body,
             text="e.g. Student plan, Annual billing, Shared with family",
             font=("Segoe UI", 8, "italic"),
             bg="#f0f4f8", fg="#718096").pack(anchor="w")
    notes_entry = make_entry(body, width=40)
    notes_entry.pack(anchor="w", pady=(2, 10))

    # ── Necessity field ───────────────────────────────────────
    # Subscriptions are always expenses
    tk.Label(body, text="Necessity:",
             font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    tk.Label(body,
             text="Is this subscription a need or a want?",
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

    # Account dropdown
    tk.Label(body, text="Account:", font=("Segoe UI", 10, "bold"),
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

    msg_label = tk.Label(body, text="", font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red", wraplength=400)
    msg_label.pack(pady=5)

    def on_submit():
        name        = name_entry.get().strip()
        category    = category_var.get()
        charge_dates = dates_entry.get().strip()
        account_id  = account_options.get(account_var.get())
        notes       = notes_entry.get().strip()
        necessity   = necessity_var.get()

        # Validate name
        if not name:
            msg_label.config(text="❌ Subscription name cannot be empty.", fg="red")
            return

        # Validate account selected
        if not account_id:
            msg_label.config(text="❌ Please select an account.", fg="red")
            return

        # Validate amount
        try:
            amount = float(amount_entry.get().strip())
        except ValueError:
            msg_label.config(text="❌ Amount must be a valid number.", fg="red")
            return

        if amount <= 0:
            msg_label.config(text="❌ Amount must be greater than 0.", fg="red")
            return

        # Validate charge dates — must be integers between 1 and 31
        try:
            date_list = [int(d.strip()) for d in charge_dates.split(",")]
            if not all(1 <= d <= 31 for d in date_list):
                raise ValueError
        except ValueError:
            msg_label.config(
                text="❌ Charge dates must be numbers between 1 and 31 separated by commas.",
                fg="red"
            )
            return

        with get_db() as conn:
            cursor = conn.cursor()

            # Check subscription limit
            cursor.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE user_id = ?", (user_id,)
            )
            if cursor.fetchone()[0] >= 5:
                msg_label.config(text="❌ Maximum 5 subscriptions reached.", fg="red")
                return

            # Check for duplicate subscription name
            cursor.execute(
                "SELECT 1 FROM subscriptions WHERE user_id = ? AND subscription_name = ?",
                (user_id, name)
            )
            if cursor.fetchone():
                msg_label.config(text="❌ Subscription name already exists.", fg="red")
                return

            # Insert subscription into database with new fields
            cursor.execute(
                '''INSERT INTO subscriptions
                   (user_id, subscription_name, category, amount,
                    charge_dates, notes, necessity)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (user_id, name, category, amount,
                 charge_dates, notes, necessity)
            )
            # Capture the new subscription's ID so we can link
            # any generated transaction back to it
            new_sub_id = cursor.lastrowid
            conn.commit()

        # Auto-charge today if charge date matches
        # Pass the new subscription ID, notes and necessity
        # so the generated transaction is linked correctly
        process_subscription_transaction(
            user_id, new_sub_id, name, category,
            charge_dates, amount, account_id,
            notes, necessity
        )

        msg_label.config(text="✅ Subscription added successfully!", fg="green")
        root.after(1000, lambda: show_subscription_list(user_id))

    # Buttons
    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=10)
    make_button(btn_frame, "✅ Add Subscription",
                on_submit, color="#38a169").pack(side="left", padx=5)
    make_button(btn_frame, "📋 View Subscriptions",
                lambda: show_subscription_list(user_id),
                color="#3182ce").pack(side="left", padx=5)
    make_button(btn_frame, "← Back to Menu",
                lambda: show_main_menu(current_user),
                color="#718096").pack(side="left", padx=5)


def show_subscription_list(user_id):
    clear_window()

    # ── Header ──────────────────────────────────────────────
    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(
        header,
        text="📋 Subscription List",
        font=("Segoe UI", 16, "bold"),
        fg="white", bg="#2b6cb0"
    ).pack()

    # ── Scrollable body ──────────────────────────────────────
    body = make_scrollable_frame(root)
    sym  = get_currency(user_id)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT id, subscription_name, category, amount,
                      charge_dates, notes, necessity
               FROM subscriptions WHERE user_id = ?''',
            (user_id,)
        )
        subscriptions = cursor.fetchall()

    if not subscriptions:
        empty_frame = tk.Frame(body, bg="#f0f4f8")
        empty_frame.pack(pady=40)
        tk.Label(
            empty_frame, text="🔄",
            font=("Segoe UI", 36), bg="#f0f4f8"
        ).pack()
        tk.Label(
            empty_frame, text="No subscriptions yet.",
            font=("Segoe UI", 13, "bold"),
            bg="#f0f4f8", fg="#2d3748"
        ).pack(pady=(5, 2))
        tk.Label(
            empty_frame,
            text="Add a subscription to auto-track recurring charges.",
            font=("Segoe UI", 10),
            bg="#f0f4f8", fg="#718096"
        ).pack()

    # ── Subscription cards ────────────────────────────────────
    for sub in subscriptions:
        (sub_id, sub_name, category, amount,
         charge_dates, notes, necessity) = sub

        # Fallback for rows created before new columns existed
        notes     = notes     or ""
        necessity = necessity or "unset"

        card = tk.Frame(body, bg="white", relief="solid", bd=1)
        card.pack(fill="x", padx=20, pady=6)

        tk.Label(
            card,
            text=f"🔄 {sub_name}",
            font=("Segoe UI", 11, "bold"), bg="white"
        ).pack(anchor="w", padx=10, pady=(8, 2))

        # Main details row
        tk.Label(
            card,
            text=(
                f"Category: {category}  |  "
                f"Amount: {sym}{amount:,.2f}  |  "
                f"Charge Days: {charge_dates}"
            ),
            font=("Segoe UI", 10), bg="white", fg="#4a5568"
        ).pack(anchor="w", padx=10, pady=(0, 2))

        # Notes row — only show if notes exist
        if notes:
            tk.Label(
                card,
                text=f"📝  {notes}",
                font=("Segoe UI", 8, "italic"),
                bg="white", fg="#4a5568",
                wraplength=500, justify="left"
            ).pack(anchor="w", padx=10, pady=(0, 2))

        # Necessity badge — only show if set
        if necessity != "unset":
            nec_bg   = "#e9d8fd" if necessity == "want" else "#c6f6d5"
            nec_text = "🛍️ Want" if necessity == "want" else "✅ Need"
            tk.Label(
                card,
                text=nec_text,
                font=("Segoe UI", 8, "bold"),
                bg=nec_bg, fg="#2d3748",
                relief="solid", bd=1,
                padx=4, pady=1
            ).pack(anchor="w", padx=10, pady=(0, 4))

        # ── Per-card action buttons ────────────────────────────
        action_row = tk.Frame(card, bg="white")
        action_row.pack(anchor="e", padx=10, pady=(0, 8))

        # View Payments button — shows past charges for this subscription
        make_button(
            action_row, "🔍 View Payments",
            lambda sid=sub_id, sname=sub_name: show_subscription_payments(
                user_id, sid, sname
            ),
            color="#805ad5", width=16
        ).pack(side="left", padx=3)

        make_button(
            action_row, "✏️ Edit",
            lambda sid=sub_id: show_edit_subscription(user_id, sid),
            color="#3182ce", width=10
        ).pack(side="left", padx=3)

        make_button(
            action_row, "🗑️ Delete",
            lambda sid=sub_id, sname=sub_name: confirm_delete_subscription(
                user_id, sid, sname
            ),
            color="#e53e3e", width=10
        ).pack(side="left", padx=3)

    # ── Bottom buttons ────────────────────────────────────────
    btn_frame = tk.Frame(body, bg="#f0f4f8")
    btn_frame.pack(pady=15)

    if len(subscriptions) < 5:
        make_button(
            btn_frame, "➕ Add Subscription",
            lambda: show_add_subscription(user_id),
            color="#38a169"
        ).pack(side="left", padx=5)
    else:
        tk.Label(
            body,
            text="⚠️ Maximum 5 subscriptions reached.",
            font=("Segoe UI", 9),
            bg="#f0f4f8", fg="#e53e3e"
        ).pack()

    make_button(
        btn_frame, "← Back to Menu",
        lambda: show_main_menu(current_user),
        color="#718096"
    ).pack(side="left", padx=5)

def confirm_delete_subscription(user_id, sub_id, sub_name):
    """
    Confirmation dialog before deleting a subscription.
    """
    confirmed = messagebox.askyesno(
        "Confirm Delete",
        f"Delete subscription '{sub_name}'?\n\nThis cannot be undone."
    )
    if confirmed:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM subscriptions WHERE id = ? AND user_id = ?",
                (sub_id, user_id)
            )
            conn.commit()
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

def show_edit_subscription(user_id, sub_id):
    """
    Edit screen for a subscription.
    Allows editing name, category, amount and charge dates.
    """
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

def validate_subscription_date(charge_dates):
    """
    Returns only valid day numbers for the current month.
    e.g. If current month is February (28 days),
    day 31 is filtered out automatically.
    """
    today = datetime.today()
    _, last_day = monthrange(today.year, today.month)
    try:
        date_list = [int(d.strip()) for d in charge_dates.split(",")]
    except ValueError:
        return []
    return [d for d in date_list if d <= last_day]


def process_subscription_transaction(user_id, subscription_id, name,
                                     category, charge_dates, amount,
                                     account_id, notes="", necessity="unset"):
    """
    Inserts an expense transaction if today matches one of the
    subscription's charge dates, then deducts from the account.

    The generated transaction stores subscription_id so the
    payment history can reliably find only this subscription's
    charges — not every expense in the same category.
    """
    valid_dates = validate_subscription_date(charge_dates)
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    # Normalise necessity — subscriptions are always expenses
    if necessity not in ("need", "want", "unset"):
        necessity = "unset"

    for charge_date in valid_dates:
        if today.day == charge_date:
            with get_db() as conn:
                cursor = conn.cursor()

                # Prevent charging the same subscription twice
                # on the same day if this runs more than once
                cursor.execute(
                    '''SELECT 1 FROM transactions
                       WHERE user_id = ?
                       AND subscription_id = ?
                       AND date = ?''',
                    (user_id, subscription_id, today_str)
                )
                if cursor.fetchone():
                    # Already charged today — skip
                    continue

                # Build the notes text for the transaction
                tx_notes = f"Subscription: {name}"
                if notes:
                    tx_notes += f" | {notes}"

                # Insert the expense with the subscription link
                cursor.execute(
                    '''INSERT INTO transactions
                       (user_id, category, type, amount,
                        date, time, account_id, notes,
                        necessity, subscription_id)
                       VALUES (?, ?, 'expense', ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        user_id,
                        category,
                        amount,
                        today_str,
                        today.strftime("%H:%M"),
                        account_id,
                        tx_notes,
                        necessity,
                        subscription_id
                    )
                )

                # Deduct from the account balance
                cursor.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                    (amount, account_id)
                )
                conn.commit()


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

    # Award dashboard badge first time user visits
    award_dashboard_access_badge(user_id)

    header = tk.Frame(root, bg="#2b6cb0", pady=12)
    header.pack(fill="x")
    tk.Label(header, text="📈 Dashboard", font=("Segoe UI", 16, "bold"),
             fg="white", bg="#2b6cb0").pack()

    # Wrap everything in scrollable frame
    # so charts don't block the back button
    scroll = make_scrollable_frame(root)

    body = tk.Frame(scroll, bg="#f0f4f8")
    body.pack(fill="x", padx=50, pady=15)

    # Month selector dropdown
    tk.Label(body, text="Select Month:", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")

    months = [
        "January", "February", "March", "April",
        "May", "June", "July", "August",
        "September", "October", "November", "December"
    ]
    month_var = tk.StringVar(value=datetime.today().strftime("%B"))
    month_dd = ttk.Combobox(body, textvariable=month_var,
                            values=months, state="readonly", width=20)
    month_dd.pack(anchor="w", pady=(2, 10))

    # Year selector — show current year and 2 previous years
    current_year = datetime.today().year
    years = [str(y) for y in range(current_year - 2, current_year + 1)]
    tk.Label(body, text="Select Year:", font=("Segoe UI", 10, "bold"),
             bg="#f0f4f8").pack(anchor="w")
    year_var = tk.StringVar(value=str(current_year))
    year_dd = ttk.Combobox(body, textvariable=year_var,
                           values=years, state="readonly", width=10)
    year_dd.pack(anchor="w", pady=(2, 10))

    msg_label = tk.Label(body, text="", font=("Segoe UI", 10),
                         bg="#f0f4f8", fg="red")
    msg_label.pack()

    # Results area — charts and table go here
    # Parent is scroll not root so it scrolls with everything else
    results_frame = tk.Frame(scroll, bg="#f0f4f8")
    results_frame.pack(fill="both", expand=True, padx=20, pady=5)

    def on_show():
        # Clear previous results
        for widget in results_frame.winfo_children():
            widget.destroy()

        month_map = {
            "January": "01", "February": "02", "March": "03",
            "April": "04", "May": "05", "June": "06",
            "July": "07", "August": "08", "September": "09",
            "October": "10", "November": "11", "December": "12"
        }
        selected_month = month_map[month_var.get()]
        selected_year  = year_var.get()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT category, amount, type, date, time
                   FROM transactions
                   WHERE user_id = ?
                   AND strftime('%m', date) = ?
                   AND strftime('%Y', date) = ?
                   ORDER BY date ASC''',
                (user_id, selected_month, selected_year)
            )
            transactions = cursor.fetchall()

        if not transactions:
            tk.Label(results_frame,
                     text=f"No transactions found for {month_var.get()} {selected_year}.",
                     font=("Segoe UI", 10), bg="#f0f4f8", fg="#718096").pack(pady=10)
            return

        # --- Transaction Table using pandas ---
        # pandas DataFrame formats data neatly into rows/columns
        df = pd.DataFrame(
            transactions,
            columns=["Category", "Amount", "Type", "Date", "Time"]
        )

        # Display table inside a scrollable text widget
        table_frame = tk.Frame(results_frame, bg="#f0f4f8")
        table_frame.pack(fill="x", pady=5)

        tk.Label(table_frame, text="📋 Transaction Summary",
                 font=("Segoe UI", 11, "bold"), bg="#f0f4f8").pack(anchor="w")

        # scrolledtext shows the DataFrame as formatted text
        table_text = scrolledtext.ScrolledText(
            table_frame, height=8, width=80,
            font=("Courier New", 9)
        )
        table_text.pack(fill="x")
        table_text.insert(tk.END, df.to_string(index=False))
        table_text.config(state="disabled")  # Read only

        # --- Summary totals ---
        total_income  = df[df["Type"] == "income"]["Amount"].sum()
        total_expense = df[df["Type"] == "expense"]["Amount"].sum()
        net           = total_income - total_expense

        summary_frame = tk.Frame(results_frame, bg="white", relief="solid", bd=1)
        summary_frame.pack(fill="x", padx=5, pady=8)

        sym = get_currency(user_id)
        tk.Label(summary_frame,
                 text=f"  💚 Total Income:   {sym}{total_income:,.2f}",
                 font=("Segoe UI", 10, "bold"), bg="white",
                 fg="#276749").pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(summary_frame,
                 text=f"  🔴 Total Expenses: {sym}{total_expense:,.2f}",
                 font=("Segoe UI", 10, "bold"), bg="white",
                 fg="#9b2c2c").pack(anchor="w", padx=10, pady=2)

        net_color = "#276749" if net >= 0 else "#9b2c2c"
        net_label = "Net Savings" if net >= 0 else "Net Deficit"
        tk.Label(summary_frame,
                 text=f"  {'💰' if net >= 0 else '⚠️'} {net_label}:    {sym}{abs(net):,.2f}",
                 font=("Segoe UI", 10, "bold"), bg="white",
                 fg=net_color).pack(anchor="w", padx=10, pady=(2, 8))

        # --- Generate Charts ---
        generate_charts(transactions, results_frame, user_id)

    make_button(body, "📊 Show Dashboard", on_show, color="#3182ce").pack(pady=8)

    back_btn = tk.Frame(scroll, bg="#f0f4f8")
    back_btn.pack(pady=15)
    make_button(back_btn, "← Back to Menu",
                lambda: show_main_menu(current_user),
                color="#718096").pack()


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
    Checks all budgets and returns a list of alerts.
    Now includes spent amount and overspend amount
    so the popup can show real money figures.
    """
    budgets = view_budgets(user_id)
    alerts = []

    for budget in budgets:
        budget_id   = budget[0]
        budget_name = budget[2]
        timeframe   = budget[3]
        amount      = budget[7]   # The budget limit

        progress = calculate_budget_progress(budget_id, user_id)

        # Calculate actual spent amount from the percentage
        # spent = (progress / 100) * limit
        spent_amount = (progress / 100) * amount

        # Calculate how much over the limit they are
        # If not exceeded this will be 0 or negative
        over_amount = spent_amount - amount

        if progress >= 100:
            alerts.append({
                "name":         budget_name,
                "timeframe":    timeframe,
                "amount":       amount,       # The limit
                "spent":        spent_amount, # How much spent
                "over":         over_amount,  # How much over limit
                "progress":     progress,
                "severity":     "exceeded"
            })
        elif progress >= 80:
            alerts.append({
                "name":         budget_name,
                "timeframe":    timeframe,
                "amount":       amount,
                "spent":        spent_amount,
                "over":         over_amount,
                "progress":     progress,
                "severity":     "warning"
            })

    return alerts

def show_budget_alert_popup(user_id, alerts):
    """
    Shows a popup listing all budgets that need attention.
    Now shows spent amount, limit, and overspend in
    real money figures — not just percentages.
    """
    if not alerts:
        return

    sym = get_currency(user_id)

    # Create popup window
    popup = tk.Toplevel(root)
    popup.title("⚠️ Budget Alert")
    popup.geometry("500x520")
    popup.resizable(False, False)
    popup.configure(bg="#f0f4f8")
    popup.transient(root)
    popup.grab_set()

    # ── Header ──────────────────────────────────────────────
    header_color = "#e53e3e" if any(
        a["severity"] == "exceeded" for a in alerts
    ) else "#dd6b20"

    header = tk.Frame(popup, bg=header_color, pady=12)
    header.pack(fill="x")

    tk.Label(
        header,
        text="⚠️ Budget Alert",
        font=("Segoe UI", 15, "bold"),
        fg="white", bg=header_color
    ).pack()

    tk.Label(
        header,
        text=f"{len(alerts)} budget(s) need your attention",
        font=("Segoe UI", 9),
        fg="white", bg=header_color
    ).pack()

    # ── Scrollable area for alert cards ─────────────────────
    alert_scroll = make_scrollable_frame(popup)

    for alert in alerts:
        name      = alert["name"]
        timeframe = alert["timeframe"]
        amount    = alert["amount"]     # Budget limit
        spent     = alert["spent"]      # Actual amount spent
        over      = alert["over"]       # How much over limit
        progress  = alert["progress"]
        severity  = alert["severity"]

        # ── Card colours based on severity ──────────────────
        if severity == "exceeded":
            card_bg      = "#fff5f5"
            border_color = "#fc8181"
            header_bg    = "#e53e3e"
            icon         = "🔴"
            status_text  = "BUDGET EXCEEDED"
            status_color = "#e53e3e"
        else:
            card_bg      = "#fffbeb"
            border_color = "#f6e05e"
            header_bg    = "#dd6b20"
            icon         = "🟡"
            status_text  = "APPROACHING LIMIT"
            status_color = "#dd6b20"

        # ── Outer card frame ─────────────────────────────────
        card = tk.Frame(
            alert_scroll,
            bg=card_bg,
            relief="solid", bd=1,
            highlightbackground=border_color,
            highlightthickness=2
        )
        card.pack(fill="x", padx=15, pady=8)

        # ── Card header strip ────────────────────────────────
        # Coloured strip at top of card showing status
        card_header = tk.Frame(card, bg=header_bg, pady=6)
        card_header.pack(fill="x")

        tk.Label(
            card_header,
            text=f"{icon}  {name}  —  {status_text}",
            font=("Segoe UI", 11, "bold"),
            bg=header_bg, fg="white"
        ).pack(anchor="w", padx=10)

        tk.Label(
            card_header,
            text=f"Timeframe: {timeframe}",
            font=("Segoe UI", 9),
            bg=header_bg, fg="white"
        ).pack(anchor="w", padx=10)

        # ── Money breakdown table ────────────────────────────
        # This is the main improvement — shows real money figures
        # in a clear table layout so user knows exactly where they stand
        breakdown = tk.Frame(card, bg=card_bg)
        breakdown.pack(fill="x", padx=15, pady=(10, 5))

        # Row helper — creates one row of the breakdown table
        def make_row(parent, label, value, bg,
                     value_color="#2d3748", bold=False):
            row = tk.Frame(parent, bg=bg)
            row.pack(fill="x", pady=1)
            tk.Label(
                row,
                text=label,
                font=("Segoe UI", 10),
                bg=bg, fg="#4a5568",
                width=20, anchor="w"
            ).pack(side="left")
            tk.Label(
                row,
                text=value,
                font=("Segoe UI", 10, "bold" if bold else "normal"),
                bg=bg, fg=value_color
            ).pack(side="left")

        # Budget limit row
        make_row(
            breakdown,
            "Budget limit:",
            f"{sym}{amount:,.2f}",
            card_bg
        )

        # Amount spent row — red if exceeded, orange if warning
        spent_color = "#e53e3e" if severity == "exceeded" else "#dd6b20"
        make_row(
            breakdown,
            "Amount spent:",
            f"{sym}{spent:,.2f}",
            card_bg,
            value_color=spent_color,
            bold=True
        )

        # Divider line between spent and over amount
        ttk.Separator(breakdown, orient="horizontal").pack(
            fill="x", pady=4
        )

        # Over by row — only show if actually exceeded
        if severity == "exceeded":
            make_row(
                breakdown,
                "⚠️  Over by:",
                f"{sym}{over:,.2f}",
                card_bg,
                value_color="#e53e3e",
                bold=True
            )
        else:
            # For warnings show how much is left before hitting limit
            remaining = amount - spent
            make_row(
                breakdown,
                "✅  Remaining:",
                f"{sym}{remaining:,.2f}",
                card_bg,
                value_color="#38a169",
                bold=True
            )

        # ── Percentage label ─────────────────────────────────
        pct_frame = tk.Frame(card, bg=card_bg)
        pct_frame.pack(fill="x", padx=15, pady=(0, 5))
        tk.Label(
            pct_frame,
            text=f"Used {progress:.1f}% of budget",
            font=("Segoe UI", 9, "italic"),
            bg=card_bg, fg="#718096"
        ).pack(anchor="w")

        # ── Progress bar ─────────────────────────────────────
        # Improved version:
        # Shows a marker line at 100% so user can see
        # how far past the limit they are
        bar_outer = tk.Frame(card, bg=card_bg)
        bar_outer.pack(fill="x", padx=15, pady=(0, 10))

        bar_canvas = tk.Canvas(
            bar_outer,
            width=430, height=20,
            bg="#e2e8f0",
            highlightthickness=0
        )
        bar_canvas.pack()

        if severity == "exceeded":
            # For exceeded budgets:
            # Show full red bar to represent 100% used
            # Then show a darker red extension to show overspend
            # The bar splits at the limit point

            # Calculate where the limit line sits
            # Limit line is always at full width (430px)
            # because we show relative overspend
            bar_canvas.create_rectangle(
                0, 0, 430, 20,
                fill="#fc8181",    # Light red = the base spend
                outline=""
            )

            # Dark red fill from left showing proportion
            # that is the "normal" spend up to limit
            # This shows 100% of the bar in darker red
            bar_canvas.create_rectangle(
                0, 0, 430, 20,
                fill="#e53e3e",    # Dark red = fully exceeded
                outline=""
            )

            # Draw a white marker line at the budget limit position
            # This visually shows WHERE the limit was
            bar_canvas.create_line(
                215, 0, 215, 20,   # Midpoint marker
                fill="white",
                width=3
            )

            # Add small labels inside the bar
            bar_canvas.create_text(
                105, 10,
                text="LIMIT",
                font=("Segoe UI", 7, "bold"),
                fill="white"
            )
            bar_canvas.create_text(
                320, 10,
                text=f"OVER: {sym}{over:,.2f}",
                font=("Segoe UI", 7, "bold"),
                fill="white"
            )

        else:
            # For warnings:
            # Show normal fill bar with orange colour
            # Fill width represents what percentage is used
            fill_width = int((min(progress, 100) / 100) * 430)
            bar_canvas.create_rectangle(
                0, 0, fill_width, 20,
                fill="#f6ad55",    # Orange for warning
                outline=""
            )

            # Show remaining space in lighter colour
            remaining_pct = 100 - progress
            tk.Label(
                bar_outer,
                text=f"{remaining_pct:.1f}% remaining before limit",
                font=("Segoe UI", 8),
                bg=card_bg, fg="#718096"
            ).pack(anchor="w", pady=(2, 0))

    # ── Bottom advice message ────────────────────────────────
    advice_frame = tk.Frame(popup, bg="#f0f4f8")
    advice_frame.pack(fill="x", padx=15, pady=(5, 0))

    has_exceeded = any(a["severity"] == "exceeded" for a in alerts)

    if has_exceeded:
        advice_text = (
            "🔴 You have exceeded one or more budgets. "
            "Review your spending and consider adjusting "
            "your budget limits or reducing expenses."
        )
        advice_color = "#e53e3e"
    else:
        advice_text = (
            "🟡 You are approaching your budget limits. "
            "Be mindful of upcoming expenses to stay on track."
        )
        advice_color = "#dd6b20"

    tk.Label(
        advice_frame,
        text=advice_text,
        font=("Segoe UI", 9, "italic"),
        bg="#f0f4f8", fg=advice_color,
        wraplength=460, justify="left"
    ).pack(anchor="w")

    # ── Action buttons ───────────────────────────────────────
    btn_frame = tk.Frame(popup, bg="#f0f4f8")
    btn_frame.pack(pady=12)

    def on_view_budgets():
        popup.destroy()
        show_budgets(user_id)

    make_button(
        btn_frame, "📊 View Budgets",
        on_view_budgets, color="#3182ce"
    ).pack(side="left", padx=5)

    make_button(
        btn_frame, "✖ Dismiss",
        popup.destroy, color="#718096"
    ).pack(side="left", padx=5)

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
    Deletes a user by username.
    Uses messagebox for confirmation — no input() needed.
    Safe to call from a button or console.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if not user:
            print(f"User '{username}' not found.")
            return

        # Use tkinter dialog for confirmation instead of input()
        confirmed = messagebox.askyesno(
            "Confirm Delete",
            f"Permanently delete user '{username}' and all their data?"
        )
        if confirmed:
            user_id = user[0]
            # Delete all related data first (foreign key safety)
            # Loop through the whitelist we defined at the top of the file
            # Only table names in ALLOWED_DELETE_TABLES can be used here
            for table in ALLOWED_DELETE_TABLES:
                cursor.execute(
                    f"DELETE FROM {table} WHERE user_id = ?", (user_id,)
                )
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            print(f"User '{username}' deleted successfully.")
        else:
            print("Deletion cancelled.")


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