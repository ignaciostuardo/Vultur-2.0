import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

# ──────────── Cargar datos ────────────
df = pd.read_csv("log_Campaña.csv", encoding='latin1')
df["Yaw_deg"] = pd.to_numeric(df["Yaw_deg"], errors="coerce")
df["Pitch_deg"] = pd.to_numeric(df["Pitch_deg"], errors="coerce")
df["Roll_deg"] = pd.to_numeric(df["Roll_deg"], errors="coerce")
df = df.dropna(subset=["Yaw_deg", "Pitch_deg", "Roll_deg"]).reset_index(drop=True)

# Convertir a radianes
yaw = np.deg2rad(df["Yaw_deg"].values)
pitch = np.deg2rad(df["Pitch_deg"].values)
roll = np.deg2rad(df["Roll_deg"].values)

# ──────────── Modelo del dron ────────────
body = np.array([[-0.3, -0.2, -0.1],
                 [-0.3,  0.2, -0.1],
                 [ 0.3,  0.2, -0.1],
                 [ 0.3, -0.2, -0.1],
                 [-0.3, -0.2,  0.1],
                 [-0.3,  0.2,  0.1],
                 [ 0.3,  0.2,  0.1],
                 [ 0.3, -0.2,  0.1]])

faces = [[0,1,2,3], [4,5,6,7], [0,1,5,4],
         [2,3,7,6], [1,2,6,5], [0,3,7,4]]

arms = [
    [[0, 0, 0], [ 0.6,  0.0, 0]],
    [[0, 0, 0], [-0.6,  0.0, 0]],
    [[0, 0, 0], [ 0.0,  0.6, 0]],
    [[0, 0, 0], [ 0.0, -0.6, 0]],
]

# ──────────── Función de rotación ────────────
def rotation_matrix(yaw, pitch, roll):
    cz, sz = np.cos(yaw), np.sin(yaw)
    cy, sy = np.cos(pitch), np.sin(pitch)
    cx, sx = np.cos(roll), np.sin(roll)

    Rz = np.array([[cz, -sz, 0],
                   [sz,  cz, 0],
                   [ 0,   0, 1]])
    Ry = np.array([[cy,  0, sy],
                   [ 0,  1,  0],
                   [-sy, 0, cy]])
    Rx = np.array([[1,  0,   0],
                   [0, cx, -sx],
                   [0, sx,  cx]])
    return Rz @ Ry @ Rx

# ──────────── Inicializar figura ────────────
fig = plt.figure(figsize=(7, 7))
ax = fig.add_subplot(111, projection='3d')
ax.set_xlim([-1, 1])
ax.set_ylim([-1, 1])
ax.set_zlim([-1, 1])
ax.set_box_aspect([1, 1, 1])
ax.set_title("Animación de orientación del dron")

# Inicializar cuerpo y brazos
cuerpo = Poly3DCollection([], facecolors='deepskyblue', edgecolors='black', alpha=0.8)
brazos = Line3DCollection([[[0, 0, 0], [0, 0, 0]]], colors='black', linewidths=2)
ax.add_collection3d(cuerpo)
ax.add_collection3d(brazos)

# ──────────── Función de animación ────────────
def actualizar(i):
    R = rotation_matrix(yaw[i], pitch[i], roll[i])
    body_rot = body @ R.T
    arms_rot = [np.dot(arm, R.T) for arm in arms]

    cuerpo.set_verts([body_rot[face] for face in faces])
    brazos.set_segments(arms_rot if arms_rot else [[[0, 0, 0], [0, 0, 0]]])

    ax.set_title(f"Frame {i+1}/{len(yaw)}")
    return cuerpo, brazos

# ──────────── Ejecutar animación ────────────
ani = FuncAnimation(fig, actualizar, frames=len(yaw), interval=100, blit=False)
plt.show()
