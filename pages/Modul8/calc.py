import numpy as np


def runDiscretePlant(xk, uk, A, B, C=None, D=None):
    xk = np.asarray(xk).reshape(-1, 1)
    uk = np.asarray(uk).reshape(1, -1) if np.ndim(uk) == 0 else np.asarray(uk)
    x_next = A @ xk + B @ uk
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
    return xHat_next


def runStateFeedback(xHatk, rk, R, N):
    xHatk = np.asarray(xHatk).reshape(-1, 1)
    rk = np.asarray(rk).reshape(-1, 1)
    uk = -R @ xHatk + N @ rk
    return uk


def stepClosedLoop(xk, xHatk, rk, A, B, C, D, L, R, N):
    uk = runStateFeedback(xHatk, rk, R, N)
    x_next, yk = runDiscretePlant(xk, uk, A, B, C, D)
    xHat_next = runObserver(xHatk, uk, yk, A, B, C, L)
    return x_next, xHat_next, uk, yk
