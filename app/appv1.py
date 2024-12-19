import os
import cv2
import mediapipe as mp
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import pyautogui
import time

# Désactivation des logs TensorFlow
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Initialisation de MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils

# Profils de jeu avec les touches mappées
game_profiles = {
    "Jeu 1": {
        "Arm Up Left": 'Left',
        "Arm Up Right": 'Right',
        "Both Arms Up": 'R',
        "Crouching": 'F',
        "Turn Left": 'A',
        "Turn Right": 'G'
    },
    "Jeu 2": {
        "Arm Up Left": 'Q',
        "Arm Up Right": 'E',
        "Both Arms Up": 'Z',
        "Crouching": 'X',
        "Turn Left": 'L',
        "Turn Right": 'P'
    },
    # Ajouter d'autres profils de jeu ici
}

# Fonction pour détecter les mouvements
def detect_movement(landmarks):
    if not landmarks:
        return None
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value]
    right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
    left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value]
    right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value]
    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
    right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
    left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value]
    right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value]

    movement = None
    if left_wrist.y < left_shoulder.y and left_elbow.y < left_shoulder.y:
        movement = "Arm Up Left"
    elif right_wrist.y < right_shoulder.y and right_elbow.y < right_shoulder.y:
        movement = "Arm Up Right"
    elif left_wrist.y > left_shoulder.y and left_elbow.y > left_shoulder.y:
        movement = "Arm Down Left"
    elif right_wrist.y > right_shoulder.y and right_elbow.y > right_shoulder.y:
        movement = "Arm Down Right"
    elif (left_wrist.y < left_shoulder.y and right_wrist.y < right_shoulder.y and 
          left_elbow.y < left_shoulder.y and right_elbow.y < right_shoulder.y):
        movement = "Both Arms Up"
    elif left_knee.y < left_hip.y and right_knee.y < right_hip.y:
        movement = "Crouching"
    elif left_shoulder.x < left_hip.x and right_shoulder.x < right_hip.x:
        movement = "Turn Left"
    elif left_shoulder.x > left_hip.x and right_shoulder.x > right_hip.x:
        movement = "Turn Right"

    return movement

class GetUpPlayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GetUpPlay - Mouvements et Commandes")
        self.root.geometry("800x600")
        
        # Appliquer le thème
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Frame principale
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=15)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Police Poppins définie
        poppins_font = ("Poppins", 14)

        # Menu déroulant pour le profil de jeu
        self.profile_var = tk.StringVar(value="Jeu 1")
        self.profile_menu = ctk.CTkOptionMenu(self.main_frame, variable=self.profile_var, 
                                              values=list(game_profiles.keys()), 
                                              command=self.update_mappings,
                                              font=poppins_font)
        self.profile_menu.pack(pady=10, fill="x", padx=20)

        # Affichage des commandes pour le profil sélectionné
        self.movement_labels = {}
        self.movement_frame = ctk.CTkFrame(self.main_frame)
        self.movement_frame.pack(pady=20, fill="both", expand=True)

        for movement in game_profiles["Jeu 1"]:
            label = ctk.CTkLabel(self.movement_frame, text=f"{movement} : ", font=poppins_font)
            label.grid(row=len(self.movement_labels), column=0, pady=5, padx=10, sticky="w")
            
            key_entry = ctk.CTkEntry(self.movement_frame, font=poppins_font, width=150)
            key_entry.grid(row=len(self.movement_labels), column=1, pady=5, padx=10, sticky="ew")
            
            self.movement_labels[movement] = key_entry

        # Mettre à jour les touches en fonction du profil
        self.update_mappings("Jeu 1")

        # Ajouter le bouton pour créer un profil personnalisé
        self.create_profile_button = ctk.CTkButton(self.main_frame, text="Créer un Profil", font=poppins_font, command=self.create_game_profile)
        self.create_profile_button.pack(pady=20, fill="x", padx=20)

        # Mettre à jour les touches en fonction du profil
        self.update_mappings("Jeu 1")

        # Canvas pour la webcam
        self.canvas_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.canvas_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.canvas = ctk.CTkLabel(self.canvas_frame)
        self.canvas.pack(fill="both", expand=True)

        # Variable pour suivre le dernier moment de détection
        self.last_detection_time = 0
        self.detection_interval = 0.0  # 0.2 seconde de latence

        self.capture_video()

    def create_game_profile(self):
        """ Ouvrir une fenêtre pour créer un nouveau profil de jeu """
        self.create_profile_window = ctk.CTkToplevel(self.root)
        self.create_profile_window.title("Créer un Nouveau Profil")
        self.create_profile_window.geometry("400x600")
        
        # Police Poppins
        poppins_font = ("Poppins", 14)

        # Créer un canvas et une scrollbar
        self.canvas = tk.Canvas(self.create_profile_window)
        self.scrollbar = tk.Scrollbar(self.create_profile_window, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Frame à l'intérieur du canvas
        self.canvas_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.canvas_frame, anchor="nw")

        # Entrée du nom du profil
        self.profile_name_label = ctk.CTkLabel(self.canvas_frame, text="Nom du profil", font=poppins_font)
        self.profile_name_label.pack(pady=10)
        self.profile_name_entry = ctk.CTkEntry(self.canvas_frame, font=poppins_font)
        self.profile_name_entry.pack(pady=10, fill="x", padx=20)

        # Créer des champs pour chaque mouvement et la touche correspondante
        self.movement_entries = {}
        self.key_entries = {}
        
        for movement in game_profiles["Jeu 1"]:
            movement_label = ctk.CTkLabel(self.canvas_frame, text=f"{movement} : ", font=poppins_font)
            movement_label.pack(pady=5)
            
            movement_menu = ctk.CTkOptionMenu(self.canvas_frame, values=[movement], font=poppins_font)
            movement_menu.pack(pady=5, fill="x", padx=20)
            self.movement_entries[movement] = movement_menu

            key_entry_label = ctk.CTkLabel(self.canvas_frame, text="Touche : ", font=poppins_font)
            key_entry_label.pack(pady=5)
            
            key_entry = ctk.CTkEntry(self.canvas_frame, font=poppins_font)
            key_entry.pack(pady=5, fill="x", padx=20)
            self.key_entries[movement] = key_entry
        
        # Bouton pour sauvegarder le profil
        self.save_button = ctk.CTkButton(self.canvas_frame, text="Sauvegarder", font=poppins_font, command=self.save_profile)
        self.save_button.pack(pady=10)

        self.canvas_frame.update_idletasks()  # Mettre à jour la taille du canvas
        self.canvas.config(scrollregion=self.canvas.bbox("all"))  # Définir la région de défilement

    def save_profile(self):
        """ Sauvegarder le profil créé """
        new_profile_name = self.profile_name_entry.get()
        new_profile = {movement: self.key_entries[movement].get() for movement in self.key_entries}
        game_profiles[new_profile_name] = new_profile
        self.create_profile_window.destroy()  # Fermer la fenêtre de création de profil

        # Mettre à jour le menu de sélection de profil
        self.profile_menu.configure(values=list(game_profiles.keys()))
        self.profile_var.set(new_profile_name)

    def update_mappings(self, profile_name):
        """ Mettre à jour les touches de jeu en fonction du profil sélectionné """
        for movement in game_profiles[profile_name]:
            self.movement_labels[movement].delete(0, tk.END)
            self.movement_labels[movement].insert(0, game_profiles[profile_name].get(movement))

    def capture_video(self):
        cap = cv2.VideoCapture(0)

        def update_frame():
            success, frame = cap.read()
            if not success:
                cap.release()
                return

            # Traitement de la détection du mouvement
            results = pose.process(frame)
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                movement = detect_movement(results.pose_landmarks.landmark)

                if movement:
                    current_time = time.time()
                    
                    # Vérifier si le temps écoulé depuis la dernière détection est suffisant
                    if current_time - self.last_detection_time >= self.detection_interval:
                        # Mettre à jour l'heure de la dernière détection
                        self.last_detection_time = current_time
                        
                        # Afficher le mouvement détecté
                        movement_text = f"Movement Detected: {movement}"
                        cv2.putText(frame, movement_text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                        
                        # Simuler la pression de la touche associée
                        key = game_profiles[self.profile_var.get()].get(movement)
                        if key:
                            self.simulate_key_press(key)

            # Afficher l'image de la caméra
            image_pil = Image.fromarray(frame)
            image_tk = ImageTk.PhotoImage(image=image_pil)
            self.canvas.configure(image=image_tk)
            self.canvas.image = image_tk
            self.root.after(10, update_frame)

        update_frame()

    def simulate_key_press(self, key):
        """ Simuler l'appui d'une touche (par exemple, en utilisant pyautogui) """
        pyautogui.press(key)

if __name__ == "__main__":
    root = ctk.CTk()
    app = GetUpPlayApp(root)
    root.mainloop()
