import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
import argparse

class LabelingApp:
    def __init__(self, root, folder_path=None, editing_mode=False):
        self.root = root
        self.folder_path = folder_path or os.getcwd()  # Default to current directory
        self.editing_mode = editing_mode  # Mode flag: True = Editing, False = View
        self.image_files = sorted([f for f in os.listdir(self.folder_path)
                                   if f.lower().endswith(('.jpg', '.jpeg'))])
        self.current_index = 0
        self.labels = []  # Store labels as (original_x, original_y, text)
        self.scale_factor = 1  # Scaling factor for resizing
        self.dragging_point = None  # Track the point being dragged
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface with canvas and buttons."""
        
        # Canvas setup
        self.canvas = tk.Canvas(self.root, width=800, height=600)
        self.canvas.grid(row=0, column=0, columnspan=5, sticky="nsew")

        # Configure row and column weights for resizing behavior
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Buttons: Navigation and other controls
        button_frame = tk.Frame(self.root)
        button_frame.grid(row=1, column=0, columnspan=5, pady=10)

        # Next Image button
        self.next_button = tk.Button(button_frame, text="Next (->)", command=self.next_image)
        self.next_button.grid(row=0, column=1, padx=5)

        # Previous Image button
        self.prev_button = tk.Button(button_frame, text="Previous (<-)", command=self.previous_image)
        self.prev_button.grid(row=0, column=0, padx=5)

        # Folder selection button
        # self.select_folder_button = tk.Button(button_frame, text="Select Folder", command=self.select_folder)
        # self.select_folder_button.grid(row=0, column=2, padx=5)

        # Quit button
        self.quit_button = tk.Button(button_frame, text="(Q)uit", command=self.quit_app)
        self.quit_button.grid(row=0, column=3, padx=5)

        # Save Labels button (only in editing mode)
        if self.editing_mode:
            self.save_button = tk.Button(button_frame, text="Save Labels", command=self.save_labels)
            self.save_button.grid(row=0, column=4, padx=5)   
            self.canvas.bind("<ButtonPress-1>", self.add_label)
            # TODO: get a real mouse. Might be a trackpad vs mouse issue
            self.canvas.bind("<ButtonRelease-1>", lambda e: print("Mouse button released"))
            self.canvas.bind("<a>", self.simulate_click)
            self.canvas.bind("<d>", self.debug_info)
            self.canvas.bind("<r>", self.refresh_state)
            # self.canvas.bind("<B1-Motion>", self.drag_label)
            # self.canvas.bind("<ButtonRelease-1>", self.stop_drag_label)
            
        self.canvas.bind("<Motion>", self.on_mouse_move) 
        self.root.bind("<Configure>", self.on_resize)
        # Bind the "Right" arrow key to next image
        self.root.bind("<Right>", lambda event: self.next_image())
        # Bind the "Left" arrow key to previous image
        self.root.bind("<Left>", lambda event: self.previous_image())

        # Bind the "Q" key to quit the application
        self.root.bind("<Q>", lambda event: self.quit_app())
        self.root.bind("<q>", lambda event: self.quit_app())
        
        self.load_image()    

    def refresh_state(self, event=None):
        self.draw_image()

    def debug_info(self, event=None):
        print(f"Focus is currently on: {self.canvas.focus_get()}")
        x = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
        y = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
        print(f"Closest: {self.canvas.find_closest(x, y)}")
        # print(self.canvas.find_all())
        for item_id in self.canvas.find_all():
            item_type = self.canvas.type(item_id)  # Get the type of the canvas item
            item_coords = self.canvas.coords(item_id)  # Get the coordinates of the item
            print(f"Item ID: {item_id}, Type: {item_type}, Coords: {item_coords}")
        
    def simulate_click(self, event=None):
        # Get mouse coordinates relative to the canvas
        x = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
        y = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
 
        print(f"Simulating click at ({x}, {y})")
        # Manually create an event object with these coordinates
        class Event:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        synthetic_event = Event(x, y)
        self.add_label(synthetic_event)


    def load_image(self):
        """Load the current image and its labels."""
        if not self.image_files:
            self.canvas.create_text(400, 300, text="No images found in the folder.", fill="black")
            return
        else:
            print(f"{len(self.image_files)} images found.")
            self.canvas.create_text(400, 300, text="", fill="black")
 
        self.image_path = os.path.join(self.folder_path, self.image_files[self.current_index])

        print(f"Loading{self.image_path}")
        label_path = f"{self.image_path}_labels.txt"
        self.labels = self.load_labels(label_path)
        # Display a message with the number of loaded labels
        print (f"Loaded {len(self.labels)} labels from {label_path}")
        self.draw_image()

    def load_image_from_file(self, file_path, max_width, max_height):
        """Load and scale an image while preserving its aspect ratio."""
        image = Image.open(file_path)
        width, height = image.size

        # Calculate scale factor
        self.scale_factor = min(max_width / width, max_height / height)
        new_width = int(width * self.scale_factor)
        new_height = int(height * self.scale_factor)

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS), new_width, new_height

    def draw_image(self):

        # Scale image based on canvas size
        width = max(self.canvas.winfo_width(), 400)
        height = max(self.canvas.winfo_height(), 320)
        
        self.current_image, self.image_width, self.image_height = self.load_image_from_file(
            self.image_path, width, height)
        self.current_image_obj = ImageTk.PhotoImage(self.current_image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image_obj)

        # Clear previous labels from canvas
        self.canvas.delete("hover")

        self.redraw_labels()

    def redraw_labels(self):
        """Redraw all labels on the canvas."""
        self.canvas.delete("label_point")
        for original_x, original_y, text in self.labels:
            x = original_x * self.scale_factor
            y = original_y * self.scale_factor
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="red", tags="label_point")
            
    def load_labels(self, label_path):
        """Load labels from a .txt file."""
        if not os.path.exists(label_path):
            print ("file not found")
            return []
        labels = []
        with open(label_path, "r") as file:
            print ("file found")
            for line in file:
                x, y, raw_text = line.strip().split(",", 2)
                text = self.unescape_text(raw_text)
                labels.append((int(x), int(y), text))
        return labels

    def save_labels(self):
        """Save labels to a text file."""
        if not self.image_files:
            return
        image_name = self.image_files[self.current_index]
        label_path = os.path.join(self.folder_path, f"{image_name}_labels.txt")
        self.save_labels_to_file(label_path, self.labels)
        print(f"Labels saved to {label_path}\nTotal: {len(self.labels)} labels")

    def save_labels_to_file(self, label_path, labels):
        """Save labels to a text file, escaping special characters."""
        with open(label_path, "w") as file:
            for original_x, original_y, text in labels:
                escaped_text = self.escape_text(text)
                file.write(f"{original_x},{original_y},{escaped_text}\n")

    def escape_text(self, text):
        """Escape special characters in the text."""
        return text.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,")

    def unescape_text(self, text):
        """Unescape special characters in the text."""
        return text.replace("\\,", ",").replace("\\n", "\n").replace("\\\\", "\\")

    def add_label(self, event):
        """Add or edit a label at the clicked point."""
        if self.dragging_point is not None:
        # If a drag is in progress, do not add a new label
            return
        # Check if the clicked point is near an existing label
        clicked_x, clicked_y = event.x, event.y
        print(f"Clicked {clicked_x}, {clicked_y}")
        threshold = 10  # Distance threshold for editing an existing label

        # Find any existing label within the threshold distance
        for i, (label_x, label_y, label_text) in enumerate(self.labels):
            # Calculate the distance from the clicked point to the existing label
            distance = ((clicked_x - label_x * self.scale_factor) ** 2 + 
                        (clicked_y - label_y * self.scale_factor) ** 2) ** 0.5
            if distance <= threshold:
                # The click is close enough to an existing label, so edit it
                label_text = self.open_text_input_dialog(existing_text=label_text)
                if label_text:  # If a new label text was entered
                    # Update the existing label with new text
                    self.labels[i] = (label_x, label_y, label_text)
                    print(f"  Updated label {i + 1} at {label_x}, {label_y} with new text.")
                return  # Exit the function to avoid adding a new label

        # If no existing label was found, create a new one
        label_text = self.open_text_input_dialog()
        print(f"text obtained")
        if label_text:
            # Store the original coordinates before scaling
            original_x = int(event.x / self.scale_factor)
            original_y = int(event.y / self.scale_factor)

            # Store the new label coordinates and text
            self.labels.append((original_x, original_y, label_text))
            print(f"  Created label {len(self.labels)} at {original_x}, {original_y}")

            # Display the point immediately on the canvas
            self.canvas.create_oval(event.x - 3, event.y - 3, event.x + 3, event.y + 3, fill="red", tags="label_point")
        else:
            print(f"  Cancelled label creatioon.")
            
    def next_image(self):
        """Go to the next image."""
        self.save_labels()
        self.current_index = (self.current_index + 1) % len(self.image_files)
        self.load_image()

    def previous_image(self):
        """Go to the previous image."""
        self.save_labels()
        self.current_index = (self.current_index - 1) % len(self.image_files)
        self.load_image()

    def on_resize(self, event):
        """Handle window resize to scale the image."""
        self.draw_image()

    def open_text_input_dialog(self, existing_text=""):
        """Open a dialog to input label text."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Enter Label Text")
        dialog.geometry("300x200")  # Set dialog size
        dialog.transient(self.root)  # Keep the dialog on top of the main window
        # Wait until the dialog is visible
        dialog.update_idletasks()
        dialog.wait_visibility()
        dialog.grab_set()  # Make this dialog modal
        print("dialog grabbed")
        # Add a label for user instructions
        label = tk.Label(dialog, text="Enter label text:")
        label.pack(padx=10, pady=5)

        # Text entry box (multiline, supports newlines)
        text_entry = tk.Text(dialog, height=4, width=40)
        text_entry.insert("1.0", existing_text)  # Pre-fill with existing text if provided
        text_entry.pack(padx=10, pady=5)
        text_entry.focus_set()  # Automatically focus the cursor on the text entry box

        # Define a variable to hold the result
        result = []

        # Function to save input and close dialog
        def save_and_close():
            result.append(text_entry.get("1.0", "end-1c"))  # Get all text except the trailing newline
            dialog.grab_release()  # Release grab before destroying the dialog
            dialog.destroy()
            print(f"dialog destroyed")
            # self.root.focus_set()
         

        # OK button
        ok_button = tk.Button(dialog, text="OK (Alt+Enter)", command=save_and_close)
        ok_button.pack(pady=5)

        # Bind Alt-Return to save and close
        dialog.bind("<Alt-Return>", lambda event: save_and_close())
        dialog.bind("<Command-Return>", lambda event: save_and_close())
        
        # Wait for the dialog to close
        self.root.wait_window(dialog)
        self.canvas.focus_set()
        self.root.after(50, lambda: print(f"Focus after 50ms: {self.root.focus_get()}"))
        print(f"Focus after dialog: {self.root.focus_get()}")
        self.root.update_idletasks()
        self.root.update()
        print(f"root updated")
        # self.draw_image()
        # doesn't seem to help
        
        # Return the result text
        return result[0] if result else None

    def on_mouse_move(self, event):
        """Handle mouse movement to display label text when hovering over a point."""
        hover_found = False

        # no need to display if dragging
        # if self.dragging_point is not None:
        #    return
        self.canvas.delete("hover")

        # Check if the mouse is near any labeled point (scaled to the resized image)
        for original_x, original_y, text in self.labels:
            x = original_x * self.scale_factor
            y = original_y * self.scale_factor
            if (x - 5 <= event.x <= x + 5) and (y - 5 <= event.y <= y + 5):
                hover_found = True

                # Remove any existing hover display
                

                # Add background rectangle with padding
                padding = 5
                # Create text first, so it is on top of the rectangle
                ox = event.x
                oy = event.y
                text_id = self.canvas.create_text(ox + 10, oy + 10, 
                                                  anchor=tk.NW, text=text, 
                                                  fill="black", tags="hover", 
                                                  font=("Arial", 10), width=250)
                # Get the bounding box for the text and use it to draw the rectangle
                bbox = self.canvas.bbox(text_id)
                if bbox:
                    x0, y0, x1, y1 = bbox

                    # Adjust rectangle position to keep it within the canvas
                    canvas_width = self.canvas.winfo_width()
                    canvas_height = self.canvas.winfo_height() - 50

                    x_shift = 0
                    y_shift = 0

                    if x1 > canvas_width:
                        x_shift = canvas_width - x1

                    if y1 > canvas_height:
                        y_shift = canvas_height - y1

                    if x0 < 0:
                        x_shift = -x0

                    if y0 < 0:
                        y_shift = -y0 

                        x0 += x_shift
                        x1 += x_shift
                        ox += x_shift
                        y0 += y_shift
                        y1 += y_shift
                        oy += y_shift
                        
                    # Draw a rectangle around the text
                    self.canvas.create_rectangle(x0 - padding, y0 - padding, 
                                                 x1 + padding, y1 + padding, 
                                                 fill="white", outline="blue", 
                                                 width=1, tags="hover")
                # draw another copy on top
                text_id_top = self.canvas.create_text(ox + 10, oy + 10, 
                                                      anchor=tk.NW, text=text, 
                                                      fill="black", tags="hover", 
                                                      font=("Arial", 10), width=250)
 
        if not hover_found:
            # if we moved out of the zone, we should delete the hover.
            self.canvas.delete("hover")

    # def select_folder(self):
    #     """Select a folder to load images from."""
    #     folder_selected = filedialog.askdirectory(initialdir=self.folder_path)
    #     if folder_selected:
    #         self.folder_path = folder_selected
    #         self.image_files = sorted([f for f in os.listdir(self.folder_path) if f.lower().endswith(('.jpg', '.jpeg'))])
    #         if self.image_files:
    #             self.current_index = 0
    #             self.load_image()
    #         else:
    #             self.canvas.create_text(400, 300, text="No images found in the selected folder.", fill="white")

    # def drag_label(self, event):
    #     """Handle dragging of a label to reposition it."""
    #     if self.dragging_point is None:
    #         # Check if we're near a point to start dragging
    #         for index, (original_x, original_y, text) in enumerate(self.labels):
    #             x = original_x * self.scale_factor
    #             y = original_y * self.scale_factor
    #             if (x - 5 <= event.x <= x + 5) and (y - 5 <= event.y <= y + 5):
    #                 self.dragging_point = index
    #                 break
    #     if self.dragging_point is not None:
    #         # Update the position of the point being dragged
    #         scaled_x = event.x / self.scale_factor
    #         scaled_y = event.y / self.scale_factor
    #         self.labels[self.dragging_point] = (scaled_x, scaled_y, self.labels[self.dragging_point][2])
    #         self.redraw_labels()

    def stop_drag_label(self, event):
        """Stop dragging the label."""
        self.dragging_point = None
    
    def quit_app(self):
        """Exit the application cleanly."""
        self.save_labels()
        print("Exiting application.")
        self.root.destroy()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Image Labeling Tool")
    parser.add_argument("folder_path", nargs="?", default=os.getcwd(), help="Path to the folder containing images")
    parser.add_argument("-E", "--edit", action="store_true", help="Start in editing mode")
    args = parser.parse_args()

    folder_path = args.folder_path
    root = tk.Tk()
    app = LabelingApp(root, folder_path, editing_mode = args.edit)
    root.mainloop()
