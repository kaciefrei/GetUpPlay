import os
import cv2
import mediapipe as mp
import tkinter as tk
import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image, ImageTk
import pyautogui
import json
import threading

# Désactivation des logs TensorFlow
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Chemin du fichier JSON pour stocker les profils de jeu
PROFILE_FILE = "game_profiles.json"

# Fonction pour charger les profils de jeu depuis un fichier JSON
def load_game_profiles():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r") as file:
            return json.load(file)
    return {}  # Retourne un dictionnaire vide si le fichier n'existe pas

# Fonction pour sauvegarder les profils de jeu dans un fichier JSON
def save_game_profiles(profiles):
    with open(PROFILE_FILE, "w") as file:
        json.dump(profiles, file, indent=4)

# Chargement des profils de jeu au démarrage
game_profiles = load_game_profiles()

# Initialisation de MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils

# Fonction pour détecter les mouvements
def detect_movement(landmarks):
    if not landmarks:
        return None
    epaule_gauche = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    epaule_droite = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    coude_gauche = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value]
    coude_droite = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
    poignet_gauche = landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value]
    poignet_droite = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value]
    hanche_gauche = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
    hanche_droite = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
    genou_gauche = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value]
    genou_droit = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value]

    movement = None
    if poignet_gauche.y < epaule_gauche.y and coude_gauche.y < epaule_gauche.y:
        movement = "Bras gauche levé"
    elif poignet_droite.y < epaule_droite.y and coude_droite.y < epaule_droite.y:
        movement = "Bras droit levé"
    elif poignet_gauche.y > epaule_gauche.y and coude_gauche.y > epaule_gauche.y:
        movement = "Bras gauche baissé"
    elif poignet_droite.y > epaule_droite.y and coude_droite.y > epaule_droite.y:
        movement = "Bras droit baissé"
    elif (poignet_gauche.y < epaule_gauche.y and poignet_droite.y < epaule_droite.y and 
          coude_gauche.y < epaule_gauche.y and coude_droite.y < epaule_droite.y):
        movement = "Les deux bras levés"
    elif genou_gauche.y < hanche_gauche.y and genou_droit.y < hanche_droite.y:
        movement = "Accroupi"
    elif epaule_gauche.x < hanche_gauche.x and epaule_droite.x < hanche_droite.x:
        movement = "Tourner à gauche"
    elif epaule_gauche.x > hanche_gauche.x and epaule_droite.x > hanche_droite.x:
        movement = "Tourner à droite"

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

        for movement in game_profiles.get("Jeu 1", {}):
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

        # Canvas pour la webcam
        self.canvas_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.canvas_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.canvas = ctk.CTkLabel(self.canvas_frame)
        self.canvas.pack(fill="both", expand=True)

        self.capture_video()

    def create_game_profile(self):
        """ Ouvrir une fenêtre pour créer un nouveau profil de jeu """
        self.create_profile_window = ctk.CTkToplevel(self.root)
        self.create_profile_window.title("Créer un Nouveau Profil")
        self.create_profile_window.geometry("400x600")
       
        # Appliquer lift() pour s'assurer que la fenêtre reste au premier plan
        self.create_profile_window.lift()
        self.create_profile_window.focus_force()  # S'assurer que la fenêtre obtient le focus au premier plan

        
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
        
        # Lier l'événement de la molette de la souris
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)

    def on_mouse_wheel(self, event):
        """ Gérer le défilement de la molette de la souris """
        if event.delta < 0:
            self.canvas.yview_scroll(1, "units")  # Faire défiler vers le bas
        else:
            self.canvas.yview_scroll(-1, "units")  # Faire défiler vers le haut

    def save_profile(self):
        profile_name = self.profile_name_entry.get().strip()
        if not profile_name:
            return

        if profile_name in game_profiles:
            return  # Le profil existe déjà
        
        new_profile = {}
        for movement, key_entry in self.key_entries.items():
            key = key_entry.get()
            new_profile[movement] = key
        
        game_profiles[profile_name] = new_profile
        save_game_profiles(game_profiles)  # Sauvegarde le profil dans le fichier JSON
        self.profile_var.set(profile_name)  # Sélectionner le nouveau profil créé
        self.create_profile_window.destroy()  # Fermer la fenêtre de création

        # Mettre à jour les menus
        self.profile_menu.configure(values=list(game_profiles.keys()))
        self.update_mappings(profile_name)

    def update_mappings(self, profile_name):
        """ Mettre à jour les touches affichées en fonction du profil sélectionné """
        mappings = game_profiles[profile_name]
        for movement, key in mappings.items():
            self.movement_labels[movement].delete(0, tk.END)
            self.movement_labels[movement].insert(tk.END, key)

    def capture_video(self):
        cap = cv2.VideoCapture(0)
        def update_frame():
            success, frame = cap.read()
            if not success:
                cap.release()
                return

            results = pose.process(frame)
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS) #afficher squelette rouge
                movement = detect_movement(results.pose_landmarks.landmark)
                if movement:
                    movement_text = f"Mouvement Détecté: {movement}"
                    cv2.putText(frame, movement_text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                    key = game_profiles[self.profile_var.get()].get(movement)
                    if key:
                        self.simulate_key_press(key)

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Conversion BGR -> RGB
            image_pil = Image.fromarray(frame)
            image_tk = ImageTk.PhotoImage(image=image_pil)
            self.canvas.configure(image=image_tk)
            self.canvas.image = image_tk
            self.root.after(10, update_frame)

        update_frame()

    def simulate_key_press(self, key):
        pyautogui.press(key)

# Création de la fenêtre Tkinter
root = ctk.CTk()
app = GetUpPlayApp(root)
root.mainloop()
