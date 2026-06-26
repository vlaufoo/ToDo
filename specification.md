# My ToDo App

## Features

This biref document shall serve as the specification to implement a to-do app.
1. The app shall be implemented in python, using flet as the graphical library and sqlite to store the task data. 
2. The app shall be compatible and compilable for Windows, compatibility with linux (specifically with debian 13 trixie)
3. Each task object shall be composed of
    - the task title
    - main text
    - any attached images
    - a creation date
    - a due date
    - links to subtasks (e.g. tasks required to complete the main task). This of course will  have to allow the creation of arbitrarily deep task dependecy trees.
    - links to parent tasks (e.g. tasks that can only be completed if the present task is completed)
    - tags, to categorize the task
    - a dedicated "e-mails" field where any details (received or sent date, title, people) can be added, pertaining to the present task
    - an "assigner", the person who assigned the task
    - any co-assignees
    - links to journal entries


### The "Main text" section
I think I am going to use this field also as a space to take any notes related to the task, so it may get quite big and dense with information. Because of this I need to be able to control the way it is displayed, so the app should implement some form of wrapper around html simplifying the syntax
(making it something akin to Markdown), but allowing me, the user, to change the styling of the rendered result without having to recompile.

### The journal
The app should also have a journal section, where the user can create entries with a title, a main text and attached content, but none of the other fields present in task objects. These journal entries can be linked to tasks.

## GUI
The gui, shall be guided by common sense principles and common practices with this kind of app. 
