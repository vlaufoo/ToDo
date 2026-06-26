import os
import sqlite3
import json
import uuid
import shutil
from typing import List, Optional, Tuple
from platformdirs import user_data_dir
from models import Task, JournalEntry, EmailInfo

DB_NAME = "todo.db"
APP_NAME = "MyToDo"

def get_app_dir() -> str:
    """Gets the system-appropriate application directory and creates it."""
    app_dir = user_data_dir(APP_NAME, appauthor=False)
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

def get_db_path() -> str:
    """Gets the database file path."""
    return os.path.join(get_app_dir(), DB_NAME)

def get_attachments_dir() -> str:
    """Gets the attachments directory and creates it."""
    attachments_dir = os.path.join(get_app_dir(), "attachments")
    os.makedirs(attachments_dir, exist_ok=True)
    return attachments_dir

def copy_attachment_to_storage(src_path: str) -> str:
    """
    Copies a file to the attachments directory.
    Returns the relative filename (e.g. 'uuid_filename.ext') stored in DB.
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Source file not found: {src_path}")
    
    filename = os.path.basename(src_path)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    dest_path = os.path.join(get_attachments_dir(), unique_filename)
    shutil.copy2(src_path, dest_path)
    return unique_filename

def get_attachment_absolute_path(relative_filename: str) -> str:
    """Gets the absolute path of an attachment."""
    return os.path.join(get_attachments_dir(), relative_filename)

def get_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database."""
    conn = sqlite3.connect(get_db_path())
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def db_init():
    """Initializes the database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Tasks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        main_text TEXT,
        creation_date TEXT NOT NULL,
        due_date TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        assigner TEXT,
        emails_json TEXT
    );
    """)
    
    # 2. Task attachments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
    );
    """)
    
    # 3. Task dependencies table (Parent-Subtask relationship)
    # parent_task_id represents the task that DEPENDS on subtask_id.
    # Meaning, subtask_id must be completed before parent_task_id.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_dependencies (
        parent_task_id INTEGER NOT NULL,
        subtask_id INTEGER NOT NULL,
        PRIMARY KEY (parent_task_id, subtask_id),
        FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
        FOREIGN KEY (subtask_id) REFERENCES tasks(id) ON DELETE CASCADE
    );
    """)
    
    # 4. Tags table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    """)
    
    # 5. Task Tags link table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_tags (
        task_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        PRIMARY KEY (task_id, tag_id),
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
    );
    """)
    
    # 6. Co-assignees table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS co_assignees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
    );
    """)
    
    # 7. Journal entries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS journal_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        main_text TEXT,
        creation_date TEXT NOT NULL
    );
    """)
    
    # 8. Journal attachments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS journal_attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        journal_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        FOREIGN KEY (journal_id) REFERENCES journal_entries(id) ON DELETE CASCADE
    );
    """)
    
    # 9. Task-Journal links table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_journal_links (
        task_id INTEGER NOT NULL,
        journal_id INTEGER NOT NULL,
        PRIMARY KEY (task_id, journal_id),
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
        FOREIGN KEY (journal_id) REFERENCES journal_entries(id) ON DELETE CASCADE
    );
    """)
    
    conn.commit()
    conn.close()

def check_dependency_cycle(parent_id: int, subtask_id: int) -> bool:
    """
    Checks if making 'subtask_id' a subtask of 'parent_id' creates a cycle.
    A cycle is created if parent_id is already reachable from subtask_id via subtask links.
    Returns True if a cycle would be created, False otherwise.
    """
    if parent_id == subtask_id:
        return True
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # Simple BFS starting from subtask_id to see if we can reach parent_id
    visited = {subtask_id}
    queue = [subtask_id]
    
    while queue:
        current = queue.pop(0)
        # Fetch all subtasks of the current node
        cursor.execute("SELECT subtask_id FROM task_dependencies WHERE parent_task_id = ?", (current,))
        for (child,) in cursor.fetchall():
            if child == parent_id:
                conn.close()
                return True
            if child not in visited:
                visited.add(child)
                queue.append(child)
                
    conn.close()
    return False

def save_task(task: Task) -> int:
    """
    Saves a Task to the database (Insert or Update).
    Handles tags, co-assignees, emails, and attachments.
    Note: Subtask/parent dependencies are managed separately via add_dependency/remove_dependency.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    emails_str = json.dumps([{"date": e.date, "title": e.title, "people": e.people} for e in task.emails])
    
    try:
        if task.id is None:
            # Insert Task
            cursor.execute("""
            INSERT INTO tasks (title, main_text, creation_date, due_date, status, assigner, emails_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task.title, task.main_text, task.creation_date, task.due_date, task.status, task.assigner, emails_str))
            task.id = cursor.lastrowid
        else:
            # Update Task
            cursor.execute("""
            UPDATE tasks
            SET title = ?, main_text = ?, creation_date = ?, due_date = ?, status = ?, assigner = ?, emails_json = ?
            WHERE id = ?
            """, (task.title, task.main_text, task.creation_date, task.due_date, task.status, task.assigner, emails_str, task.id))
            
        task_id = task.id
        
        # Save Co-assignees: clear and re-insert
        cursor.execute("DELETE FROM co_assignees WHERE task_id = ?", (task_id,))
        for name in task.co_assignees:
            cursor.execute("INSERT INTO co_assignees (task_id, name) VALUES (?, ?)", (task_id, name))
            
        # Save Attachments: clear and re-insert
        cursor.execute("DELETE FROM task_attachments WHERE task_id = ?", (task_id,))
        for path in task.attachments:
            cursor.execute("INSERT INTO task_attachments (task_id, file_path) VALUES (?, ?)", (task_id, path))
            
        # Save Tags:
        # First, ensure all tags exist in the tags table
        cursor.execute("DELETE FROM task_tags WHERE task_id = ?", (task_id,))
        for tag in task.tags:
            tag = tag.strip().lower()
            if not tag:
                continue
            cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
            tag_db_id = cursor.fetchone()[0]
            cursor.execute("INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)", (task_id, tag_db_id))
            
        conn.commit()
        return task_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_task(task_id: int) -> Optional[Task]:
    """Retrieves a single task with all relationships."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, title, main_text, creation_date, due_date, status, assigner, emails_json
    FROM tasks WHERE id = ?
    """, (task_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return None
        
    tid, title, main_text, creation_date, due_date, status, assigner, emails_json = row
    
    # Load Co-assignees
    cursor.execute("SELECT name FROM co_assignees WHERE task_id = ?", (task_id,))
    co_assignees = [r[0] for r in cursor.fetchall()]
    
    # Load Attachments
    cursor.execute("SELECT file_path FROM task_attachments WHERE task_id = ?", (task_id,))
    attachments = [r[0] for r in cursor.fetchall()]
    
    # Load Tags
    cursor.execute("""
    SELECT t.name FROM tags t 
    JOIN task_tags tt ON t.id = tt.tag_id 
    WHERE tt.task_id = ?
    """, (task_id,))
    tags = [r[0] for r in cursor.fetchall()]
    
    # Parse Emails
    emails = []
    if emails_json:
        try:
            emails_data = json.loads(emails_json)
            for item in emails_data:
                emails.append(EmailInfo(date=item["date"], title=item["title"], people=item["people"]))
        except Exception:
            pass
            
    # Load Dependencies
    # Subtasks: tasks required to complete task_id
    cursor.execute("SELECT subtask_id FROM task_dependencies WHERE parent_task_id = ?", (task_id,))
    subtasks = [r[0] for r in cursor.fetchall()]
    
    # Parent tasks: tasks that depend on task_id
    cursor.execute("SELECT parent_task_id FROM task_dependencies WHERE subtask_id = ?", (task_id,))
    parent_tasks = [r[0] for r in cursor.fetchall()]
    
    # Load Journal links
    cursor.execute("SELECT journal_id FROM task_journal_links WHERE task_id = ?", (task_id,))
    journal_entries = [r[0] for r in cursor.fetchall()]
    
    conn.close()
    
    return Task(
        id=tid,
        title=title,
        main_text=main_text,
        creation_date=creation_date,
        due_date=due_date,
        status=status,
        assigner=assigner,
        co_assignees=co_assignees,
        tags=tags,
        emails=emails,
        attachments=attachments,
        subtasks=subtasks,
        parent_tasks=parent_tasks,
        journal_entries=journal_entries
    )

def get_all_tasks(tag_filter: Optional[str] = None, status_filter: Optional[str] = None, search_query: Optional[str] = None) -> List[Task]:
    """Retrieves all tasks matching filter criteria."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
    SELECT DISTINCT t.id FROM tasks t
    LEFT JOIN task_tags tt ON t.id = tt.task_id
    LEFT JOIN tags tag ON tt.tag_id = tag.id
    WHERE 1=1
    """
    params = []
    
    if tag_filter:
        query += " AND tag.name = ?"
        params.append(tag_filter.strip().lower())
        
    if status_filter:
        query += " AND t.status = ?"
        params.append(status_filter)
        
    if search_query:
        query += " AND (t.title LIKE ? OR t.main_text LIKE ? OR t.assigner LIKE ?)"
        like_expr = f"%{search_query}%"
        params.extend([like_expr, like_expr, like_expr])
        
    cursor.execute(query, params)
    task_ids = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    # Fetch full object for each task
    tasks = []
    for tid in task_ids:
        task_obj = get_task(tid)
        if task_obj:
            tasks.append(task_obj)
    return tasks

def delete_task(task_id: int):
    """Deletes a task by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def add_dependency(parent_id: int, subtask_id: int) -> bool:
    """
    Links parent_id as depending on subtask_id.
    Ensures cycle is not introduced. Returns True on success, False if cycle detected.
    """
    if check_dependency_cycle(parent_id, subtask_id):
        return False
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO task_dependencies (parent_task_id, subtask_id)
        VALUES (?, ?)
        """, (parent_id, subtask_id))
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def remove_dependency(parent_id: int, subtask_id: int):
    """Removes dependency link between parent and subtask."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    DELETE FROM task_dependencies WHERE parent_task_id = ? AND subtask_id = ?
    """, (parent_id, subtask_id))
    conn.commit()
    conn.close()

def save_journal_entry(entry: JournalEntry) -> int:
    """Saves a JournalEntry to database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if entry.id is None:
            cursor.execute("""
            INSERT INTO journal_entries (title, main_text, creation_date)
            VALUES (?, ?, ?)
            """, (entry.title, entry.main_text, entry.creation_date))
            entry.id = cursor.lastrowid
        else:
            cursor.execute("""
            UPDATE journal_entries
            SET title = ?, main_text = ?, creation_date = ?
            WHERE id = ?
            """, (entry.title, entry.main_text, entry.creation_date, entry.id))
            
        journal_id = entry.id
        
        # Save attachments
        cursor.execute("DELETE FROM journal_attachments WHERE journal_id = ?", (journal_id,))
        for path in entry.attachments:
            cursor.execute("INSERT INTO journal_attachments (journal_id, file_path) VALUES (?, ?)", (journal_id, path))
            
        conn.commit()
        return journal_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_journal_entry(journal_id: int) -> Optional[JournalEntry]:
    """Retrieves a single journal entry."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, title, main_text, creation_date
    FROM journal_entries WHERE id = ?
    """, (journal_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return None
        
    jid, title, main_text, creation_date = row
    
    # Load attachments
    cursor.execute("SELECT file_path FROM journal_attachments WHERE journal_id = ?", (journal_id,))
    attachments = [r[0] for r in cursor.fetchall()]
    
    conn.close()
    
    return JournalEntry(
        id=jid,
        title=title,
        main_text=main_text,
        creation_date=creation_date,
        attachments=attachments
    )

def get_all_journal_entries() -> List[JournalEntry]:
    """Retrieves all journal entries sorted by creation date descending."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM journal_entries ORDER BY creation_date DESC")
    ids = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    entries = []
    for jid in ids:
        entry = get_journal_entry(jid)
        if entry:
            entries.append(entry)
    return entries

def delete_journal_entry(journal_id: int):
    """Deletes a journal entry by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM journal_entries WHERE id = ?", (journal_id,))
    conn.commit()
    conn.close()

def link_task_journal(task_id: int, journal_id: int):
    """Links a task with a journal entry."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR IGNORE INTO task_journal_links (task_id, journal_id)
    VALUES (?, ?)
    """, (task_id, journal_id))
    conn.commit()
    conn.close()

def unlink_task_journal(task_id: int, journal_id: int):
    """Unlinks a task from a journal entry."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    DELETE FROM task_journal_links WHERE task_id = ? AND journal_id = ?
    """, (task_id, journal_id))
    conn.commit()
    conn.close()

def get_journal_entries_for_task(task_id: int) -> List[JournalEntry]:
    """Gets all journal entries linked to a given task."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT journal_id FROM task_journal_links WHERE task_id = ?
    """, (task_id,))
    ids = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    entries = []
    for jid in ids:
        entry = get_journal_entry(jid)
        if entry:
            entries.append(entry)
    return entries

def get_tasks_for_journal_entry(journal_id: int) -> List[Task]:
    """Gets all tasks linked to a given journal entry."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT task_id FROM task_journal_links WHERE journal_id = ?
    """, (journal_id,))
    ids = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    tasks = []
    for tid in ids:
        task_obj = get_task(tid)
        if task_obj:
            tasks.append(task_obj)
    return tasks
