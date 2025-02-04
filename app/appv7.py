import os
import cv2
import mediapipe as mp
import tkinter as tk
import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image, ImageTk
import pyautogui
import json
from tkinter import filedialog
import shutil
from tkinter import messagebox
import time


# Désactivation des logs TensorFlow
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Chemin du fichier JSON pour stocker les profils de jeu
PROFILE_FILE = "game_profiles.json"

frame_counter = 0  # Compteur pour analyser les frames toutes les 5 frames
last_key_press_time = 0  # Timestamp pour limiter les répétitions des appuis clavier

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

# Variable globale pour garder la trace du dernier mouvement et du temps
last_movement_time = 0
latency = 1  # Délai de 1 seconde pour éviter la répétition immédiate

def detect_movement(landmarks):
    global last_movement_time  # Utiliser la variable globale pour le dernier mouvement

    if not landmarks:
        return None

    # Points clés
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
    tete = landmarks[mp_pose.PoseLandmark.NOSE.value]  # Utilisation du nez comme référence de la tête

    movement = None

    # Bras gauche levé
    if poignet_gauche.y < epaule_gauche.y and coude_gauche.y < epaule_gauche.y:
        movement = "Bras gauche leve"
    # Bras droit levé
    elif poignet_droite.y < epaule_droite.y and coude_droite.y < epaule_droite.y:
        movement = "Bras droit leve"
    # Les deux bras levés
    elif (poignet_gauche.y < epaule_gauche.y and poignet_droite.y < epaule_droite.y and 
          coude_gauche.y < epaule_gauche.y and coude_droite.y < epaule_droite.y):
        movement = "Les deux bras leves"
    # Accroupi
    elif genou_gauche.y < hanche_gauche.y and genou_droit.y < hanche_droite.y:
        movement = "Accroupi"
    # Tourner à gauche
    elif epaule_gauche.x < hanche_gauche.x and epaule_droite.x < hanche_droite.x:
        movement = "Tourner a gauche"
    # Tourner à droite
    elif epaule_gauche.x > hanche_gauche.x and epaule_droite.x > hanche_droite.x:
        movement = "Tourner a droite"
    
    # Bras droit à l'horizontale
    elif abs(poignet_droite.y - coude_droite.y) < 0.1 and abs(coude_droite.y - epaule_droite.y) < 0.1:
        movement = "Bras droit horizontal"
    # Bras gauche à l'horizontale
    elif abs(poignet_gauche.y - coude_gauche.y) < 0.1 and abs(coude_gauche.y - epaule_gauche.y) < 0.1:
        movement = "Bras gauche horizontal"
    # Tête baissée
    elif tete.y > epaule_gauche.y and tete.y > epaule_droite.y:
        movement = "Tete baissee"
    
    # Tolérance pour éviter les petites variations non voulues
    tolerance = 0.1  # Ajuste cette valeur selon les besoins

    # Temps actuel
    current_time = time.time()

    # Se pencher à droite (épaule droite plus haute)
    if epaule_droite.y > epaule_gauche.y + tolerance:
        # Si le dernier mouvement était dans le délai de latence, ignorer
        if current_time - last_movement_time >= latency:
            movement = "Se pencher a droite"
            last_movement_time = current_time  # Mettre à jour le temps du dernier mouvement

    # Se pencher à gauche (épaule gauche plus haute)
    elif epaule_gauche.y > epaule_droite.y + tolerance:
        # Si le dernier mouvement était dans le délai de latence, ignorer
        if current_time - last_movement_time >= latency:
            movement = "Se pencher a gauche"
            last_movement_time = current_time  # Mettre à jour le temps du dernier mouvement

    # Saut (flèche haut)
    elif tete.y > epaule_gauche.y and tete.y > epaule_droite.y:
        movement = "Saut"

    return movement


class GetUpPlayApp:
    def __init__(self, root): 

        # Si ce n'est pas un rechargement, exécute cette partie
        

        self.root = root
        self.root.title("GetUpPlay - Mouvements et Commandes")
        self.root.geometry("1440x900")
        self.camera_index = 0  # Caméra par défaut

        # Configure rows and columns for the main app
        for i in range(1024):
            self.root.grid_rowconfigure(i, weight=1)

        for j in range(1440):
            self.root.grid_columnconfigure(j, weight=1)

        self.create_widget()
    
    def create_widget(self):
        self.cap = None

        # Appliquer le thème
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        poppins_font = ("Poppins", 14)

        GUP_add = ImageTk.PhotoImage(Image.open("../public/Mask group (6).png").resize((30, 30), Image.Resampling.LANCZOS))
        GUP_delete = ImageTk.PhotoImage(Image.open("../public/delete 1.png").resize((30, 30), Image.Resampling.LANCZOS))
        GUP_download = ImageTk.PhotoImage(Image.open("../public/downloads 1.png").resize((30, 30), Image.Resampling.LANCZOS))
        GUP_import = ImageTk.PhotoImage(Image.open("../public/import 1.png").resize((30, 30), Image.Resampling.LANCZOS))
        GUP_refresh = ImageTk.PhotoImage(Image.open("../public/refresh 1.png").resize((30, 30), Image.Resampling.LANCZOS))
        GUP_logo = ImageTk.PhotoImage(Image.open("../public/Group 16.png").resize((50, 50), Image.Resampling.LANCZOS))

        # Initialisation de la variable de profil
        self.profile_var = tk.StringVar(value="Jeu 1")



        # Left frame
        self.left_frame = ctk.CTkFrame(self.root, width=0, height=0, fg_color=("#054DC2"), corner_radius=0)
        self.left_frame.grid(row=0, rowspan=1024, column=0, columnspan=145, sticky="nsew")


        # Right frame
        self.right_frame = ctk.CTkFrame(self.root, width=0, height=0, fg_color=("#0579C2"), corner_radius=0)
        self.right_frame.grid(row=0, rowspan=1024, column=145, columnspan=1295, sticky="nsew")

        # LEFT FRAME


        # Configure rows and columns for the left_frame
        for i in range(1024):  # Adjust as needed for the layout inside the right_frame
            self.left_frame.grid_rowconfigure(i, weight=1)

        for j in range(145):  # Adjust as needed for the layout inside the right_frame
            self.left_frame.grid_columnconfigure(j, weight=1)


        # RIGHT FRAME


        # Configure rows and columns for the right_frame
        for i in range(1024):  # Adjust as needed for the layout inside the right_frame
            self.right_frame.grid_rowconfigure(i, weight=1)

        for j in range(1295):  # Adjust as needed for the layout inside the right_frame
            self.right_frame.grid_columnconfigure(j, weight=1)



        # Frames inside the right_frame
        self.description_frame = ctk.CTkFrame(self.right_frame, width=0, height=0, fg_color=("#CDEAF3"), corner_radius=17)
        self.description_frame.grid(row=48, rowspan=145, column=30, columnspan=757, sticky="nsew")

        self.button_frame = ctk.CTkFrame(self.right_frame, width=0, height=0, fg_color=("#CDEAF3"), corner_radius=17)
        self.button_frame.grid(row=223, rowspan=549, column=30, columnspan=424, sticky="nsew")

        self.cam_frame = ctk.CTkFrame(self.right_frame, width=0, height=0, fg_color=("#000000"), corner_radius=30)
        self.cam_frame.grid(row=223, rowspan=549, column=474, columnspan='757', sticky="nsew")

        self.control_frame = ctk.CTkFrame(self.right_frame, width=0, height=0, fg_color=("#0579C2"), corner_radius=17)
        self.control_frame.grid(row=48, rowspan=76, column=1004, columnspan=227, sticky="nsew")

        image_label = ctk.CTkLabel(self.left_frame, image=GUP_logo, text="")
        image_label.pack(pady=48)



        for i in range(549):  # Adjust as needed for the layout inside the right_frame
            self.button_frame.grid_rowconfigure(i, weight=1)

        for j in range(424):  # Adjust as needed for the layout inside the right_frame
            self.button_frame.grid_columnconfigure(j, weight=1)

        # Ajouter le menu déroulant dans le left_frame
        for profile in game_profiles.keys():
            button = ctk.CTkButton(
                master=self.left_frame,
                text=profile,  # Set the button text to the profile name
                text_color="#0579C2",
                font=("Poppins", 14, "bold", "italic"),
                fg_color="#CDEAF3",  # Button color
                hover_color="#1565C0",  # Hover effect color
                command=lambda p=profile: self.update_mappings(p)  # Pass the profile to the function
            )
            button.pack(pady=5)  # Add some spacing between buttons

        # Ajouter les commandes de mouvement dans le left_frame
        self.movement_labels = {}

        for movement in game_profiles.get("Jeu 1", {}):
            label = ctk.CTkLabel(self.button_frame, text=f"{movement} : ", font=poppins_font)
            label.grid(row=len(self.movement_labels), column=0, pady=5, padx=10, sticky="w")

            key_entry = ctk.CTkEntry(self.button_frame, font=poppins_font, width=150)
            key_entry.grid(row=len(self.movement_labels), column=1, pady=5, padx=10, sticky="ew")

            self.movement_labels[movement] = key_entry
        
        # Mettre à jour les touches en fonction du profil
        self.update_mappings("Jeu 1")


        

        # Ajouter le retour vidéo dans le right_frame
        self.canvas = ctk.CTkLabel(self.cam_frame)
        self.canvas.grid(sticky="nsew")

        self.capture_video()

        # Ajouter les boutons dans le frame aligné horizontalement
        self.create_profile_button = ctk.CTkButton(self.left_frame, image=GUP_add, text="", width=60, height=60, fg_color="#CDEAF3", command=self.create_game_profile)
        self.create_profile_button.pack(pady=10)

        self.delete_profile_button = ctk.CTkButton(self.description_frame, image=GUP_delete, text="", width=60, height=60, fg_color="transparent", command=self.delete_profile)
        self.delete_profile_button.pack()

        self.download_profile_button = ctk.CTkButton(self.control_frame, image=GUP_download, text="", width=60, height=60, fg_color="transparent", hover=False, command=self.download_profile)
        self.download_profile_button.grid(row=0, column=0, sticky="e")

        self.import_profile_button = ctk.CTkButton(self.control_frame, image=GUP_import, text="", width=60, height=60, fg_color="transparent", hover=False, command=self.import_profile)
        self.import_profile_button.grid(row=0, column=1)

        self.refresh_button = ctk.CTkButton(self.control_frame, image=GUP_refresh, text="", width=60, height=60, fg_color="transparent", hover=False, command=self.reload)
        self.refresh_button.grid(row=0, column=2, sticky="w")


    def reload(self):
        print("Rechargement des widgets...")

        # Supprimer tous les widgets dans la fenêtre principale (root)
        for widget in self.root.winfo_children():
            widget.destroy()

        # Vider le cache et forcer un rafraîchissement de l'interface
        self.root.update_idletasks()  # Mettre à jour les tâches en attente
        self.root.update()  # Forcer un rafraîchissement de l'interface

        # Recréer les widgets après la suppression
        self.create_widget()

        # Optionnel : forcer un refresh complet
        self.root.after(100, lambda: self.root.update())

    def delete_profile(self):
        """Supprime le profil actuellement sélectionné."""
        current_profile_name = self.profile_var.get()

        if not current_profile_name:
            print("Aucun profil sélectionné.")
            return

        # Confirmation de l'utilisateur
        confirm = tk.messagebox.askyesno(
            "Confirmation",
            f"Êtes-vous sûr de vouloir supprimer le profil {current_profile_name} ?"
        )
        
        if confirm:
            try:
                # Supprimer le profil de game_profiles
                if current_profile_name in game_profiles:
                    del game_profiles[current_profile_name]
                
                # Sauvegarder les modifications dans le fichier JSON
                save_game_profiles(game_profiles)
                
                print(f"Le profil '{current_profile_name}' a été supprimé.")
                
                # Actualiser la liste des profils
                self.update_profile_list()
                
                # Mettre à jour le menu déroulant
                self.profile_menu.configure(values=list(game_profiles.keys()))
                self.profile_var.set(list(game_profiles.keys())[0] if game_profiles else "")
            except Exception as e:
                print(f"Erreur lors de la suppression du profil : {e}")
            self.reload()

    def download_profile(self):
        """Télécharge le profil en cours d'utilisation sous forme de fichier .gup."""
        current_profile_name = self.profile_var.get()
        
        # Vérifie si le profil existe dans game_profiles
        if current_profile_name not in game_profiles:
            print(f"Le profil {current_profile_name} n'existe pas.")
            return

        # Récupérer les données du profil
        profile_data = game_profiles[current_profile_name]
        
        # Crée un chemin pour le fichier de téléchargement
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")  # Répertoire de téléchargement de l'utilisateur
        file_path = os.path.join(download_dir, f"{current_profile_name}.gup")
        
        # Enregistrer le profil dans un fichier .gup
        with open(file_path, 'w') as file:
            json.dump({current_profile_name: profile_data}, file, indent=4)
        
        print(f"Le profil {current_profile_name} a été téléchargé sous {file_path}")

    def import_profile(self):
        """Importer un profil à partir d'un fichier .gup et l'ajouter au fichier game_profiles.json."""
        file_path = filedialog.askopenfilename(title="Importer un profil", filetypes=[("GetUpPlay Profile", "*.gup")])
        
        if file_path:
            try:
                # Charger le profil depuis le fichier .gup
                with open(file_path, "r") as file:
                    imported_profile = json.load(file)
                
                # Charger les profils existants depuis game_profiles.json
                try:
                    with open(PROFILE_FILE, "r") as file:
                        profiles = json.load(file)
                except (FileNotFoundError, json.JSONDecodeError):
                    profiles = {}

                # Ajouter le profil importé dans les profils existants
                profiles.update(imported_profile)

                # Sauvegarder les profils mis à jour dans le fichier game_profiles.json
                with open(PROFILE_FILE, "w") as file:
                    json.dump(profiles, file, indent=4, ensure_ascii=False)
                
                print(f"Le profil '{list(imported_profile.keys())[0]}' a été importé avec succès.")

                # Recharger les profils et actualiser l'affichage
                global game_profiles
                game_profiles = load_game_profiles()  # Recharger les profils depuis le fichier JSON
                self.update_profile_list()  # Mettre à jour la liste des profils dans l'interface
                self.update_mappings(self.profile_var.get())  # Mettre à jour les commandes du profil actif
                
            except json.JSONDecodeError:
                print("Le fichier importé n'est pas valide.")
            except Exception as e:
                print(f"Une erreur est survenue lors de l'importation : {e}")
            self.reload()

    def create_game_profile(self):
        """ Ouvrir une fenêtre pour créer un nouveau profil de jeu dans la même fenêtre """
        # Nettoyer tous les widgets existants pour éviter les conflits
        for widget in self.root.winfo_children():
            widget.destroy()
        # Masquer l'écran principal
        self.right_frame.pack_forget()

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
        """Sauvegarder le profil de jeu dans le fichier JSON"""
        profile_name = self.profile_name_entry.get()
        
        if not profile_name:
            print("Veuillez entrer un nom pour le profil.")
            return
        
        game_profile = {}

        # Récupérer les mouvements et leurs touches
        for i, movement_menu in self.movement_entries.items():
            movement = movement_menu.get()
            key_entry = self.key_entries[i].get()
            
            if movement and key_entry:
                game_profile[movement] = key_entry
        
        if game_profile:
            try:
                with open("game_profiles.json", "r") as file:
                    profiles = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                profiles = {}

            profiles[profile_name] = game_profile
            
            with open("game_profiles.json", "w") as file:
                json.dump(profiles, file, indent=4, ensure_ascii=False)
            
            print(f"Le profil '{profile_name}' a été sauvegardé avec succès.")
            self.show_main_screen()
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
        for widget in self.button_frame.winfo_children():
            widget.destroy()

        # Réinitialiser le dictionnaire des labels
        self.movement_labels = {}

        # Ajouter les mouvements du profil sélectionné
        mappings = game_profiles.get(profile_name, {})
        for movement, key in mappings.items():

            input_frame= ctk.CTkFrame(self.button_frame, fg_color="#0579C2")
            input_frame.grid(pady=(10,0), column=23, columnspan=378, sticky="ew")

            input_frame.grid_columnconfigure((0,1), weight=1)

            # Ajouter une ligne pour chaque mouvement
            label = ctk.CTkLabel(input_frame, text=f"{movement}", font=("Poppins", 18, "bold", "italic"), width=0, text_color="#CDEAF3", anchor="w")
            label.grid(row=len(self.movement_labels), column=0, padx=15, pady=5, sticky="w")

            key_entry = ctk.CTkEntry(input_frame, font=("Poppins", 14, "bold", "italic"), width=70, text_color="#0579C2")
            key_entry.insert(tk.END, key)  # Pré-remplir avec la touche associée
            key_entry.grid(row=len(self.movement_labels), column=1, pady=5, padx=10, sticky="e")

            # Sauvegarder le champ dans le dictionnaire
            self.movement_labels[movement] = key_entry

    def switch_camera(self):
        """Changer de caméra entre les indices disponibles."""
        if self.cap is not None:
            self.cap.release()

        self.camera_index = (self.camera_index + 1) % 3
        print(f"Passage à la caméra index {self.camera_index}")

        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"Impossible d'ouvrir la caméra index {self.camera_index}.")
            return

        self.capture_video()
        self.reload()

    def capture_video(self):
        """ Lancer ou relancer la capture vidéo """
        if self.cap is not None:
            self.cap.release()  # Libérer la ressource vidéo si elle existe déjà
        self.cap = cv2.VideoCapture(self.camera_index)

        self.update_frame()

    def update_frame(self):
        """Mettre à jour les frames capturées, traiter les poses, et afficher les résultats."""
        global frame_counter  # Compteur global pour gérer la fréquence de traitement
        frame_counter += 1

        # Réduire la fréquence de détection (1 fois toutes les 5 frames)
        if frame_counter % 5 != 0:
            self.root.after(10, self.update_frame)  # Continuer la boucle après 10ms
            return

        success, frame = self.cap.read()  # Lire une frame de la capture
        if not success:
            self.cap.release()  # Libérer la caméra si la capture échoue
            return

        # Option : Redimensionner la frame pour optimiser les performances
        frame = cv2.resize(frame, (640, 480))

        # Analyse des poses avec MediaPipe
        results = pose.process(frame)

        if results.pose_landmarks:
            # Dessiner les landmarks sur la frame
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            # Détecter les mouvements
            movement = detect_movement(results.pose_landmarks.landmark)
            if movement:
                current_profile_name = self.profile_var.get()
                if current_profile_name in game_profiles:
                    key = game_profiles[current_profile_name].get(movement)
                    if key:
                        self.simulate_key_press(key)

        # Convertir la frame en RGB pour l'affichage
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_pil = Image.fromarray(frame)
        image_tk = ImageTk.PhotoImage(image=image_pil)
        self.canvas.configure(image=image_tk)
        self.canvas.image = image_tk

        # Répéter l'appel après 10ms
        self.root.after(10, self.update_frame)


    def update_video(self):
        """ Fonction pour relancer la vidéo après une mise à jour """
        self.capture_video()  # Relancer la capture vidéo
        self.update_mappings(self.profile_var.get())  # Mettre à jour les commandes associées au profil

    def simulate_key_press(self, key):
        global last_key_press_time
        current_time = time.time()

        # Seuil de 300ms entre deux appuis (ajustez selon vos besoins)
        if current_time - last_key_press_time > 0.3:
            pyautogui.press(key)
            last_key_press_time = current_time


    def refresh_window(self):
        """ Rafraîchir la fenêtre principale """
        self.update_video()  # Mettre à jour la vidéo



# Création de la fenêtre Tkinter
root = ctk.CTk()
app = GetUpPlayApp(root)
root.mainloop()
