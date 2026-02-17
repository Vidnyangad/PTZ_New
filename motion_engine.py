import time
import threading


class MotionEngine:
    def __init__(self, ptz_controller):
        self.ptz = ptz_controller
        self.is_running = False
        self.thread = None

    def _simulate_diagonal(self, pan, tilt, duration):
        interval = 0.04  # 40ms feels smooth
        end_time = time.time() + duration

        while time.time() < end_time and self.is_running:

            if abs(pan) > 0:
                self.ptz.move_vector(pan, 0.0)
                time.sleep(interval)
                self.ptz.stop()

            if abs(tilt) > 0:
                self.ptz.move_vector(0.0, tilt)
                time.sleep(interval)
                self.ptz.stop()

    def run_recipe(self, recipe):
        if self.is_running:
            print("Motion already running")
            return False

        self.is_running = True
        self.thread = threading.Thread(
            target=self._execute_recipe,
            args=(recipe,),
            daemon=True
        )
        self.thread.start()
        return True

    def _execute_recipe(self, recipe):
        try:
            for step in recipe:
                if not self.is_running:
                    break

                action = step["action"]

                if action == "preset":
                    preset_id = step["preset"]
                    wait_time = step.get("wait", 3)

                    self.ptz.goto_preset(preset_id)
                    time.sleep(wait_time)

                elif action == "move":
                    
                    if "pan" in step or "tilt" in step:
                        # Direct control mode
                        pan = step.get("pan", 0.0)
                        tilt = step.get("tilt", 0.0)
                        print("PAN:", pan, "TILT:", tilt)
                        self.ptz.move_vector(pan, tilt)

                    else:
                        # Direction string mode (backward compatible)
                        self.ptz.move(step["direction"], step["speed"])

                    time.sleep(step["duration"])
                    self.ptz.stop()

                elif action == "move_diagonal":
                    pan = step.get("pan", 0.0)
                    tilt = step.get("tilt", 0.0)
                    duration = step["duration"]

                    self._simulate_diagonal(pan, tilt, duration)
                
                elif action == "zoom":
                    self.ptz.zoom(
                        step["direction"],
                        step["speed"]
                    )
                    time.sleep(step["duration"])
                    self.ptz.stop()
                
                elif action == "wait":
                    time.sleep(step["duration"])

            print("Recipe completed")

        finally:
            self.ptz.stop()
            self.is_running = False

    def stop(self):
        self.is_running = False
        self.ptz.stop()
