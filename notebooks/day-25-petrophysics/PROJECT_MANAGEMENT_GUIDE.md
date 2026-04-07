"""
PETROARX - PROJECT MANAGEMENT SYSTEM
=============================================

This document describes the complete project management system integration
for PetroARX, including how projects flow through the entire application.


ARCHITECTURE OVERVIEW
=====================

The project management system consists of:

1. Core Layer (core/project_manager.py)
   - ProjectData: In-memory project representation
   - save_project(): Serialize to JSON file
   - load_project(): Deserialize from JSON file
   - get_recent_projects(): Get recently used projects
   - add_recent_project(): Update recent projects list

2. Service Layer (services/project_service.py)
   - ProjectService: High-level project operations
   - Handles UI dialogs and user interactions
   - Tracks modification state
   - Manages serialization/deserialization
   - Updates UI state (window title, project header)

3. Data Layer (services/data_service.py, core/data_model.py)
   - DataService: Well data import and management
   - Well: Data model for well information
   - Maintains wells in memory (_wells dict)

4. Controller (controllers/main_controller.py)
   - MainController: Wires all UI actions to services
   - Tracks modifications when data is imported/modified
   - Provides tab switching helpers
   - Keeps references to services for cross-access

5. Main Window (app/petrovision_main.py)
   - PetroVisionMainWindow: Main application window
   - Handles closeEvent for save-on-exit prompts
   - Supports loading project from command line
   - Tab switching and UI integration


DATA FLOW
=========

PROJECT CREATION:
1. User clicks "New Project" on Dashboard
2. ProjectService.new_project() opens dialog
3. User enters project name and description
4. ProjectData object created in memory
5. UI updated: window title, project header, project state
6. Project ready for well data import

WELL DATA IMPORT:
1. User clicks "Load Well Logs" or similar
2. DataService.import_data() opens file dialog
3. User selects LAS/CSV/etc file
4. well_data_loader.load_well() parses file
5. Well object created and added to DataService._wells
6. ProjectService marks project as modified
7. UI updated: well names in combos, data views populated

DATA ANALYSIS:
1. User performs calculations (Vsh, Phi, Sw, etc.)
2. InterpretationService.compute_*() updates Well.data
3. ProjectService marks modified on each change
4. Results visible in relevant analysis tabs

PROJECT SAVING:
1. User clicks "Save Project"
OR User closes app with unsaved changes
2. ProjectService._serialize_well_data() called
   - Iterates over DataService._wells
   - Converts each Well to dict format
   - Extracts pandas DataFrame as JSON records
   - Updates ProjectData.wells with serialized data
3. save_project() writes ProjectData to JSON file
4. Recent projects list updated
5. Project marked as unmodified
6. UI updated with save confirmation

PROJECT LOADING:
1. User clicks "Load Project" or recent project button
2. ProjectService.load_project_from_path() called
3. load_project() reads JSON file into ProjectData
4. ProjectService._deserialize_well_data() called
   - Iterates over ProjectData.wells
   - Recreates Well objects
   - Converts JSON records back to pandas DataFrame
   - Returns dict of Well objects
5. DataService._wells populated with loaded wells
6. UI updated: combos populated, data views loaded
7. Project marked as unmodified

MODIFICATION TRACKING:
1. ProjectService.modified flag tracks state
2. Set to True when:
   - New data imported: _import_and_track()
   - Analysis performed: _compute_*_and_track()
   - Any explicit mark_modified() call
3. Set to False when:
   - Project saved: _perform_save()
   - Project loaded: load_project_from_path()
4. Window title shows "*" when modified
5. closeEvent checks flag and prompts save


KEY COMPONENTS
==============

ProjectData Class:
  Represents a project with:
  - name: Project name
  - path: File path (None if not saved)
  - created: Creation timestamp
  - modified: Last modification timestamp
  - wells: Dict[str, Dict] with serialized well data
  - metadata: Dict with field, region, description, etc.

ProjectService Methods:
  new_project(): Create new project
  open_project(): Open file dialog to load
  load_project_from_path(path): Load specific file
  load_recent_project(path): Load from recent list
  save_project(): Save to current path (or prompt)
  save_project_as(): Save with new path
  mark_modified(): Mark project as modified
  refresh_recent_projects(): Update UI buttons
  get_current_project(): Get ProjectData object

DataService Integration:
  _wells: Dict[str, Well] of loaded wells
  import_data(): Load well data from file
  set_current_well(name): Switch active well
  load_data_view(): Refresh data displays
  get_recent_projects(): Used during load

MainController Wiring:
  Dashboard buttons → project operations
  btnLoadProject → projects.open_project()
  btnSaveProject → save_and_track()
  btnDashRecent1,2,3 → load_recent_project()
  btnDashLoadLogs → data.import_data()
  btnDash*Eval → calculation functions
  Data changes → projects.mark_modified()


UI INTEGRATION
==============

Dashboard Header Frame:
  Shows current project info:
  - Project name
  - Well count and names
  - Load/Save buttons

Recent Projects Section:
  Three buttons (btnDashRecent1/2/3):
  - Populated by refresh_recent_projects()
  - Connected to load_recent_project()
  - Shows project names with tooltips

Module Launch Buttons:
  btnDashLoadLogs → Import data
  btnDashQualityAssess → Go to QC tab
  btnDashViewEditLogs → View log plots
  btnDashAnalyzeCrossplot → Create crossplot
  btnDashNetPay → Go to net pay tab
  And calculation buttons...

Window Title:
  Shows: "PetroARX v1.0 — ProjectName"
  With "*" suffix when modified
  Example: "PetroARX v1.0 — Example Project *"


USAGE EXAMPLES
==============

Creating and Saving a Project:
  1. File → New Project
  2. Enter project name
  3. File → Import Well Data (or Dashboard button)
  4. Select LAS file
  5. Perform analysis
  6. File → Save Project
  7. Choose location (auto-named as ProjectName.pproj)

Opening a Project:
  1. File → Open Project
  2. Select .pproj file (or click recent)
  3. All well data restored automatically
  4. Ready to continue analysis

Command Line:
  python petrovision_main.py /path/to/project.pproj
  - Loads project automatically on startup

Recent Projects:
  - Stored in ~/.petrovision/recent_projects.json
  - Shows last 10 projects
  - Removes non-existent files on access
  - Dashboard shows top 3 as quick links


JSON PROJECT FILE FORMAT
========================

A .pproj file is JSON with structure:

{
  "name": "My Project",
  "created": "2026-04-05T14:32:00",
  "modified": "2026-04-05T14:35:00",
  "metadata": {
    "description": "Description...",
    "field": "North Sea",
    "basin": "...",
    "region": "...",
    "country": "Norway"
  },
  "wells": {
    "Well-A": {
      "name": "Well-A",
      "header": {
        "UWI": "Well-A-001",
        "LOCATION": "...",
        "DEPTH": 3500
      },
      "log_info": {
        "GR": {"min": 20, "max": 150, "unit": "API"},
        "RHOB": {"min": 2.0, "max": 2.8, "unit": "g/cc"}
      },
      "data": [
        {"DEPTH": 1000, "GR": 50, "RHOB": 2.3, ...},
        {"DEPTH": 1500, "GR": 75, "RHOB": 2.5, ...},
        ...
      ]
    }
  }
}


ERROR HANDLING
==============

File Operations:
  - File not found → Warning dialog
  - Permission denied → Error message
  - Invalid JSON → Load failure message
  - Disk full → Save failure message

Project State:
  - Modified on exit → Save prompt
  - Recent file missing → Skipped silently
  - Corrupted project → Load failure

User Feedback:
  - Success messages after save/load
  - Error messages with file paths
  - Status bar updates (in window title)


TESTING
=======

Run the example script:
  python example_project_usage.py

This demonstrates:
  - Creating and saving projects
  - Loading existing projects
  - Recent projects management
  - Integration workflow

Test workflow:
  1. Run app, create new project
  2. Import well data
  3. Save project
  4. Close app
  5. Reopen app, load project
  6. Verify data intact


FUTURE ENHANCEMENTS
====================

- Multi-well project support with syncing
- Cloud backup integration
- Project templates
- Undo/redo stack
- Version history
- Collaborative editing
- Import/export formats (Excel, CSV, etc.)
- Project statistics and summaries
"""

# This is a documentation file - run example_project_usage.py for tests
