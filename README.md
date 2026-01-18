# Stormhalter Mapping Tools

This guide explains how to set up and use the mapping tools to create maps from Legends of Kesmai (LoK) game data.

## Quick Start (Recommended)

For most users, use the **GUI Launcher** for an easier experience:

1. Install [Python](https://www.python.org/downloads/) and [PostgreSQL](https://www.postgresql.org/download/)
2. Double-click **`Stormhalter Mapper.bat`** to launch the application
3. Go to the **Setup** tab, enter your PostgreSQL password, and click **Initialize**
4. Go to the **Data Extraction** tab to extract game assets and load terrain data
5. Use the **Mapping** and **Manage** tabs to load replays and generate maps

The launcher handles package installation, database setup, and provides buttons for all common operations. The rest of this guide covers the manual command-line approach for advanced users or troubleshooting.

### GUI Launcher Tabs

- **Setup** - First-time configuration: enter your PostgreSQL password and initialize the database
- **Data Extraction** - Extract game assets from .bin files, convert XNB textures, and load terrain definitions
- **Mapping** - Load replay files and generate PNG map images
- **Manage** - Create segments, rename regions, and delete region data for re-mapping

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Opening a Command Prompt](#opening-a-command-prompt)
3. [Installation](#installation)
4. [Database Setup](#database-setup)
5. [Script Reference](#script-reference)
6. [Mapping Workflow](#mapping-workflow)
7. [Using Sandbox for Mapping](#using-sandbox-for-mapping)

---

## Prerequisites

Before you begin, you need to install two external programs:

### Python

Python is the programming language these scripts are written in.

1. Go to https://www.python.org/downloads/
2. Download the latest Python 3.x version (e.g., Python 3.12)
3. Run the installer
4. **Important:** Check the box that says "Add Python to PATH" during installation
5. Click "Install Now"

To verify Python is installed, open a Command Prompt and type:
```
python --version
```
You should see something like `Python 3.12.0`.

### PostgreSQL

PostgreSQL is the database that stores all the map data.

1. Go to https://www.postgresql.org/download/
2. Click on "Windows"
3. Download the installer from EnterpriseDB
4. Run the installer
5. During installation:
   - Remember the password you set for the `postgres` user - you'll need it later
   - Keep the default port (5432)
   - Complete the installation

---

## Opening a Command Prompt

> **Note:** If you're using the GUI Launcher (`launcher.py`), you can skip this section. The launcher provides a graphical interface for all common tasks. This section is for advanced users who prefer the command line or need to troubleshoot.

You'll need to use the Command Prompt to run the Python scripts. Here's how to open it:

### Method 1: From the Start Menu
1. Click the **Start** button (Windows icon in the bottom-left corner)
2. Type `cmd` or `Command Prompt`
3. Click on **Command Prompt** when it appears in the search results

### Method 2: From File Explorer (Recommended)
This method opens the Command Prompt directly in the mapping programs folder:
1. Open **File Explorer** (the folder icon on your taskbar, or press `Windows + E`)
2. Navigate to the folder containing the mapping scripts (e.g., `C:\Users\YourUsername\Downloads\Stormhalter Mapping Programs`)
3. Click in the **address bar** at the top (where the folder path is shown)
4. Type `cmd` and press **Enter**
5. A Command Prompt window will open, already in that folder

### Method 3: Right-Click Menu
1. Open **File Explorer** and navigate to the mapping programs folder
2. Hold **Shift** and **right-click** on an empty space in the folder
3. Select **Open command window here** or **Open PowerShell window here**

Once the Command Prompt is open, you'll see a black window with white text showing something like:
```
C:\Users\YourUsername\Downloads\Stormhalter Mapping Programs>
```

This is where you'll type commands to run the scripts.

---

## Installation (Manual Method)

> **Note:** The GUI Launcher handles all of this automatically. Only follow these steps if you prefer manual setup or are troubleshooting.

### Install Python Packages

Open a Command Prompt and navigate to the mapping programs folder (or use Method 2 above to open it directly there):
```
cd "C:\Users\YourUsername\Downloads\Stormhalter Mapping Programs"
```

Install the required Python packages:
```
pip install psycopg pillow beautifulsoup4 lxml pyodbc lz4 numpy soundfile
```

### Configure Database Connection

Open `db_config.py` in a text editor (like Notepad) and update the password to match your PostgreSQL password:

```python
DB_CONFIG = {
    "dbname": "stormhalter",
    "user": "postgres",
    "password": "YOUR_PASSWORD_HERE",
}
```

### Initialize the Database

The `initdb.py` script will automatically create the database and restore it from the most recent backup file in the `backup` folder.

1. Make sure there's a backup file (`.dump`, `.sql`, or `.backup`) in the `backup` folder
2. Run the initialization script:
   ```
   python initdb.py
   ```
3. The script will:
   - Check that PostgreSQL is installed and accessible
   - Find the most recent backup file
   - Create the `stormhalter` database
   - Restore all tables and data from the backup

If the database already exists, the script will ask if you want to drop and recreate it.

**Note:** If you see an error about PostgreSQL tools not being found, you need to add the PostgreSQL `bin` folder to your system PATH:
1. Search for "Environment Variables" in Windows
2. Click "Environment Variables..."
3. Under "System variables", find "Path" and click "Edit"
4. Click "New" and add: `C:\Program Files\PostgreSQL\16\bin` (adjust version number if different)
5. Click OK and restart your Command Prompt

---

## Script Reference

### Core Scripts

#### `db_config.py`
**Purpose:** Stores database connection settings used by all other scripts.
**Arguments:** None (configuration file only)
**Usage:** Edit this file to set your database password.

#### `initdb.py`
**Purpose:** Creates the database and restores it from a backup file. Run this once when setting up on a new computer.
**Arguments:** None (interactive prompts)
**Usage:**
```
python initdb.py
```
The script will find the most recent backup file in the `backup` folder and restore it. If the database already exists, it will ask for confirmation before dropping and recreating it.

#### `get segments.py`
**Purpose:** Lists all segments (world areas) and their IDs.
**Arguments:** None
**Usage:**
```
python "get segments.py"
```
**Output:** A table showing segment IDs and names (e.g., 1 = Kesmai, 2 = Leng)

#### `create segment.py`
**Purpose:** Creates a new segment for mapping new areas.
**Arguments:**
- `--segmentname` (required): Name of the new segment

**Usage:**
```
python "create segment.py" --segmentname "New Area Name"
```

#### `name segmentregion.py`
**Purpose:** Updates the name of a region within a segment.
**Arguments:**
- `--segment` (required): Segment ID number
- `--region` (required): Region ID number
- `--regionname` (required): New name for the region

**Usage:**
```
python "name segmentregion.py" --segment 1 --region 5 --regionname "Town Square"
```

#### `delete segmentregion.py`
**Purpose:** Removes all tile data for a specific segment/region combination. Use this to re-map an area from scratch.
**Arguments:**
- `--segment` (required): Segment ID number
- `--region` (required): Region ID number

**Usage:**
```
python "delete segmentregion.py" --segment 1 --region 5
```

### Map Generation Scripts

#### `load replay.py`
**Purpose:** Loads a game replay file and extracts tile data into the database.
**Arguments:** None (uses file picker dialog)
**Usage:**
```
python "load replay.py"
```
A file picker will open. Select your `.sr` replay file. Then follow the prompts to enter coordinates for each region transition.

#### `make maps.py`
**Purpose:** Generates PNG map images from the database. Supports multi-threaded processing for faster generation.
**Arguments:**
- `--segment` (optional): Filter by segment ID
- `--region` (optional): Filter by region ID
- `--threads` (optional): Number of worker threads for parallel processing (default: 4)

**Usage:**
```
# Generate all maps
python "make maps.py"

# Generate maps for segment 1 only
python "make maps.py" --segment 1

# Generate map for segment 1, region 5 only
python "make maps.py" --segment 1 --region 5

# Generate all maps using 8 threads for faster processing
python "make maps.py" --threads 8
```

### Asset Conversion Scripts

#### `convert from extracted xnbs.py`
**Purpose:** Converts XNB game assets (textures, audio) to PNG/WAV files. This is **required** before generating maps - it extracts the terrain textures that `make maps.py` uses.
**Arguments:** None
**Usage:**
```
python "convert from extracted xnbs.py"
```
**Note:** Run this after extracting .bin files. Output goes to the `./unxnb/` folder.

### Asset Loading Scripts

#### `load terrain.py`
**Purpose:** Loads terrain definitions from game XML files into the database.
**Arguments:** None
**Usage:**
```
python "load terrain.py"
```

#### `load mapproj.py`
**Purpose:** Loads map projection data from game files.
**Arguments:** None (uses file picker dialog)
**Usage:**
```
python "load mapproj.py"
```

#### `bitmap generated sprites.py`
**Purpose:** Generates sprite coordinate data from bitmap files.
**Arguments:** None
**Usage:**
```
python "bitmap generated sprites.py"
```

### Utility Scripts

#### `view terrain.py`
**Purpose:** Generates a preview image of specific terrain or tiles.
**Arguments:** Various (used for debugging/previewing)

#### `regiontiles.py`
**Purpose:** Processes and adjusts tile rendering data.
**Arguments:** None (typically run as part of other scripts)

#### `bitmapfiles.py`
**Purpose:** Helper module for extracting sprites from bitmap files.
**Arguments:** None (library module, not run directly)

### Asset Extraction Scripts

#### `extract files from gziped bins.py`
**Purpose:** Extracts compressed game data files.
**Arguments:** None

#### `convert from extracted xnbs.py`
**Purpose:** Converts XNB game assets to usable formats.
**Arguments:** None

---

## Mapping Workflow

This section walks you through the complete process of creating a map from a game replay. These concepts apply whether you use the GUI Launcher or the command-line scripts.

### Step 1: Create a Replay in the Game

1. Launch Legends of Kesmai
2. Before exploring, start recording a replay:
   - Use the game's replay recording feature
   - The replay file will be saved with a `.sr` extension
3. Walk around the area you want to map
4. Stop the replay recording when done

### Step 2: Find Your Segment ID

Before loading the replay, you need to know the segment ID for the area you mapped.

- **GUI:** Go to the **Mapping** tab and click **List All Segments**
- **Terminal:** Run `python "get segments.py"`

This shows a list like:
```
ID     Name
------------------------------
1      Kesmai
2      Leng
3      Axe Glacier
...
```

If your segment doesn't exist yet, create it:
- **GUI:** Go to the **Manage** tab, enter the segment name, and click **Create**
- **Terminal:** Run `python "create segment.py" --segmentname "Area Name"`

### Step 3: Load the Replay

Load your replay file to extract map data:

- **GUI:** Go to the **Mapping** tab and click **Load Replay File**
- **Terminal:** Run `python "load replay.py"`

1. A file picker dialog will appear - select your `.sr` replay file
2. A coordinate prompt will appear for the starting position and each region transition

#### Understanding Transitions

A **transition** occurs whenever your surrounding tiles completely change. This happens when you:
- Climb up or down stairs
- Use a rope or ladder
- Step through a teleporter or portal
- Fall into a pit
- Enter or exit a building (Sometimes, it depends on if the mapping app can figure out where you went or not. Areas like the Light/Dark crafters in BG or Kesh gate teleports)
- Move between dungeon levels

Each transition requires you to enter new coordinates because the game has moved you to a completely different map area. A single replay file may have anywhere from **1 transition** (if you stayed in one area) to **many transitions** (if you moved between multiple areas).

**Important:** When recording a replay, use `/props` immediately after each transition to note your new coordinates. You'll need to enter these coordinates in the same order when loading the replay. The app will attempt to generate an image of your vision from immediately before the transition as sometimes moving between dark spaces can surprise you and be considered a transition, and this happening can completely mess up your mapping effort. It's recommended to try to split up your replays as much as possible so when this happens it doesn't completely ruin the effort put into mapping. (Usually only a problem in areas with a lot of darkness, like Battlegrounds)

**Handling Unexpected Transitions:** Sometimes darkness tiles can be misread as a transition. If you encounter an unexpected transition prompt and don't know the correct coordinates, **click Cancel (X) to stop processing the replay**. This prevents bad data from being written to the database. All previously processed data from the replay is saved. Generate maps to see the current state, then record a new replay to continue mapping from where you left off.

#### Entering Coordinates

The prompt asks for: `segment, x, y, region`

- **Segment ID:** The number from `get segments.py` (e.g., 1 for Kesmai)
- **X coordinate:** Your character's X position
- **Y coordinate:** Your character's Y position
- **Region ID:** The region number within the segment

**How to find X, Y, and Region:**
- In-game, type `/props` to see your current coordinates
- The game shows: `x, y, [region]`
- Combine with your segment ID in the format: `segment, x, y, region`

**Example:** If you're in Kesmai (segment 1) and `/props` shows `25, 30, [5]`, enter:
```
1, 25, 30, 5
```

After the first region, subsequent prompts will show a map image of where you were before the transition to help you figure out the new coordinates.

### Step 4: Generate the Map

Once the replay is loaded, generate the map images:

- **GUI:** Go to the **Mapping** tab, optionally enter Segment/Region IDs to filter, and click **Generate Maps**
- **Terminal:**
  ```
  # Generate just the map you worked on
  python "make maps.py" --segment 1 --region 5

  # Or generate all maps
  python "make maps.py"
  ```

Map images are saved as PNG files in the `newmaps` folder, organized by segment name.

### Step 5: Name Your Region (Optional)

Give the region a descriptive name so it's easier to identify:

- **GUI:** Go to the **Manage** tab, enter the Segment ID, Region ID, and new name, then click **Rename**
- **Terminal:** Run `python "name segmentregion.py" --segment 1 --region 5 --regionname "Underground Dungeon Level 1"`

### Re-mapping an Area

Use this **only** if bad map data was written due to an unexpected transition (e.g., darkness tiles were misread as a transition and you entered wrong coordinates). The solution is to delete the affected region entirely and start over:

1. Delete the existing data:
   - **GUI:** Go to the **Manage** tab, enter the Segment and Region IDs, and click **Delete**
   - **Terminal:** Run `python "delete segmentregion.py" --segment 1 --region 5`

2. Record a new replay and load it following steps 3-4 above

**Note:** This permanently deletes ALL tile data for the specified region. Only do this if the region has corrupted data that needs to be cleared.

---

## Using Sandbox for Mapping

The Sandbox server is highly recommended for mapping because you can make your character invulnerable and invisible, allowing you to explore dangerous areas safely.

### Sandbox Benefits

- **Invulnerability:** Explore without dying to monsters
- **Invisibility:** Move through areas without monsters attacking
- **Teleportation:** Quickly move to different areas
- **No consequences:** Test freely without affecting your main character

### Getting Started with Sandbox

Visit the Sandbox wiki for command references:
http://www.stormhalter.com/wiki/Sandbox

### Useful Sandbox Commands

Here are some helpful commands for mapping:

- Make yourself invulnerable (monsters can't hurt you)
- Make yourself invisible (monsters ignore you)
- Teleport to specific coordinates
- Spawn at different locations

Check the wiki link above for the complete list of commands and their syntax.

### Mapping Tips

1. **Plan your route:** Before recording, decide which areas you want to map
2. **Use `/props` frequently:** Note your coordinates at transitions
3. **Cover edges:** Walk along the borders of rooms to capture wall tiles
4. **Multiple replays:** You can load multiple replays for the same region to fill in gaps
5. **Consider a Thief:** Between speed and perception, it can make mapping go much quicker and generally is more complete. Find Secret Door is also handy w/ Perception

---

## Troubleshooting

### "Segment X not found"
Run `get segments.py` to see available segments, or create a new one with `create segment.py`.

### Database connection errors
- Make sure PostgreSQL is running
- Check your password in `db_config.py`
- Verify the `stormhalter` database exists

### Missing Python packages
Run the pip install command again:
```
pip install psycopg pillow beautifulsoup4 lxml pyodbc lz4 numpy soundfile
```

### Map images are blank or incomplete
- Make sure the replay covered the area
- Check that terrain data is loaded (`load terrain.py`)
- Verify coordinates were entered correctly during replay loading
