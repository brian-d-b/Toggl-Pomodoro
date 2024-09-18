import tkinter as tk
import time
import subprocess
import pygame
import tkinter.font as tkFont
import logging

# Configure Logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants and Configurable Variables
PINK_NOISE_PATH = "./noises/pink_noise.mp3"
STOP_WORK_SOUND_PATH = "./noises/stop-work.mp3"
START_WORK_SOUND_PATH = "./noises/start-work.mp3"
START_TIMER_SCRIPT = "./toggl-scripts/start-timer.py"
STOP_TIMER_SCRIPT = "./toggl-scripts/stop-timer.py"

DEFAULT_WORK_TIME = 18  # in minutes
DEFAULT_BREAK_TIME = 8  # in minutes
DEFAULT_DELAY_TIME = 5  # in minutes
DING_QUIT_THRESHOLD = 5  # Number of dings after which it quits if no response


class PomodoroTimer:
    def __init__(self, gui):
        # Initialize pygame for audio playback
        pygame.mixer.init()

        # Variables
        self.gui = gui
        self.description = ""
        self.work_time = DEFAULT_WORK_TIME
        self.break_time = DEFAULT_BREAK_TIME
        self.extend_work_time = DEFAULT_DELAY_TIME
        self.extend_break_time = DEFAULT_DELAY_TIME
        self.is_running = False
        self.in_break = False
        self.ding_count = 0  # Track number of dings
        self.remaining_time = 0  # Remaining time in seconds
        self.timer_after_id = None
        self.reminder_after_id = None

        # Initialize audio channels
        # Remove pink_noise_channel as we are using pygame.mixer.music
        self.sound_effects_channel = pygame.mixer.Channel(1)

    def start_work(self):
        logging.info("Starting work session")
        self.cancel_timer()
        self.stop_reminder()
        self.is_running = True
        self.in_break = False
        self.ding_count = 0
        self.play_pink_noise()
        self.call_script(START_TIMER_SCRIPT)
        self.start_timer(self.work_time * 60, self.work_timer_end)
        self.gui.update_ui_state()

    def work_timer_end(self):
        logging.info("Work timer ended")
        self.is_running = False
        self.stop_pink_noise()
        self.play_sound(STOP_WORK_SOUND_PATH)
        self.call_script(STOP_TIMER_SCRIPT)
        self.gui.restore_window()
        self.start_reminder()
        self.gui.prompt_action(
            "Time to start your break!",
            "CTRL + B - Start Break\nCTRL + E - Extend Work"
        )

    def start_break(self):
        logging.info("Starting break session")
        self.cancel_timer()
        self.stop_reminder()
        self.is_running = True
        self.in_break = True
        self.ding_count = 0
        self.stop_pink_noise()
        self.start_timer(self.break_time * 60, self.break_timer_end)
        self.gui.update_ui_state()

    def break_timer_end(self):
        logging.info("Break timer ended")
        self.is_running = False
        self.play_sound(START_WORK_SOUND_PATH)
        self.call_script(START_TIMER_SCRIPT)
        self.gui.restore_window()
        self.start_reminder()
        self.gui.prompt_action(
            "Time to get back to work!",
            "CTRL + W - Start Work\nCTRL + E - Extend Break"
        )

    def extend_work(self, minutes=None):
        if self.is_running and not self.in_break:
            extension = (minutes if minutes is not None else self.extend_work_time) * 60
            logging.info(f"Extending work session by {extension // 60} minutes")
            self.stop_reminder()
            self.remaining_time += extension
            self.gui.hide_prompt()
            self.gui.update_ui_state()
        else:
            logging.warning("Cannot extend work session: either not running or in break")

    def extend_break(self, minutes=None):
        if self.is_running and self.in_break:
            extension = (minutes if minutes is not None else self.extend_break_time) * 60
            logging.info(f"Extending break session by {extension // 60} minutes")
            self.stop_reminder()
            self.remaining_time += extension
            self.gui.hide_prompt()
            self.gui.update_ui_state()
        else:
            logging.warning("Cannot extend break session: either not running or not in break")

    def start_timer(self, duration, callback):
        self.cancel_timer()  # Stop any existing timer
        self.remaining_time = duration
        self.is_running = True
        self.timer_callback = callback
        self._timer_update()

    def _timer_update(self):
        if self.remaining_time <= 0:
            self.is_running = False
            self.gui.timer_var.set("Time Left: 00:00")
            logging.info("Timer reached zero")
            self.timer_callback()
        else:
            mins, secs = divmod(self.remaining_time, 60)
            time_format = f"{int(mins):02d}:{int(secs):02d}"
            self.gui.timer_var.set(f"Time Left: {time_format}")
            self.remaining_time -= 1
            # Schedule the next update and store the after_id
            self.timer_after_id = self.gui.root.after(1000, self._timer_update)

    def cancel_timer(self):
        if self.timer_after_id:
            self.gui.root.after_cancel(self.timer_after_id)
            self.timer_after_id = None
            logging.debug("Cancelled existing timer")

    def start_reminder(self):
        self.cancel_reminder()
        self.ding_count = 0
        self.reminder_intervals = [30, 60, 60]  # Intervals between beeps in seconds
        self._reminder_update()

    def _reminder_update(self):
        if self.ding_count < len(self.reminder_intervals):
            interval = self.reminder_intervals[self.ding_count]
        else:
            interval = 60  # Continue reminders every 60 seconds
        self.ding_count += 1
        logging.debug(f"Scheduling reminder {self.ding_count} in {interval} seconds")
        self.reminder_after_id = self.gui.root.after(interval * 1000, self._reminder_action)

    def _reminder_action(self):
        logging.info(f"Reminder {self.ding_count}")
        if self.ding_count >= DING_QUIT_THRESHOLD:
            self.quit_application()
            return
        if self.in_break:
            self.play_sound(START_WORK_SOUND_PATH)
        else:
            self.play_sound(STOP_WORK_SOUND_PATH)
        if self.ding_count == 1:
            self.gui.restore_window()
        elif self.ding_count == 3:
            self.gui.maximize_window()
        self._reminder_update()

    def cancel_reminder(self):
        if self.reminder_after_id:
            self.gui.root.after_cancel(self.reminder_after_id)
            self.reminder_after_id = None
            logging.debug("Cancelled existing reminder")

    def stop_reminder(self):
        self.cancel_reminder()

    def play_pink_noise(self):
        try:
            pygame.mixer.music.load(PINK_NOISE_PATH)
            pygame.mixer.music.play(-1)  # Loop indefinitely
            logging.info("Started playing pink noise")
        except pygame.error as e:
            logging.error(f"Error playing pink noise: {e}")

    def stop_pink_noise(self):
        pygame.mixer.music.stop()
        logging.info("Stopped pink noise")

    def play_sound(self, sound_path):
        try:
            sound = pygame.mixer.Sound(sound_path)
            self.sound_effects_channel.play(sound)
            logging.info(f"Played sound: {sound_path}")
        except pygame.error as e:
            logging.error(f"Error playing sound {sound_path}: {e}")

    def call_script(self, script_path):
        description = self.description  # Assuming self.description is updated from Tkinter
        logging.info(f"Calling script {script_path} with description '{description}'")
        try:
            subprocess.Popen(["python", script_path, "--description", description])
        except Exception as e:
            logging.error(f"Error calling script {script_path}: {e}")

    def quit_application(self):
        logging.info("Quitting application due to inactivity")
        # Stop the timer, close the reminder thread, and exit the application
        self.cancel_timer()
        self.stop_reminder()
        self.stop_pink_noise()
        pygame.mixer.quit()
        self.gui.root.quit()  # Close the Tkinter window


class PomodoroGUI:
    def __init__(self, root, timer):
        self.root = root
        self.timer = timer
        self.timer.gui = self
        self.root.title("Brians-Toggl-Pomodoro")
        self.root.geometry("800x600")  # Set window size

        # Set default fonts
        self.default_font = tkFont.Font(family="Arial", size=16)
        self.mode_font = tkFont.Font(family="Arial", size=32, weight="bold")
        self.prompt_font = tkFont.Font(family="Arial", size=24, weight="bold")

        # Tkinter Variables
        self.description_var = tk.StringVar(value=self.timer.description)
        self.work_time_var = tk.IntVar(value=self.timer.work_time)
        self.break_time_var = tk.IntVar(value=self.timer.break_time)
        self.extend_work_var = tk.IntVar(value=self.timer.extend_work_time)
        self.extend_break_var = tk.IntVar(value=self.timer.extend_break_time)
        self.mode_var = tk.StringVar(value="Currently Working 💸 🛠️ 🫅")
        self.timer_var = tk.StringVar(value="")

        # Build GUI
        self.create_widgets()
        self.bind_hotkeys()

    def create_widgets(self):
        # Configure grid spacing
        for i in range(9):
            self.root.rowconfigure(i, pad=10)
        for i in range(3):
            self.root.columnconfigure(i, pad=20)

        # Description Entry
        tk.Label(self.root, text="Description:", font=self.default_font).grid(row=0, column=0, sticky="e")
        self.description_entry = tk.Entry(self.root, textvariable=self.description_var, font=self.default_font)
        self.description_entry.grid(row=0, column=1)
        self.go_button = tk.Button(self.root, text="Start Work", command=self.go_action, font=self.default_font)
        self.go_button.grid(row=0, column=2)

        # Work Time Entry
        tk.Label(self.root, text="Work Duration (minutes):", font=self.default_font).grid(row=1, column=0, sticky="e")
        tk.Entry(self.root, textvariable=self.work_time_var, font=self.default_font).grid(row=1, column=1)

        # Break Time Entry
        tk.Label(self.root, text="Break Duration (minutes):", font=self.default_font).grid(row=2, column=0, sticky="e")
        tk.Entry(self.root, textvariable=self.break_time_var, font=self.default_font).grid(row=2, column=1)
        self.break_button = tk.Button(self.root, text="Break", command=self.break_action, font=self.default_font)
        self.break_button.grid(row=2, column=2)

        # Extend Work Entry
        tk.Label(self.root, text="Extend Work (minutes):", font=self.default_font).grid(row=3, column=0, sticky="e")
        self.extend_work_entry = tk.Entry(self.root, textvariable=self.extend_work_var, font=self.default_font)
        self.extend_work_entry.grid(row=3, column=1)
        self.extend_work_entry.bind('<Return>', self.update_extend_work)  # Bind Enter key
        self.update_extend_work_button = tk.Button(self.root, text="Update", command=self.update_extend_work, font=self.default_font)
        self.update_extend_work_button.grid(row=3, column=2)

        # Extend Break Entry
        tk.Label(self.root, text="Extend Break (minutes):", font=self.default_font).grid(row=4, column=0, sticky="e")
        self.extend_break_entry = tk.Entry(self.root, textvariable=self.extend_break_var, font=self.default_font)
        self.extend_break_entry.grid(row=4, column=1)
        self.extend_break_entry.bind('<Return>', self.update_extend_break)  # Bind Enter key
        self.update_extend_break_button = tk.Button(self.root, text="Update", command=self.update_extend_break, font=self.default_font)
        self.update_extend_break_button.grid(row=4, column=2)

        # Timer Label
        self.timer_label = tk.Label(self.root, textvariable=self.timer_var, font=self.mode_font)
        self.timer_label.grid(row=5, column=0, columnspan=3, pady=10)

        # Mode Indicator
        self.mode_label = tk.Label(self.root, textvariable=self.mode_var, font=self.mode_font)
        self.mode_label.grid(row=6, column=0, columnspan=3, pady=10)

        # Prompt Label (initially hidden)
        self.prompt_var = tk.StringVar(value="")
        self.prompt_label = tk.Label(self.root, textvariable=self.prompt_var, font=self.prompt_font, fg="red")
        self.prompt_label.grid(row=7, column=0, columnspan=3, pady=10)
        self.prompt_label.grid_remove()

        # Hotkeys Label
        self.hotkeys_label = tk.Label(self.root, text="Shortcuts:", font=self.default_font)
        self.hotkeys_label.grid(row=8, column=0, sticky="e")

        self.hotkeys_text = tk.Label(
            self.root,
            text="Ctrl+W: Start Work  |  Ctrl+B: Break  |  Ctrl+D: Description  |  Ctrl+E: Extend",
            font=self.default_font
        )
        self.hotkeys_text.grid(row=8, column=1, columnspan=2, sticky="w")

        # Initial State
        self.update_ui_state()

    def bind_hotkeys(self):
        self.root.bind('<Control-d>', self.focus_description)
        self.root.bind('<Control-w>', self.hotkey_work_action)
        self.root.bind('<Control-b>', self.hotkey_break_action)
        self.root.bind('<Control-e>', self.focus_extend_entry)

    def focus_description(self, event=None):
        self.description_entry.focus_set()

    def focus_extend_entry(self, event=None):
        if self.timer.in_break:
            self.extend_break_entry.focus_set()
        else:
            self.extend_work_entry.focus_set()

    def hotkey_work_action(self, event=None):
        self.go_action()

    def hotkey_break_action(self, event=None):
        self.break_action()

    def restore_window(self):
        # Restore the minimized window
        self.root.deiconify()
        self.root.state('normal')

    def maximize_window(self):
        # Maximize the window
        self.root.state('zoomed')

    def go_action(self):
        self.update_timer_variables()
        self.timer.start_work()
        self.update_ui_state()

    def break_action(self):
        self.update_timer_variables()
        self.timer.start_break()
        self.update_ui_state()

    def update_extend_work(self, event=None):
        try:
            minutes = int(self.extend_work_entry.get())
            self.extend_work_var.set(minutes)  # Update the GUI variable
            self.timer.extend_work_time = minutes  # Update the timer's variable
            self.timer.extend_work(minutes)  # Extend the timer
            self.hide_prompt()  # Hide any prompts
            logging.info(f"Extended work by {minutes} minutes")
        except ValueError:
            logging.error("Invalid input for extending work time")

    def update_extend_break(self, event=None):
        try:
            minutes = int(self.extend_break_entry.get())
            self.extend_break_var.set(minutes)  # Update the GUI variable
            self.timer.extend_break_time = minutes  # Update the timer's variable
            self.timer.extend_break(minutes)  # Extend the timer
            self.hide_prompt()  # Hide any prompts
            logging.info(f"Extended break by {minutes} minutes")
        except ValueError:
            logging.error("Invalid input for extending break time")

    def update_timer_variables(self):
        self.timer.description = self.description_var.get()
        self.timer.work_time = self.work_time_var.get()
        self.timer.break_time = self.break_time_var.get()
        self.timer.extend_work_time = self.extend_work_var.get()
        self.timer.extend_break_time = self.extend_break_var.get()
        logging.debug("Updated timer variables from GUI")

    def update_ui_state(self):
        if self.timer.is_running:
            # Disable input fields during timer
            self.disable_inputs()
            if self.timer.in_break:
                # Break mode
                self.mode_var.set("Currently on Break 🏖️")
                self.root.configure(bg="light sky blue")
                # Disable Extend Work controls
                self.extend_work_entry.config(state="disabled")
                self.update_extend_work_button.config(state="disabled")
                # Enable Extend Break controls
                self.extend_break_entry.config(state="normal")
                self.update_extend_break_button.config(state="normal")
            else:
                # Work mode
                self.mode_var.set("Currently Working 💸")
                self.root.configure(bg="light green")
                # Enable Extend Work controls
                self.extend_work_entry.config(state="normal")
                self.update_extend_work_button.config(state="normal")
                # Disable Extend Break controls
                self.extend_break_entry.config(state="disabled")
                self.update_extend_break_button.config(state="disabled")
        else:
            # Enable input fields when timer is not running
            self.enable_inputs()
            # Reset the timer label
            self.timer_var.set("")
            self.extend_work_entry.config(state="normal")
            self.update_extend_work_button.config(state="normal")
            self.extend_break_entry.config(state="normal")
            self.update_extend_break_button.config(state="normal")
            # Update mode indicator and background based on break/work mode
            if self.timer.in_break:
                self.mode_var.set("Break Time!")
                self.root.configure(bg="light sky blue")
            else:
                self.mode_var.set("Work Time!")
                self.root.configure(bg="SystemButtonFace")  # Default background color
            self.hide_prompt()

    def disable_inputs(self):
        self.go_button.config(state="disabled")
        self.description_var.set(self.timer.description)
        self.work_time_var.set(self.timer.work_time)
        self.break_time_var.set(self.timer.break_time)
        # Disable description, work time, and break time entries
        for child in self.root.grid_slaves():
            if isinstance(child, tk.Entry):
                if child not in [self.extend_work_entry, self.extend_break_entry]:
                    child.config(state="disabled")
        self.break_button.config(state="disabled")
        logging.debug("Disabled inputs during active session")

    def enable_inputs(self):
        self.go_button.config(state="normal")
        # Enable description, work time, and break time entries
        for child in self.root.grid_slaves():
            if isinstance(child, tk.Entry):
                child.config(state="normal")
        self.break_button.config(state="normal")
        logging.debug("Enabled inputs")

    def prompt_action(self, message, submessage):
        self.prompt_var.set(f"{message}\n{submessage}")
        self.prompt_label.grid()

    def hide_prompt(self):
        self.prompt_label.grid_remove()
        self.prompt_var.set("")


if __name__ == "__main__":
    root = tk.Tk()
    timer = PomodoroTimer(None)
    gui = PomodoroGUI(root, timer)
    root.mainloop()
