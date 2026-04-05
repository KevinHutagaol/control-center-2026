import io
import numpy as np
import matplotlib.pyplot as plt
import control

from pages.Modul7.session import moduleCOD_session

def plot_response(t, y, title="Step Response"):
    plt.figure(figsize=(10, 5))
    plt.plot(t, y.T, label="Output")
    plt.plot(t, np.ones_like(t), 'k--', label="Setpoint")
    plt.title(title)
    plt.xlabel("Time (s)")
    plt.ylabel("Output")
    plt.legend()
    plt.grid(True)
    
    # Tangkap gambar ke dalam memori
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    img_bytes = buf.getvalue()
    
    plt.show() # Tampilkan ke layar
    
    return img_bytes # Kembalikan bytes gambarnya

def simulate_and_plot(ui, R_user=None, N_user=None):
    A = moduleCOD_session["A_user"]
    B = moduleCOD_session["B_user"]
    C = moduleCOD_session["C_user"]
    D = moduleCOD_session["D_user"]

    t = np.linspace(0, 10, 500)

    # 1. Buat flag/penanda yang aman dari error NoneType vs Array
    r_is_empty = True if R_user is None else np.all(np.asarray(R_user) == 0)
    n_is_empty = True if N_user is None else np.all(np.asarray(N_user) == 0)

    # Pastikan ui punya tempat nampung grafik
    if not hasattr(ui, 'generated_plots'):
        ui.generated_plots = {}

    # Original system (open-loop) -> R kosong, N kosong
    if r_is_empty and n_is_empty:
        sys_orig = control.StateSpace(A, B, C, D)
        t, y_orig = control.step_response(sys_orig, T=t)
        print("Simulating original system (open-loop)...")
        ui.cb_open_loop.setText("● Original system (open-loop): Ready")
        ui.cb_open_loop.setStyleSheet("color: #00ff00; font-weight: bold; border-image: none; background: transparent; font-size: 14px;")
        
        img_bytes = plot_response(t, y_orig, "Original System (Open-Loop)")
        ui.generated_plots["Original_System_OpenLoop.png"] = img_bytes

    # Closed-loop system without pre-gain -> R ada isi, N kosong
    elif not r_is_empty and n_is_empty:
        A_cl_no_N = A - B @ R_user
        B_cl_no_N = B
        sys_cl_no_N = control.StateSpace(A_cl_no_N, B_cl_no_N, C, D)
        _, y_cl_no_N = control.step_response(sys_cl_no_N, T=t)
        print("Simulating closed-loop system without pre-gain...")
        ui.cb_cl_no_pregain.setText("● Closed-loop system without pre-gain: Ready")
        ui.cb_cl_no_pregain.setStyleSheet("color: #00ff00; font-weight: bold; border-image: none; background: transparent; font-size: 14px;")
        
        img_bytes = plot_response(t, y_cl_no_N, "Closed-Loop (No Pre-Gain)")
        ui.generated_plots["ClosedLoop_No_PreGain.png"] = img_bytes
    
    # Closed-loop system with pre-gain -> R ada isi, N ada isi
    elif not r_is_empty and not n_is_empty:
        A_cl = A - B @ R_user
        # Konversi aman N_user ke array 2D buat perkalian matriks
        N_arr = np.asarray(N_user).reshape(-1, 1)
        B_cl = B @ N_arr
        sys_cl = control.StateSpace(A_cl, B_cl, C, D)
        _, y_cl = control.step_response(sys_cl, T=t)
        print("Simulating closed-loop system with pre-gain...")
        ui.cb_cl_with_pregain.setText("● Closed-loop system with pre-gain: Ready")
        ui.cb_cl_with_pregain.setStyleSheet("color: #00ff00; font-weight: bold; border-image: none; background: transparent; font-size: 14px;")
        
        img_bytes = plot_response(t, y_cl, "Closed-Loop (With Pre-Gain)")
        ui.generated_plots["ClosedLoop_With_PreGain.png"] = img_bytes
    
    else:
        raise ValueError("Invalid combination: N_user diberikan tetapi R_user kosong/nol.")