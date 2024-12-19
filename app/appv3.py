import os
import cv2
import mediapipe as mp
import tkinter as tk
import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image, ImageTk
import pyautogui
import json

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

        for widget in root.winfo_children():
            widget.destroy()
        self.root = root
        self.root.title("GetUpPlay - Mouvements et Commandes")
        self.root.geometry("800x600")

        self.cap = None
        
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
        self.profile_menu = ctk.CTkOptionMenu(
            self.main_frame,
            variable=self.profile_var,
            values=list(game_profiles.keys()),
            command=self.update_mappings,
            font=poppins_font,
            fg_color="#1E88E5",  # Bleu, comme le bouton
            button_color="#1E88E5",  # Couleur du bouton
            button_hover_color="#1565C0",  # Couleur au survol
            dropdown_fg_color="#1E88E5",  # Couleur du menu déroulant
            dropdown_hover_color="#1565C0",  # Couleur au survol des options
            text_color="white",  # Texte blanc comme les boutons
            dropdown_text_color="white"  # Texte blanc pour les options
        )
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
        """ Ouvrir une fenêtre pour créer un nouveau profil de jeu dans la même fenêtre """
        # Nettoyer tous les widgets existants pour éviter les conflits
        for widget in self.root.winfo_children():
            widget.destroy()
        # Masquer l'écran principal
        self.main_frame.pack_forget()

        # Créer un Frame pour la création du profil
        self.create_profile_frame = ctk.CTkFrame(self.root, corner_radius=15)
        self.create_profile_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Créer une frame défilable
        self.canvas = ctk.CTkCanvas(self.create_profile_frame)
        self.scrollbar = ctk.CTkScrollbar(self.create_profile_frame, command=self.canvas.yview)
        self.scrollable_frame = ctk.CTkFrame(self.canvas)  # Recréer une nouvelle frame
        
        # Police Poppins
        poppins_font = ("Poppins", 14)

        # Entrée du nom du profil
        self.profile_name_label = ctk.CTkLabel(self.create_profile_frame, text="Nom du profil", font=poppins_font)
        self.profile_name_label.pack(pady=10)
        self.profile_name_entry = ctk.CTkEntry(self.create_profile_frame, font=poppins_font)
        self.profile_name_entry.pack(pady=10, fill="x", padx=20)

        # Liste des mouvements disponibles (initialement tous les mouvements)
        self.available_movements = list(game_profiles["Jeu 1"])

        # Créer des dictionnaires pour les champs de mouvement et de touche
        self.movement_entries = {}
        self.key_entries = {}

        # Ajouter un premier mouvement par défaut
        self.add_movement_fields()

        # Frame pour les boutons en bas
        self.buttons_frame = tk.Frame(self.create_profile_frame)
        self.buttons_frame.pack(side="bottom", fill="x", pady=10)

        # Bouton pour ajouter un nouveau mouvement
        self.add_button = ctk.CTkButton(self.buttons_frame, text="Ajouter un mouvement", font=poppins_font, command=self.add_movement_fields)
        self.add_button.pack(pady=5)

        # Bouton pour sauvegarder le profil
        self.save_button = ctk.CTkButton(self.buttons_frame, text="Sauvegarder", font=poppins_font, command=self.save_profile)
        self.save_button.pack(pady=5)

        # Ajouter un bouton pour revenir à l'écran principal
        self.back_button = ctk.CTkButton(self.buttons_frame, text="Retour", font=poppins_font, command=self.show_main_screen)
        self.back_button.pack(pady=5)

        # Mettre à jour la taille du canvas
        self.create_profile_frame.update_idletasks()

    def show_main_screen(self):
        """ Revenir à l'écran principal en réinitialisant tout proprement """
        # Détruire tous les widgets existants
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Réinitialiser le contexte et recharger les profils de jeu
        global game_profiles
        game_profiles = load_game_profiles()
        
        # Forcer un nettoyage complet de Tkinter
        self.root.update_idletasks()  # Met à jour l'état des widgets avant de réinitialiser
        
        # Réinitialiser l'application principale
        self.__init__(self.root)

        print("\n \n \n ICI : \n \n")


    def add_movement_fields(self):
        """Ajouter dynamiquement un champ pour mouvement et touche."""
        # Frame contenant les champs de mouvement et touche dans un Canvas
        if not hasattr(self, 'scroll_canvas_frame'):
            self.scroll_canvas_frame = ctk.CTkFrame(self.create_profile_frame)
            self.scroll_canvas_frame.pack(fill="both", expand=True)

            # Ajout du Canvas
            self.canvas = tk.Canvas(self.scroll_canvas_frame)
            self.scrollable_frame = ctk.CTkFrame(self.canvas)

            # Barre de défilement
            self.scrollbar = tk.Scrollbar(self.scroll_canvas_frame, orient="vertical", command=self.canvas.yview)
            self.canvas.configure(yscrollcommand=self.scrollbar.set)

            self.scrollbar.pack(side="right", fill="y")
            self.canvas.pack(side="left", fill="both", expand=True)

            # Ajouter le Frame à l'intérieur du Canvas
            self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

            # Gérer la mise à jour des dimensions
            self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Créer des champs de mouvement
        index = len(self.movement_entries)
        if not self.available_movements:
            self.add_button.config(state="disabled")

        # Ajout des labels et menus déroulants
        movement_label = ctk.CTkLabel(self.scrollable_frame, text=f"Mouvement {index + 1} : ", font=("Poppins", 14))
        movement_label.grid(row=index, column=0, padx=5, pady=5, sticky="w")

        movement_menu = ctk.CTkOptionMenu(self.scrollable_frame, values=self.available_movements, font=("Poppins", 14))
        movement_menu.grid(row=index, column=1, padx=5, pady=5, sticky="ew")
        self.movement_entries[index] = movement_menu

        movement_menu.bind("<Configure>", self.update_available_movements)

        key_label = ctk.CTkLabel(self.scrollable_frame, text="Touche : ", font=("Poppins", 14))
        key_label.grid(row=index, column=2, padx=5, pady=5, sticky="w")

        key_entry = ctk.CTkEntry(self.scrollable_frame, font=("Poppins", 14))
        key_entry.grid(row=index, column=3, padx=5, pady=5, sticky="ew")
        self.key_entries[index] = key_entry

        self.scrollable_frame.update_idletasks()
        
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)

    def update_available_movements(self, event=None):
        """ Met à jour la liste des mouvements disponibles après un ajout """
        # Récupérer les mouvements déjà utilisés
        used_movements = [menu.get() for menu in self.movement_entries.values()]
        
        # Mettre à jour la liste des mouvements disponibles (exclure les mouvements utilisés)
        self.available_movements = [movement for movement in game_profiles["Jeu 1"] if movement not in used_movements]
        
        # Recréer les menus déroulants avec les nouvelles valeurs disponibles
        for index, movement_menu in self.movement_entries.items():
            movement_menu.configure(values=self.available_movements)

    def update_scroll_region(self):
        """ Met à jour la région de défilement du canvas pour inclure tout le contenu ajouté """
        self.canvas_frame.update_idletasks()  # Assurez-vous que la taille des widgets est mise à jour
        self.canvas.config(scrollregion=self.canvas.bbox("all"))  # Ajuste la région de défilement pour inclure tout

    def on_mouse_wheel(self, event):
        """ Gérer le défilement de la molette de la souris """
        if event.delta < 0:
            self.canvas.yview_scroll(1, "units")  # Faire défiler vers le bas
        else:
            self.canvas.yview_scroll(-1, "units")  # Faire défiler vers le haut

    def save_profile(self):
        """ Sauvegarder le profil de jeu dans le fichier JSON """
        profile_name = self.profile_name_entry.get()
        
        if not profile_name:
            # Si aucun nom de profil n'est entré, afficher un message d'erreur
            print("Veuillez entrer un nom pour le profil.")
            return
        
        # Créer un dictionnaire pour stocker les mouvements et les touches
        game_profile = {}
        
        # Récupérer les mouvements et leurs touches correspondantes
        for i, movement_menu in self.movement_entries.items():
            movement = movement_menu.get()  # Obtenez le mouvement sélectionné
            key_entry = self.key_entries[i].get()  # Obtenez la touche associée
            
            if movement and key_entry:
                game_profile[movement] = key_entry
        
        # Assurez-vous que le profil de jeu est valide
        if game_profile:
            # Charger les profils existants depuis le fichier JSON (ou en créer un nouveau)
            try:
                with open("game_profiles.json", "r") as file:
                    profiles = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                profiles = {}

            # Ajoutez ou mettez à jour le profil dans la structure JSON
            profiles[profile_name] = game_profile
            
            # Sauvegarder à nouveau dans le fichier JSON
            with open("game_profiles.json", "w") as file:
                json.dump(profiles, file, indent=4, ensure_ascii=False)
            
            print(f"Le profil '{profile_name}' a été sauvegardé avec succès.")
            
            # Revenir à l'écran principal après la sauvegarde
            self.show_main_screen()

            # Rafraîchir l'affichage dans la fenêtre principale
            self.update_profile_list()
            self.refresh_window()
        else:
            print("Le profil de jeu est invalide. Assurez-vous que tous les mouvements et touches sont définis.")

    def update_profile_list(self):
        """ Mise à jour de la liste des profils dans la fenêtre principale """
        # Supprimer l'ancienne liste de profils (si elle existe)
        for widget in self.profile_list_frame.winfo_children():
            widget.destroy()

        # Charger les profils depuis le fichier JSON
        try:
            with open("game_profiles.json", "r") as file:
                profiles = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            profiles = {}

        # Créer des labels ou des menus pour afficher les nouveaux profils
        for profile_name in profiles:
            profile_label = ctk.CTkLabel(self.profile_list_frame, text=profile_name, font=("Poppins", 14))
            profile_label.pack(pady=5)

        # Redessiner la fenêtre pour afficher la mise à jour
        self.profile_list_frame.update_idletasks()
        
    def update_mappings(self, profile_name):
        """ Mettre à jour les touches affichées en fonction du profil sélectionné """
        # Effacer les anciens widgets de mouvements
        for widget in self.movement_frame.winfo_children():
            widget.destroy()

        # Réinitialiser le dictionnaire des labels
        self.movement_labels = {}

        # Ajouter les mouvements du profil sélectionné
        mappings = game_profiles.get(profile_name, {})
        for movement, key in mappings.items():
            # Ajouter une ligne pour chaque mouvement
            label = ctk.CTkLabel(self.movement_frame, text=f"{movement} : ", font=("Poppins", 14))
            label.grid(row=len(self.movement_labels), column=0, pady=5, padx=10, sticky="w")

            key_entry = ctk.CTkEntry(self.movement_frame, font=("Poppins", 14), width=150)
            key_entry.insert(tk.END, key)  # Pré-remplir avec la touche associée
            key_entry.grid(row=len(self.movement_labels), column=1, pady=5, padx=10, sticky="ew")

            # Sauvegarder le champ dans le dictionnaire
            self.movement_labels[movement] = key_entry

    def capture_video(self):
        """ Lancer ou relancer la capture vidéo """
        if self.cap is not None:
            self.cap.release()  # Libérer la ressource vidéo si elle existe déjà
        self.cap = cv2.VideoCapture(0)

        def update_frame():
            success, frame = self.cap.read()
            if not success:
                self.cap.release()  # Relâcher la caméra si la lecture échoue
                return

            results = pose.process(frame)
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)  # Afficher le squelette
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
            self.root.after(10, update_frame)  # Mettre à jour la vidéo après 10ms

        update_frame()

    def update_video(self):
        """ Fonction pour relancer la vidéo après une mise à jour """
        self.capture_video()  # Relancer la capture vidéo
        self.update_mappings(self.profile_var.get())  # Mettre à jour les commandes associées au profil

    def simulate_key_press(self, key):
        pyautogui.press(key)

    def refresh_window(self):
        """ Rafraîchir la fenêtre principale """
        self.update_video()  # Mettre à jour la vidéo

    def simulate_key_press(self, key):
        pyautogui.press(key)

# Création de la fenêtre Tkinter
root = ctk.CTk()
app = GetUpPlayApp(root)
root.mainloop()
