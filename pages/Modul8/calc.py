import numpy as np


def runDiscretePlant(xk, uk, A, B, C=None, D=None):
    xk = np.asarray(xk).reshape(-1, 1)
    uk = np.asarray(uk).reshape(1, -1) if np.ndim(uk) == 0 else np.asarray(uk)
    x_next = A @ xk + B @ uk
    
    if np.any(np.isnan(x_next)) or np.any(np.isinf(x_next)):
        raise ValueError("Simulation unstable: NaN or Inf detected in plant state")
    
    if C is None or D is None:
        return x_next, None
    yk = C @ xk + D @ uk
    return x_next, yk


def runObserver(xHatk, uk, yk, A, B, C, L):
    xHatk = np.asarray(xHatk).reshape(-1, 1)
    uk = np.asarray(uk).reshape(1, -1) if np.ndim(uk) == 0 else np.asarray(uk)
    yk = np.asarray(yk).reshape(-1, 1)
    innovation = yk - C @ xHatk
    xHat_next = A @ xHatk + B @ uk + L @ innovation
    
    if np.any(np.isnan(xHat_next)) or np.any(np.isinf(xHat_next)):
        raise ValueError("Simulation unstable: NaN or Inf detected in observer state")
    
    return xHat_next


def runStateFeedback(xHatk, rk, R, N):
    xHatk = np.asarray(xHatk).reshape(-1, 1)
    rk = np.asarray(rk).reshape(1, -1) if np.ndim(rk) == 0 else np.asarray(rk)
    uk = -R @ xHatk + N @ rk
    
    if np.any(np.isnan(uk)) or np.any(np.isinf(uk)):
        raise ValueError("Simulation unstable: NaN or Inf detected in control input")
    
    return uk


def stepClosedLoop(xk, xHatk, rk, A, B, C, D, L, R, N):
    uk = runStateFeedback(xHatk, rk, R, N)
    x_next, yk = runDiscretePlant(xk, uk, A, B, C, D)
    xHat_next = runObserver(xHatk, uk, yk, A, B, C, L)
    return x_next, xHat_next, uk, yk


def calculate_statistics(time_data, response_data, setpoint=1.0, settling_band=0.02):
    if len(response_data) == 0 or len(time_data) == 0:
        return {
            "overshoot_before": "N/A",
            "overshoot_after": "N/A",
            "settling_time_before": "N/A",
            "settling_time_after": "N/A",
            "peak_time_before": "N/A",
            "peak_time_after": "N/A",
            "steady_state_error": "N/A"
        }

    response_arr = np.array(response_data)
    time_arr = np.array(time_data)

    final_value = response_arr[-1] if len(response_arr) > 0 else 0.0
    
    max_val = np.max(response_arr)
    min_val = np.min(response_arr[:max(1, len(response_arr)//10)])
    
    peak_idx = np.argmax(np.abs(response_arr - setpoint))
    peak_time = time_arr[peak_idx] if peak_idx < len(time_arr) else 0.0
    
    if setpoint != 0:
        overshoot_percent = ((max_val - setpoint) / setpoint) * 100 if max_val > setpoint else 0
    else:
        overshoot_percent = 0

    steady_state_err = abs(setpoint - final_value)
    
    band = settling_band * setpoint
    settling_idx = len(response_arr) - 1
    for i in range(len(response_arr) - 1, -1, -1):
        if abs(response_arr[i] - final_value) > band:
            settling_idx = i + 1
            break
    settling_time = time_arr[settling_idx] if settling_idx < len(time_arr) else time_arr[-1]

    return {
        "overshoot_after": f"{overshoot_percent:.2f}%" if overshoot_percent > 0 else "0%",
        "settling_time_after": f"{settling_time:.3f}s",
        "peak_time_after": f"{peak_time:.3f}s",
        "steady_state_value": f"{final_value:.4f}",
        "steady_state_error": f"{steady_state_err:.4f}"
    }
