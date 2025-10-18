import numpy as np
import matplotlib.pyplot as plt
import control
from problems import problem_set

def plot_response(t, y):
    plt.figure(figsize=(10, 5))
    plt.plot(t, y.T, label="Output")
    plt.plot(t, np.ones_like(t), 'k--', label="Setpoint")
    plt.title("Step Response")
    plt.xlabel("Time (s)")
    plt.ylabel("Output")
    plt.legend()
    plt.grid(True)
    plt.show()

def simulate_and_plot(no, R_user=None, N_user=None):
    A = problem_set[no]["A"]
    B = problem_set[no]["B"]
    C = problem_set[no]["C"]
    D = problem_set[no]["D"]

    t = np.linspace(0, 10, 500)

    # Original system (open-loop)
    if R_user is None and N_user is None:
        sys_orig = control.StateSpace(A, B, C, D)
        t, y_orig = control.step_response(sys_orig, T=t)
        plot_response(t, y_orig)

    # Closed-loop system without pre-gain (A_cl = A - B*R)
    elif R_user is not None and N_user is None:
        A_cl_no_N = A - B @ R_user
        B_cl_no_N = B
        sys_cl_no_N = control.StateSpace(A_cl_no_N, B_cl_no_N, C, D)
        _, y_cl_no_N = control.step_response(sys_cl_no_N, T=t)
        plot_response(t, y_cl_no_N)
    
    # Closed-loop system with pre-gain (A_cl = A - B*R, B_cl = B*N)
    elif R_user is not None and N_user is not None:
        A_cl = A - B @ R_user
        N_arr = np.array(N_user).reshape(-1, 1)
        B_cl = B @ N_arr
        sys_cl = control.StateSpace(A_cl, B_cl, C, D)
        _, y_cl = control.step_response(sys_cl, T=t)
        plot_response(t, y_cl)
    
    else:
        raise ValueError("Invalid combination of R_user and N_user.")