from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class EmailInfo:
    date: str  # received/sent date
    title: str
    people: str  # sender/receivers list or description

@dataclass
class JournalEntry:
    id: Optional[int] = None
    title: str = ""
    main_text: str = ""
    creation_date: str = ""  # ISO format string
    attachments: List[str] = field(default_factory=list)  # list of file paths (images/files)

@dataclass
class Task:
    id: Optional[int] = None
    title: str = ""
    main_text: str = ""
    creation_date: str = ""  # ISO format string
    due_date: Optional[str] = None  # ISO format string
    status: str = "pending"  # "pending", "completed"
    assigner: Optional[str] = None
    co_assignees: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    emails: List[EmailInfo] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)  # list of attached images/files
    
    # Relationships (represented by IDs)
    subtasks: List[int] = field(default_factory=list)      # tasks required to complete this task
    parent_tasks: List[int] = field(default_factory=list)  # tasks dependent on this task
    journal_entries: List[int] = field(default_factory=list) # linked journal entry IDs
