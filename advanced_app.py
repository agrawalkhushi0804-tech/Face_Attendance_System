import os
import cv2
import pandas as pd
from datetime import datetime
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import messagebox

# --- AI Engine Loading ---
try:
    from deepface import DeepFace
    DEEPFACE_READY = True
except Exception as e:
    print(f"DeepFace Load Error: {e}")
    DEEPFACE_READY = False

# --- Configuration ---
DB_PATH = "database"
CSV_FILE = "attendance.csv"
if not os.path.exists(DB_PATH): os.makedirs(DB_PATH)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AttendanceSystemPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Attendance Professional v5.0")
        self.geometry("1280x720")

        # System State
        self.cap = cv2.VideoCapture(0)
        self.scanning = False
        
        self.setup_ui()
        self.update_loop()

    def setup_ui(self):
        # 1. Left Sidebar: Registration & Controls
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)

        ctk.CTkLabel(self.sidebar, text="STUDENT MANAGEMENT", font=("Arial", 18, "bold")).pack(pady=20)
        
        self.name_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Student Full Name", height=35)
        self.name_entry.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkButton(self.sidebar, text="Register Face", command=self.register_student, fg_color="#3498db").pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(self.sidebar, text="OPERATIONS", font=("Arial", 18, "bold")).pack(pady=30)
        
        self.scan_btn = ctk.CTkButton(self.sidebar, text="▶ Start Attendance", fg_color="#2ecc71", hover_color="#27ae60", height=45, command=self.toggle_scan)
        self.scan_btn.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkButton(self.sidebar, text="Reset Camera", fg_color="#95a5a6", command=self.reset_camera).pack(pady=5, padx=20, fill="x")
        
        self.info_label = ctk.CTkLabel(self.sidebar, text="Status: Ready", text_color="gray")
        self.info_label.pack(side="bottom", pady=20)

        # 2. Middle Panel: Video Feed
        self.video_container = ctk.CTkFrame(self, corner_radius=15)
        self.video_container.pack(side="left", expand=True, fill="both", padx=10, pady=10)
        
        self.video_label = ctk.CTkLabel(self.video_container, text="Initializing Camera...", font=("Arial", 20))
        self.video_label.pack(expand=True, fill="both")

        # 3. Right Panel: Live Attendance Table
        self.right_panel = ctk.CTkFrame(self, width=350)
        self.right_panel.pack(side="right", fill="y", padx=10, pady=10)
        
        ctk.CTkLabel(self.right_panel, text="LIVE ATTENDANCE LOG", font=("Arial", 16, "bold")).pack(pady=15)
        
        # The "Table" Display
        self.log_display = ctk.CTkTextbox(self.right_panel, width=320, font=("Courier New", 13), corner_radius=10)
        self.log_display.pack(expand=True, fill="both", padx=10, pady=5)
        self.reset_table_headers()
        
        ctk.CTkButton(self.right_panel, text="Clear Log View", command=self.reset_table_headers, height=30).pack(pady=10)

    def reset_table_headers(self):
        self.log_display.configure(state="normal")
        self.log_display.delete("0.0", "end")
        header = f"{'STUDENT NAME':<18} | {'TIME':<8}\n"
        divider = "-" * 30 + "\n"
        self.log_display.insert("end", header + divider)
        self.log_display.configure(state="disabled")

    def reset_camera(self):
        self.cap.release()
        self.cap = cv2.VideoCapture(0)
        self.info_label.configure(text="Status: Camera Reset", text_color="white")

    def register_student(self):
        name = self.name_entry.get().strip().replace(" ", "_")
        if not name:
            messagebox.showwarning("Error", "Please enter a name first!")
            return
        
        ret, frame = self.cap.read()
        if ret:
            file_path = os.path.join(DB_PATH, f"{name}.jpg")
            cv2.imwrite(file_path, frame)
            
            # Force DeepFace to re-index the database
            pkl_path = os.path.join(DB_PATH, "representations_vgg_face.pkl")
            if os.path.exists(pkl_path): os.remove(pkl_path)
            
            self.name_entry.delete(0, 'end')
            messagebox.showinfo("Success", f"Face registered for {name}")
            self.info_label.configure(text=f"Last Reg: {name}", text_color="#3498db")

    def toggle_scan(self):
        if not DEEPFACE_READY:
            messagebox.showerror("Error", "DeepFace AI is not properly installed.")
            return
        
        self.scanning = not self.scanning
        if self.scanning:
            self.scan_btn.configure(text="■ Stop Scanning", fg_color="#e74c3c", hover_color="#c0392b")
            self.info_label.configure(text="Status: Scanning...", text_color="#2ecc71")
        else:
            self.scan_btn.configure(text="▶ Start Attendance", fg_color="#2ecc71", hover_color="#27ae60")
            self.info_label.configure(text="Status: Paused", text_color="gray")

    def mark_attendance(self, name):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        # Ensure CSV exists
        if not os.path.exists(CSV_FILE):
            pd.DataFrame(columns=["Name", "Date", "Time"]).to_csv(CSV_FILE, index=False)
        
        df = pd.read_csv(CSV_FILE)
        
        # CHECK: Is this person already marked TODAY?
        already_marked = not df[(df['Name'] == name) & (df['Date'] == date_str)].empty
        
        if not already_marked:
            # Save to CSV
            new_entry = pd.DataFrame([[name, date_str, time_str]], columns=["Name", "Date", "Time"])
            new_entry.to_csv(CSV_FILE, mode='a', header=False, index=False)
            
            # Update GUI Table (Add to the top of the list)
            self.log_display.configure(state="normal")
            # We insert at line 3.0 (just below the header)
            self.log_display.insert("3.0", f"{name[:18]:<18} | {time_str:<8}\n")
            self.log_display.configure(state="disabled")
            print(f"Logged: {name}")
        else:
            # This logic prevents the table from flickering or re-logging
            pass

    def update_loop(self):
        ret, frame = self.cap.read()
        if ret:
            display_frame = frame.copy()
            
            if self.scanning:
                try:
                    # Model Search
                    results = DeepFace.find(img_path=frame, 
                                            db_path=DB_PATH, 
                                            model_name="VGG-Face", 
                                            enforce_detection=False, 
                                            silent=True)
                    
                    if len(results) > 0 and not results[0].empty:
                        # Extract Name
                        identity = results[0]['identity'][0]
                        name = os.path.splitext(os.path.basename(identity))[0]
                        
                        # UI Bounding Box
                        x, y, w, h = int(results[0]['source_x'][0]), int(results[0]['source_y'][0]), \
                                     int(results[0]['source_w'][0]), int(results[0]['source_h'][0])
                        
                        cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        cv2.putText(display_frame, f"Match: {name}", (x, y-10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
                        # Attempt to log
                        self.mark_attendance(name)
                except Exception as e:
                    print(f"Scanning pause: {e}")

            # Update Video Frame
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            imgtk = ImageTk.PhotoImage(image=img.resize((700, 500)))
            self.video_label.configure(image=imgtk, text="")
            self.video_label.imgtk = imgtk
        else:
            self.video_label.configure(text="CAMERA ERROR: RECONNECT & RESET")

        self.after(10, self.update_loop)

if __name__ == "__main__":
    app = AttendanceSystemPro()
    app.mainloop()