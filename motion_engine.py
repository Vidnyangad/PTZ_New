import time
import threading


class MotionEngine:
    def __init__(self, ptz_controller):
        self.ptz = ptz_controller
        self.is_running = False
        self.thread = None

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
                    self.ptz.move(
                        step["direction"],
                        step["speed"]
                    )
                    time.sleep(step["duration"])
                    self.ptz.stop()

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
