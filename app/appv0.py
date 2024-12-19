import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import cv2
import mediapipe as mp

# Initialisation de MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils

# Ouvre la webcam
cap = cv2.VideoCapture(0)

# Fonction pour détecter les mouvements du corps
def detect_movement(landmarks):
    # Vérification si les landmarks existent
    if not landmarks:
        return None

    # Récupère les coordonnées des points clés pertinents
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

    # Détection des bras levés ou abaissés
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

    # Détection de l'accroupissement
    elif left_knee.y < left_hip.y and right_knee.y < right_hip.y:
        movement = "Crouching"

    # Détection de rotation du torse
    elif left_shoulder.x < left_hip.x and right_shoulder.x < right_hip.x:
        movement = "Turn Left"
    elif left_shoulder.x > left_hip.x and right_shoulder.x > right_hip.x:
        movement = "Turn Right"

    return movement

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Conversion en RGB pour MediaPipe
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)

    # Dessiner les repères du squelette et détecter les mouvements
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # Appel de la fonction de détection des mouvements
        movement = detect_movement(results.pose_landmarks.landmark)

        # Affichage du mouvement détecté sur l'écran
        if movement:
            cv2.putText(frame, f'Movement Detected: {movement}', (10, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

    # Affichage de la vidéo
    cv2.imshow('GetUpPlay - Webcam Feed', frame)

    # Quitter avec la touche 'q'
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
