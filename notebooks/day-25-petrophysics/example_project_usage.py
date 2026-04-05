"""
Example usage of the project management system.

This demonstrates how the project system works end-to-end:
1. Creating new projects
2. Loading existing projects
3. Saving projects with well data
4. Tracking modifications
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from core.project_manager import ProjectData, save_project, load_project, get_recent_projects
from core.data_model import Well
import pandas as pd


def example_create_and_save_project():
    """Example: Create and save a project with well data."""
    print("=" * 60)
    print("EXAMPLE 1: Create and Save Project")
    print("=" * 60)
    
    # Create project
    project = ProjectData(
        name="Example Well Project",
    )
    project.metadata["description"] = "Example project for demonstration"
    project.metadata["field"] = "Example Field"
    project.metadata["region"] = "North Sea"
    
    # Add well data
    well_data = {
        "name": "Well-A",
        "header": {
            "UWI": "Well-A-001",
            "LOCATION": "North Sea Block 1",
            "DEPTH": 3500
        },
        "log_info": {
            "GR": {"min": 20, "max": 150, "unit": "API"},
            "RHOB": {"min": 2.0, "max": 2.8, "unit": "g/cc"},
            "NPHI": {"min": 0.0, "max": 0.4, "unit": "v/v"}
        },
        "data": [
            {"DEPTH": 1000, "GR": 50, "RHOB": 2.3, "NPHI": 0.25},
            {"DEPTH": 1500, "GR": 75, "RHOB": 2.5, "NPHI": 0.20},
            {"DEPTH": 2000, "GR": 100, "RHOB": 2.6, "NPHI": 0.15},
            {"DEPTH": 2500, "GR": 120, "RHOB": 2.7, "NPHI": 0.10},
            {"DEPTH": 3000, "GR": 140, "RHOB": 2.8, "NPHI": 0.05},
        ]
    }
    project.wells["Well-A"] = well_data
    
    # Save project
    project_path = Path.home() / "Documents" / "example_project.pproj"
    success = save_project(str(project_path), project)
    
    if success:
        print(f"✓ Project saved to: {project_path}")
        print(f"  - Project Name: {project.name}")
        print(f"  - Wells: {list(project.wells.keys())}")
        print(f"  - Field: {project.metadata.get('field', 'N/A')}")
    else:
        print(f"✗ Failed to save project")
    
    return str(project_path)


def example_load_project(project_path):
    """Example: Load a project from file."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Load Project")
    print("=" * 60)
    
    project = load_project(project_path)
    if project is None:
        print(f"✗ Failed to load project: {project_path}")
        return
    
    print(f"✓ Project loaded: {project.name}")
    print(f"  - Path: {project.path}")
    print(f"  - Created: {project.created}")
    print(f"  - Modified: {project.modified}")
    print(f"  - Wells: {list(project.wells.keys())}")
    print(f"  - Metadata: {project.metadata}")
    
    # Print well data
    for well_name, well_data in project.wells.items():
        print(f"\n  Well: {well_name}")
        print(f"    - Header: {well_data.get('header', {})}")
        print(f"    - Log Info: {well_data.get('log_info', {})}")
        data_records = well_data.get('data', [])
        print(f"    - Data records: {len(data_records)}")
        if data_records:
            print(f"      First record: {data_records[0]}")
            print(f"      Last record: {data_records[-1]}")


def example_recent_projects():
    """Example: Get recent projects."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Recent Projects")
    print("=" * 60)
    
    recent = get_recent_projects(5)
    if recent:
        print(f"✓ Found {len(recent)} recent projects:")
        for i, path in enumerate(recent, 1):
            print(f"  {i}. {Path(path).name} - {path}")
    else:
        print("No recent projects found")


def example_integration_workflow():
    """Example: Full workflow integration."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Full Workflow Integration")
    print("=" * 60)
    
    from services.project_service import ProjectService
    from services.data_service import DataService
    
    # This would normally be part of MainController
    # but shown here for clarity
    
    print("""
    In the actual application, the workflow is:
    
    1. User clicks "New Project" on Dashboard
       → ProjectService.new_project() shows dialog
       → Creates ProjectData object
       → Updates UI state (window title, project header)
    
    2. User imports well data via "Load Well Logs" button
       → DataService.import_data() loads LAS/CSV file
       → Creates Well object in DataService._wells dict
       → ProjectService marks project as modified
    
    3. User performs analysis (Vsh, Phi, Sw calculations)
       → InterpretationService computes values
       → Updates Well.data dataframe
       → ProjectService marks modified
    
    4. User clicks "Save Project"
       → ProjectService._serialize_well_data() exports wells
       → ProjectData.wells updated with serialized data
       → save_project() writes JSON to disk
       → Recent projects list updated
    
    5. User closes app or opens another project
       → Check if modified, prompt to save
       → ProjectData cleared from memory
    
    6. User clicks "Load Recent Project" (e.g., btnDashRecent1)
       → ProjectService.load_recent_project()
       → load_project() reads JSON from disk
       → _deserialize_well_data() restores Well objects
       → DataService._wells populated
       → UI updated with project state
    """)


if __name__ == "__main__":
    # Run examples
    print("\nPETROVISION PROJECT MANAGEMENT EXAMPLES\n")
    
    # Example 1: Create and save
    project_path = example_create_and_save_project()
    
    # Example 2: Load project
    example_load_project(project_path)
    
    # Example 3: Recent projects
    example_recent_projects()
    
    # Example 4: Integration workflow
    example_integration_workflow()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
