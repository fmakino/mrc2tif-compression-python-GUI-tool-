"""
MIT License

Copyright (c) 2024 Fumiaki Makino, JEOL Ltd.,

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor
import glob
import time
import threading

def compress_file(file_path, output_dir, text_widget):
    output_file = os.path.join(output_dir, os.path.basename(file_path).replace('.mrc', '.tif'))

    if os.path.exists(output_file):
        text_widget.insert(tk.END, f"File {output_file} already exists, skipping compression.\n")
        text_widget.yview(tk.END)  # Scroll to the end of the text box
        return file_path

    command = f'mrc2tif -s -c lzw "{file_path}" "{output_file}"'
    try:
        subprocess.run(command, shell=True, check=True)
        text_widget.insert(tk.END, f"Compressed {file_path} successfully.\n")
        text_widget.yview(tk.END)
        # Delete original files if option is selected and compression was successful
        if delete_after:
            os.remove(file_path)
        return file_path 
    except subprocess.CalledProcessError as e:
        text_widget.insert(tk.END, f"Error compressing {file_path}: {e}\n")
        text_widget.yview(tk.END)
        return f"Error compressing {file_path}: {e}"

def process_files(input_dir, output_dir, wildcard, cpu_count, delete_after, check_interval, stop_event, text_widget):
    # Collect all .mrc files in the directory matching the wildcard
    all_files = glob.glob(os.path.join(input_dir, wildcard))
    last_processed_time = time.time()

    # Process all existing files initially
    files_to_process = all_files

    if files_to_process:
        with ThreadPoolExecutor(max_workers=cpu_count) as executor:
            future_to_file = {executor.submit(compress_file, file_path, output_dir, text_widget): file_path for file_path in files_to_process}
            for future in future_to_file:
                result = future.result()
                if isinstance(result, str) and "Error" in result:
                    messagebox.showerror("Error", result)
        if delete_after:

    while not stop_event.is_set():  # Check if the stop event is set
        # Get the files that were added in the last interval (excluding the most recent file)
        time.sleep(check_interval)
        new_files = [f for f in glob.glob(os.path.join(input_dir, wildcard)) if os.path.getmtime(f) > last_processed_time]
        if new_files:
            last_processed_time = time.time()
        time.sleep(5)
        # Exclude the most recent file
        new_files = sorted(new_files, key=os.path.getmtime)

        if new_files:
            with ThreadPoolExecutor(max_workers=cpu_count) as executor:
                future_to_file = {executor.submit(compress_file, file_path, output_dir, text_widget): file_path for file_path in new_files}
                
                for future in future_to_file:
                    result = future.result()
                    if isinstance(result, str) and "Error" in result:
                        messagebox.showerror("Error", result)

            # Delete original files if option is selected and compression was successful
            if delete_after:
                for file_path in new_files:
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        messagebox.showerror("Error", f"Failed to delete file {file_path}: {e}")

def run_compression():
    # Disable the start button to prevent further clicks
    start_button.config(state=tk.DISABLED)

    input_dir = entry_input_dir.get()
    wildcard = entry_wildcard.get()
    output_dir = entry_output_dir.get()
    delete_after = var_delete.get()

    # Get the CPU count from user input
    try:
        cpu_count = int(entry_cpu_count.get())
        if cpu_count < 1:
            raise ValueError("CPU count must be at least 1")
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid CPU count.")
        # Enable the button again in case of an error
        start_button.config(state=tk.NORMAL)
        return

    # Get the interval time from user input
    try:
        check_interval = float(entry_check_interval.get())
        if check_interval <= 0:
            raise ValueError("Interval must be greater than 0")
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid interval time.")
        # Enable the button again in case of an error
        start_button.config(state=tk.NORMAL)
        return

    if not input_dir or not wildcard or not output_dir:
        messagebox.showerror("Error", "Please fill in all input fields.")
        # Enable the button again in case of an error
        start_button.config(state=tk.NORMAL)
        return

    # Check if specified folders exist
    if not os.path.isdir(input_dir):
        messagebox.showerror("Error", f"Input folder not found: {input_dir}")
        # Enable the button again in case of an error
        start_button.config(state=tk.NORMAL)
        return
    if not os.path.isdir(output_dir):
        messagebox.showerror("Error", f"Output folder not found: {output_dir}")
        # Enable the button again in case of an error
        start_button.config(state=tk.NORMAL)
        return

    # Create an event to stop the loop
    stop_event = threading.Event()

    # Start a separate thread for the file processing
    threading.Thread(target=process_files, args=(input_dir, output_dir, wildcard, cpu_count, delete_after, check_interval, stop_event, text_output), daemon=True).start()

def browse_input_dir():
    folder = filedialog.askdirectory(title="Select Input Folder")
    entry_input_dir.delete(0, tk.END)
    entry_input_dir.insert(0, folder)

def browse_output_dir():
    folder = filedialog.askdirectory(title="Select Output Folder")
    entry_output_dir.delete(0, tk.END)
    entry_output_dir.insert(0, folder)

# GUI setup
root = tk.Tk()
root.title("File Compression Tool")

# Input folder selection
frame_input = tk.Frame(root)
frame_input.pack(pady=5)
tk.Label(frame_input, text="Input Folder:").pack(side=tk.LEFT)
entry_input_dir = tk.Entry(frame_input, width=50)
entry_input_dir.pack(side=tk.LEFT)
tk.Button(frame_input, text="Browse", command=browse_input_dir).pack(side=tk.LEFT)

# Wildcard input
frame_wildcard = tk.Frame(root)
frame_wildcard.pack(pady=5)
tk.Label(frame_wildcard, text="Filename Wildcard:").pack(side=tk.LEFT)
entry_wildcard = tk.Entry(frame_wildcard, width=20)
entry_wildcard.insert(0, "*.mrc")  # Default to "*.mrc"
entry_wildcard.pack(side=tk.LEFT)

# Output folder selection
frame_output = tk.Frame(root)
frame_output.pack(pady=5)
tk.Label(frame_output, text="Output Folder:").pack(side=tk.LEFT)
entry_output_dir = tk.Entry(frame_output, width=50)
entry_output_dir.pack(side=tk.LEFT)
tk.Button(frame_output, text="Browse", command=browse_output_dir).pack(side=tk.LEFT)

# CPU count input
frame_cpu = tk.Frame(root)
frame_cpu.pack(pady=5)
tk.Label(frame_cpu, text="CPU Count for Parallel Processing:").pack(side=tk.LEFT)
entry_cpu_count = tk.Entry(frame_cpu, width=5)
entry_cpu_count.insert(0, "6")  # Default to 6 CPUs
entry_cpu_count.pack(side=tk.LEFT)

# Interval input
frame_interval = tk.Frame(root)
frame_interval.pack(pady=5)
tk.Label(frame_interval, text="File Check Interval (seconds):").pack(side=tk.LEFT)
entry_check_interval = tk.Entry(frame_interval, width=5)
entry_check_interval.insert(0, "3")  # Default interval of 10 seconds
entry_check_interval.pack(side=tk.LEFT)

# Deletion option
frame_delete = tk.Frame(root)
frame_delete.pack(pady=5)
var_delete = tk.BooleanVar()
chk_delete = tk.Checkbutton(frame_delete, text="Delete original files after compression", variable=var_delete)
chk_delete.pack(side=tk.LEFT)

# Text widget for output messages
frame_output_text = tk.Frame(root)
frame_output_text.pack(pady=5)
text_output = tk.Text(frame_output_text, width=60, height=15, wrap=tk.NONE)
text_output.pack(side=tk.LEFT)
scrollbar = tk.Scrollbar(frame_output_text, command=text_output.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
text_output.config(yscrollcommand=scrollbar.set)

# Run button
start_button = tk.Button(root, text="Start Processing", command=run_compression)
start_button.pack(pady=20)

# Exit handler for closing the Tkinter window
def on_closing():
    root.quit()

root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()

