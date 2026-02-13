import cv2
import os

def register_student():
    # 1. Create database folder if it doesn't exist
    if not os.path.exists("database"):
        os.makedirs("database")

    # 2. Get Student Name
    name = input("Enter Student Name: ").replace(" ", "_")
    
    cap = cv2.VideoCapture(0)
    print(f"Look at the camera, {name}. Press 's' to save or 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Display the "Live" viewfinder
        cv2.putText(frame, "Press 's' to Capture", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.imshow("Register Student", frame)

        key = cv2.waitKey(1)
        
        # Press 's' to save the photo
        if key == ord('s'):
            img_path = f"database/{name}.jpg"
            cv2.imwrite(img_path, frame)
            print(f"✅ Success! {name} has been registered.")
            break
        
        # Press 'q' to quit without saving
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    register_student()