import os
import datetime
import shutil
import flet as ft
from models import Task, JournalEntry, EmailInfo
import database
import styles

class TodoApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "My ToDo App"
        
        # Load style config
        self.style_config = styles.load_style_config()
        
        # Configure overall theme based on config
        self.page.theme_mode = ft.ThemeMode.DARK if self.style_config.get("theme_mode") == "dark" else ft.ThemeMode.LIGHT
        self.page.bgcolor = self.style_config.get("bg_color")
        self.page.padding = 0
        
        # Application State
        self.selected_view = "tasks"  # "tasks" or "journal"
        self.selected_task_id = None
        self.selected_journal_id = None
        self.search_query = ""
        self.tag_filter = None
        self.status_filter = "pending"  # "pending", "completed", "all"
        self.available_views = ["tasks", "journal"]
        
        # Edit/Create State
        self.is_editing = False
        self.editing_item_type = None  # "task" or "journal"
        
        # Temp state during editing (for tables/lists that are dynamic)
        self.temp_emails = []
        self.temp_attachments = []
        
        # Initialize Database
        database.db_init()
        
        # Setup Date Picker
        self.date_picker = ft.DatePicker(on_change=self.on_date_picker_result)
        self.page.overlay.append(self.date_picker)

        self.page.on_keyboard_event = self.global_key_handler
        
        # Build UI layout
        self.build_ui()

    def build_ui(self):
        # 1. Sidebar (Left)
        self.sidebar = self.create_sidebar()
        
        # 2. Main List Panel (Center)
        self.list_panel = self.create_list_panel()
        
        # 3. Detail/Edit Panel (Right)
        self.detail_panel = self.create_detail_panel()
        
        # Assemble Main Layout
        self.main_layout = ft.Row(
            controls=[
                self.sidebar,
                self.list_panel,
                self.detail_panel
            ],
            expand=True,
            spacing=0
        )

        self.page.add(self.main_layout)



    # ==========================================
    # UI Component Creators
    # ==========================================
    
    def create_sidebar(self) -> ft.Container:
        # Title Header
        header = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.CHECKLIST_ROUNDED, color=self.style_config["primary_color"], size=30),
                    ft.Text("MyToDo", size=22, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"])
                ],
                alignment=ft.MainAxisAlignment.START
            ),
            padding=ft.Padding.only(bottom=20, top=10)
        )
        
        # Navigation Items
        self.nav_tasks = self.create_nav_button("Tasks", ft.Icons.TASK_ALT_ROUNDED, "tasks", True)
        self.nav_journal = self.create_nav_button("Journal", ft.Icons.BOOK_ROUNDED, "journal", False)
        
        # Task Sub-filters (Status)
        self.task_subfilters_container = ft.Column(
            controls=[
                self.create_subfilter_button("Pending Tasks", ft.Icons.PENDING_ACTIONS, "pending", True),
                self.create_subfilter_button("Completed Tasks", ft.Icons.DONE_ALL, "completed", False),
                self.create_subfilter_button("All Tasks", ft.Icons.LIST_ALT, "all", False),
            ],
            spacing=5,
            visible=True
        )
        
        # Tag Cloud
        self.tag_list = ft.Column(spacing=5)
        self.update_tag_cloud()
        
        tag_section = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Divider(height=20, color=self.style_config["card_bg_color"]),
                    ft.Text("CATEGORIES / TAGS", size=11, color=self.style_config["text_muted"], weight=ft.FontWeight.BOLD),
                    self.tag_list
                ]
            ),
            padding=ft.Padding.only(top=10)
        )
        
        # Action Buttons
        btn_new_task = ft.Container(
            content=ft.Button(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ADD, size=18, color=ft.Colors.WHITE),
                        ft.Text("New Task", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                style=ft.ButtonStyle(
                    bgcolor=self.style_config["primary_color"],
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=self.on_new_task_clicked,
                height=45
            ),
            padding=ft.Padding.only(top=20)
        )
        
        btn_new_journal = ft.Container(
            content=ft.OutlinedButton(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ADD_BOX_OUTLINED, size=18, color=self.style_config["primary_color"]),
                        ft.Text("New Journal", weight=ft.FontWeight.BOLD, color=self.style_config["primary_color"])
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                style=ft.ButtonStyle(
                    side=ft.BorderSide(color=self.style_config["primary_color"]),
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=self.on_new_journal_clicked,
                height=45
            ),
            padding=ft.Padding.only(top=10)
        )

        btn_calendar = ft.Container(
            content=ft.OutlinedButton(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CALENDAR_MONTH, size=18, color=self.style_config["primary_color"]),
                        ft.Text("Calendar View", weight=ft.FontWeight.BOLD, color=self.style_config["primary_color"])
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                style=ft.ButtonStyle(
                    side=ft.BorderSide(color=self.style_config["primary_color"]),
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=self.on_new_journal_clicked,
                height=45
            ),
            padding=ft.Padding.only(top=10)
        )
        
        # Sidebar Assembly
        sidebar_content = ft.Column(
            controls=[
                header,
                self.nav_tasks,
                self.task_subfilters_container,
                self.nav_journal,
                btn_new_task,
                btn_new_journal,
                tag_section,
                btn_calendar
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        return ft.Container(
            content=sidebar_content,
            width=260,
            bgcolor=self.style_config["bg_color"],
            border=ft.Border.only(right=ft.BorderSide(1, self.style_config["card_bg_color"])),
            padding=20
        )

    def create_list_panel(self) -> ft.Container:
        # Search Bar
        self.search_field = ft.TextField(
            hint_text="Search tasks or assigner...",
            prefix_icon=ft.Icons.SEARCH,
            bgcolor=self.style_config["card_bg_color"],
            border_radius=8,
            border_color=ft.Colors.TRANSPARENT,
            text_size=14,
            content_padding=10,
            on_change=self.on_search_changed,
            expand=True
        )
        
        # Clear filter banner
        self.filter_banner = ft.Row(
            controls=[
                ft.Text("Filter: ", size=12, color=self.style_config["text_muted"]),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text("Tag", size=11, color=ft.Colors.WHITE),
                            ft.IconButton(ft.Icons.CLOSE, icon_color=ft.Colors.WHITE, on_click=self.clear_tag_filter, padding=0)
                        ]
                    ),
                    bgcolor=self.style_config["primary_color"],
                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                    border_radius=12
                )
            ],
            visible=False
        )
        
        search_row = ft.Row(
            controls=[self.search_field]
        )
        
        # Cards Container
        self.cards_list = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=10,
            expand=True
        )
        
        list_content = ft.Column(
            controls=[
                search_row,
                self.filter_banner,
                ft.Container(height=10),
                self.cards_list
            ],
            expand=True
        )
        
        self.refresh_list()
        
        return ft.Container(
            content=list_content,
            width=360,
            bgcolor=self.style_config["bg_color"],
            border=ft.Border.only(right=ft.BorderSide(1, self.style_config["card_bg_color"])),
            padding=15
        )

    def create_detail_panel(self) -> ft.Container:
        self.detail_container = ft.Container(
            content=self.create_empty_state(),
            expand=True,
            bgcolor=self.style_config["card_bg_color"],
            padding=20,
            border_radius=ft.BorderRadius.only(top_left=12, bottom_left=12)
        )
        return self.detail_container

    # ==========================================
    # Helper Component Builders
    # ==========================================

    def create_nav_button(self, text: str, icon: str, view_name: str, active: bool) -> ft.Container:
        color = self.style_config["primary_color"] if active else ft.Colors.TRANSPARENT
        text_color = self.style_config["text_color"] if active else self.style_config["text_muted"]
        
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=text_color, size=20),
                    ft.Text(text, color=text_color, weight=ft.FontWeight.BOLD, size=15)
                ],
                spacing=10
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            bgcolor=color,
            border_radius=8,
            on_click=lambda e: self.on_nav_clicked(view_name),
        )

    def create_subfilter_button(self, text: str, icon: str, status_val: str, active: bool) -> ft.Container:
        text_color = self.style_config["primary_color"] if active else self.style_config["text_muted"]
        
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=text_color, size=16),
                    ft.Text(text, color=text_color, size=13, weight=ft.FontWeight.W_600)
                ],
                spacing=8
            ),
            padding=ft.Padding.only(left=30, top=6, bottom=6, right=10),
            on_click=lambda e: self.on_status_filter_clicked(status_val),
        )

    def create_empty_state(self) -> ft.Column:
        return ft.Column(
            controls=[
                ft.Icon(ft.Icons.TASK_ROUNDED, size=80, color=self.style_config["text_muted"]),
                ft.Text("No task or journal entry selected", size=16, color=self.style_config["text_muted"], weight=ft.FontWeight.BOLD),
                ft.Text("Click on any item in the list or create a new one to view details.", size=12, color=self.style_config["text_muted"])
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True
        )

    # ==========================================
    # State updates and events
    # ==========================================
    def global_key_handler(self, e: ft.KeyboardEvent):
        
        if not self.is_editing:
            if e.ctrl and e.key.lower() == "tab":
                current_index = self.available_views.index(self.selected_view)
                next_index = (current_index + 1) % len(self.available_views)
                new_view = self.available_views[next_index]
                self.on_nav_clicked(view_name=new_view)
            elif e.ctrl and e.key.lower() == "n":
                if self.selected_view == "tasks":
                    self.on_new_task_clicked()
                elif self.selected_view == "journal":
                    self.on_new_journal_clicked()
                    

        elif self.is_editing:
            if self.selected_view == "tasks":
                if e.ctrl and e.key.lower() == "s":
                    self.on_save_task_clicked()
                elif e.key.lower() == "escape":
                    self.on_cancel_edit_clicked()


        ## Action behavior depending on current route
        #if self.selected_view == "tasks":
        #        # Actions while browsing the list
        #    if e.key.lower() == "n":
        #            page.route = "/add"
        #            render_view()
        #        elif e.key.lower() == "q":
        #            page.window_close()
        #            
        #    elif self.slected_view = "journal":
        #        # Actions while typing / interacting with add form
        #        if e.key == "Enter":
        #            # Execute the save action we bound to page data
        #            if "save_action" in page.data:
        #                page.data["save_action"]()
        #        elif e.key == "Escape":
        #            page.route = "/"
        #            render_view()
    

    def on_nav_clicked(self, view_name: str):
        self.selected_view = view_name
        self.is_editing = False
        self.selected_task_id = None
        self.selected_journal_id = None
        
        # Toggle sub-filters visibility
        self.task_subfilters_container.visible = (view_name == "tasks")
        self.search_field.hint_text = "Search tasks..." if view_name == "tasks" else "Search journals..."
        
        self.refresh_sidebar_nav()
        self.refresh_list()
        self.show_details()
        self.page.update()

    def on_status_filter_clicked(self, status_val: str):
        self.status_filter = status_val
        self.refresh_sidebar_nav()
        self.refresh_list()
        self.page.update()

    def refresh_sidebar_nav(self):
        # Update active colors on main nav buttons
        self.nav_tasks.bgcolor = self.style_config["primary_color"] if self.selected_view == "tasks" else ft.Colors.TRANSPARENT
        self.nav_tasks.content.controls[0].color = self.style_config["text_color"] if self.selected_view == "tasks" else self.style_config["text_muted"]
        self.nav_tasks.content.controls[1].color = self.style_config["text_color"] if self.selected_view == "tasks" else self.style_config["text_muted"]
        
        self.nav_journal.bgcolor = self.style_config["primary_color"] if self.selected_view == "journal" else ft.Colors.TRANSPARENT
        self.nav_journal.content.controls[0].color = self.style_config["text_color"] if self.selected_view == "journal" else self.style_config["text_muted"]
        self.nav_journal.content.controls[1].color = self.style_config["text_color"] if self.selected_view == "journal" else self.style_config["text_muted"]
        
        # Update task sub-filters active color
        for control in self.task_subfilters_container.controls:
            # We determine status_val from the button text
            btn_text = control.content.controls[1].value
            is_active = False
            if "Pending" in btn_text and self.status_filter == "pending":
                is_active = True
            elif "Completed" in btn_text and self.status_filter == "completed":
                is_active = True
            elif "All" in btn_text and self.status_filter == "all":
                is_active = True
                
            text_color = self.style_config["primary_color"] if is_active else self.style_config["text_muted"]
            control.content.controls[0].color = text_color
            control.content.controls[1].color = text_color

    def update_tag_cloud(self):
        self.tag_list.controls.clear()
        
        # Get all tasks to extract unique tags
        tasks_list = database.get_all_tasks()
        all_tags = set()
        for t in tasks_list:
            for tag in t.tags:
                all_tags.add(tag)
                
        if not all_tags:
            self.tag_list.controls.append(
                ft.Text("No tags created yet", size=12, italic=True, color=self.style_config["text_muted"])
            )
            return
            
        for tag in sorted(all_tags):
            is_selected = (self.tag_filter == tag)
            bg = self.style_config["primary_color"] if is_selected else self.style_config["card_bg_color"]
            fg = ft.Colors.WHITE if is_selected else self.style_config["text_color"]
            
            self.tag_list.controls.append(
                ft.Container(
                    content=ft.Text(f"# {tag}", size=12, color=fg, weight=ft.FontWeight.W_600),
                    bgcolor=bg,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    border_radius=6,
                    on_click=lambda e, t=tag: self.on_tag_clicked(t),
                )
            )

    def on_tag_clicked(self, tag: str):
        if self.tag_filter == tag:
            self.tag_filter = None  # toggle off
        else:
            self.tag_filter = tag
            
        self.update_tag_cloud()
        self.refresh_list()
        self.page.update()

    def clear_tag_filter(self, e):
        self.tag_filter = None
        self.update_tag_cloud()
        self.refresh_list()
        self.page.update()

    def on_search_changed(self, e):
        self.search_query = e.control.value
        self.refresh_list()
        self.page.update()

    def refresh_list(self):
        self.cards_list.controls.clear()
        
        # Check active tag filter visibility
        if self.tag_filter:
            self.filter_banner.controls[1].content.controls[0].value = f"Tag: #{self.tag_filter}"
            self.filter_banner.visible = True
        else:
            self.filter_banner.visible = False
            
        if self.selected_view == "tasks":
            # Query Tasks
            tasks_list = database.get_all_tasks(
                tag_filter=self.tag_filter,
                status_filter=None if self.status_filter == "all" else self.status_filter,
                search_query=self.search_query if self.search_query else None
            )
            
            if not tasks_list:
                self.cards_list.controls.append(
                    ft.Container(
                        content=ft.Text("No tasks found", color=self.style_config["text_muted"]),
                        alignment=ft.Alignment.CENTER,
                        padding=40
                    )
                )
            else:
                # Sorts the list in-place
                tasks_list.sort(
                    key=lambda task: (task.due_date is None, task.due_date)
                )
                for task in tasks_list:
                    self.cards_list.controls.append(self.create_task_card(task))
        else:
            # Query Journal Entries
            journals = database.get_all_journal_entries()
            # Basic search query matching on journal title / text
            if self.search_query:
                journals = [j for j in journals if self.search_query.lower() in j.title.lower() or self.search_query.lower() in j.main_text.lower()]
                
            if not journals:
                self.cards_list.controls.append(
                    ft.Container(
                        content=ft.Text("No journal entries found", color=self.style_config["text_muted"]),
                        alignment=ft.Alignment.CENTER,
                        padding=40
                    )
                )
            else:
                for entry in journals:
                    self.cards_list.controls.append(self.create_journal_card(entry))

    def create_task_card(self, task: Task) -> ft.Container:
        is_selected = (self.selected_task_id == task.id)
        border_side = ft.BorderSide(2, self.style_config["primary_color"]) if is_selected else ft.BorderSide(1, self.style_config["card_bg_color"])
        
        # Status Checkbox
        status_checkbox = ft.Checkbox(
            value=(task.status == "completed"),
            fill_color={
                ft.ControlState.SELECTED: self.style_config["primary_color"],
                ft.ControlState.DEFAULT: self.style_config["text_muted"]
            },
            on_change=lambda e, t_id=task.id, completion=not (task.status == "completed"): self.on_task_status_changed(t_id, completion)
        )
        
        # Task due date indicator
        due_info = ft.Container()
        if task.due_date:
            try:
                due_dt = datetime.datetime.fromisoformat(task.due_date)
                date_str = due_dt.strftime("%b %d, %Y")
                is_overdue = (due_dt < datetime.datetime.now() and task.status == "pending")
                color = ft.Colors.RED_400 if is_overdue else self.style_config["text_muted"]
                due_info = ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CALENDAR_MONTH, size=13, color=color),
                        ft.Text(f"Due: {date_str}", size=11, color=color)
                    ],
                    spacing=4
                )
            except Exception:
                pass
                
        # Tag badges
        tags_row = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(f"#{tag}", size=10, color=self.style_config["primary_color"], weight=ft.FontWeight.BOLD),
                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                    bgcolor=ft.Colors.with_opacity(0.1, self.style_config["primary_color"]),
                    border_radius=4
                ) for tag in task.tags[:3]
            ],
            spacing=4
        )
        
        # Subtask completion progress indicator
        progress_info = ft.Container()
        if task.subtasks:
            completed_subtasks = 0
            for st_id in task.subtasks:
                sub_task = database.get_task(st_id)
                if sub_task and sub_task.status == "completed":
                    completed_subtasks += 1
            progress_info = ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ACCOUNT_TREE, size=13, color=self.style_config["text_muted"]),
                    ft.Text(f"{completed_subtasks}/{len(task.subtasks)} subtasks", size=11, color=self.style_config["text_muted"])
                ],
                spacing=4
            )
            
        footer = ft.Row(
            controls=[due_info, progress_info, tags_row],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        title_style = ft.TextStyle(
            size=14,
            weight=ft.FontWeight.BOLD,
            color=self.style_config["text_color"],
            decoration=ft.TextDecoration.LINE_THROUGH if task.status == "completed" else ft.TextDecoration.NONE
        )
        
        card_content = ft.Row(
            controls=[
                status_checkbox,
                ft.Column(
                    controls=[
                        ft.Text(task.title, style=title_style, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Container(height=4),
                        footer
                    ],
                    expand=True
                )
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        return ft.Container(
            content=card_content,
            bgcolor=self.style_config["card_bg_color"] if not is_selected else ft.Colors.with_opacity(0.05, self.style_config["primary_color"]),
            border=border_side,
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=10, vertical=12),
            on_click=lambda e, t_id=task.id: self.on_task_selected(t_id),
        )

    def create_journal_card(self, entry: JournalEntry) -> ft.Container:
        is_selected = (self.selected_journal_id == entry.id)
        border_side = ft.BorderSide(2, self.style_config["primary_color"]) if is_selected else ft.BorderSide(1, self.style_config["card_bg_color"])
        
        try:
            date_dt = datetime.datetime.fromisoformat(entry.creation_date)
            date_str = date_dt.strftime("%b %d, %Y - %I:%M %p")
        except Exception:
            date_str = entry.creation_date
            
        snippet = entry.main_text or ""
        if len(snippet) > 60:
            snippet = snippet[:60] + "..."
            
        card_content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.BOOK_OUTLINED, size=16, color=self.style_config["primary_color"]),
                        ft.Text(entry.title, size=14, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                    ],
                    spacing=6
                ),
                ft.Text(snippet, size=12, color=self.style_config["text_muted"], max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Container(height=4),
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ACCESS_TIME, size=12, color=self.style_config["text_muted"]),
                        ft.Text(date_str, size=11, color=self.style_config["text_muted"])
                    ],
                    spacing=4
                )
            ],
            spacing=4
        )
        
        return ft.Container(
            content=card_content,
            bgcolor=self.style_config["card_bg_color"] if not is_selected else ft.Colors.with_opacity(0.05, self.style_config["primary_color"]),
            border=border_side,
            border_radius=8,
            padding=12,
            on_click=lambda e, j_id=entry.id: self.on_journal_selected(j_id),
        )

    def on_task_status_changed(self, task_id: int, completed: bool):
        task = database.get_task(task_id)
        if task:
            task.status = "completed" if completed else "pending"
            database.save_task(task)
            self.refresh_list()
            
            # If the current selected task details are shown, refresh details
            if self.selected_task_id == task_id:
                self.show_details()
                
            self.page.update()

    def on_task_selected(self, task_id: int):
        self.selected_task_id = task_id
        self.selected_journal_id = None
        self.is_editing = False
        self.refresh_list()
        self.show_details()
        self.page.update()

    def on_journal_selected(self, journal_id: int):
        self.selected_journal_id = journal_id
        self.selected_task_id = None
        self.is_editing = False
        self.refresh_list()
        self.show_details()
        self.page.update()

    # ==========================================
    # Detail View Rendering & Action Event Handlers
    # ==========================================
    
    def show_details(self):
        if self.is_editing:
            self.render_edit_view()
            return
            
        if self.selected_view == "tasks" and self.selected_task_id:
            task = database.get_task(self.selected_task_id)
            if task:
                self.render_task_detail(task)
            else:
                self.detail_container.content = self.create_empty_state()
        elif self.selected_view == "journal" and self.selected_journal_id:
            entry = database.get_journal_entry(self.selected_journal_id)
            if entry:
                self.render_journal_detail(entry)
            else:
                self.detail_container.content = self.create_empty_state()
        else:
            self.detail_container.content = self.create_empty_state()

    def render_task_detail(self, task: Task):
        # 1. Header with Title & Action buttons
        status_text = "Completed" if task.status == "completed" else "Pending"
        status_color = ft.Colors.GREEN_400 if task.status == "completed" else ft.Colors.AMBER_400
        
        status_badge = ft.Container(
            content=ft.Text(status_text, size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
            bgcolor=status_color,
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            border_radius=4
        )
        
        title_row = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Row(controls=[status_badge, ft.Text(f"Task ID: #{task.id}", size=11, color=self.style_config["text_muted"])]),
                        ft.Text(task.title, size=22, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"])
                    ]
                ),
                ft.Row(
                    controls=[
                        ft.IconButton(ft.Icons.EDIT_NOTE_ROUNDED, tooltip="Edit Task", on_click=self.on_edit_clicked),
                        ft.IconButton(ft.Icons.DELETE_FOREVER_ROUNDED, icon_color=ft.Colors.RED_400, tooltip="Delete Task", on_click=self.on_delete_clicked)
                    ]
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        # 2. Key Metadata details
        try:
            created_dt = datetime.datetime.fromisoformat(task.creation_date)
            created_str = created_dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            created_str = task.creation_date
            
        due_str = "No due date"
        if task.due_date:
            try:
                due_dt = datetime.datetime.fromisoformat(task.due_date)
                due_str = due_dt.strftime("%Y-%m-%d")
            except Exception:
                due_str = task.due_date
                
        meta_grid = ft.GridView(
            runs_count=2,
            max_extent=250,
            child_aspect_ratio=4,
            spacing=10,
            run_spacing=10,
            controls=[
                self.create_meta_item("Created", created_str, ft.Icons.DATE_RANGE),
                self.create_meta_item("Due Date", due_str, ft.Icons.CALENDAR_MONTH),
                self.create_meta_item("Assigner", task.assigner or "None Specified", ft.Icons.PERSON),
                self.create_meta_item("Co-assignees", ", ".join(task.co_assignees) if task.co_assignees else "None", ft.Icons.PEOPLE),
            ]
        )
        
        # 3. Tags listing
        tags_row = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(f"#{tag}", size=11, color=self.style_config["primary_color"], weight=ft.FontWeight.BOLD),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                    bgcolor=ft.Colors.with_opacity(0.1, self.style_config["primary_color"]),
                    border_radius=6
                ) for tag in task.tags
            ] if task.tags else [ft.Text("No tags", italic=True, size=12, color=self.style_config["text_muted"])],
            wrap=True
        )
        
        # 4. Main Notes View (Styled Markdown)
        md_styled_map = styles.get_markdown_styles(self.style_config)
        markdown_view = ft.Container(
            content=ft.Markdown(
                value=task.main_text or "*No details or notes provided.*",
                selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                #**md_styled_map
                md_style_sheet=ft.MarkdownStyleSheet(**md_styled_map),
                width=float("inf")
            ),
            bgcolor=self.style_config["bg_color"],
            padding=15,
            border_radius=8,
            border=ft.Border.all(1, self.style_config["card_bg_color"])
        )
        
        # Render dynamic style reload option
        reload_style_btn = ft.TextButton(
            "Reload style stylesheet",
            icon=ft.Icons.REFRESH_ROUNDED,
            on_click=self.on_reload_stylesheet_clicked,
            style=ft.ButtonStyle(color=self.style_config["primary_color"])
        )
        
        notes_header = ft.Row(
            controls=[
                ft.Text("Main Text & Notes", size=14, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"]),
                reload_style_btn
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        # 5. Emails Section
        emails_section = ft.Container()
        if task.emails:
            email_rows = []
            for email in task.emails:
                email_rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(email.date, size=12, color=self.style_config["text_color"])),
                            ft.DataCell(ft.Text(email.title, size=12, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"])),
                            ft.DataCell(ft.Text(email.people, size=12, color=self.style_config["text_muted"])),
                        ]
                    )
                )
                
            emails_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Date", size=12, weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Title / Details", size=12, weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("People Involved", size=12, weight=ft.FontWeight.BOLD)),
                ],
                rows=email_rows,
                heading_row_height=35,
                data_row_min_height=30,
                column_spacing=15
            )
            
            emails_section = ft.Column(
                controls=[
                    ft.Divider(height=25, color=self.style_config["bg_color"]),
                    ft.Row(controls=[
                        ft.Icon(ft.Icons.EMAIL_ROUNDED, size=18, color=self.style_config["primary_color"]),
                        ft.Text("Related Emails", size=14, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"])
                    ], spacing=6),
                    ft.Container(content=emails_table, padding=ft.Padding.only(top=5))
                ]
            )
            
        # 6. Attachments section
        attachments_section = ft.Container()
        if task.attachments:
            attachment_controls = []
            for filepath in task.attachments:
                # Check if it's an image
                is_image = False
                ext = filepath.split(".")[-1].lower() if "." in filepath else ""
                if ext in ["png", "jpg", "jpeg", "gif", "webp"]:
                    is_image = True
                    
                abs_path = database.get_attachment_absolute_path(filepath)
                
                # Setup display card
                if is_image:
                    attachment_controls.append(
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Image(src=abs_path, height=120, fit=ft.BoxFit.CONTAIN, border_radius=6),
                                    ft.Text(filepath.split("_", 1)[-1], size=11, color=self.style_config["text_muted"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                                ]
                            ),
                            border=ft.Border.all(1, self.style_config["bg_color"]),
                            border_radius=8,
                            padding=6
                        )
                    )
                else:
                    attachment_controls.append(
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.ATTACHMENT_ROUNDED, color=self.style_config["primary_color"]),
                                    ft.Column(
                                        controls=[
                                            ft.Text(filepath.split("_", 1)[-1], size=12, color=self.style_config["text_color"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                            ft.Text("File", size=10, color=self.style_config["text_muted"])
                                        ],
                                        expand=True,
                                        spacing=0
                                    )
                                ]
                            ),
                            border=ft.Border.all(1, self.style_config["bg_color"]),
                            border_radius=8,
                            padding=10,
                            width=180
                        )
                    )
                    
            attachments_section = ft.Column(
                controls=[
                    ft.Divider(height=25, color=self.style_config["bg_color"]),
                    ft.Row(controls=[
                        ft.Icon(ft.Icons.ATTACH_FILE_ROUNDED, size=18, color=self.style_config["primary_color"]),
                        ft.Text("Attachments", size=14, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"])
                    ], spacing=6),
                    ft.Row(controls=attachment_controls, wrap=True, spacing=10)
                ]
            )
            
        # 7. Subtasks Tree (Dependency tree)
        subtask_items = []
        if task.subtasks:
            for sub_id in task.subtasks:
                sub = database.get_task(sub_id)
                if sub:
                    status_icon = ft.Icons.CHECK_CIRCLE if sub.status == "completed" else ft.Icons.RADIO_BUTTON_UNCHECKED
                    status_col = ft.Colors.GREEN_400 if sub.status == "completed" else self.style_config["text_muted"]
                    
                    subtask_items.append(
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.IconButton(status_icon, icon_color=status_col, icon_size=18, on_click=lambda e, sid=sub.id, sval=(sub.status != "completed"): self.on_task_status_changed(sid, sval)),
                                    ft.Text(
                                        spans=[
                                            ft.TextSpan(text=sub.title, style=ft.TextStyle(size=13, color=self.style_config["text_color"], weight=ft.FontWeight.W_600, decoration=ft.TextDecoration.LINE_THROUGH if sub.status == "completed" else ft.TextDecoration.NONE)),
                                        ],
                                    ),
                                    ft.Text(f"(#{sub.id})", size=11, color=self.style_config["text_muted"]),
                                    ##ft.Spacer(),
                                    ft.IconButton(ft.Icons.LINK_OFF, tooltip="Remove dependency link", icon_size=16, on_click=lambda e, sid=sub.id: self.on_remove_dependency(task.id, sid)),
                                    ft.IconButton(ft.Icons.ARROW_FORWARD_ROUNDED, tooltip="Jump to subtask", icon_size=16, on_click=lambda e, sid=sub.id: self.on_task_selected(sid))
                                ]
                            ),
                            bgcolor=self.style_config["bg_color"],
                            border_radius=6,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2)
                        )
                    )
                    
        parent_task_items = []
        if task.parent_tasks:
            for parent_id in task.parent_tasks:
                parent = database.get_task(parent_id)
                if parent:
                    parent_task_items.append(
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.ARROW_UPWARD, size=14, color=self.style_config["primary_color"]),
                                    ft.Text(parent.title, size=13, color=self.style_config["text_color"]),
                                    ft.Text(f"(#{parent.id})", size=11, color=self.style_config["text_muted"]),
                                    #ft.Spacer(),
                                    ft.IconButton(ft.Icons.ARROW_FORWARD_ROUNDED, tooltip="Jump to parent task", icon_size=16, on_click=lambda e, pid=parent.id: self.on_task_selected(pid))
                                ]
                            ),
                            bgcolor=self.style_config["bg_color"],
                            border_radius=6,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2)
                        )
                    )
                    
        btn_add_dependency = ft.Button(
            "Link Existing Subtask",
            icon=ft.Icons.ADD_LINK,
            on_click=lambda e: self.show_link_subtask_dialog(task),
            style=ft.ButtonStyle(bgcolor=self.style_config["bg_color"])
        )
        
        btn_create_and_link_subtask = ft.Button(
            "Create New Subtask",
            icon=ft.Icons.PLAYLIST_ADD,
            on_click=lambda e: self.on_new_subtask_clicked(task.id),
            style=ft.ButtonStyle(bgcolor=self.style_config["bg_color"])
        )
        
        dependencies_section = ft.Column(
            controls=[
                ft.Divider(height=25, color=self.style_config["bg_color"]),
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ACCOUNT_TREE_ROUNDED, size=18, color=self.style_config["primary_color"]),
                        ft.Text("Task Dependency Hierarchy", size=14, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"])
                    ]
                ),
                ft.Text("Required Subtasks (Dependencies):", size=12, weight=ft.FontWeight.BOLD, color=self.style_config["text_muted"]),
                ft.Column(controls=subtask_items) if subtask_items else ft.Text("No subtask dependencies defined.", italic=True, size=12, color=self.style_config["text_muted"]),
                ft.Row(controls=[btn_add_dependency, btn_create_and_link_subtask]),
                ft.Container(height=5),
                ft.Text("Dependent Parent Tasks (Required by):", size=12, weight=ft.FontWeight.BOLD, color=self.style_config["text_muted"]),
                ft.Column(controls=parent_task_items) if parent_task_items else ft.Text("This task is not required by any other tasks.", italic=True, size=12, color=self.style_config["text_muted"]),
            ],
            spacing=8
        )
        
        # 8. Linked Journal Entries
        linked_journal_items = []
        linked_journals = database.get_journal_entries_for_task(task.id)
        if linked_journals:
            for entry in linked_journals:
                linked_journal_items.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.BOOK_ROUNDED, size=14, color=self.style_config["primary_color"]),
                                ft.Text(entry.title, size=13, color=self.style_config["text_color"]),
                                #ft.Spacer(),
                                ft.IconButton(ft.Icons.LINK_OFF, tooltip="Unlink journal entry", icon_size=16, on_click=lambda e, jid=entry.id: self.on_unlink_journal(task.id, jid)),
                                ft.IconButton(ft.Icons.ARROW_FORWARD_ROUNDED, tooltip="Jump to journal entry", icon_size=16, on_click=lambda e, jid=entry.id: self.on_jump_to_journal(jid))
                            ]
                        ),
                        bgcolor=self.style_config["bg_color"],
                        border_radius=6,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=2)
                    )
                )
                
        btn_link_journal = ft.Button(
            "Link Journal Entry",
            icon=ft.Icons.LINK,
            on_click=lambda e: self.show_link_journal_dialog(task.id),
            style=ft.ButtonStyle(bgcolor=self.style_config["bg_color"])
        )
        
        journal_section = ft.Column(
            controls=[
                ft.Divider(height=25, color=self.style_config["bg_color"]),
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.BOOK_OUTLINED, size=18, color=self.style_config["primary_color"]),
                        ft.Text("Linked Journal Notes", size=14, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"])
                    ]
                ),
                ft.Column(controls=linked_journal_items) if linked_journal_items else ft.Text("No linked journal notes.", italic=True, size=12, color=self.style_config["text_muted"]),
                btn_link_journal
            ],
            spacing=8
        )
        
        # Details Scroll Wrapper
        details_scroll = ft.Column(
            controls=[
                title_row,
                ft.Divider(height=20, color=self.style_config["bg_color"]),
                meta_grid,
                ft.Container(height=10),
                ft.Text("Tags", size=12, weight=ft.FontWeight.BOLD, color=self.style_config["text_muted"]),
                tags_row,
                ft.Divider(height=20, color=self.style_config["bg_color"]),
                notes_header,
                markdown_view,
                emails_section,
                attachments_section,
                dependencies_section,
                journal_section,
                ft.Container(height=40)  # padding at bottom
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        self.detail_container.content = details_scroll

    def render_journal_detail(self, entry: JournalEntry):
        # Header
        title_row = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Journal Entry Details", size=11, color=self.style_config["text_muted"]),
                        ft.Text(entry.title, size=22, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"])
                    ]
                ),
                ft.Row(
                    controls=[
                        ft.IconButton(ft.Icons.EDIT_NOTE_ROUNDED, tooltip="Edit Journal", on_click=self.on_edit_clicked),
                        ft.IconButton(ft.Icons.DELETE_FOREVER_ROUNDED, icon_color=ft.Colors.RED_400, tooltip="Delete Journal", on_click=self.on_delete_clicked)
                    ]
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        try:
            created_dt = datetime.datetime.fromisoformat(entry.creation_date)
            created_str = created_dt.strftime("%Y-%m-%d %I:%M %p")
        except Exception:
            created_str = entry.creation_date
            
        meta_row = ft.Row(
            controls=[
                ft.Icon(ft.Icons.ACCESS_TIME, size=14, color=self.style_config["text_muted"]),
                ft.Text(f"Logged on: {created_str}", size=12, color=self.style_config["text_muted"])
            ],
            spacing=5
        )
        
        # Notes View (Styled Markdown)
        md_styled_map = styles.get_markdown_styles(self.style_config)
        markdown_view = ft.Container(
            content=ft.Markdown(
                value=entry.main_text or "*No entry text.*",
                selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                #**md_styled_map
                md_style_sheet=ft.MarkdownStyleSheet(**md_styled_map),
                width=float("inf")
            ),
            bgcolor=self.style_config["bg_color"],
            padding=15,
            border_radius=8,
            border=ft.Border.all(1, self.style_config["card_bg_color"])
        )
        
        # Attachments
        attachments_section = ft.Container()
        if entry.attachments:
            attachment_controls = []
            for filepath in entry.attachments:
                is_image = False
                ext = filepath.split(".")[-1].lower() if "." in filepath else ""
                if ext in ["png", "jpg", "jpeg", "gif", "webp"]:
                    is_image = True
                    
                abs_path = database.get_attachment_absolute_path(filepath)
                
                if is_image:
                    attachment_controls.append(
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Image(src=abs_path, height=120, fit=ft.ImageFit.CONTAIN, border_radius=6),
                                    ft.Text(filepath.split("_", 1)[-1], size=11, color=self.style_config["text_muted"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                                ]
                            ),
                            border=ft.Border.all(1, self.style_config["bg_color"]),
                            border_radius=8,
                            padding=6
                        )
                    )
                else:
                    attachment_controls.append(
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.ATTACHMENT_ROUNDED, color=self.style_config["primary_color"]),
                                    ft.Column(
                                        controls=[
                                            ft.Text(filepath.split("_", 1)[-1], size=12, color=self.style_config["text_color"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                            ft.Text("File", size=10, color=self.style_config["text_muted"])
                                        ],
                                        expand=True,
                                        spacing=0
                                    )
                                ]
                            ),
                            border=ft.Border.all(1, self.style_config["bg_color"]),
                            border_radius=8,
                            padding=10,
                            width=180
                        )
                    )
            attachments_section = ft.Column(
                controls=[
                    ft.Divider(height=25, color=self.style_config["bg_color"]),
                    ft.Row(controls=[
                        ft.Icon(ft.Icons.ATTACH_FILE_ROUNDED, size=18, color=self.style_config["primary_color"]),
                        ft.Text("Attached Content", size=14, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"])
                    ], spacing=6),
                    ft.Row(controls=attachment_controls, wrap=True, spacing=10)
                ]
            )
            
        # Linked Tasks
        linked_task_items = []
        linked_tasks = database.get_tasks_for_journal_entry(entry.id)
        if linked_tasks:
            for task in linked_tasks:
                linked_task_items.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.TASK_ALT_ROUNDED, size=14, color=self.style_config["primary_color"]),
                                ft.Text(task.title, size=13, color=self.style_config["text_color"]),
                                #ft.Spacer(),
                                ft.IconButton(ft.Icons.LINK_OFF, tooltip="Unlink task", icon_size=16, on_click=lambda e, tid=task.id: self.on_unlink_task(tid, entry.id)),
                                ft.IconButton(ft.Icons.ARROW_FORWARD_ROUNDED, tooltip="Jump to task", icon_size=16, on_click=lambda e, tid=task.id: self.on_jump_to_task(tid))
                            ]
                        ),
                        bgcolor=self.style_config["bg_color"],
                        border_radius=6,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=2)
                    )
                )
                
        btn_link_task = ft.Button(
            "Link Task",
            icon=ft.Icons.LINK,
            on_click=lambda e: self.show_link_task_dialog(entry.id),
            style=ft.ButtonStyle(bgcolor=self.style_config["bg_color"])
        )
        
        task_section = ft.Column(
            controls=[
                ft.Divider(height=25, color=self.style_config["bg_color"]),
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.TASK_ALT_ROUNDED, size=18, color=self.style_config["primary_color"]),
                        ft.Text("Linked Tasks", size=14, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"])
                    ]
                ),
                ft.Column(controls=linked_task_items) if linked_task_items else ft.Text("This journal entry is not linked to any tasks.", italic=True, size=12, color=self.style_config["text_muted"]),
                btn_link_task
            ],
            spacing=8
        )
        
        self.detail_container.content = ft.Column(
            controls=[
                title_row,
                meta_row,
                ft.Divider(height=20, color=self.style_config["bg_color"]),
                ft.Text("Entry Notes", size=14, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"]),
                markdown_view,
                attachments_section,
                task_section,
                ft.Container(height=40)
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )

    def create_meta_item(self, label: str, value: str, icon: str) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=18, color=self.style_config["primary_color"]),
                    ft.Column(
                        controls=[
                            ft.Text(label, size=10, color=self.style_config["text_muted"], weight=ft.FontWeight.BOLD),
                            ft.Text(value, size=12, color=self.style_config["text_color"], weight=ft.FontWeight.W_600, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1)
                        ],
                        spacing=0,
                        expand=True
                    )
                ],
                spacing=8
            ),
            bgcolor=self.style_config["bg_color"],
            padding=10,
            border_radius=8
        )

    # ==========================================
    # Action Dialogs & Relationship Adjustments
    # ==========================================
    
    def on_reload_stylesheet_clicked(self, e):
        self.style_config = styles.load_style_config()
        self.page.theme_mode = ft.ThemeMode.DARK if self.style_config.get("theme_mode") == "dark" else ft.ThemeMode.LIGHT
        self.page.bgcolor = self.style_config.get("bg_color")
        self.show_details()
        self.page.update()
        self.page.show_dialog(ft.SnackBar(content=ft.Text("Stylesheet reloaded!")))

    def on_remove_dependency(self, parent_id: int, sub_id: int):
        database.remove_dependency(parent_id, sub_id)
        self.show_details()
        self.refresh_list()
        self.page.update()

    def on_unlink_journal(self, task_id: int, journal_id: int):
        database.unlink_task_journal(task_id, journal_id)
        self.show_details()
        self.page.update()

    def on_jump_to_journal(self, journal_id: int):
        self.selected_view = "journal"
        self.selected_journal_id = journal_id
        self.selected_task_id = None
        self.task_subfilters_container.visible = False
        self.refresh_sidebar_nav()
        self.refresh_list()
        self.show_details()
        self.page.update()

    def on_unlink_task(self, task_id: int, journal_id: int):
        database.unlink_task_journal(task_id, journal_id)
        self.show_details()
        self.page.update()

    def on_jump_to_task(self, task_id: int):
        self.selected_view = "tasks"
        self.selected_task_id = task_id
        self.selected_journal_id = None
        self.task_subfilters_container.visible = True
        self.refresh_sidebar_nav()
        self.refresh_list()
        self.show_details()
        self.page.update()

    # Link Subtask Dialog
    def show_link_subtask_dialog(self, task: Task):
        all_tasks = database.get_all_tasks()
        
        # Exclude: current task, already linked subtasks, and tasks that would cause a cycle
        candidate_tasks = []
        for t in all_tasks:
            if t.id == task.id:
                continue
            if t.id in task.subtasks:
                continue
            # Check cycle: making t a subtask of task (i.e. task depends on t).
            # If t transitively depends on task, it's a cycle.
            if database.check_dependency_cycle(parent_id=task.id, subtask_id=t.id):
                continue
            candidate_tasks.append(t)
            print(candidate_tasks)
            
        if not candidate_tasks:
            self.show_alert("No eligible tasks available to link as subtasks without creating loops.")
            return
            
        dropdown_options = [ft.DropdownOption(key=str(t.id), text=f"{t.title} (#{t.id})") for t in candidate_tasks]
        
        dd_tasks = ft.Dropdown(
            label="Select task to depend on",
            options=dropdown_options,
            width=600
        )
        
        def on_link(e):
            if dd_tasks.value:
                sub_id = int(dd_tasks.value)
                database.add_dependency(parent_id=task.id, subtask_id=sub_id)
                self.page.pop_dialog()
                self.show_details()
                self.refresh_list()
                self.page.update()
                
        dialog = ft.AlertDialog(
            title=ft.Text("Link Existing Subtask"),
            content=ft.Row(controls=[dd_tasks]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog()),
                ft.Button("Link Dependency", bgcolor=self.style_config["primary_color"], on_click=on_link)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        #self.page.dialog = dialog
        self.page.show_dialog(dialog)
        self.page.update()

    # Link Journal Dialog
    def show_link_journal_dialog(self, task_id: int):
        journals = database.get_all_journal_entries()
        
        # Exclude already linked ones
        linked_ids = [j.id for j in database.get_journal_entries_for_task(task_id)]
        candidate_journals = [j for j in journals if j.id not in linked_ids]
        
        if not candidate_journals:
            self.show_alert("No journals available to link.")
            return
            
        dd_journals = ft.Dropdown(
            label="Select journal note",
            options=[ft.dropdown.Option(key=str(j.id), text=j.title) for j in candidate_journals],
            expand=True
        )
        
        def on_link(e):
            if dd_journals.value:
                j_id = int(dd_journals.value)
                database.link_task_journal(task_id, j_id)
                self.page.pop_dialog()
                self.show_details()
                self.page.update()
                
        dialog = ft.AlertDialog(
            title=ft.Text("Link Journal Entry to Task"),
            content=ft.Row(controls=[dd_journals]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog()),
                ft.Button("Link", bgcolor=self.style_config["primary_color"], on_click=on_link)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        #self.page.dialog = dialog
        self.page.show_dialog(dialog)
        self.page.update()

    # Link Task Dialog (from journal detail)
    def show_link_task_dialog(self, journal_id: int):
        tasks = database.get_all_tasks()
        
        linked_ids = [t.id for t in database.get_tasks_for_journal_entry(journal_id)]
        candidate_tasks = [t for t in tasks if t.id not in linked_ids]
        
        if not candidate_tasks:
            self.show_alert("No tasks available to link.")
            return
            
        dd_tasks = ft.Dropdown(
            label="Select task",
            options=[ft.dropdown.Option(key=str(t.id), text=t.title) for t in candidate_tasks],
            expand=True
        )
        
        def on_link(e):
            if dd_tasks.value:
                t_id = int(dd_tasks.value)
                database.link_task_journal(t_id, journal_id)
                self.page.pop_dialog()
                self.show_details()
                self.page.update()
                
        dialog = ft.AlertDialog(
            title=ft.Text("Link Task to Journal Entry"),
            content=ft.Row(controls=[dd_tasks]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog()),
                ft.Button("Link", bgcolor=self.style_config["primary_color"], on_click=on_link)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        #self.page.dialog = dialog
        self.page.show_dialog(dialog)
        self.page.update()

    def close_dialog(self):
        self.page.pop_dialog()
        self.page.update()

    def show_alert(self, message: str):
        dialog = ft.AlertDialog(
            title=ft.Text("Alert"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_dialog())]
        )
        #self.page.dialog = dialog
        self.page.show_dialog(dialog)
        self.page.update()

    # ==========================================
    # Deleting Items
    # ==========================================
    
    def on_delete_clicked(self, e):
        title = "Delete Task" if self.selected_view == "tasks" else "Delete Journal"
        body = "Are you sure you want to permanently delete this task?" if self.selected_view == "tasks" else "Are you sure you want to delete this journal entry?"
        
        def perform_delete(e):
            if self.selected_view == "tasks" and self.selected_task_id:
                database.delete_task(self.selected_task_id)
                self.selected_task_id = None
            elif self.selected_view == "journal" and self.selected_journal_id:
                database.delete_journal_entry(self.selected_journal_id)
                self.selected_journal_id = None
                
            self.page.pop_dialog()
            self.refresh_list()
            self.update_tag_cloud()
            self.show_details()
            self.page.update()
            
        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(body),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog()),
                ft.Button("Delete", bgcolor=ft.Colors.RED_500, color=ft.Colors.WHITE, on_click=perform_delete)
            ]
        )
        #self.page.dialog = dialog
        self.page.show_dialog(dialog)
        self.page.update()

    # ==========================================
    # Creating / Editing View Renderers
    # ==========================================
    
    def on_new_task_clicked(self, e=None):
        self.is_editing = True
        self.editing_item_type = "task"
        self.selected_task_id = None
        self.temp_emails = []
        self.temp_attachments = []
        self.render_edit_view()
        self.page.update()

    def on_new_subtask_clicked(self, parent_id: int):
        self.is_editing = True
        self.editing_item_type = "task"
        self.selected_task_id = None
        self.temp_emails = []
        self.temp_attachments = []
        # Prepopulate subtask creation to save later
        # We will save this dependency AFTER task is created successfully
        self.parent_to_link_after_creation = parent_id
        self.render_edit_view()
        self.page.update()

    def on_new_journal_clicked(self, e=None):
        self.is_editing = True
        self.editing_item_type = "journal"
        self.selected_journal_id = None
        self.temp_attachments = []
        self.render_edit_view()
        self.page.update()

    def on_edit_clicked(self, e):
        self.is_editing = True
        self.temp_emails = []
        self.temp_attachments = []
        
        if self.selected_view == "tasks" and self.selected_task_id:
            self.editing_item_type = "task"
            task = database.get_task(self.selected_task_id)
            if task:
                self.temp_emails = list(task.emails)
                self.temp_attachments = list(task.attachments)
        else:
            self.editing_item_type = "journal"
            entry = database.get_journal_entry(self.selected_journal_id)
            if entry:
                self.temp_attachments = list(entry.attachments)
                
        self.render_edit_view()
        self.page.update()

    def render_edit_view(self):
        if self.editing_item_type == "task":
            self.render_task_edit_form()
        else:
            self.render_journal_edit_form()

    def render_task_edit_form(self):
        # Load existing details if editing
        task = None
        if self.selected_task_id:
            task = database.get_task(self.selected_task_id)
            
        title_text = "Edit Task" if task else "Create New Task"
        
        self.edit_task_title = ft.TextField(label="Task Title", value=task.title if task else "", border_radius=6, bgcolor=self.style_config["bg_color"])
        self.edit_task_main = ft.TextField(
            label="Main Text & Notes (Markdown supported)",
            value=task.main_text if task else "",
            multiline=True,
            min_lines=8,
            max_lines=15,
            border_radius=6,
            bgcolor=self.style_config["bg_color"],
            width=float("inf")
        )
        
        self.edit_task_due = ft.TextField(
            label="Due Date (YYYY-MM-DD)",
            value=task.due_date[:10] if task and task.due_date else "",
            read_only=True,
            border_radius=6,
            bgcolor=self.style_config["bg_color"],
            expand=True
        )
        
        btn_due_picker = ft.IconButton(
            ft.Icons.DATE_RANGE,
            on_click=lambda e: self.page.show_dialog(self.date_picker),
            tooltip="Choose Date"
        )
        
        self.edit_task_assigner = ft.TextField(label="Assigner", value=task.assigner if task else "", border_radius=6, bgcolor=self.style_config["bg_color"])
        
        # Co-assignees (comma-separated input string)
        co_assign_str = ", ".join(task.co_assignees) if task and task.co_assignees else ""
        self.edit_task_co = ft.TextField(label="Co-assignees (comma-separated)", value=co_assign_str, border_radius=6, bgcolor=self.style_config["bg_color"])
        
        # Tags (comma-separated input string)
        tag_str = ", ".join(task.tags) if task and task.tags else ""
        self.edit_task_tags = ft.TextField(label="Tags (comma-separated)", value=tag_str, border_radius=6, bgcolor=self.style_config["bg_color"])
        
        # --- Emails dynamic builder ---
        self.emails_builder_container = ft.Column(spacing=5)
        self.refresh_emails_builder_ui()
        
        email_date_field = ft.TextField(label="Email Date", hint_text="e.g. 2026-06-25", width=110, text_size=12, border_radius=6)
        email_title_field = ft.TextField(label="Email Subject/Title", hint_text="e.g. FWD: Urgent Specs", expand=True, text_size=12, border_radius=6)
        email_people_field = ft.TextField(label="People", hint_text="e.g. Alice -> Me", expand=True, text_size=12, border_radius=6)
        
        def add_email_to_temp(e):
            if email_title_field.value:
                self.temp_emails.append(
                    EmailInfo(
                        date=email_date_field.value or datetime.date.today().isoformat(),
                        title=email_title_field.value,
                        people=email_people_field.value or "N/A"
                    )
                )
                email_date_field.value = ""
                email_title_field.value = ""
                email_people_field.value = ""
                self.refresh_emails_builder_ui()
                self.page.update()
                
        btn_add_email = ft.Button("Add Email Info", icon=ft.Icons.ADD, on_click=add_email_to_temp, bgcolor=self.style_config["bg_color"])
        
        email_entry_row = ft.Row(
            controls=[
                email_date_field,
                email_title_field,
                email_people_field,
                btn_add_email
            ],
            spacing=8
        )
        
        # --- Attachments Builder ---
        self.attachments_builder_container = ft.Column(spacing=5)
        self.refresh_attachments_builder_ui()
        
        btn_add_attachment = ft.Button(
            "Select Attachment File",
            icon=ft.Icons.ATTACHMENT,
            on_click=self.pick_files_clicked,
            bgcolor=self.style_config["bg_color"]
        )
        
        # Form buttons
        btn_save = ft.Button("Save Task", icon=ft.Icons.SAVE, bgcolor=self.style_config["primary_color"], color=ft.Colors.WHITE, on_click=self.on_save_task_clicked, height=45)
        btn_cancel = ft.OutlinedButton("Cancel", on_click=self.on_cancel_edit_clicked, height=45)
        
        form_scroll = ft.Column(
            controls=[
                ft.Text(title_text, size=20, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"]),
                ft.Divider(height=15, color=self.style_config["bg_color"]),
                self.edit_task_title,
                self.edit_task_main,
                ft.Row(controls=[self.edit_task_due, btn_due_picker], spacing=5),
                self.edit_task_assigner,
                self.edit_task_co,
                self.edit_task_tags,
                ft.Divider(height=20, color=self.style_config["bg_color"]),
                ft.Text("Attach Emails Related to This Task", size=13, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"]),
                self.emails_builder_container,
                email_entry_row,
                ft.Divider(height=20, color=self.style_config["bg_color"]),
                ft.Text("Attachments (copied locally)", size=13, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"]),
                self.attachments_builder_container,
                btn_add_attachment,
                ft.Divider(height=30, color=self.style_config["bg_color"]),
                ft.Row(controls=[btn_save, btn_cancel], alignment=ft.MainAxisAlignment.END, spacing=10),
                ft.Container(height=40)
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        self.detail_container.content = form_scroll

    def render_journal_edit_form(self):
        entry = None
        if self.selected_journal_id:
            entry = database.get_journal_entry(self.selected_journal_id)
            
        title_text = "Edit Journal Entry" if entry else "Create New Journal Entry"
        
        self.edit_journal_title = ft.TextField(label="Journal Title", value=entry.title if entry else "", border_radius=6, bgcolor=self.style_config["bg_color"])
        self.edit_journal_main = ft.TextField(
            label="Write entry details... (Markdown supported)",
            value=entry.main_text if entry else "",
            multiline=True,
            min_lines=12,
            max_lines=20,
            border_radius=6,
            bgcolor=self.style_config["bg_color"],
            width=float("inf")
        )
        
        # Attachments
        self.attachments_builder_container = ft.Column(spacing=5)
        self.refresh_attachments_builder_ui()
        
        btn_add_attachment = ft.Button(
            "Select Attached File / Content",
            icon=ft.Icons.ATTACHMENT,
            on_click=self.pick_files_clicked,
            bgcolor=self.style_config["bg_color"]
        )
        
        # Form buttons
        btn_save = ft.Button("Save Journal", icon=ft.Icons.SAVE, bgcolor=self.style_config["primary_color"], color=ft.Colors.WHITE, on_click=self.on_save_journal_clicked, height=45)
        btn_cancel = ft.OutlinedButton("Cancel", on_click=self.on_cancel_edit_clicked, height=45)
        
        form_scroll = ft.Column(
            controls=[
                ft.Text(title_text, size=20, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"]),
                ft.Divider(height=15, color=self.style_config["bg_color"]),
                self.edit_journal_title,
                self.edit_journal_main,
                ft.Divider(height=20, color=self.style_config["bg_color"]),
                ft.Text("Attached Files / Images", size=13, weight=ft.FontWeight.BOLD, color=self.style_config["text_color"]),
                self.attachments_builder_container,
                btn_add_attachment,
                ft.Divider(height=30, color=self.style_config["bg_color"]),
                ft.Row(controls=[btn_save, btn_cancel], alignment=ft.MainAxisAlignment.END, spacing=10),
                ft.Container(height=40)
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        self.detail_container.content = form_scroll

    def refresh_emails_builder_ui(self):
        self.emails_builder_container.controls.clear()
        if not self.temp_emails:
            self.emails_builder_container.controls.append(
                ft.Text("No emails added yet.", italic=True, size=12, color=self.style_config["text_muted"])
            )
            return
            
        for i, email in enumerate(self.temp_emails):
            self.emails_builder_container.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.EMAIL, size=16, color=self.style_config["primary_color"]),
                            ft.Text(f"[{email.date}] {email.title} ({email.people})", size=12, color=self.style_config["text_color"], expand=True),
                            ft.IconButton(ft.Icons.DELETE_OUTLINED, icon_color=ft.Colors.RED_400, icon_size=16, on_click=lambda e, idx=i: self.remove_temp_email(idx))
                        ]
                    ),
                    bgcolor=self.style_config["bg_color"],
                    padding=5,
                    border_radius=4
                )
            )

    def remove_temp_email(self, index: int):
        self.temp_emails.pop(index)
        self.refresh_emails_builder_ui()
        self.page.update()

    def refresh_attachments_builder_ui(self):
        self.attachments_builder_container.controls.clear()
        if not self.temp_attachments:
            self.attachments_builder_container.controls.append(
                ft.Text("No attachments added.", italic=True, size=12, color=self.style_config["text_muted"])
            )
            return
            
        for i, path in enumerate(self.temp_attachments):
            display_name = path.split("_", 1)[-1]
            self.attachments_builder_container.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ATTACH_FILE, size=16, color=self.style_config["primary_color"]),
                            ft.Text(display_name, size=12, color=self.style_config["text_color"], expand=True),
                            ft.IconButton(ft.Icons.DELETE_OUTLINED, icon_color=ft.Colors.RED_400, icon_size=16, on_click=lambda e, idx=i: self.remove_temp_attachment(idx))
                        ]
                    ),
                    bgcolor=self.style_config["bg_color"],
                    padding=5,
                    border_radius=4
                )
            )

    def remove_temp_attachment(self, index: int):
        self.temp_attachments.pop(index)
        self.refresh_attachments_builder_ui()
        self.page.update()

    # ==========================================
    # Date Picker & File Picker Handlers
    # ==========================================
    
    def on_date_picker_result(self, e):
        if self.date_picker.value:
            # Format value as YYYY-MM-DD
            formatted_date = self.date_picker.value.strftime("%Y-%m-%d")
            self.edit_task_due.value = formatted_date
            self.page.update()

    async def pick_files_clicked(self, e):
        files = await ft.FilePicker().pick_files(allow_multiple=True)
        if files:
            file_path = files[0].path
            if file_path:
                try:
                    # Copy file to storage directory using database helper
                    relative_filename = database.copy_attachment_to_storage(file_path)
                    self.temp_attachments.append(relative_filename)
                    self.refresh_attachments_builder_ui()
                    self.page.update()
                except Exception as ex:
                    self.show_alert(f"Failed to copy file: {str(ex)}")

    # ==========================================
    # Saving Forms
    # ==========================================
    
    def on_save_task_clicked(self, e=None):
        if not self.edit_task_title.value:
            self.show_alert("Title is required.")
            return
            
        # Parse tags (comma separated)
        tags = [t.strip().lower() for t in self.edit_task_tags.value.split(",") if t.strip()]
        
        # Parse co-assignees (comma separated)
        co_assignees = [c.strip() for c in self.edit_task_co.value.split(",") if c.strip()]
        
        # Retrieve existing status or set pending
        status = "pending"
        creation_date = datetime.datetime.now().isoformat()
        
        if self.selected_task_id:
            existing = database.get_task(self.selected_task_id)
            if existing:
                status = existing.status
                creation_date = existing.creation_date
                
        # Build Task Object
        task = Task(
            id=self.selected_task_id,
            title=self.edit_task_title.value,
            main_text=self.edit_task_main.value,
            creation_date=creation_date,
            due_date=self.edit_task_due.value if self.edit_task_due.value else None,
            status=status,
            assigner=self.edit_task_assigner.value or None,
            co_assignees=co_assignees,
            tags=tags,
            emails=self.temp_emails,
            attachments=self.temp_attachments
        )
        
        # Save Task
        task_id = database.save_task(task)
        
        # Handle linked parent if we just created a subtask
        if not self.selected_task_id and hasattr(self, 'parent_to_link_after_creation') and self.parent_to_link_after_creation:
            database.add_dependency(parent_id=self.parent_to_link_after_creation, subtask_id=task_id)
            self.parent_to_link_after_creation = None
            
        # Update app state
        self.selected_task_id = task_id
        self.is_editing = False
        
        self.refresh_list()
        self.update_tag_cloud()
        self.show_details()
        self.page.update()

    def on_save_journal_clicked(self, e):
        if not self.edit_journal_title.value:
            self.show_alert("Title is required.")
            return
            
        creation_date = datetime.datetime.now().isoformat()
        if self.selected_journal_id:
            existing = database.get_journal_entry(self.selected_journal_id)
            if existing:
                creation_date = existing.creation_date
                
        # Build Journal Entry Object
        entry = JournalEntry(
            id=self.selected_journal_id,
            title=self.edit_journal_title.value,
            main_text=self.edit_journal_main.value,
            creation_date=creation_date,
            attachments=self.temp_attachments
        )
        
        # Save Journal
        journal_id = database.save_journal_entry(entry)
        
        self.selected_journal_id = journal_id
        self.is_editing = False
        
        self.refresh_list()
        self.show_details()
        self.page.update()

    def on_cancel_edit_clicked(self, e=None):
        self.is_editing = False
        self.parent_to_link_after_creation = None
        self.show_details()
        self.page.update()

def main(page: ft.Page):
    TodoApp(page)

if __name__ == "__main__":
    ft.run(main)
