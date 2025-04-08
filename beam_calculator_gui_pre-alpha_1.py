import traceback  
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from scipy.integrate import quad
import pandas as pd
import math
from math import ceil
import matplotlib
matplotlib.use('TkAgg')


class BeamCalculatorApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Расчет усиления композитными лентами")
        self.root.geometry("1800x1200")

        # Параметры плиты
        self.slab_params = {
            'width': 1.2,
            'height': 0.265,
            'n_voids': 5,
            'void_radius': 0.075,
            'void_rect_height': 0.055,
            'E_concrete': 3e10,
            'E_carbon': 1.65e11,
            'q_load': 10602,
            'span_length': 9.4
        }

        self.base_inertia = self.calculate_inertia()  # Момент инерции без усиления
        self.LAYER_THICKNESS_MM = 0.4  # Толщина одного слоя в мм
        
        # Диапазоны параметров
        self.width_options = [50, 100, 150, 200, 250, 300]
        self.LAYER_THICKNESS_MM = 0.4  # Толщина одного слоя в мм
        self.layer_options = list(range(1, 26))  # 1-25 слоёв (25*0.4=10 мм)
        self.current_layers = 1  # Текущее значение слоёв по умолчанию
        self.length_options = list(range(0, 101, 5))

        # Переменные для графиков
        self.current_width = 100
        self.current_length = 30
        self.current_thickness = 0
        self.graph_data = []
        self.base_deflection = None
        
        # Добавляем параметры для нескольких лент
        self.tape_count_options = [1, 2, 3]  # Количество лент
        self.current_tape_count = 1

        self.calculate_base_deflection()  # Важно: рассчитать базовый прогиб
        self.update_info()
        self.update_efficiency_graph()
        self.update_epures()

        # Основной контейнер
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Создаем Notebook для вкладок
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)

        # Создаем вкладки
        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)
        self.tab3 = ttk.Frame(self.notebook)

        self.notebook.add(self.tab1, text="Основные расчеты")
        self.notebook.add(self.tab2, text="График эффективности")
        self.notebook.add(self.tab3, text="Эпюры M, Q и прогибов")

        # Создаем содержимое вкладок
        self.create_tab1_content(self.tab1)
        self.create_tab2_content(self.tab2)
        self.create_tab3_content(self.tab3)

        # Инициализация переменных для третьей вкладки
        self.epure_selection_var = tk.StringVar()
        self.epure_selection = None  # Будет создан в create_tab3_content
        
        # Значения по умолчанию
        self.current_width = 100
        self.current_length = 30
        self.current_tape_count = 1
        self.base_deflection = 0
        self.graph_data = []
        
        # Добавьте эти атрибуты
        self.width_slider = None
        self.length_slider = None
        self.width_label = None
        self.length_label = None
        self.tape_count_var = tk.StringVar(value="1")
        
        # Расчет базовых значений
        self.calculate_base_deflection()
        self.update_info()

        # Привязка клавиш масштабирования
        self.section_zoom = 1.0  # Инициализация переменной масштаба
        # Привязка клавиш
        self.root.bind('<plus>', self.zoom_in)
        self.root.bind('<minus>', self.zoom_out)
        self.root.bind('<KP_Add>', self.zoom_in)
        self.root.bind('<KP_Subtract>', self.zoom_out)

        self.calculate_base_deflection()
        self.update_info()
        
        self.width_combobox.bind("<<ComboboxSelected>>", lambda e: self.calculate())
        self.length_combobox.bind("<<ComboboxSelected>>", lambda e: self.calculate())
        self.tape_count_combobox.bind("<<ComboboxSelected>>", lambda e: self.calculate())
        
        # Инициализация критических переменных
        self.current_width = 100
        self.current_length = 30
        self.current_tape_count = 1
        self.base_deflection = 0
        self.graph_data = []
        self.LAYER_THICKNESS_MM = 0.4  # Толщина одного слоя в мм
        
        # Создаем вкладки
        self.create_tab1_content(self.tab1)
        self.create_tab2_content(self.tab2)
        self.create_tab3_content(self.tab3)
        
        # Первоначальный расчет
        self.calculate_base_deflection()
        self.update_info()
        self.update_efficiency_graph()
        self.update_epures()

    def zoom_in(self, event=None):
        """Увеличение масштаба"""
        self.zoom_section(1.1)

    def zoom_out(self, event=None):
        """Уменьшение масштаба"""
        self.zoom_section(0.9)

    def zoom_section(self, factor):
        """Масштабирование с проверкой атрибута"""
        try:
            if not hasattr(self, 'section_zoom'):
                self.section_zoom = 1.0

            new_zoom = self.section_zoom * factor
            # Ограничение масштаба
            new_zoom = max(0.5, min(5.0, new_zoom))

            if abs(new_zoom - self.section_zoom) > 0.01:
                self.section_zoom = new_zoom
                self.draw_section_plot()
            if hasattr(self, 'canvas_epure'):
                self.canvas_epure.draw()
        except Exception as e:
            print(f"Zoom error: {e}")

    def calculate_base_deflection(self):
        """Расчёт базового прогиба (без усиления)"""
        try:
            # Явно задаём параметры для базового расчёта
            self.base_deflection = self.calculate_deflection(0, 0, 0, 1)
            if self.base_deflection is None:
                raise ValueError("Не удалось рассчитать базовый прогиб")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка расчёта базового прогиба: {str(e)}")
            self.base_deflection = 0  # Значение по умолчанию

    def create_tab1_content(self, parent):
        """Создание основной вкладки с расчетами"""
        # Настройка сетки
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)

        # Панель параметров (левая верхняя)
        param_frame = ttk.LabelFrame(parent, text="Параметры усиления")
        param_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        param_frame.grid_propagate(False)

        # Ширина ленты
        ttk.Label(param_frame, text="Ширина ленты (мм):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.width_var = tk.StringVar(value="100")
        self.width_combobox = ttk.Combobox(
            param_frame,
            textvariable=self.width_var,
            values=[50, 100, 150, 200, 250, 300],
            state="readonly",
            width=10
        )
        self.width_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Длина усиления
        ttk.Label(param_frame, text="Длина усиления (%):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.length_var = tk.StringVar(value="30")
        self.length_combobox = ttk.Combobox(
            param_frame,
            textvariable=self.length_var,
            values=list(range(0, 101, 5)),
            state="readonly",
            width=10
        )
        self.length_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Количество лент
        ttk.Label(param_frame, text="Количество лент:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.tape_count_var = tk.StringVar(value="1")
        self.tape_count_combobox = ttk.Combobox(
            param_frame,
            textvariable=self.tape_count_var,
            values=[1, 2, 3],
            state="readonly",
            width=10
        )
        self.tape_count_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Кнопка расчета
        ttk.Button(
            param_frame,
            text="Рассчитать",
            command=self.calculate
        ).grid(row=3, column=0, columnspan=2, pady=10)

        # Привязка событий
        self.width_combobox.bind("<<ComboboxSelected>>", lambda e: self.calculate())
        self.length_combobox.bind("<<ComboboxSelected>>", lambda e: self.calculate())
        self.tape_count_combobox.bind("<<ComboboxSelected>>", lambda e: self.calculate())

        # Панель информации (правая верхняя)
        info_frame = ttk.LabelFrame(parent, text="Информация о расчете")
        info_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Текстовое поле для информации
        self.info_text = tk.Text(info_frame, wrap="word", height=10, state="disabled")
        scrollbar_info = ttk.Scrollbar(info_frame, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=scrollbar_info.set)
        
        scrollbar_info.pack(side="right", fill="y")
        self.info_text.pack(fill="both", expand=True)

        # Таблица результатов (левая нижняя)
        result_frame = ttk.LabelFrame(parent, text="Результаты")
        result_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        columns = ("layers", "thickness", "deflection", "reduction", "area", "efficiency")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=10)
        
        # Настройка столбцов
        self.tree.heading("layers", text="Слои")
        self.tree.heading("thickness", text="Толщина (мм)")
        self.tree.heading("deflection", text="Прогиб (мм)")
        self.tree.heading("reduction", text="Снижение (%)")
        self.tree.heading("area", text="Площадь (м²)")
        self.tree.heading("efficiency", text="Эффективность")
        
        for col in columns:
            self.tree.column(col, width=80, anchor="center")
        
        scrollbar_tree = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree.yview)
        scrollbar_tree.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.configure(yscrollcommand=scrollbar_tree.set)

        # График прогиба (правая нижняя)
        graph_frame = ttk.LabelFrame(parent, text="График прогиба")
        graph_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        self.figure_deflection = Figure(figsize=(8, 4), dpi=100)
        self.deflection_plot = self.figure_deflection.add_subplot(111)
        self.canvas_deflection = FigureCanvasTkAgg(self.figure_deflection, master=graph_frame)
        self.canvas_deflection.get_tk_widget().pack(fill="both", expand=True)
        
        # Настройка весов для правильного растягивания
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        
        # Инициализация информации
        self.update_info()
        
    def create_tab2_content(self, parent):
        """Создание вкладки с графиком эффективности"""
        # Очистка предыдущих элементов
        for widget in parent.winfo_children():
            widget.destroy()

        # Основной контейнер
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True)

        # График
        self.figure_efficiency = Figure(figsize=(8, 5), dpi=100)
        self.efficiency_plot = self.figure_efficiency.add_subplot(111)
        self.canvas_efficiency = FigureCanvasTkAgg(self.figure_efficiency, master=main_frame)
        self.canvas_efficiency.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # Панель управления
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", padx=10, pady=5)

        # Ползунок ширины
        ttk.Label(control_frame, text="Ширина (мм):").grid(row=0, column=0, padx=5)
        self.width_slider = ttk.Scale(control_frame, from_=50, to=300, orient="horizontal")
        self.width_slider.grid(row=0, column=1, padx=5)
        self.width_slider.set(100)
        self.width_label = ttk.Label(control_frame, text="100")
        self.width_label.grid(row=0, column=2, padx=5)

        # Ползунок длины
        ttk.Label(control_frame, text="Длина (%):").grid(row=1, column=0, padx=5)
        self.length_slider = ttk.Scale(control_frame, from_=0, to=100, orient="horizontal")
        self.length_slider.grid(row=1, column=1, padx=5)
        self.length_slider.set(30)
        self.length_label = ttk.Label(control_frame, text="30")
        self.length_label.grid(row=1, column=2, padx=5)

        # Привязка событий
        self.width_slider.bind("<B1-Motion>", self.update_efficiency_graph)
        self.width_slider.bind("<ButtonRelease-1>", self.update_efficiency_graph)
        self.length_slider.bind("<B1-Motion>", self.update_efficiency_graph)
        self.length_slider.bind("<ButtonRelease-1>", self.update_efficiency_graph)

        # Первое построение
        self.update_efficiency_graph()

    def calculate_main(self):
        """Основной метод расчета, вызываемый из первой вкладки"""
        try:
            width = int(self.width_var.get())
            length = int(self.length_var.get())
            tape_count = int(self.tape_count_var.get())

            # Обновляем слайдеры (без вызова расчета)
            self.width_slider_eff.set(width)
            self.length_slider_eff.set(length)

            # Основной расчет
            self.perform_calculations(width, length, tape_count)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка расчета: {str(e)}")

    def apply_slider_values(self):
        """Применение параметров из слайдеров второй вкладки"""
        try:
            width = int(self.width_slider_eff.get())
            length = int(self.length_slider_eff.get())
            tape_count = int(self.tape_count_var.get())  # Берем из основного combobox

            # Обновляем основные параметры
            self.width_var.set(width)
            self.length_var.set(length)
            self.width_combobox.set(width)
            self.length_combobox.set(length)

            # Выполняем расчет
            self.perform_calculations(width, length, tape_count)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка применения параметров: {str(e)}")

    def perform_calculations(self, width, length, tape_count):
        """Основной метод расчета"""
        try:
            # Получаем параметры из интерфейса
            width = int(self.width_var.get())
            length = int(self.length_var.get())
            tape_count = int(self.tape_count_var.get())
            
            # Сохраняем текущие параметры
            self.current_width = width
            self.current_length = length
            self.current_tape_count = tape_count
            
            # Расчет базового прогиба (без усиления)
            try:
                self.base_deflection = self.calculate_deflection(0, 0, 0, 1)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось рассчитать базовый прогиб: {str(e)}")
                return

            # Очищаем предыдущие данные
            self.tree.delete(*self.tree.get_children())
            self.graph_data = []
            
            # Расчет для всех вариантов слоев
            for layers in range(1, 26):
                try:
                    thickness_mm = layers * self.LAYER_THICKNESS_MM
                    
                    # ВАЖНО: Правильный расчет прогиба с учетом ВСЕХ параметров
                    deflection = self.calculate_deflection(width, thickness_mm, length, tape_count)
                    
                    # Расчет эффективности
                    reduction = ((self.base_deflection - deflection) / self.base_deflection * 100) if self.base_deflection != 0 else 0
                    area_per_layer = (width/1000) * (self.slab_params['span_length'] * length/100) * tape_count
                    total_area = area_per_layer * layers
                    efficiency = reduction / total_area if total_area > 0 else 0
                    
                    # Добавляем в таблицу (с реальным прогибом)
                    self.tree.insert("", "end", values=(
                        layers,
                        f"{thickness_mm:.1f}",
                        f"{deflection:.2f}",  # Фактический прогиб
                        f"{reduction:.1f}",
                        f"{total_area:.4f}",
                        f"{efficiency:.2f}" if efficiency > 0 else "-"
                    ))
                    
                    # Сохраняем для графиков
                    self.graph_data.append({
                        'layers': layers,
                        'thickness': thickness_mm,
                        'deflection': deflection,
                        'width': width,
                        'length': length,
                        'tape_count': tape_count,
                        'reduction': reduction,
                        'efficiency': efficiency
                    })
                    
                except Exception as e:
                    messagebox.showwarning("Предупреждение", f"Для {layers} слоёв: {str(e)}")
            
            # Обновляем графики и информацию
            self.update_deflection_graph()
            self.update_efficiency_graph()
            self.update_info()
            self.update_epure_selection()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка расчёта: {str(e)}")

    def on_slider_change(self, event=None):
        """Обновление значений при движении слайдера"""
        width = int(self.width_slider_eff.get())
        length = int(self.length_slider_eff.get())
        
        self.width_slider_value.config(text=str(width))
        self.length_slider_value.config(text=str(length))

    def update_from_sliders(self):
        """Обновление расчетов при нажатии кнопки"""
        width = int(self.width_slider_eff.get())
        length = int(self.length_slider_eff.get())
        
        # Обновляем основные параметры
        self.width_var.set(width)
        self.length_var.set(length)
        
        # Запускаем расчет
        self.calculate()
        
        # Обновляем график эффективности
        self.update_efficiency_graph()
    
    def create_tab3_content(self, parent):
        """Полностью переработанная реализация 3-й вкладки"""
        # Основной контейнер
        self.tab3_frame = ttk.Frame(parent)
        self.tab3_frame.pack(fill="both", expand=True)

        # Создаем холст для графиков ПЕРВЫМ
        self.figure_epure = Figure(figsize=(12, 8), dpi=100)
        self.canvas_epure = FigureCanvasTkAgg(self.figure_epure, master=self.tab3_frame)
        self.canvas_widget = self.canvas_epure.get_tk_widget()
        self.canvas_widget.pack(side="left", fill="both", expand=True)

        # Создаем оси для всех эпюр
        self.epure_m_plot = self.figure_epure.add_subplot(231)
        self.epure_q_plot = self.figure_epure.add_subplot(232)
        self.epure_deflection_plot = self.figure_epure.add_subplot(233)
        self.epure_section_plot = self.figure_epure.add_subplot(234)
        self.epure_stress_plot = self.figure_epure.add_subplot(235)
        self.figure_epure.add_subplot(236).axis('off')  # Пустая область

        # Панель управления справа
        control_frame = ttk.Frame(self.tab3_frame)
        control_frame.pack(side="right", fill="y", padx=5, pady=5)

        # Параметры усиления
        ttk.Label(control_frame, text="Параметры усиления").pack(pady=5)
        
        ttk.Label(control_frame, text="Ширина ленты (мм):").pack()
        self.width_combobox_tab3 = ttk.Combobox(control_frame, values=self.width_options, width=8)
        self.width_combobox_tab3.pack(pady=5)
        self.width_combobox_tab3.current(1)
        
        ttk.Label(control_frame, text="Количество слоев:").pack()
        self.layer_combobox_tab3 = ttk.Combobox(control_frame, values=self.layer_options, width=8)
        self.layer_combobox_tab3.pack(pady=5)
        self.layer_combobox_tab3.current(0)
        
        ttk.Label(control_frame, text="Количество лент:").pack()
        self.tape_count_combobox_tab3 = ttk.Combobox(control_frame, values=self.tape_count_options, width=8)
        self.tape_count_combobox_tab3.pack(pady=5)
        self.tape_count_combobox_tab3.current(0)

        # Управление эпюрой напряжений
        ttk.Label(control_frame, text="Положение сечения:").pack(pady=(20,5))
        self.section_pos_slider = ttk.Scale(
            control_frame,
            from_=0,
            to=self.slab_params['span_length'],
            orient="vertical",
            length=200,
            command=lambda v: self._update_stress_plot(float(v))
        )
        self.section_pos_slider.pack()
        self.section_pos_label = ttk.Label(control_frame, text="4.70 м")
        self.section_pos_label.pack()
        
        ttk.Button(
            control_frame,
            text="Среднее сечение",
            command=self._reset_to_mid_section
        ).pack(pady=10)

        # Привязка событий
        for cb in [self.width_combobox_tab3, self.layer_combobox_tab3, self.tape_count_combobox_tab3]:
            cb.bind("<<ComboboxSelected>>", lambda e: self._update_all_epures())

        # Первоначальное построение
        self._update_all_epures()

    def _reset_to_mid_section(self):
        """Возврат к среднему сечению"""
        mid = self.slab_params['span_length']/2
        self.section_pos_slider.set(mid)
        self._update_stress_plot(mid)

    def _update_stress_plot(self, x_pos):
        """Корректная эпюра нормальных напряжений"""
        try:
            # Получаем параметры
            width = int(self.width_combobox_tab3.get())
            layers = int(self.layer_combobox_tab3.get())
            tape_count = int(self.tape_count_combobox_tab3.get())
            thickness = layers * self.LAYER_THICKNESS_MM / 1000
            
            # Расчет момента инерции
            carbon_area = (width/1000) * thickness * tape_count
            I = self.calculate_inertia(carbon_area, thickness, tape_count)
            
            # Расчет момента в сечении
            L = self.slab_params['span_length']
            q = self.slab_params['q_load']
            M = q * x_pos * (L - x_pos) / 2
            
            # Обновляем подпись положения
            self.section_pos_label.config(text=f"{x_pos:.2f} м")
            
            # Очищаем график
            self.epure_stress_plot.clear()
            
            # Координаты по высоте сечения
            y = np.linspace(-thickness, self.slab_params['height'], 100)
            
            # Расчет напряжений
            sigma = M * y / I  # Основная формула
            
            # Учет разных модулей упругости
            n = self.slab_params['E_carbon'] / self.slab_params['E_concrete']
            sigma[y < 0] *= n  # Для углепластика
            
            # Переводим в МПа
            sigma_mpa = sigma / 1e6
            
            # Рисуем эпюру (правильная ориентация)
            self.epure_stress_plot.plot(sigma_mpa, y, 'm-', linewidth=2)
            
            # Заливка для растяжения/сжатия
            self.epure_stress_plot.fill_betweenx(y, 0, sigma_mpa, 
                                               where=(sigma_mpa>0), 
                                               color='r', alpha=0.3, label='Растяжение (+)')
            self.epure_stress_plot.fill_betweenx(y, 0, sigma_mpa,
                                               where=(sigma_mpa<0),
                                               color='b', alpha=0.3, label='Сжатие (-)')
            
            # Нейтральная ось и оформление
            self.epure_stress_plot.axvline(0, color='k', linestyle='-', linewidth=1)
            self.epure_stress_plot.axhline(0, color='k', linestyle='--', linewidth=0.5)
            
            self.epure_stress_plot.set_title(f"Нормальные напряжения (x = {x_pos:.2f} м)")
            self.epure_stress_plot.set_xlabel("σ, МПа")
            self.epure_stress_plot.set_ylabel("Высота сечения, м")
            self.epure_stress_plot.grid(True)
            self.epure_stress_plot.legend()
            
            self.canvas_epure.draw()
            
        except Exception as e:
            print(f"Ошибка обновления эпюры напряжений: {str(e)}")

    def update_epures_from_tab3(self):
        """Обновление всех эпюр с исправлениями"""
        try:
            # Получаем параметры
            width = int(self.width_combobox_tab3.get())
            length = int(self.length_combobox_tab3.get())
            layers = int(self.layer_combobox_tab3.get())
            tape_count = int(self.tape_count_combobox_tab3.get())
            
            # Обновляем каждую эпюру
            self._update_moment_epure()
            self._update_shear_epure()
            self._update_deflection_epure(width, layers*self.LAYER_THICKNESS_MM, length, tape_count)
            self._draw_section_plot(width/1000, layers*self.LAYER_THICKNESS_MM/1000, tape_count)
            self.update_stress_plot(float(self.section_pos_slider.get()))
            
        except Exception as e:
            print(f"Ошибка обновления эпюр: {str(e)}")

    def calculate_inertia(self, carbon_area=0, carbon_thickness=0, tape_count=1):
        """Расчет момента инерции с учетом пустот и усиления углеволокном"""
        # Момент инерции сплошного прямоугольника
        width = self.slab_params['width']
        height = self.slab_params['height']
        I_solid = (width * height**3) / 12

        # Параметры пустоты
        r = self.slab_params['void_radius']
        h_rect = self.slab_params['void_rect_height']
        n_voids = self.slab_params['n_voids']

        # Момент инерции одной составной пустоты:
        I_semicircle = (math.pi * r**4) / 8  # Для верхнего и нижнего полукруга
        I_rect = (2 * r * h_rect**3) / 12    # Центральная прямоугольная часть
        I_one_void = 2 * I_semicircle + I_rect

        # Общий момент инерции всех пустот
        total_I_void = n_voids * I_one_void

        # Момент инерции бетонного сечения
        I_concrete = I_solid - total_I_void

        # Учет усиления углеволокном
        if carbon_area > 0 and carbon_thickness > 0:
            d = (height + carbon_thickness) / 2
            n = self.slab_params['E_carbon'] / self.slab_params['E_concrete']
            
            # Расчет для нескольких лент
            if tape_count > 1:
                total_I_carbon = 0
                # Расчет ширины одной ленты с учетом промежутков
                if hasattr(self, 'tape_spacing'):
                    width_per_tape = (width - (tape_count + 1) * self.tape_spacing) / tape_count
                else:
                    width_per_tape = carbon_area / carbon_thickness
                    
                carbon_area_per_tape = width_per_tape * carbon_thickness
                
                for i in range(tape_count):
                    if hasattr(self, 'tape_spacing'):
                        x_pos = self.tape_spacing * (i + 1) + width_per_tape * (i + 0.5)
                    else:
                        x_pos = width / (tape_count + 1) * (i + 1)
                        
                    d_tape = x_pos - width / 2
                    total_I_carbon += carbon_area_per_tape * (d**2 + d_tape**2)
                
                I_total = I_concrete + n * total_I_carbon
            else:
                # Одиночная лента по центру
                I_total = I_concrete + n * carbon_area * d**2
                
            return I_total
        
        return I_concrete

    def calculate_deflection(self, width_mm, thickness_mm, length_percent, tape_count):
        """Расчет прогиба с учетом всех параметров"""
        try:
            width = width_mm / 1000
            thickness = thickness_mm / 1000
            L = self.slab_params['span_length']
            q = self.slab_params['q_load']
            E = self.slab_params['E_concrete']
            
            # Площадь усиления с учетом количества лент
            carbon_area = width * thickness * tape_count if thickness_mm > 0 else 0
            
            # Момент инерции
            I = self.calculate_inertia(carbon_area, thickness, tape_count)
            
            # Расчет прогиба
            def integrand(x):
                M = q * L * x / 2 - q * x**2 / 2
                M_bar = x / 2 if x <= L/2 else (L - x)/2
                return M * M_bar / (E * I)
            
            if length_percent >= 100:
                result, _ = quad(integrand, 0, L)
            else:
                L_lenta = L * length_percent / 100
                a = (L - L_lenta)/2
                b = L - a
                
                I_unreinforced = self.calculate_inertia(0, 0)
                def integrand_unreinforced(x):
                    M = q * L * x / 2 - q * x**2 / 2
                    M_bar = x / 2 if x <= L/2 else (L - x)/2
                    return M * M_bar / (E * I_unreinforced)
                
                part1, _ = quad(integrand_unreinforced, 0, a)
                part2, _ = quad(integrand, a, b)
                part3, _ = quad(integrand_unreinforced, b, L)
                result = part1 + part2 + part3
                
            return result * 1000  # в мм
            
        except Exception as e:
            raise RuntimeError(f"Ошибка расчета прогиба: {str(e)}")

    def calculate_moment(self, x, L, q):
        """Расчет изгибающего момента в сечении x"""
        return (q * L * x / 2) - (q * x**2 / 2)

    def calculate_shear_force(self, x, L, q):
        """Расчет поперечной силы в сечении x"""
        return (q * L / 2) - (q * x)

    def calculate_deflection_curve(self, width_mm, thickness_mm, length_percent, n_points=50):
        """Расчёт кривой прогибов с проверками"""
        try:
            width = width_mm / 1000
            thickness = thickness_mm / 1000
            L = self.slab_params['span_length']
            q = self.slab_params['q_load']
            E = self.slab_params['E_concrete']
            
            # Проверка параметров
            if thickness_mm <= 0 or width_mm <= 0:
                return np.linspace(0, L, n_points), np.zeros(n_points)
                
            carbon_area = width * thickness
            I = self.calculate_inertia(carbon_area, thickness)
            
            x_points = np.linspace(0, L, n_points)
            deflections = []
            
            for x in x_points:
                def integrand(xi):
                    M = q * L * xi / 2 - q * xi**2 / 2
                    M_bar = xi * (L - x) / L if xi <= x else x * (L - xi) / L
                    return M * M_bar / (E * I)
                
                if length_percent >= 100:
                    deflection, _ = quad(integrand, 0, L)
                else:
                    L_lenta = L * length_percent / 100
                    a = (L - L_lenta)/2
                    b = L - a
                    
                    I_unreinforced = self.calculate_inertia(0, 0)
                    def integrand_unreinforced(xi):
                        M = q * L * xi / 2 - q * xi**2 / 2
                        M_bar = xi * (L - x) / L if xi <= x else x * (L - xi) / L
                        return M * M_bar / (E * I_unreinforced)
                    
                    part1, _ = quad(integrand_unreinforced, 0, a)
                    part2, _ = quad(integrand, a, b)
                    part3, _ = quad(integrand_unreinforced, b, L)
                    deflection = part1 + part2 + part3
                
                deflections.append(deflection)
            
            return x_points, np.array(deflections)
            
        except Exception as e:
            print(f"Ошибка расчёта кривой прогибов: {str(e)}")
            traceback.print_exc()
            return np.linspace(0, L, n_points), np.zeros(n_points)

    def calculate(self):
        """Основной метод расчета"""
        try:
            # Получаем параметры
            width = int(self.width_var.get())
            length = int(self.length_var.get())
            tape_count = int(self.tape_count_var.get())
            
            # Сохраняем текущие параметры
            self.current_width = width
            self.current_length = length
            self.current_tape_count = tape_count
            
            # Очищаем предыдущие данные
            self.tree.delete(*self.tree.get_children())
            self.graph_data = []
            
            # Расчет для всех вариантов слоев
            for layers in range(1, 26):
                thickness_mm = layers * self.LAYER_THICKNESS_MM
                
                # Расчет прогиба с текущими параметрами
                deflection = self.calculate_deflection(width, thickness_mm, length, tape_count)
                
                # Расчет эффективности
                reduction = ((self.base_deflection - deflection) / self.base_deflection * 100) if self.base_deflection != 0 else 0
                area_per_layer = (width/1000) * (self.slab_params['span_length'] * length/100) * tape_count
                total_area = area_per_layer * layers
                efficiency = reduction / total_area if total_area > 0 else 0
                
                # Добавляем в таблицу
                self.tree.insert("", "end", values=(
                    layers,
                    f"{thickness_mm:.1f}",
                    f"{deflection:.2f}",
                    f"{reduction:.1f}",
                    f"{total_area:.4f}",
                    f"{efficiency:.2f}"
                ))
                
                # Сохраняем для графиков
                self.graph_data.append({
                    'layers': layers,
                    'thickness': thickness_mm,
                    'deflection': deflection,
                    'reduction': reduction,
                    'efficiency': efficiency
                })
            
            # Обновляем графики
            self.update_deflection_graph()
            self.update_info()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка расчета: {str(e)}")
        
    def update_epure_selection(self):
        """Обновление выпадающего списка на 3-й вкладке"""
        if hasattr(self, 'epure_selection') and hasattr(self, 'graph_data'):
            options = [
                f"{d['layers']} слоев ({d['thickness']:.1f} мм) - Прогиб {d['deflection']:.2f} мм"
                for d in self.graph_data
            ]
            self.epure_selection['values'] = options
            if options:
                self.epure_selection.current(0)
    
    def update_efficiency_display(self, event=None):
        """Обновление значений ползунков и графика"""
        width = int(self.width_slider_eff.get())
        length = int(self.length_slider_eff.get())
        
        self.width_value_label.config(text=str(width))
        self.length_value_label.config(text=str(length))
        
        self.update_efficiency_graph()

    def update_deflection_graph(self):
        """Обновление графика прогибов"""
        if not hasattr(self, 'graph_data') or not self.graph_data:
            return
            
        try:
            self.deflection_plot.clear()
            
            # Данные для графика
            thicknesses = [d['thickness'] for d in self.graph_data]
            deflections = [d['deflection'] for d in self.graph_data]
            
            # Базовая линия
            self.deflection_plot.axhline(
                y=self.base_deflection,
                color='r',
                linestyle='--',
                label=f'Без усиления: {self.base_deflection:.2f} мм'
            )
            
            # График прогибов
            self.deflection_plot.plot(
                thicknesses, deflections,
                'b-o',
                label=f'Усиление ({self.current_tape_count} ленты)'
            )
            
            # Настройки графика
            self.deflection_plot.set_title("Зависимость прогиба от толщины усиления")
            self.deflection_plot.set_xlabel("Толщина (мм)")
            self.deflection_plot.set_ylabel("Прогиб (мм)")
            self.deflection_plot.legend()
            self.deflection_plot.grid(True)
            
            self.canvas_deflection.draw()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка обновления графика: {str(e)}")

    def update_efficiency_graph(self, event=None):
        """Обновление графика эффективности"""
        try:
            width = int(self.width_slider.get())
            length = int(self.length_slider.get())
            
            # Обновляем значения
            self.width_label.config(text=str(width))
            self.length_label.config(text=str(length))
            
            # Пример данных (замените на свои расчеты)
            layers = np.arange(1, 26)
            efficiency = np.linspace(5, 50, 25) * (width/100) * (length/100)
            
            # Построение графика
            self.efficiency_plot.clear()
            self.efficiency_plot.plot(layers, efficiency, 'b-o')
            self.efficiency_plot.set_title(f"Эффективность (Ширина: {width}мм, Длина: {length}%)")
            self.efficiency_plot.set_xlabel("Количество слоев")
            self.efficiency_plot.set_ylabel("Эффективность (%/м²)")
            self.efficiency_plot.grid(True)
            
            self.canvas_efficiency.draw()
            
        except Exception as e:
            print(f"Ошибка обновления графика: {str(e)}")

    def update_epures(self):
        """Обновление всех эпюр с исправлениями"""
        try:
            # Проверка инициализации
            if not hasattr(self, 'epure_m_plot'):
                return

            # Параметры балки
            L = self.slab_params['span_length']
            q = self.slab_params['q_load']
            x = np.linspace(0, L, 100)
            
            # Текущие параметры усиления с проверками
            width = getattr(self, 'current_width', 100)
            length_pct = getattr(self, 'current_length', 30)
            tape_count = getattr(self, 'current_tape_count', 1)
            layers = getattr(self, 'current_layers', 1)
            
            # 1. Эпюра моментов
            M = q * x * (L - x) / 2
            self._plot_moment_epure(x, M)
            
            # 2. Эпюра поперечных сил
            Q = q * (L/2 - x)
            self._plot_shear_epure(x, Q)
            
            # 3. Эпюра прогибов (с проверкой)
            try:
                x_points, deflection = self.calculate_deflection_curve(width, layers*self.LAYER_THICKNESS_MM, length_pct)
                deflection_mm = deflection * 1000  # в мм
                self._plot_deflection_epure(x_points, deflection_mm)
            except Exception as e:
                print(f"Ошибка расчёта прогибов: {str(e)}")
                traceback.print_exc()
            
            # 4. Схема сечения (всегда рисуем)
            thickness = layers * self.LAYER_THICKNESS_MM / 1000
            self.draw_section_plot(width/1000, thickness, tape_count)
            
            # 5. Эпюра напряжений (всегда рисуем)
            carbon_area = (width/1000) * thickness
            I = self.calculate_inertia(carbon_area, thickness, tape_count)
            self.draw_stress_plot(max(M), I, thickness)
            
            self.figure_epure.tight_layout()
            self.canvas_epure.draw()
            
        except Exception as e:
            print(f"Ошибка обновления эпюр: {str(e)}")
            traceback.print_exc()

    def _update_all_epures(self):
        """Обновление всех эпюр"""
        try:
            width = int(self.width_combobox_tab3.get())
            layers = int(self.layer_combobox_tab3.get())
            tape_count = int(self.tape_count_combobox_tab3.get())
            thickness = layers * self.LAYER_THICKNESS_MM / 1000

            # Обновляем все эпюры
            self._update_moment_epure()
            self._update_shear_epure()
            self._update_deflection_epure(width, thickness*1000, tape_count)
            self._draw_section_plot(width/1000, thickness, tape_count)
            self._update_stress_plot(float(self.section_pos_slider.get()))
            
        except Exception as e:
            print(f"Ошибка обновления эпюр: {str(e)}")

    def _update_moment_epure(self):
        """Эпюра изгибающих моментов"""
        L = self.slab_params['span_length']
        q = self.slab_params['q_load']
        x = np.linspace(0, L, 100)
        M = q * x * (L - x) / 2

        self.epure_m_plot.clear()
        self.epure_m_plot.plot(x, M, 'r-', linewidth=2)
        self.epure_m_plot.set_title("Эпюра моментов (M)")
        self.epure_m_plot.set_xlabel("Длина, м")
        self.epure_m_plot.set_ylabel("M, Н·м")
        self.epure_m_plot.grid(True)
        self.canvas_epure.draw()

    def _update_shear_epure(self):
        """Эпюра поперечных сил"""
        L = self.slab_params['span_length']
        q = self.slab_params['q_load']
        x = np.linspace(0, L, 100)
        Q = q * (L/2 - x)

        self.epure_q_plot.clear()
        self.epure_q_plot.plot(x, Q, 'b-', linewidth=2)
        self.epure_q_plot.set_title("Эпюра поперечных сил (Q)")
        self.epure_q_plot.set_xlabel("Длина, м")
        self.epure_q_plot.set_ylabel("Q, Н")
        self.epure_q_plot.grid(True)
        self.canvas_epure.draw()

    def _update_deflection_epure(self, width_mm, thickness_mm, tape_count):
        """Эпюра прогибов"""
        try:
            # Используем текущую длину усиления из combobox
            length_percent = int(self.length_combobox_tab3.get()) if hasattr(self, 'length_combobox_tab3') else 30
            x, deflection = self.calculate_deflection_curve(width_mm, thickness_mm, length_percent, tape_count)
            
            self.epure_deflection_plot.clear()
            self.epure_deflection_plot.plot(x, deflection, 'g-', linewidth=2)
            self.epure_deflection_plot.set_title("Эпюра прогибов")
            self.epure_deflection_plot.set_xlabel("Длина, м")
            self.epure_deflection_plot.set_ylabel("Прогиб, мм")
            self.epure_deflection_plot.grid(True)
            self.canvas_epure.draw()
        except Exception as e:
            print(f"Ошибка обновления эпюры прогибов: {str(e)}")

    def _draw_section_plot(self, width, thickness, tape_count):
        """Отрисовка поперечного сечения с пустотами"""
        try:
            self.epure_section_plot.clear()
            
            # Параметры плиты
            slab_width = self.slab_params['width']
            slab_height = self.slab_params['height']
            n_voids = self.slab_params['n_voids']
            void_radius = self.slab_params['void_radius']
            void_rect_height = self.slab_params['void_rect_height']
            
            # Контур плиты
            rect = patches.Rectangle(
                (0, 0), slab_width, slab_height,
                linewidth=2, edgecolor='black', facecolor='lightgray'
            )
            self.epure_section_plot.add_patch(rect)
            
            # Пустоты
            void_spacing = slab_width / (n_voids + 1)
            for i in range(n_voids):
                center_x = void_spacing * (i + 1)
                void_bottom = (slab_height - void_rect_height)/2
                
                # Прямоугольная часть
                void_rect = patches.Rectangle(
                    (center_x - void_radius, void_bottom),
                    2*void_radius, void_rect_height,
                    linewidth=1, edgecolor='red', facecolor='white'
                )
                self.epure_section_plot.add_patch(void_rect)
                
                # Верхний полукруг
                upper_semi = patches.Wedge(
                    (center_x, void_bottom + void_rect_height),
                    void_radius, 0, 180,
                    width=0.001, facecolor='white', edgecolor='red'
                )
                self.epure_section_plot.add_patch(upper_semi)
                
                # Нижний полукруг
                lower_semi = patches.Wedge(
                    (center_x, void_bottom),
                    void_radius, 180, 360,
                    width=0.001, facecolor='white', edgecolor='red'
                )
                self.epure_section_plot.add_patch(lower_semi)
            
            # Усиление (ленты)
            if tape_count == 1:
                # Одна лента по центру
                carbon = patches.Rectangle(
                    (slab_width/2 - width/2, -thickness),
                    width, thickness,
                    linewidth=1, edgecolor='blue', facecolor='cyan'
                )
                self.epure_section_plot.add_patch(carbon)
            else:
                # Несколько лент с равными промежутками
                spacing = (slab_width - width*tape_count) / (tape_count + 1)
                for i in range(tape_count):
                    carbon = patches.Rectangle(
                        (spacing + i*(width + spacing), -thickness),
                        width, thickness,
                        linewidth=1, edgecolor='blue', facecolor='cyan'
                    )
                    self.epure_section_plot.add_patch(carbon)
            
            # Настройки отображения
            self.epure_section_plot.set_title("Поперечное сечение")
            self.epure_section_plot.set_aspect('equal')
            self.epure_section_plot.set_xlim(-0.1, slab_width + 0.1)
            self.epure_section_plot.set_ylim(-thickness - 0.1, slab_height + 0.1)
            self.epure_section_plot.axis('off')
            
            self.canvas_epure.draw()
        except Exception as e:
            print(f"Ошибка отрисовки сечения: {str(e)}")
            
    def _add_dimension_lines(self, ax, slab_width, slab_height, thickness):
        """Добавление размерных линий для наглядности"""
        # Размер плиты по высоте
        ax.annotate('', xy=(slab_width+0.05, 0), xytext=(slab_width+0.05, slab_height),
                    arrowprops=dict(arrowstyle='<->', lw=1))
        ax.text(slab_width+0.07, slab_height/2, f'{slab_height*1000:.0f} мм', 
                rotation=90, va='center')
        
        # Размер плиты по ширине
        ax.annotate('', xy=(0, -thickness-0.01), xytext=(slab_width, -thickness-0.01),
                    arrowprops=dict(arrowstyle='<->', lw=1))
        ax.text(slab_width/2, -thickness-0.02, f'{slab_width*1000:.0f} мм', 
                ha='center')
        
        # Размер усиления
        if thickness > 0:
            ax.annotate('', xy=(slab_width+0.05, -thickness), xytext=(slab_width+0.05, 0),
                        arrowprops=dict(arrowstyle='<->', lw=1, color='blue'))
            ax.text(slab_width+0.07, -thickness/2, f'{thickness*1000:.1f} мм', 
                    rotation=90, va='center', color='blue')

    def _plot_moment_epure(self, x, M):
        """Отрисовка эпюры изгибающих моментов"""
        self.epure_m_plot.clear()
        
        # Основной график
        self.epure_m_plot.plot(x, M, 'r-', linewidth=2, label='Изгибающий момент')
        self.epure_m_plot.fill_between(x, M, color='r', alpha=0.1)
        
        # Аннотация максимального значения
        max_moment = max(M)
        max_moment_x = x[np.argmax(M)]
        self.epure_m_plot.annotate(
            f'Mmax = {max_moment:.2f} Н·м',
            xy=(max_moment_x, max_moment),
            xytext=(max_moment_x + 0.5, max_moment * 0.8),
            arrowprops=dict(arrowstyle="->")
        )
        
        # Настройки графика
        self.epure_m_plot.set_title("Эпюра изгибающего момента")
        self.epure_m_plot.set_xlabel("Длина пролета, м")
        self.epure_m_plot.set_ylabel("M, Н·м")
        self.epure_m_plot.grid(True)
        self.epure_m_plot.legend()

    def _plot_shear_epure(self, x, Q):
        """Отрисовка эпюры поперечных сил"""
        self.epure_q_plot.clear()
        
        # Основной график
        self.epure_q_plot.plot(x, Q, 'b-', linewidth=2, label='Поперечная сила')
        self.epure_q_plot.fill_between(x, Q, color='b', alpha=0.1)
        
        # Аннотация максимального значения
        max_shear = max(abs(Q))
        max_shear_x = x[np.argmax(abs(Q))]
        self.epure_q_plot.annotate(
            f'Qmax = {max_shear:.2f} Н',
            xy=(max_shear_x, Q[np.argmax(abs(Q))]),
            xytext=(max_shear_x + 0.5, max_shear * 0.8),
            arrowprops=dict(arrowstyle="->")
        )
        
        # Настройки графика
        self.epure_q_plot.set_title("Эпюра поперечных сил")
        self.epure_q_plot.set_xlabel("Длина пролета, м")
        self.epure_q_plot.set_ylabel("Q, Н")
        self.epure_q_plot.grid(True)
        self.epure_q_plot.legend()

    def _plot_deflection_epure(self, x, deflection):
        """Отрисовка эпюры прогибов"""
        self.epure_deflection_plot.clear()
        
        # Основной график
        self.epure_deflection_plot.plot(x, deflection, 'g-', linewidth=2, label='Прогиб')
        
        # Аннотация максимального значения
        max_deflection = max(deflection)
        max_deflection_x = x[np.argmax(deflection)]
        self.epure_deflection_plot.annotate(
            f'fmax = {max_deflection:.2f} мм',
            xy=(max_deflection_x, max_deflection),
            xytext=(max_deflection_x + 0.5, max_deflection * 0.8),
            arrowprops=dict(arrowstyle="->")
        )
        
        # Базовая линия (без усиления)
        if hasattr(self, 'base_deflection'):
            self.epure_deflection_plot.axhline(
                y=self.base_deflection,
                color='r',
                linestyle='--',
                label=f'Без усиления: {self.base_deflection:.2f} мм'
            )
        
        # Настройки графика
        self.epure_deflection_plot.set_title("Эпюра прогибов")
        self.epure_deflection_plot.set_xlabel("Длина пролета, м")
        self.epure_deflection_plot.set_ylabel("Прогиб, мм")
        self.epure_deflection_plot.grid(True)
        self.epure_deflection_plot.legend()

    def update_info(self):
        """Обновление информационной панели"""
        try:
            if not hasattr(self, 'info_text'):
                return
                
            self.info_text.config(state="normal")
            self.info_text.delete(1.0, tk.END)
            
            # Проверяем наличие необходимых атрибутов
            width = getattr(self, 'current_width', 100)
            length = getattr(self, 'current_length', 30)
            base_deflection = getattr(self, 'base_deflection', 0)
            
            info_lines = [
                "=== Параметры плиты ===",
                f"Ширина: {self.slab_params['width']:.3f} м",
                f"Высота: {self.slab_params['height']:.3f} м",
                f"Пролет: {self.slab_params['span_length']:.2f} м",
                "",
                "=== Параметры усиления ===",
                f"Ширина ленты: {width} мм",
                f"Длина усиления: {length}%",
                f"Толщина слоя: {self.LAYER_THICKNESS_MM:.1f} мм",
                "",
                "=== Результаты ===",
                f"Базовый прогиб: {base_deflection:.2f} мм"
            ]
            
            self.info_text.insert(tk.END, "\n".join(info_lines))
            self.info_text.config(state="disabled")
            
        except Exception as e:
            print(f"Ошибка обновления информации: {str(e)}")

    def export(self):
        try:
            data = []
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                data.append({
                    "Толщина (мм)": values[0],
                    "Прогиб (мм)": values[1],
                    "Снижение (%)": values[2],
                    "Слоёв": values[3],
                    "Площадь (м²)": values[4],
                    "Эффективность (%/м²)": values[5]
                })
            
            if not data:
                messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
                return
                
            df = pd.DataFrame(data)
            filename = f"Результаты_{self.current_width}мм_{self.current_length}%.xlsx"
            df.to_excel(filename, index=False)
            messagebox.showinfo("Успех", f"Файл сохранен:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка экспорта: {str(e)}")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = BeamCalculatorApp(root)
        root.mainloop()
    except Exception as e:
        import traceback
        with open("error_log.txt", "w") as f:
            traceback.print_exc(file=f)
        input("Программа завершилась с ошибкой. Подробности в файле error_log.txt. Нажмите Enter для выхода...")