import os
import datetime
from models import Task, JournalEntry, EmailInfo
import database

def main():
    print("Initializing test database...")
    database.db_init()
    
    db_path = database.get_db_path()
    print(f"Database path: {db_path}")
    print(f"Attachments dir: {database.get_attachments_dir()}")
    
    # 1. Create task 1
    t1 = Task(
        title="Main Project Task",
        main_text="# Main Project\n- [ ] Task 1\n- [ ] Task 2",
        creation_date=datetime.datetime.now().isoformat(),
        due_date=(datetime.datetime.now() + datetime.timedelta(days=7)).isoformat(),
        assigner="Alice",
        co_assignees=["Bob", "Charlie"],
        tags=["work", "programming"],
        emails=[
            EmailInfo(date="2026-06-25", title="FWD: Urgent Specs", people="Alice -> Me")
        ]
    )
    t1_id = database.save_task(t1)
    print(f"Created task 1 with ID: {t1_id}")
    
    # 2. Create task 2 (subtask)
    t2 = Task(
        title="Subtask: Database Design",
        main_text="Need to design schema",
        creation_date=datetime.datetime.now().isoformat(),
        tags=["database", "work"]
    )
    t2_id = database.save_task(t2)
    print(f"Created task 2 with ID: {t2_id}")
    
    # 3. Add dependency t1 depends on t2 (t2 is subtask of t1)
    print("Linking subtask...")
    success = database.add_dependency(parent_id=t1_id, subtask_id=t2_id)
    print(f"Linking parent {t1_id} -> subtask {t2_id} success: {success}")
    
    # Try invalid cycle: make t2 depend on t1 (should fail)
    print("Testing cycle detection (should fail)...")
    fail_link = database.add_dependency(parent_id=t2_id, subtask_id=t1_id)
    print(f"Linking parent {t2_id} -> subtask {t1_id} success: {fail_link}")
    
    # 4. Create journal entry
    j1 = JournalEntry(
        title="Day 1 Coding journal",
        main_text="Started coding the database layer today.",
        creation_date=datetime.datetime.now().isoformat()
    )
    j1_id = database.save_journal_entry(j1)
    print(f"Created journal entry 1 with ID: {j1_id}")
    
    # 5. Link task 1 and journal entry 1
    print("Linking task 1 and journal entry...")
    database.link_task_journal(task_id=t1_id, journal_id=j1_id)
    
    # 6. Retrieve task 1 and check
    retrieved_t1 = database.get_task(t1_id)
    print("\n--- Retrieved Task 1 ---")
    print(f"ID: {retrieved_t1.id}")
    print(f"Title: {retrieved_t1.title}")
    print(f"Assigner: {retrieved_t1.assigner}")
    print(f"Co-assignees: {retrieved_t1.co_assignees}")
    print(f"Tags: {retrieved_t1.tags}")
    print(f"Emails: {retrieved_t1.emails}")
    print(f"Subtask IDs: {retrieved_t1.subtasks}")
    print(f"Journal Entries: {retrieved_t1.journal_entries}")
    
    # Retrieve journal entry
    retrieved_j1 = database.get_journal_entry(j1_id)
    print("\n--- Retrieved Journal Entry ---")
    print(f"ID: {retrieved_j1.id}")
    print(f"Title: {retrieved_j1.title}")
    
    # Retrieve linked items
    linked_j = database.get_journal_entries_for_task(t1_id)
    print(f"Linked journal count for task 1: {len(linked_j)}")
    
    linked_t = database.get_tasks_for_journal_entry(j1_id)
    print(f"Linked tasks count for journal 1: {len(linked_t)}")
    
    # Clean up test entries (Optional, let's keep them so database exists or delete them)
    print("Cleaning up database entries...")
    database.delete_task(t1_id)
    database.delete_task(t2_id)
    database.delete_journal_entry(j1_id)
    print("Test passed successfully!")

if __name__ == "__main__":
    main()
