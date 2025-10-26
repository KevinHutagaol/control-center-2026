import argparse, os, sys, time, shutil, subprocess

def log(msg):
    """Print with timestamp and flush immediately."""
    now = time.strftime("%H:%M:%S")
    print(f"[{now}] {msg}", flush=True)

def wait_for_pid_exit(pid: int, timeout_s: int = 60):
    log(f"Waiting for process {pid} to exit (timeout {timeout_s}s)...")
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            import psutil
            if not psutil.pid_exists(pid):
                log(f"Process {pid} exited.")
                return True
        except Exception:
            # psutil missing or error; assume OK
            log("psutil not available; skipping PID check.")
            return True
        time.sleep(0.25)
    log(f"Timeout waiting for process {pid}. Continuing anyway.")
    return False

def robust_replace(src_new: str, dst_target: str, max_retries: int = 50, sleep_s: float = 0.2):
    log(f"Replacing:\n  NEW: {src_new}\n  OLD: {dst_target}")
    backup = dst_target + ".bak"
    # Clean old backup
    try:
        if os.path.exists(backup):
            os.remove(backup)
            log(f"Removed old backup {backup}")
    except Exception as e:
        log(f"Warning: failed to remove old backup: {e}")

    for i in range(max_retries):
        try:
            if os.path.exists(dst_target):
                os.replace(dst_target, backup)
                log(f"Renamed old exe to backup (attempt {i+1})")
            os.replace(src_new, dst_target)
            log("✅ Replacement successful!")
            # Success: cleanup backup
            try:
                if os.path.exists(backup):
                    os.remove(backup)
                    log("Deleted backup file.")
            except Exception as e:
                log(f"Warning: could not delete backup: {e}")
            return True
        except Exception as e:
            log(f"Retry {i+1}/{max_retries}: file locked ({e})")
            time.sleep(sleep_s)
    log("❌ Replacement failed after all retries.")
    return False

def main():
    log("=== ControlCenter Updater ===")
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="Path to current ControlCenter.exe")
    ap.add_argument("--new", required=True, help="Path to newly downloaded exe")
    ap.add_argument("--waitpid", type=int, default=0)
    ap.add_argument("--relaunch", action="store_true")
    args = ap.parse_args()

    log(f"Target exe : {args.target}")
    log(f"New exe     : {args.new}")
    log(f"Wait PID    : {args.waitpid}")
    log(f"Relaunch    : {args.relaunch}")

    # 1) Wait for the main process to exit (best-effort)
    if args.waitpid:
        wait_for_pid_exit(args.waitpid, timeout_s=90)
    else:
        log("No PID to wait for.")

    # 2) Replace
    ok = robust_replace(args.new, args.target)
    if not ok:
        log("❌ Could not replace file. Creating fallback copy instead...")
        try:
            fallback = args.target + ".new"
            shutil.copy2(args.new, fallback)
            log(f"Fallback copy created at: {fallback}")
        except Exception as e:
            log(f"Fallback failed: {e}")
        sys.exit(2)

    # 3) Relaunch
    if args.relaunch:
        try:
            log("Relaunching new executable...")
            subprocess.Popen([args.target], close_fds=True)
            log("New executable launched successfully.")
        except Exception as e:
            log(f"Warning: could not relaunch: {e}")

    log("Updater finished. Exiting.")
    sys.exit(0)

if __name__ == "__main__":
    main()
