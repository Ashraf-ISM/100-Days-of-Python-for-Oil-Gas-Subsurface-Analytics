"""
QUICKSTART GUIDE - PROJECT MANAGEMENT
======================================

Get started with project management in PetroARX
"""

# ============================================================================
# STARTING THE APPLICATION
# ============================================================================

"""
METHOD 1: Start with no project
  $ python app/petrovision_main.py
  - Dashboard shows "No Project"
  - Click buttons to create new or open existing project

METHOD 2: Open specific project from command line
  $ python app/petrovision_main.py /path/to/myproject.pproj
  - Project loads automatically
  - Ready to continue analysis

METHOD 3: Click desktop shortcut or file association
  - Double-click .pproj file
  - App opens with project loaded
"""


# ============================================================================
# CREATING A NEW PROJECT
# ============================================================================

"""
WORKFLOW:

1. Launch PetroARX
   Dashboard appears showing "No Project"

2. Click "Load Project" button
   OR: File → New Project from menu

3. Enter project details:
   - Project Name: "My Well Evaluation"
   - Description: "2024 Q1 Assessment"
   (Other fields optional)

4. Click "Create"
   - Project created in memory
   - Window title shows: "PetroARX — My Well Evaluation"
   - Dashboard header updated

5. Click "Load Well Logs" (Dashboard button)
   OR: File → Import Well Data

6. Select well data file:
   - .las files: LAS format (most common)
   - .csv files: Comma/tab-separated
   - .xlsx files: Excel workbooks
   - And more...

7. File loads automatically:
   - Well name appears in dropdowns throughout app
   - Data Info tab shows well header and curve info
   - Ready for analysis

8. Perform analysis:
   - Quality Control tab: Check/clean data
   - Formation Evaluation: Calculate Vsh, Phi, Sw
   - Log Plots: View and interact with data
   - Other analysis modules...

9. Save project:
   - File → Save Project
   - OR: Click "Save Project" button on Dashboard
   - Choose location (will suggest ProjectName.pproj)
   - Saved to disk with all well data

10. Window title now shows:
    "PetroARX — My Well Evaluation"
    (no asterisk = saved state)
"""


# ============================================================================
# OPENING AN EXISTING PROJECT
# ============================================================================

"""
WORKFLOW:

1. Launch PetroARX
   Dashboard appears

2. Option A - Load from Recent:
   - Click one of "📦 Recent1/2/3" buttons
   - Project loads automatically

   Option B - Open File Dialog:
   - Click "Load Project" button
   - Browse to your .pproj file
   - Click Open
   - Project loads automatically

3. Project status displayed:
   - Window title: "PetroARX — ProjectName"
   - Dashboard shows current project name
   - All wells and data loaded into memory
   - Ready to continue analysis

4. Continue analysis:
   - All previous work preserved
   - All well data available
   - Can import additional wells
   - Can create new analyses
"""


# ============================================================================
# SAVING YOUR WORK
# ============================================================================

"""
WHEN TO SAVE:

- After importing new well data
- After performing calculations
- Before closing application
- Before switching to another project
- Periodically during work session

HOW TO SAVE:

1. Manual save:
   - Click "Save Project" button (Dashboard or Toolbar)
   - File → Save Project menu
   - Keyboard shortcut: Ctrl+S (if implemented)

2. Auto-save check:
   - If project is modified (window title has "*"):
     "PetroARX — My Project *"
   - When you close the app, dialog prompts:
     "Project has unsaved changes. Save before closing?"

3. What gets saved:
   - All well names and well data
   - Well headers (UWI, location, depth, etc.)
   - Log curves and values
   - Project name, description, metadata
   - Timestamps (created, modified)

4. File location:
   - Default: My Documents/MyProject.pproj
   - Can save anywhere with "Save As"
   - Opens in file browser for selection
"""


# ============================================================================
# UNDERSTANDING PROJECT FILES
# ============================================================================

"""
PROJECT FILE FORMAT (.pproj):

File extension: .pproj
File type: JSON (text-based)
Stored location: User selects during save

FILE CONTENTS:

{
  "name": "My Project Name",
  "created": "2026-04-05T14:32:00",
  "modified": "2026-04-05T15:45:00",
  "metadata": {
    "description": "Project description",
    "field": "North Sea",
    "region": "Block 1",
    "country": "Norway"
  },
  "wells": {
    "Well-A": {
      Data for Well-A...
    },
    "Well-B": {
      Data for Well-B...
    }
  }
}

BENEFITS:

✓ Human-readable format
✓ Can be edited in text editor if needed
✓ Works across platforms (Windows, Mac, Linux)
✓ No database required
✓ Can be backed up easily
✓ Version control friendly (Git, etc.)
"""


# ============================================================================
# MANAGING MULTIPLE PROJECTS
# ============================================================================

"""
RECENT PROJECTS:

Dashboard shows 3 recent projects:
- 📦 Recent1: Most recently opened
- 📦 Recent2: Second most recent
- 📦 Recent3: Third most recent

Click any to load instantly

Recent projects stored in:
- Windows: %USERPROFILE%\.petrovision\recent_projects.json
- Mac/Linux: ~/.petrovision/recent_projects.json

Keeps history of last 10 projects

SWITCHING BETWEEN PROJECTS:

1. Open Project A → Work → Save
2. File → Open Project
   OR: Click "Load Project" button
3. Select Project B from file browser
   OR: Click recent project button
4. Project A closed, Project B loaded
5. If Project A was modified, prompted to save first

WORKING WITH MULTIPLE WELLS:

One project can contain multiple wells:

1. Create new project "Multi-Well Eval"
2. Import Well-A data (Load Well Logs)
3. Import Well-B data (Load Well Logs again)
4. Both wells now in project
5. Switch between wells in dropdowns throughout app
6. Perform analysis on each well
7. Save project (all wells saved together)
"""


# ============================================================================
# TROUBLESHOOTING
# ============================================================================

"""
PROBLEM: Can't find recent project file

SOLUTION:
- File may have been moved or deleted
- Click "Load Project" and browse to new location
- Recent projects list auto-updates to remove missing files

---

PROBLEM: Project file corrupted

SOLUTION:
- Project files are JSON text files
- Can be repaired with text editor
- Or reload from backup
- Contact support with corrupted file

---

PROBLEM: Project takes long time to load

SOLUTION:
- Project has many wells with large datasets
- This is normal for large projects
- First load may be slower
- Subsequent loads cached in memory

---

PROBLEM: Accidentally closed without saving

SOLUTION:
- Changes were lost
- Dialog should have prompted before close
- Check if auto-backup exists
- Next time: Always save before closing!

---

PROBLEM: Run out of disk space when saving

SOLUTION:
- Save error message displayed
- Free up disk space
- Try saving project again
- Consider archiving old projects

---

PROBLEM: Can't write to project save location

SOLUTION:
- Check file permissions
- Try "Save As" to different location
- Check if file is opened in another program
- Ensure folder is writable
"""


# ============================================================================
# BEST PRACTICES
# ============================================================================

"""
DO:

✓ Save projects regularly (after each major task)
✓ Use descriptive project names
✓ Add descriptions and metadata (field, region, etc.)
✓ Organize projects by year/quarter/region
✓ Keep project files in organized folder structure
✓ Backup important projects regularly
✓ Close unused projects before opening new ones
✓ Check modification indicator (asterisk in title)

DON'T:

✗ Store projects on network drives without sync
✗ Rename or move project files without app
✗ Edit project files directly (unless you know JSON)
✗ Keep projects open for extended periods
✗ Ignore save prompts when closing
✗ Store in temporary folders
✗ Open same project in multiple instances
✗ Delete projects without backup

WORKFLOW RECOMMENDATIONS:

1. Start of session:
   - Launch app
   - Open recent project OR create new one
   - Check if project modified (review work)

2. During session:
   - Save periodically (every 30-60 minutes)
   - After each major analysis step
   - Before running long calculations

3. End of session:
   - Save final work
   - Review all calculations
   - Add notes in project description
   - Close app properly (respond to save prompt)

4. Before taking break:
   - Save project
   - Create backup copy if important
   - Close app or minimize
"""


# ============================================================================
# KEYBOARD SHORTCUTS
# ============================================================================

"""
Ctrl+N ........... New Project
Ctrl+O ........... Open Project
Ctrl+S ........... Save Project
Ctrl+Shift+S .... Save Project As...
Alt+F4 ........... Close Application (prompts save)

(More shortcuts available in menu)
"""


# ============================================================================
# GETTING HELP
# ============================================================================

"""
DOCUMENTATION:

- QUICKSTART.md .................. Fast workflow reference
- PROJECT_MANAGEMENT_GUIDE.md .... Technical architecture details
- README_PROJECT_SYSTEM.md ....... End-to-end project system behavior
- example_project_usage.py ....... Automation and usage examples

SUPPORT:

- In app: Help -> Documentation (F1)
- In app: Help -> About PetroARX
- Review traceback or popup message details before rerun
- Verify active well and required curves before calculations
"""


# Run only for documentation display
if __name__ == "__main__":
    import pydoc
    pydoc.render_doc(__doc__)
