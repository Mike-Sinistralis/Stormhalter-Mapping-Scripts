import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import zipfile
import gzip
import glob
import shutil


class ScrollableFrame(ttk.Frame):
    """A scrollable frame container that adds scrollbars when content exceeds visible area."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar_y = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar_x = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)

        # Create the inner frame that will hold all content
        self.inner_frame = ttk.Frame(self.canvas, padding="10")

        # Create window inside canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        # Configure canvas scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)

        # Layout
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.scrollbar_x.grid(row=1, column=0, sticky="ew")

        # Make canvas expand
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Bind events
        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Bind mouse wheel scrolling
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _on_frame_configure(self, event):
        """Update scroll region when inner frame size changes."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Expand inner frame width to fill canvas when canvas is wider."""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def _bind_mousewheel(self, event):
        """Bind mouse wheel when entering canvas."""
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

    def _unbind_mousewheel(self, event):
        """Unbind mouse wheel when leaving canvas."""
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Shift-MouseWheel>")

    def _on_mousewheel(self, event):
        """Handle vertical mouse wheel scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(self, event):
        """Handle horizontal mouse wheel scrolling (Shift+scroll)."""
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")


class MapperLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Stormhalter Mapping Tools")
        self.root.geometry("600x850")
        self.root.resizable(True, True)

        # Get the directory where this script is located
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Create main container with padding
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Use PanedWindow for resizable split between tabs and output
        paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Top pane: notebook with tabs
        notebook_frame = ttk.Frame(paned)
        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs with scrollable frames
        self.setup_tab = ScrollableFrame(self.notebook)
        self.extract_tab = ScrollableFrame(self.notebook)
        self.mapping_tab = ScrollableFrame(self.notebook)
        self.manage_tab = ScrollableFrame(self.notebook)

        self.notebook.add(self.setup_tab, text="Setup")
        self.notebook.add(self.extract_tab, text="Data Extraction")
        self.notebook.add(self.mapping_tab, text="Mapping")
        self.notebook.add(self.manage_tab, text="Manage")

        # Build each tab (using inner_frame for content)
        self.build_setup_tab()
        self.build_extract_tab()
        self.build_mapping_tab()
        self.build_manage_tab()

        paned.add(notebook_frame, weight=1)

        # Bottom pane: Output area (always visible, resizable)
        output_frame = ttk.LabelFrame(paned, text="Output", padding="5")

        self.output_text = scrolledtext.ScrolledText(output_frame, height=8, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # Clear output button
        ttk.Button(output_frame, text="Clear Output", command=self.clear_output).pack(pady=(5, 0))

        paned.add(output_frame, weight=1)

        self.log("Stormhalter Mapping Tools ready.")
        self.log(f"Working directory: {self.script_dir}")

    def build_setup_tab(self):
        """Build the Setup tab with initialization controls."""
        tab = self.setup_tab.inner_frame

        # Description
        desc = ttk.Label(tab, text="First-time setup: Enter your PostgreSQL password and click Initialize.\n"
            "This will install Python packages and set up the database.",
            wraplength=500, justify="center")
        desc.pack(pady=(0, 15))

        # Password frame
        pw_frame = ttk.Frame(tab)
        pw_frame.pack(fill=tk.X, pady=5)

        ttk.Label(pw_frame, text="PostgreSQL Password:").pack(side=tk.LEFT)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(pw_frame, textvariable=self.password_var, show="*", width=30)
        self.password_entry.pack(side=tk.LEFT, padx=(10, 0))

        # Show password checkbox
        self.show_pw_var = tk.BooleanVar()
        ttk.Checkbutton(pw_frame, text="Show", variable=self.show_pw_var,
            command=self.toggle_password_visibility).pack(side=tk.LEFT, padx=(10, 0))

        # Load existing password if available
        self.load_existing_password()

        # Initialize button
        init_frame = ttk.Frame(tab)
        init_frame.pack(fill=tk.X, pady=20)

        self.init_btn = ttk.Button(init_frame, text="Initialize (Install Packages + Setup Database)",
            command=self.run_initialize)
        self.init_btn.pack()

        # Status indicators
        status_frame = ttk.LabelFrame(tab, text="Status", padding="10")
        status_frame.pack(fill=tk.X, pady=10)

        ttk.Button(status_frame, text="Test Database Connection",
            command=self.test_connection).pack(pady=5)

    def build_mapping_tab(self):
        """Build the Mapping tab with replay and map generation controls."""
        tab = self.mapping_tab.inner_frame

        # Load Replay section
        replay_frame = ttk.LabelFrame(tab, text="Load Replay", padding="10")
        replay_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(replay_frame, text="Load a .sr replay file to extract map data.",
            wraplength=500).pack()
        ttk.Button(replay_frame, text="Load Replay File",
            command=self.run_load_replay).pack(pady=10)

        # Generate Maps section
        maps_frame = ttk.LabelFrame(tab, text="Generate Maps", padding="10")
        maps_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(maps_frame, text="Generate PNG map images. Leave fields blank to generate all maps.\n"
            "Threads controls how many maps are generated in parallel (higher = faster but uses more memory).",
            wraplength=500).pack()

        # Segment/Region inputs
        input_frame = ttk.Frame(maps_frame)
        input_frame.pack(fill=tk.X, pady=10)

        ttk.Label(input_frame, text="Segment ID:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.map_segment_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.map_segment_var, width=10).grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="Region ID:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.map_region_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.map_region_var, width=10).grid(row=0, column=3, padx=5)

        ttk.Label(input_frame, text="Threads:").grid(row=0, column=4, sticky=tk.W, padx=5)
        self.map_threads_var = tk.StringVar(value="4")
        ttk.Entry(input_frame, textvariable=self.map_threads_var, width=5).grid(row=0, column=5, padx=5)

        ttk.Button(maps_frame, text="Generate Maps",
            command=self.run_make_maps).pack(pady=5)

        # List Segments section
        segments_frame = ttk.LabelFrame(tab, text="View Segments", padding="10")
        segments_frame.pack(fill=tk.X)

        ttk.Button(segments_frame, text="List All Segments",
            command=self.run_get_segments).pack(pady=5)

    def build_extract_tab(self):
        """Build the Data Extraction tab for extracting game assets."""
        tab = self.extract_tab.inner_frame

        # Description
        desc = ttk.Label(tab,
            text="Extract game data from Stormhalter/LoK .bin files.\n"
                 "This is needed to get terrain graphics and definitions for map generation.",
            wraplength=500, justify="center")
        desc.pack(pady=(0, 15))

        # Game folder selection
        folder_frame = ttk.LabelFrame(tab, text="Game Data Location", padding="10")
        folder_frame.pack(fill=tk.X, pady=(0, 10))

        path_frame = ttk.Frame(folder_frame)
        path_frame.pack(fill=tk.X)

        ttk.Label(path_frame, text="Game Folder:").pack(side=tk.LEFT)
        self.game_folder_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.game_folder_var, width=50).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Button(path_frame, text="Browse...", command=self.browse_game_folder).pack(side=tk.LEFT)

        ttk.Label(folder_frame, text="Select the Stormhalter game folder (contains Data.bin, etc.)",
            foreground="gray").pack(anchor=tk.W, pady=(5, 0))

        # Extraction section
        extract_frame = ttk.LabelFrame(tab, text="Extract .bin Files", padding="10")
        extract_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(extract_frame,
            text="Extracts compressed data from .bin files to the ./unzip/ folder.\n"
                 "Re-extracting will update existing files with newer versions.",
            wraplength=500).pack()

        btn_frame = ttk.Frame(extract_frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Extract Data.bin",
            command=lambda: self.extract_bin_file("Data.bin")).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Extract All .bin Files",
            command=self.extract_all_bins).pack(side=tk.LEFT, padx=5)

        # Status frame
        status_frame = ttk.LabelFrame(tab, text="Extraction Status", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.extract_status_text = tk.Text(status_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.extract_status_text.pack(fill=tk.X)

        ttk.Button(status_frame, text="Refresh Status", command=self.check_extraction_status).pack(pady=(5, 0))

        # Convert XNB section
        convert_frame = ttk.LabelFrame(tab, text="Convert XNB Files", padding="10")
        convert_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(convert_frame,
            text="Converts .xnb files from ./unzip/ to PNG/WAV in ./unxnb/.\n"
                 "This is REQUIRED before generating maps - it extracts the terrain textures.\n"
                 "Run this after extracting .bin files.",
            wraplength=500).pack()

        ttk.Button(convert_frame, text="Convert XNB Files",
            command=self.run_convert_xnb).pack(pady=10)

        # Load terrain section
        terrain_frame = ttk.LabelFrame(tab, text="Load Terrain Data", padding="10")
        terrain_frame.pack(fill=tk.X)

        ttk.Label(terrain_frame,
            text="After extraction, load terrain definitions into the database.\n"
                 "This reads terrain*.xml files from the extracted data.\n"
                 "Safe to re-run if game content has been updated.",
            wraplength=500).pack()

        ttk.Button(terrain_frame, text="Load Terrain Data",
            command=self.run_load_terrain).pack(pady=10)

        # Check status on tab load
        self.check_extraction_status()

    def browse_game_folder(self):
        """Open folder browser for game directory."""
        folder = filedialog.askdirectory(title="Select Stormhalter Game Folder")
        if folder:
            self.game_folder_var.set(folder)
            self.check_extraction_status()

    def detect_container_type(self, filepath):
        """Detect if file is ZIP or GZIP based on magic bytes."""
        try:
            with open(filepath, 'rb') as f:
                header = f.read(4)
                if header[:2] == b'\x1f\x8b':
                    return 'gzip'
                elif header[:4] == b'PK\x03\x04':
                    return 'zip'
                else:
                    return 'unknown'
        except Exception as e:
            self.log(f"Error reading file header: {e}")
            return 'unknown'

    def extract_bin_file(self, bin_name):
        """Extract a single .bin file."""
        game_folder = self.game_folder_var.get().strip()
        if not game_folder:
            messagebox.showerror("Error", "Please select the game folder first.")
            return

        bin_path = os.path.join(game_folder, bin_name)
        if not os.path.exists(bin_path):
            messagebox.showerror("Error", f"File not found: {bin_path}")
            return

        output_dir = os.path.join(self.script_dir, "unzip")

        # Check if output already exists
        existing_files = 0
        if os.path.exists(output_dir):
            existing_files = sum(1 for _ in glob.glob(os.path.join(output_dir, "**", "*"), recursive=True)
                               if os.path.isfile(_))

        if existing_files > 0:
            self.log(f"\nExtracting {bin_name}... (updating {existing_files} existing files)")
        else:
            self.log(f"\nExtracting {bin_name}... (first-time extraction)")

        def do_extract():
            try:
                container_type = self.detect_container_type(bin_path)
                self.root.after(0, lambda: self.log(f"Detected format: {container_type}"))

                os.makedirs(output_dir, exist_ok=True)

                new_files = 0
                updated_files = 0

                if container_type == 'zip':
                    with zipfile.ZipFile(bin_path, 'r') as zf:
                        file_list = zf.namelist()
                        self.root.after(0, lambda: self.log(f"Archive contains {len(file_list)} files"))

                        for file_name in file_list:
                            dest_path = os.path.join(output_dir, file_name)
                            if os.path.exists(dest_path):
                                updated_files += 1
                            else:
                                new_files += 1

                        zf.extractall(output_dir)
                        self.root.after(0, lambda: self.log(f"Extracted to {output_dir}"))
                        self.root.after(0, lambda: self.log(f"  New files: {new_files}, Updated: {updated_files}"))

                elif container_type == 'gzip':
                    # GZIP typically contains a single file - extract based on bin name
                    output_name = bin_name.replace('.bin', '')
                    output_path = os.path.join(output_dir, output_name)

                    action = "Updating" if os.path.exists(output_path) else "Creating"

                    with gzip.open(bin_path, 'rb') as gz:
                        with open(output_path, 'wb') as out:
                            shutil.copyfileobj(gz, out)
                    self.root.after(0, lambda: self.log(f"{action}: {output_path}"))

                else:
                    self.root.after(0, lambda: self.log(f"Unknown format - trying as ZIP..."))
                    try:
                        with zipfile.ZipFile(bin_path, 'r') as zf:
                            zf.extractall(output_dir)
                            self.root.after(0, lambda: self.log(f"Extracted as ZIP to {output_dir}"))
                    except zipfile.BadZipFile:
                        self.root.after(0, lambda: self.log(f"Failed - not a valid ZIP or GZIP file"))
                        return

                self.root.after(0, lambda: self.log(f"\n{bin_name} extraction complete!"))
                self.root.after(0, self.check_extraction_status)

            except Exception as e:
                self.root.after(0, lambda: self.log(f"Error extracting: {e}"))

        thread = threading.Thread(target=do_extract, daemon=True)
        thread.start()

    def extract_all_bins(self):
        """Extract all .bin files from game folder."""
        game_folder = self.game_folder_var.get().strip()
        if not game_folder:
            messagebox.showerror("Error", "Please select the game folder first.")
            return

        bin_files = glob.glob(os.path.join(game_folder, "*.bin"))
        if not bin_files:
            messagebox.showinfo("Info", "No .bin files found in the selected folder.")
            return

        output_dir = os.path.join(self.script_dir, "unzip")

        # Check existing state
        existing_files = 0
        if os.path.exists(output_dir):
            existing_files = sum(1 for _ in glob.glob(os.path.join(output_dir, "**", "*"), recursive=True)
                               if os.path.isfile(_))

        if existing_files > 0:
            self.log(f"\nFound {len(bin_files)} .bin files to extract...")
            self.log(f"(./unzip/ already contains {existing_files} files - will update)")
        else:
            self.log(f"\nFound {len(bin_files)} .bin files to extract... (first-time extraction)")

        def do_extract_all():
            total_new = 0
            total_updated = 0

            for bin_path in bin_files:
                bin_name = os.path.basename(bin_path)
                self.root.after(0, lambda n=bin_name: self.log(f"\nProcessing {n}..."))

                try:
                    container_type = self.detect_container_type(bin_path)
                    os.makedirs(output_dir, exist_ok=True)

                    if container_type == 'zip':
                        with zipfile.ZipFile(bin_path, 'r') as zf:
                            for file_name in zf.namelist():
                                if os.path.exists(os.path.join(output_dir, file_name)):
                                    total_updated += 1
                                else:
                                    total_new += 1
                            zf.extractall(output_dir)
                            self.root.after(0, lambda: self.log("  Extracted (ZIP)"))

                    elif container_type == 'gzip':
                        output_name = bin_name.replace('.bin', '')
                        output_path = os.path.join(output_dir, output_name)

                        if os.path.exists(output_path):
                            total_updated += 1
                        else:
                            total_new += 1

                        with gzip.open(bin_path, 'rb') as gz:
                            with open(output_path, 'wb') as out:
                                shutil.copyfileobj(gz, out)
                        self.root.after(0, lambda: self.log("  Extracted (GZIP)"))

                    else:
                        try:
                            with zipfile.ZipFile(bin_path, 'r') as zf:
                                zf.extractall(output_dir)
                                self.root.after(0, lambda: self.log("  Extracted (ZIP fallback)"))
                        except:
                            self.root.after(0, lambda: self.log("  Skipped (unknown format)"))

                except Exception as e:
                    self.root.after(0, lambda e=e: self.log(f"  Error: {e}"))

            self.root.after(0, lambda: self.log(f"\nAll extractions complete!"))
            self.root.after(0, lambda: self.log(f"  New files: {total_new}, Updated: {total_updated}"))
            self.root.after(0, self.check_extraction_status)

        thread = threading.Thread(target=do_extract_all, daemon=True)
        thread.start()

    def check_extraction_status(self):
        """Check what data has been extracted."""
        status_lines = []

        unzip_dir = os.path.join(self.script_dir, "unzip")
        unxnb_dir = os.path.join(self.script_dir, "unxnb")

        terrain_found = False
        ready_for_mapping = False

        # Check unzip folder
        if os.path.exists(unzip_dir):
            file_count = sum(1 for _ in glob.glob(os.path.join(unzip_dir, "**", "*"), recursive=True)
                           if os.path.isfile(_))
            status_lines.append(f"./unzip/ folder: {file_count} files extracted")

            # Check for terrain XML files
            terrain_files = glob.glob(os.path.join(unzip_dir, "**", "terrain*.xml"), recursive=True)
            if terrain_files:
                status_lines.append(f"  Found {len(terrain_files)} terrain XML file(s) - ready for terrain load")
                terrain_found = True
            else:
                status_lines.append("  No terrain*.xml files found - extract Data.bin first")

            # Check for XNB files
            xnb_files = glob.glob(os.path.join(unzip_dir, "**", "*.xnb"), recursive=True)
            if xnb_files:
                status_lines.append(f"  Found {len(xnb_files)} .xnb file(s)")
        else:
            status_lines.append("./unzip/ folder: Not yet created")
            status_lines.append("  Click 'Extract Data.bin' or 'Extract All' to begin")

        # Check unxnb folder
        if os.path.exists(unxnb_dir):
            png_count = len(glob.glob(os.path.join(unxnb_dir, "**", "*.png"), recursive=True))
            wav_count = len(glob.glob(os.path.join(unxnb_dir, "**", "*.wav"), recursive=True))
            status_lines.append(f"./unxnb/ folder: {png_count} PNG, {wav_count} WAV files")
            if png_count > 0:
                ready_for_mapping = True
        else:
            status_lines.append("./unxnb/ folder: Not yet created")

        # Summary
        status_lines.append("")
        if terrain_found and ready_for_mapping:
            status_lines.append("Status: Ready for mapping!")
        elif terrain_found:
            status_lines.append("Status: Terrain XML found. Load terrain data, then proceed to mapping.")
        else:
            status_lines.append("Status: Extract game data to begin.")

        # Update status text
        self.extract_status_text.config(state=tk.NORMAL)
        self.extract_status_text.delete(1.0, tk.END)
        self.extract_status_text.insert(tk.END, "\n".join(status_lines))
        self.extract_status_text.config(state=tk.DISABLED)

    def run_convert_xnb(self):
        """Run the XNB conversion script."""
        self.run_script("convert from extracted xnbs.py", description="Convert XNB Files")

    def run_load_terrain(self):
        """Run the load terrain script."""
        self.run_script("load terrain.py", description="Load Terrain Data")

    def build_manage_tab(self):
        """Build the Manage tab with segment/region management controls."""
        tab = self.manage_tab.inner_frame

        # Create Segment section
        create_frame = ttk.LabelFrame(tab, text="Create New Segment", padding="10")
        create_frame.pack(fill=tk.X, pady=(0, 10))

        input_frame = ttk.Frame(create_frame)
        input_frame.pack(fill=tk.X)

        ttk.Label(input_frame, text="Segment Name:").pack(side=tk.LEFT)
        self.new_segment_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.new_segment_var, width=30).pack(side=tk.LEFT, padx=10)
        ttk.Button(input_frame, text="Create", command=self.run_create_segment).pack(side=tk.LEFT)

        # Rename Region section
        rename_frame = ttk.LabelFrame(tab, text="Rename Region", padding="10")
        rename_frame.pack(fill=tk.X, pady=(0, 10))

        input_frame2 = ttk.Frame(rename_frame)
        input_frame2.pack(fill=tk.X)

        ttk.Label(input_frame2, text="Segment:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.rename_segment_var = tk.StringVar()
        ttk.Entry(input_frame2, textvariable=self.rename_segment_var, width=8).grid(row=0, column=1, padx=2)

        ttk.Label(input_frame2, text="Region:").grid(row=0, column=2, sticky=tk.W, padx=2)
        self.rename_region_var = tk.StringVar()
        ttk.Entry(input_frame2, textvariable=self.rename_region_var, width=8).grid(row=0, column=3, padx=2)

        ttk.Label(input_frame2, text="New Name:").grid(row=0, column=4, sticky=tk.W, padx=2)
        self.rename_name_var = tk.StringVar()
        ttk.Entry(input_frame2, textvariable=self.rename_name_var, width=20).grid(row=0, column=5, padx=2)

        ttk.Button(input_frame2, text="Rename", command=self.run_rename_region).grid(row=0, column=6, padx=10)

        # Delete Region section
        delete_frame = ttk.LabelFrame(tab, text="Delete Region Data", padding="10")
        delete_frame.pack(fill=tk.X)

        ttk.Label(delete_frame, text="Use this when you accidentally entered wrong coordinates while loading a replay.\n"
            "Deleting the region data lets you re-load the replay with correct coordinates.",
            wraplength=500, justify="center").pack(pady=(0, 5))

        ttk.Label(delete_frame, text="Warning: This permanently deletes all tile data for a region!",
            foreground="red").pack()

        input_frame3 = ttk.Frame(delete_frame)
        input_frame3.pack(fill=tk.X, pady=10)

        ttk.Label(input_frame3, text="Segment:").pack(side=tk.LEFT)
        self.delete_segment_var = tk.StringVar()
        ttk.Entry(input_frame3, textvariable=self.delete_segment_var, width=8).pack(side=tk.LEFT, padx=5)

        ttk.Label(input_frame3, text="Region:").pack(side=tk.LEFT)
        self.delete_region_var = tk.StringVar()
        ttk.Entry(input_frame3, textvariable=self.delete_region_var, width=8).pack(side=tk.LEFT, padx=5)

        ttk.Button(input_frame3, text="Delete Region",
            command=self.run_delete_region).pack(side=tk.LEFT, padx=20)

    def toggle_password_visibility(self):
        """Toggle password field visibility."""
        if self.show_pw_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")

    def load_existing_password(self):
        """Load existing password from db_config.py if available."""
        config_path = os.path.join(self.script_dir, "db_config.py")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    content = f.read()
                    # Simple extraction - look for password in the config
                    import re
                    match = re.search(r'"password":\s*"([^"]*)"', content)
                    if match:
                        pw = match.group(1)
                        if pw and pw != "YOUR_PASSWORD_HERE":
                            self.password_var.set(pw)
            except:
                pass

    def save_password(self):
        """Save password to db_config.py."""
        password = self.password_var.get()
        if not password:
            messagebox.showerror("Error", "Please enter a password.")
            return False

        config_content = f'''import psycopg
from psycopg.rows import dict_row

# Database configuration - edit these values for your setup
DB_CONFIG = {{
    "dbname": "stormhalter",
    "user": "postgres",
    "password": "{password}",
}}


def get_connection():
    """Get a database connection with dict_row factory."""
    return psycopg.connect(**DB_CONFIG, row_factory=dict_row)
'''
        config_path = os.path.join(self.script_dir, "db_config.py")
        try:
            with open(config_path, 'w') as f:
                f.write(config_content)
            self.log("Password saved to db_config.py")
            return True
        except Exception as e:
            self.log(f"Error saving config: {e}")
            return False

    def log(self, message):
        """Add a message to the output area."""
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.root.update_idletasks()

    def clear_output(self):
        """Clear the output area."""
        self.output_text.delete(1.0, tk.END)

    def run_command(self, cmd, description):
        """Run a command and display output."""
        self.log(f"\n{'='*50}")
        self.log(f"Running: {description}")
        self.log(f"{'='*50}")

        def execute():
            try:
                # Use the Python executable that's running this script
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=self.script_dir,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )

                for line in process.stdout:
                    self.root.after(0, lambda l=line: self.log(l.rstrip()))

                process.wait()

                if process.returncode == 0:
                    self.root.after(0, lambda: self.log(f"\n{description} completed successfully."))
                else:
                    self.root.after(0, lambda: self.log(f"\n{description} finished with errors."))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Error: {e}"))

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()

    def run_script(self, script_name, args=None, description=None):
        """Run a Python script with optional arguments."""
        script_path = os.path.join(self.script_dir, script_name)
        # Use -u flag for unbuffered output so print() statements appear immediately
        cmd = [sys.executable, "-u", script_path]
        if args:
            cmd.extend(args)

        if description is None:
            description = script_name

        self.run_command(cmd, description)

    def run_initialize(self):
        """Run the full initialization process."""
        if not self.save_password():
            return

        self.log("\n" + "="*50)
        self.log("Starting initialization...")
        self.log("="*50)

        def do_init():
            # Step 1: Install pip packages
            self.root.after(0, lambda: self.log("\nStep 1: Installing Python packages..."))
            packages = ["psycopg[binary]", "pillow", "beautifulsoup4", "lxml", "pyodbc", "lz4", "numpy", "soundfile"]

            try:
                process = subprocess.Popen(
                    [sys.executable, "-m", "pip", "install"] + packages,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )

                for line in process.stdout:
                    self.root.after(0, lambda l=line: self.log(l.rstrip()))

                process.wait()

                if process.returncode != 0:
                    self.root.after(0, lambda: self.log("Warning: Some packages may have failed to install."))
                else:
                    self.root.after(0, lambda: self.log("Packages installed successfully."))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Error installing packages: {e}"))
                return

            # Step 2: Run initdb.py
            self.root.after(0, lambda: self.log("\nStep 2: Initializing database..."))

            try:
                script_path = os.path.join(self.script_dir, "initdb.py")
                process = subprocess.Popen(
                    [sys.executable, script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    cwd=self.script_dir,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )

                # Send "yes" to confirm database recreation if prompted
                stdout, _ = process.communicate(input="yes\n", timeout=300)

                for line in stdout.split('\n'):
                    if line:
                        self.root.after(0, lambda l=line: self.log(l))

                if process.returncode == 0:
                    self.root.after(0, lambda: self.log("\nInitialization complete!"))
                else:
                    self.root.after(0, lambda: self.log("\nDatabase initialization had issues. Check output above."))
            except subprocess.TimeoutExpired:
                process.kill()
                self.root.after(0, lambda: self.log("Database initialization timed out."))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Error during database init: {e}"))

        thread = threading.Thread(target=do_init, daemon=True)
        thread.start()

    def test_connection(self):
        """Test the database connection."""
        self.log("\nTesting database connection...")

        def do_test():
            try:
                # Try to import and connect
                sys.path.insert(0, self.script_dir)

                # Reload db_config in case password changed
                import importlib
                if 'db_config' in sys.modules:
                    importlib.reload(sys.modules['db_config'])

                from db_config import get_connection
                conn = get_connection()
                conn.close()
                self.root.after(0, lambda: self.log("Database connection successful!"))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Connection failed: {e}"))

        thread = threading.Thread(target=do_test, daemon=True)
        thread.start()

    def run_load_replay(self):
        """Run the load replay script."""
        self.run_script("load replay.py", description="Load Replay")

    def run_make_maps(self):
        """Run the make maps script."""
        args = []
        segment = self.map_segment_var.get().strip()
        region = self.map_region_var.get().strip()
        threads = self.map_threads_var.get().strip()

        if segment:
            args.extend(["--segment", segment])
        if region:
            args.extend(["--region", region])
        if threads:
            try:
                thread_count = int(threads)
                if thread_count > 0:
                    args.extend(["--threads", str(thread_count)])
            except ValueError:
                pass  # Use default if invalid

        self.run_script("make maps.py", args if args else None, description="Generate Maps")

    def run_get_segments(self):
        """Run the get segments script."""
        self.run_script("get segments.py", description="List Segments")

    def run_create_segment(self):
        """Run the create segment script."""
        name = self.new_segment_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter a segment name.")
            return

        self.run_script("create segment.py", ["--segmentname", name], description="Create Segment")
        self.new_segment_var.set("")

    def run_rename_region(self):
        """Run the rename region script."""
        segment = self.rename_segment_var.get().strip()
        region = self.rename_region_var.get().strip()
        name = self.rename_name_var.get().strip()

        if not segment or not region or not name:
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        self.run_script("name segmentregion.py",
            ["--segment", segment, "--region", region, "--regionname", name],
            description="Rename Region")

    def run_delete_region(self):
        """Run the delete region script with confirmation."""
        segment = self.delete_segment_var.get().strip()
        region = self.delete_region_var.get().strip()

        if not segment or not region:
            messagebox.showerror("Error", "Please enter both segment and region IDs.")
            return

        if not messagebox.askyesno("Confirm Delete",
            f"Are you sure you want to delete all data for segment {segment}, region {region}?\n\n"
            "This cannot be undone!"):
            return

        self.run_script("delete segmentregion.py",
            ["--segment", segment, "--region", region],
            description="Delete Region")


def main():
    root = tk.Tk()
    app = MapperLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
