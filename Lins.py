import customtkinter as ctk
import json
import os
from datetime import datetime
from tkinter import messagebox
from tkcalendar import DateEntry
from PIL import Image, ImageDraw
import threading
import pystray
from time import sleep
import winreg
import sys

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

TASKS_FILE = "tasks.json"
SETTINGS_FILE = "settings.json"

class TaskManagerApp:
    ASSETS_PATH = os.path.join(os.path.dirname(__file__), "assets")
    AUTO_START_KEY = "Lins_Task_Manager"
    DEFAULT_ALERT_SOUND = os.path.join(ASSETS_PATH, "alert.wav")
    DEFAULT_REPEAT_INTERVAL = 30

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Lins - ваш менеджер задач")
        self.root.geometry("839x600")
        self.root.resizable(True, True)

        icon_path = os.path.join(self.ASSETS_PATH, "icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
        else:
            print(f"Иконка окна не найдена: {icon_path}")

        self.settings = self.load_settings()
        self.apply_window_settings()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.tasks = []
        self.load_tasks()

        self.start_background_monitor()

        self.icon = None
        self.notifications_enabled = True

        self.img_complete = None
        self.img_delete = None
        self.img_pending = None
        self.img_settings = None
        self.img_update = None
        self.img_about = None
        self.img_close = None
        self.load_images()

        self.setup_ui()
        self.update_task_list()

        self.root.bind("<Unmap>", self.on_minimize)
        self.root.bind("<Map>", self.on_restore)

        self.create_tray_icon()

        tray_thread = threading.Thread(target=self.run_tray, daemon=True)
        tray_thread.start()

    def load_images(self):
        try:
            # Основные иконки задач
            if os.path.exists(os.path.join(self.ASSETS_PATH, "complete.png")):
                self.img_complete = ctk.CTkImage(
                    Image.open(os.path.join(self.ASSETS_PATH, "complete.png")),
                    size=(20, 20)
                )
            else:
                print("Файл: assets/complete.png не найден")

            if os.path.exists(os.path.join(self.ASSETS_PATH, "delete.png")):
                self.img_delete = ctk.CTkImage(
                    Image.open(os.path.join(self.ASSETS_PATH, "delete.png")),
                    size=(20, 20)
                )
            else:
                print("Файл: assets/delete.png не найден")

            if os.path.exists(os.path.join(self.ASSETS_PATH, "pending.png")):
                self.img_pending = ctk.CTkImage(
                    Image.open(os.path.join(self.ASSETS_PATH, "pending.png")),
                    size=(20, 20)
                )
            else:
                print("Файл: assets/pending.png не найден")

            # Иконки для меню
            if os.path.exists(os.path.join(self.ASSETS_PATH, "settings.png")):
                self.img_settings = ctk.CTkImage(
                    Image.open(os.path.join(self.ASSETS_PATH, "settings.png")),
                    size=(16, 16)
                )
            else:
                print("Файл: assets/settings.png не найден")

            if os.path.exists(os.path.join(self.ASSETS_PATH, "update.png")):
                self.img_update = ctk.CTkImage(
                    Image.open(os.path.join(self.ASSETS_PATH, "update.png")),
                    size=(16, 16)
                )
            else:
                print("Файл: assets/update.png не найден")

            if os.path.exists(os.path.join(self.ASSETS_PATH, "about.png")):
                self.img_about = ctk.CTkImage(
                    Image.open(os.path.join(self.ASSETS_PATH, "about.png")),
                    size=(16, 16)
                )
            else:
                print("Файл: assets/about.png не найден")

            if os.path.exists(os.path.join(self.ASSETS_PATH, "close.png")):
                self.img_close = ctk.CTkImage(
                    Image.open(os.path.join(self.ASSETS_PATH, "close.png")),
                    size=(16, 16)
                )
            else:
                print("Файл: assets/close.png не найден")

        except Exception as e:
            print(f"Ошибка загрузки изображений: {e}")

    def load_settings(self):
        self.notifications_enabled = True
        self.repeat_interval = self.DEFAULT_REPEAT_INTERVAL
        self.sound_enabled = True
        self.autostart_enabled = False

        self.autostart_enabled = self.is_auto_start_enabled()

        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)

                self.notifications_enabled = settings.get("notifications_enabled", True)
                self.repeat_interval = settings.get("repeat_interval", self.DEFAULT_REPEAT_INTERVAL)
                self.sound_enabled = settings.get("sound_enabled", True)

                saved_autostart = settings.get("autostart_enabled", None)
                if saved_autostart is not None and saved_autostart != self.autostart_enabled:
                    pass

                return settings
            except Exception as e:
                print(f"Ошибка загрузки настроек из файла: {e}")

        return {}

    def open_menu(self):
        if hasattr(self, 'menu_popup') and self.menu_popup.winfo_exists():
            self.menu_popup.focus()
            return

        self.menu_popup = ctk.CTkToplevel(self.root)
        self.menu_popup.title("")
        self.menu_popup.geometry("200x115+{}+{}".format(
            self.root.winfo_x() + self.root.winfo_width() - 210,
            self.root.winfo_y() + 50
        ))
        self.menu_popup.overrideredirect(True)
        self.menu_popup.attributes("-topmost", True)
        self.menu_popup.configure(fg_color="#333333", border_width=2, border_color="#555")

        # Фрейм для кнопок
        menu_frame = ctk.CTkFrame(self.menu_popup, fg_color="transparent")
        menu_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkButton(
            menu_frame,
            image=self.img_settings,
            text=" Настройки",
            anchor="w",
            command=lambda: self.open_settings_window(),  # ← lambda
            fg_color="#444444",
            hover_color="#555555",
            text_color="white"
        ).pack(fill="x", pady=2)

        ctk.CTkButton(
            menu_frame,
            image=self.img_update,
            text=" Проверить обновления",
            anchor="w",
            command=lambda: self.check_for_updates(),  # ← lambda
            fg_color="#444444",
            hover_color="#555555",
            text_color="white"
        ).pack(fill="x", pady=2)

        ctk.CTkButton(
            menu_frame,
            image=self.img_about,
            text=" О программе",
            anchor="w",
            command=lambda: self.open_about_window(),  # ← lambda
            fg_color="#444444",
            hover_color="#555555",
            text_color="white"
        ).pack(fill="x", pady=2)

        self.menu_popup.bind("<FocusOut>", lambda e: self.close_menu())
        self.root.bind("<Button-1>", self.on_click_outside_menu)
        self.root.bind("<Configure>", self.on_window_move)

    def apply_window_settings(self):
        if self.settings:
            width = self.settings.get("width", 700)
            height = self.settings.get("height", 600)
            x = self.settings.get("x")
            y = self.settings.get("y")
            state = self.settings.get("state", "normal")

            if x is not None and y is not None and x > -1000 and y > -1000:
                geometry = f"{width}x{height}+{x}+{y}"
            else:
                geometry = f"{width}x{height}"
            self.root.geometry(geometry)

            if state == "zoomed":
                self.root.wm_state('zoomed')
        else:
            self.center_window(839, 600)

    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        input_frame = ctk.CTkFrame(self.root, fg_color="#2B2B2B")
        input_frame.pack(pady=10, padx=20, fill="x")

        self.task_entry = ctk.CTkEntry(input_frame, placeholder_text="Описание задачи...", width=300,
                                     fg_color="#333333", border_color="#444", text_color="white")
        self.task_entry.grid(row=0, column=0, padx=5, pady=5)

        self.date_entry = DateEntry(input_frame, date_pattern='dd.mm.yyyy',
                                  background='#333333', foreground='white',
                                  selectbackground='#444444', selectforeground='white',
                                  normalbackground='#333333', normalforeground='white',
                                  weekendbackground='#333333', weekendforeground='white',
                                  headersbackground='#2B2B2B', headersforeground='white',
                                  bordercolor='#444444', arrowcolor='white',
                                  disabledbackground='#2B2B2B', disabledforeground='#666666')
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)

        time_frame = ctk.CTkFrame(input_frame, fg_color="#2B2B2B")
        time_frame.grid(row=0, column=2, padx=5, pady=5)

        self.hour_var = ctk.StringVar(value="12")
        self.minute_var = ctk.StringVar(value="00")

        self.hour_spinbox = ctk.CTkComboBox(time_frame, values=[f"{i:02d}" for i in range(24)], variable=self.hour_var,
                                            width=55, fg_color="#333333", button_color="#444444",
                                            button_hover_color="#555555", text_color="white")
        self.minute_spinbox = ctk.CTkComboBox(time_frame, values=[f"{i:02d}" for i in range(0, 60, 5)],
                                              variable=self.minute_var, width=55, fg_color="#333333",
                                              button_color="#444444", button_hover_color="#555555",
                                              text_color="white")

        self.hour_spinbox.pack(side="left")
        ctk.CTkLabel(time_frame, text=":", text_color="white").pack(side="left", padx=2)
        self.minute_spinbox.pack(side="left")

        self.add_button = ctk.CTkButton(input_frame, text="Добавить задачу", command=self.add_task,
                                      fg_color="#444444", hover_color="#555555", text_color="white")
        self.add_button.grid(row=0, column=3, padx=10)

        self.menu_button = ctk.CTkButton(input_frame, text="⋯", width=40, command=self.open_menu,
                                       fg_color="#444444", hover_color="#555555", text_color="white")
        self.menu_button.grid(row=0, column=4, padx=5)

        list_frame = ctk.CTkFrame(self.root, fg_color="#2B2B2B")
        list_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.canvas = ctk.CTkCanvas(list_frame, bg="#2B2B2B", highlightthickness=0)
        self.scrollbar = ctk.CTkScrollbar(list_frame, orientation="vertical", command=self.canvas.yview,
                                        fg_color="#2B2B2B", button_color="#444444", button_hover_color="#555555")
        self.scrollable_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="frame")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollable_frame.grid_columnconfigure(0, weight=3)
        self.scrollable_frame.grid_columnconfigure(1, weight=2)
        self.scrollable_frame.grid_columnconfigure(2, weight=1)
        self.scrollable_frame.grid_columnconfigure(3, weight=1)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def add_task(self):
        description = self.task_entry.get().strip()
        date_str = self.date_entry.get()
        hour = self.hour_var.get()
        minute = self.minute_var.get()

        if not description:
            messagebox.showwarning("Предупреждение", "Введите описание задачи!")
            return

        try:
            due_datetime = f"{date_str} {hour}:{minute}"
            datetime.strptime(due_datetime, "%d.%m.%Y %H:%M")
        except ValueError:
            messagebox.showwarning("Ошибка", "Некорректная дата или время!")
            return

        task = {
            "description": description,
            "due": due_datetime,
            "completed": False,
            "created": datetime.now().strftime("%d.%m.%Y %H:%M")
        }

        self.tasks.append(task)
        self.task_entry.delete(0, "end")
        self.update_task_list()

        self.show_notification("Задача добавлена", f"Вы добавили: {description[:30]}...")

    def update_task_list(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.tasks:
            placeholder = ctk.CTkLabel(
                self.scrollable_frame,
                text="Нет задач.\nДобавьте новую!",
                text_color="gray",
                font=("Arial", 14),
                justify="center"
            )
            placeholder.grid(row=0, column=0, columnspan=3, pady=20)
            return

        for i in range(4):
            self.scrollable_frame.grid_columnconfigure(i, weight=1)

        for idx, task in enumerate(self.tasks):
            row = idx // 4
            col = idx % 4

            desc = task["description"]
            due = task["due"]
            created = task.get("created", "")
            completed = task["completed"]

            now = datetime.now()
            try:
                due_dt = datetime.strptime(due, "%d.%m.%Y %H:%M")
            except ValueError:
                due_dt = now

            fg_color = "#FF4C4C" if now > due_dt and not completed else "white"

            task_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="#333333", corner_radius=10)
            task_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            task_frame.grid_columnconfigure(0, weight=1)

            desc_label = ctk.CTkLabel(
                task_frame,
                text=desc,
                anchor="w",
                justify="left",
                wraplength=220,
                text_color=fg_color,
                font=("Arial", 14, "bold")
            )
            desc_label.pack(anchor="w", padx=10, pady=(8, 4))

            due_label = ctk.CTkLabel(
                task_frame,
                text=f"Срок: {due}",
                anchor="w",
                text_color=fg_color,
                font=("Arial", 12)
            )
            due_label.pack(anchor="w", padx=10)

            created_label = ctk.CTkLabel(
                task_frame,
                text=f"Создано: {created}",
                anchor="w",
                text_color="gray",
                font=("Arial", 10)
            )
            created_label.pack(anchor="w", padx=10, pady=(0, 8))

            status_frame = ctk.CTkFrame(task_frame, fg_color="transparent")
            status_frame.pack(fill="x", padx=10, pady=(0, 8))

            if self.img_complete and self.img_pending:
                status_img = self.img_complete if completed else self.img_pending
                status_label = ctk.CTkLabel(status_frame, image=status_img, text="")
            else:
                status_text = "✅ Выполнено" if completed else "🕒 В процессе"
                status_color = "green" if completed else "orange"
                status_label = ctk.CTkLabel(status_frame, text=status_text, text_color=status_color)
            status_label.pack(anchor="w")

            action_frame = ctk.CTkFrame(task_frame, fg_color="transparent")
            action_frame.pack(fill="x", padx=10, pady=(4, 8))

            if not completed:
                complete_btn = ctk.CTkButton(
                    action_frame,
                    image=self.img_complete if self.img_complete else None,
                    text="Выполнить" if not self.img_complete else "",
                    width=60,
                    height=25,
                    fg_color="#444444",
                    hover_color="#555555",
                    text_color="white",
                    font=("Arial", 12),
                    command=lambda i=idx: self.complete_task(i)
                )
                complete_btn.pack(side="left", padx=4)

            delete_btn = ctk.CTkButton(
                action_frame,
                image=self.img_delete if self.img_delete else None,
                text="Удалить" if not self.img_delete else "",
                width=60,
                height=25,
                fg_color="#444444",
                hover_color="#555555",
                text_color="white",
                font=("Arial", 12),
                command=lambda i=idx: self.delete_task(i)
            )
            delete_btn.pack(side="left", padx=4)

    def complete_task(self, idx):
        self.tasks[idx]["completed"] = True
        self.update_task_list()
        task_desc = self.tasks[idx]["description"]
        self.show_notification("Задача выполнена", f" {task_desc[:30]}...")

    def delete_task(self, idx):
        task_desc = self.tasks[idx]["description"]
        del self.tasks[idx]
        self.update_task_list()
        self.show_notification("Задача удалена", f" {task_desc[:30]}...")

    def show_notification(self, title="Уведомление", message=""):
        if not self.notifications_enabled:
            return

        notify = ctk.CTkToplevel(self.root)
        notify.overrideredirect(True)
        notify.attributes("-topmost", True)
        notify.configure(fg_color="#2D2D2D", border_width=2, border_color="#444")

        width = 300
        height = 100
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - width - 20
        y = screen_height - height - 50

        notify.geometry(f"{width}x{height}+{x}+{y}")

        ctk.CTkLabel(notify, text=title, font=("Arial", 14, "bold"), text_color="white").pack(pady=(10, 0))
        ctk.CTkLabel(notify, text=message, wraplength=280, justify="left", font=("Arial", 12), text_color="white").pack(pady=5)

        close_btn = ctk.CTkButton(
            notify,
            image=self.img_close if self.img_close else None,
            text="×" if not self.img_close else "",
            width=30,
            height=30,
            fg_color="transparent",
            text_color="gray",
            font=("Arial", 16),
            command=lambda: notify.destroy()
        )
        close_btn.place(relx=0.95, rely=0.1, anchor="ne")

        notify.after(3000, lambda: self.safe_destroy(notify))

    def safe_destroy(self, window):
        try:
            window.destroy()
        except:
            pass

    def create_tray_image(self):
        width = 64
        height = 64
        color1 = "#333333"
        color2 = "white"

        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle([width // 4, height // 4, width // 2, height // 2], outline=color2, width=4)
        dc.text((width // 3, height // 3), "L", fill=color2)
        return image

    def create_tray_icon(self):
        image = self.create_tray_image()
        menu = pystray.Menu(
            pystray.MenuItem('Показать', self.on_tray_click),
            pystray.MenuItem('Закрыть', self.on_tray_exit),
            pystray.MenuItem('Уведомления', self.toggle_notifications, checked=lambda item: self.notifications_enabled)
        )
        self.icon = pystray.Icon("Lins", image, "Lins", menu)

    def run_tray(self):
        self.icon.run()

    def on_minimize(self, event):
        if self.root.state() == 'iconic':
            self.root.withdraw()
            if self.icon:
                self.icon.visible = True

    def on_restore(self, event):
        if self.root.state() != 'iconic':
            self.root.deiconify()
            self.icon.visible = False

    def on_tray_click(self, icon, item):
        self.root.deiconify()
        self.root.state('normal')
        self.root.lift()
        self.icon.visible = False

    def on_tray_exit(self, icon, item):
        self.save_settings()
        self.save_tasks()
        self.icon.stop()
        self.root.quit()
        self.root.destroy()

    def toggle_notifications(self, icon, item):
        self.notifications_enabled = not self.notifications_enabled
        icon.update_menu()

    def save_tasks(self):
        try:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить задачи: {e}")

    def load_tasks(self):
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить задачи: {e}")
                self.tasks = []

    def get_window_state(self):
        is_zoomed = self.root.wm_state() == 'zoomed'
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        width = self.root.winfo_width()
        height = self.root.winfo_height()

        if x < -1000 or y < -1000:
            x = None
            y = None

        state = "zoomed" if is_zoomed else "normal"

        return {
            "width": width,
            "height": height,
            "x": x,
            "y": y,
            "state": state
        }

    def save_settings(self):
        window_state = self.get_window_state()

        settings = {
            "width": window_state["width"],
            "height": window_state["height"],
            "x": window_state["x"],
            "y": window_state["y"],
            "state": window_state["state"],
            "notifications_enabled": self.notifications_enabled,
            "repeat_interval": self.repeat_interval,
            "sound_enabled": self.sound_enabled,
            "autostart_enabled": self.autostart_enabled
        }

        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Не удалось сохранить настройки в файл: {e}")

        try:
            reg_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_WRITE
            )
            if self.autostart_enabled:
                executable_path = os.path.abspath(sys.argv[0])
                if executable_path.endswith(".py"):
                    pythonw_path = sys.executable
                    command = f'"{pythonw_path}" "{executable_path}"'
                else:
                    command = f'"{executable_path}"'
                winreg.SetValueEx(reg_key, self.AUTO_START_KEY, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(reg_key, self.AUTO_START_KEY)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(reg_key)
        except Exception as e:
            messagebox.showerror("Ошибка автозапуска", f"Не удалось обновить автозапуск: {e}")

    def on_closing(self):
        if self.icon:
            self.icon.stop()
        self.save_settings()
        self.save_tasks()
        self.root.quit()
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        if hasattr(self, 'about_window') and self.about_window.winfo_exists():
            self.about_window.destroy()
        if hasattr(self, 'menu_popup') and self.menu_popup.winfo_exists():
            self.menu_popup.destroy()

    def run(self):
        try:
            self.root.mainloop()
        except:
            pass

    def close_menu(self):
        if hasattr(self, 'menu_popup') and self.menu_popup.winfo_exists():
            self.menu_popup.destroy()

    def on_click_outside_menu(self, event):
        if hasattr(self, 'menu_popup') and self.menu_popup.winfo_exists():
            x, y = event.x_root, event.y_root
            wx = self.menu_popup.winfo_rootx()
            wy = self.menu_popup.winfo_rooty()
            ww = self.menu_popup.winfo_width()
            wh = self.menu_popup.winfo_height()
            if not (wx <= x <= wx + ww and wy <= y <= wy + wh):
                self.close_menu()

    def on_window_move(self, event):
        if hasattr(self, 'menu_popup') and self.menu_popup.winfo_exists():
            self.menu_popup.geometry("+{}+{}".format(
                self.root.winfo_x() + self.root.winfo_width() - 210,
                self.root.winfo_y() + 50
            ))

    def open_settings_window(self):
        self.close_menu()
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.focus()
            self.center_window_on_parent(self.settings_window, 350, 300)
            return

        self.settings_window = ctk.CTkToplevel(self.root)
        self.settings_window.title("Настройки")
        self.settings_window.geometry("325x3400")
        self.settings_window.attributes("-topmost", True)
        self.settings_window.resizable(False, False)
        self.settings_window.overrideredirect(True)
        self.settings_window.configure(fg_color="#333333", border_width=2, border_color="#555")
        self.center_window_on_parent(self.settings_window, 350, 350)

        title_label = ctk.CTkLabel(self.settings_window, text="Настройки", font=("Arial", 16, "bold"),
                                   text_color="white")
        title_label.pack(pady=(15, 10))

        def toggle_notifications():
            self.notifications_enabled = not self.notifications_enabled
            notify_switch.configure(text="Уведомления: Вкл" if self.notifications_enabled else "Уведомления: Выкл")

        notify_switch = ctk.CTkSwitch(
            self.settings_window,
            text="Уведомления: " + ("Вкл" if self.notifications_enabled else "Выкл"),
            command=toggle_notifications,
            fg_color="#444444",
            progress_color="#666666",
            text_color="white"
        )
        notify_switch.pack(pady=5)
        if self.notifications_enabled:
            notify_switch.select()
        else:
            notify_switch.deselect()

        def toggle_sound():
            self.sound_enabled = not self.sound_enabled
            sound_switch.configure(text="Звук: Вкл" if self.sound_enabled else "Звук: Выкл")

        sound_switch = ctk.CTkSwitch(
            self.settings_window,
            text="Звук: " + ("Вкл" if self.sound_enabled else "Выкл"),
            command=toggle_sound,
            fg_color="#444444",
            progress_color="#666666",
            text_color="white"
        )
        sound_switch.pack(pady=5)
        if self.sound_enabled:
            sound_switch.select()
        else:
            sound_switch.deselect()

        ctk.CTkLabel(self.settings_window, text="Интервал (мин):", text_color="white", font=("Arial", 12)).pack(
            pady=(10, 2))
        interval_var = ctk.StringVar(value=str(self.repeat_interval))
        interval_combo = ctk.CTkComboBox(
            self.settings_window,
            values=["5", "10", "15", "30", "60", "120"],
            variable=interval_var,
            width=100
        )
        interval_combo.pack(pady=5)

        def toggle_autostart():
            self.autostart_enabled = not self.autostart_enabled
            autostart_switch.configure(text="Автозапуск: Вкл" if self.autostart_enabled else "Автозапуск: Выкл")
            self.set_auto_start(self.autostart_enabled)

        autostart_switch = ctk.CTkSwitch(
            self.settings_window,
            text="Автозапуск: " + ("Вкл" if self.autostart_enabled else "Выкл"),
            command=toggle_autostart,
            fg_color="#444444",
            progress_color="#666666",
            text_color="white"
        )
        autostart_switch.pack(pady=5)
        if self.autostart_enabled:
            autostart_switch.select()
        else:
            autostart_switch.deselect()

        def save_interval():
            try:
                self.repeat_interval = int(interval_var.get())
            except:
                pass

        save_btn = ctk.CTkButton(
            self.settings_window,
            text="Сохранить",
            command=save_interval,
            fg_color="#444444",
            hover_color="#555555"
        )
        save_btn.pack(pady=5)

        close_btn = ctk.CTkButton(
            self.settings_window,
            image=self.img_close if self.img_close else None,
            text="Закрыть" if not self.img_close else "",
            command=self.settings_window.destroy,
            fg_color="#444444",
            hover_color="#555555",
            text_color="white"
        )
        close_btn.pack(pady=10)

        self.settings_window.bind("<FocusOut>", lambda e: self.settings_window.focus())
        self.root.bind("<Button-1>", lambda e: self.close_if_outside(self.settings_window, e))

    def check_for_updates(self):
        self.close_menu()
        update_window = ctk.CTkToplevel(self.root)
        update_window.title("Проверка обновлений")
        update_window.geometry("300x150")
        update_window.attributes("-topmost", True)
        update_window.resizable(False, False)
        update_window.overrideredirect(True)
        update_window.configure(fg_color="#333333", border_width=2, border_color="#555")

        self.center_window_on_parent(update_window, 300, 150)

        ctk.CTkLabel(update_window, text="🔍 Проверка обновлений...", font=("Arial", 14), text_color="white").pack(pady=20)

        def simulate_check():
            sleep(1.5)
            try:
                for widget in update_window.winfo_children():
                    widget.destroy()
                ctk.CTkLabel(update_window, text="✅ У вас последняя версия", text_color="green",
                             font=("Arial", 12)).pack(pady=10)
                ctk.CTkButton(
                    update_window,
                    image=self.img_close if self.img_close else None,
                    text="Закрыть" if not self.img_close else "",
                    command=update_window.destroy,
                    fg_color="#444444",
                    hover_color="#555555",
                    text_color="white"
                ).pack(pady=5)
            except:
                pass

        threading.Thread(target=simulate_check, daemon=True).start()

    def open_about_window(self):
        self.close_menu()
        if hasattr(self, 'about_window') and self.about_window.winfo_exists():
            self.about_window.focus()
            self.center_window_on_parent(self.about_window, 350, 150)
            return

        self.about_window = ctk.CTkToplevel(self.root)
        self.about_window.title("О программе")
        self.about_window.geometry("350x150")
        self.about_window.attributes("-topmost", True)
        self.about_window.resizable(False, False)
        self.about_window.overrideredirect(True)
        self.about_window.configure(fg_color="#333333", border_width=2, border_color="#555")

        # Центрируем
        self.center_window_on_parent(self.about_window, 350, 150)

        ctk.CTkLabel(self.about_window, text="Lins — Менеджер задач", font=("Arial", 16, "bold"), text_color="white").pack(pady=20)
        ctk.CTkLabel(
            self.about_window,
            text="© 2025 Zerio Command. Все права защищены.",
            font=("Arial", 9),
            text_color="gray"
        ).pack(pady=5)

        ctk.CTkButton(
            self.about_window,
            image=self.img_close if self.img_close else None,
            text="Закрыть" if not self.img_close else "",
            command=self.about_window.destroy,
            fg_color="#444444",
            hover_color="#555555",
            text_color="white"
        ).pack(pady=10)

        self.root.bind("<Button-1>", lambda e: self.close_if_outside(self.about_window, e))

    def close_if_outside(self, window, event):
        if not window.winfo_exists():
            return
        x, y = event.x_root, event.y_root
        wx = window.winfo_rootx()
        wy = window.winfo_rooty()
        ww = window.winfo_width()
        wh = window.winfo_height()
        if not (wx <= x <= wx + ww and wy <= y <= wy + wh):
            window.destroy()

    def center_window_on_parent(self, window, width, height):
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (width // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def play_sound(self):
        if self.sound_enabled and os.path.exists(self.DEFAULT_ALERT_SOUND):
            try:
                from playsound import playsound
                threading.Thread(target=playsound, args=(self.DEFAULT_ALERT_SOUND,), daemon=True).start()
            except Exception as e:
                print(f"Ошибка воспроизведения звука: {e}")

    def start_background_monitor(self):

        def monitor():
            last_notify_time = datetime.now()
            while True:
                now = datetime.now()

                for task in self.tasks:
                    if not task["completed"]:
                        try:
                            due_dt = datetime.strptime(task["due"], "%d.%m.%Y %H:%M")
                            if (due_dt - now).total_seconds() <= 300 and (due_dt - now).total_seconds() > 0:
                                self.show_notification(
                                    "Срок истекает!",
                                    f"⚠️ Задача скоро истечёт:\n{task['description'][:30]}..."
                                )
                                self.play_sound()
                        except:
                            pass

                if self.repeat_interval > 0:
                    if (now - last_notify_time).total_seconds() >= self.repeat_interval * 60:
                        self.show_notification(
                            "Напоминание",
                            f"⏰ Прошло {self.repeat_interval} минут."
                        )
                        self.play_sound()
                        last_notify_time = now

                sleep(10)

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    def is_auto_start_enabled(self):
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                                     winreg.KEY_READ)
            try:
                value, _ = winreg.QueryValueEx(reg_key, self.AUTO_START_KEY)
                winreg.CloseKey(reg_key)
                return value != ""
            except FileNotFoundError:
                winreg.CloseKey(reg_key)
                return False
        except Exception as e:
            print(f"Ошибка при проверке автозапуска: {e}")
            return False

    def set_auto_start(self, enable: bool):
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                                     winreg.KEY_WRITE)
            if enable:
                executable_path = os.path.abspath(sys.argv[0])
                if executable_path.endswith(".py"):
                    pythonw_path = sys.executable
                    command = f'"{pythonw_path}" "{executable_path}"'
                else:
                    command = f'"{executable_path}"'
                winreg.SetValueEx(reg_key, self.AUTO_START_KEY, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(reg_key, self.AUTO_START_KEY)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(reg_key)
        except Exception as e:
            messagebox.showerror("Ошибка автозапуска", f"Не удалось изменить автозапуск: {e}")

    def create_tray_image(self):
        icon_path = os.path.join(self.ASSETS_PATH, "tray_icon.png")
        if os.path.exists(icon_path):
            return Image.open(icon_path)
        else:
            width = 64
            height = 64
            image = Image.new('RGB', (width, height), "#333333")
            dc = ImageDraw.Draw(image)
            dc.text((20, 20), "L", fill="white")
            return image


if __name__ == "__main__":
    app = TaskManagerApp()
    app.run()