import cv2
import pandas as pd
from datetime import datetime
import os
from deepface import DeepFace

# --- Configuration ---
DB_PATH = "database"
CSV_FILE = "attendance.csv"

def mark_attendance(name):
    """Saves name and time to CSV, preventing duplicates for the same day."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    # Create file with headers if it doesn't exist
    if not os.path.isfile(CSV_FILE):
        df = pd.DataFrame(columns=["Name", "Date", "Time"])
        df.to_csv(CSV_FILE, index=False)
        print(f"📁 Created new file: {CSV_FILE}")

    df = pd.read_csv(CSV_FILE)
    
    # Check if student is already marked today
    # Ensure the 'Name' column is compared as a string
    already_marked = df[(df['Name'].astype(str) == str(name)) & (df['Date'] == date_str)]
    
    if already_marked.empty:
        new_entry = pd.DataFrame([[name, date_str, time_str]], columns=["Name", "Date", "Time"])
        new_entry.to_csv(CSV_FILE, mode='a', header=False, index=False)
        print(f"✅ Attendance marked for {name} at {time_str}")
    else:
        # This helps you know why the CSV isn't changing during testing
        print(f"ℹ️ {name} is already marked for today.")

# --- Start Webcam ---
cap = cv2.VideoCapture(0)

print("--- System Started ---")
print("Looking for faces in the 'database' folder...")
print("Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    try:
        # DeepFace.find compares the webcam frame to the database folder
        # enforce_detection=False prevents the code from crashing if no face is found
        results = DeepFace.find(img_path=frame, 
                                db_path=DB_PATH, 
                                model_name="VGG-Face", 
                                enforce_detection=False,
                                silent=True) # silent=True hides the progress bars in terminal

        if len(results) > 0 and not results[0].empty:
            # 1. Get the path from the result
            full_path = results[0]['identity'][0]
            
            # 2. Extract just the name (removes folder path and .jpg extension)
            student_name = os.path.splitext(os.path.basename(full_path))[0]
            
            # 3. Get coordinates for the bounding box
            x = int(results[0]['source_x'][0])
            y = int(results[0]['source_y'][0])
            w = int(results[0]['source_w'][0])
            h = int(results[0]['source_h'][0])
            
            # 4. Draw UI on the webcam feed
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"Match: {student_name}", (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 5. Log to CSV
            mark_attendance(student_name)
        else:
            # Helpful for debugging: let's you know the camera is working but no match found
            cv2.putText(frame, "Scanning for registered faces...", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    except Exception as e:
        # If there's a serious error, it will show here
        print(f"Error: {e}")

    cv2.imshow("Attendance System", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()