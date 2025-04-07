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
        """Расчет базового прогиба без усиления"""
        try:
            self.base_deflection = self.calculate_deflection(0, 0, 0, 1)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось рассчитать базовый прогиб: {str(e)}")
            self.base_deflection = 0

    def create_tab1_content(self, parent):
        """Создание основной вкладки с расчетами"""
        # Панель параметров
        param_frame = ttk.LabelFrame(parent, text="Параметры усиления")
        param_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Ширина ленты
        ttk.Label(param_frame, text="Ширина ленты (мм):").grid(row=0, column=0, padx=5, pady=5)
        self.width_var = tk.StringVar(value="100")
        width_combobox = ttk.Combobox(
            param_frame,
            textvariable=self.width_var,
            values=[50, 100, 150, 200, 250, 300],
            state="readonly"
        )
        width_combobox.grid(row=0, column=1, padx=5, pady=5)

        # Длина усиления
        ttk.Label(param_frame, text="Длина усиления (%):").grid(row=1, column=0, padx=5, pady=5)
        self.length_var = tk.StringVar(value="30")
        length_combobox = ttk.Combobox(
            param_frame,
            textvariable=self.length_var,
            values=list(range(0, 101, 5)),
            state="readonly"
        )
        length_combobox.grid(row=1, column=1, padx=5, pady=5)

        # Количество лент
        ttk.Label(param_frame, text="Количество лент:").grid(row=2, column=0, padx=5, pady=5)
        self.tape_count_var = tk.StringVar(value="1")
        tape_count_combobox = ttk.Combobox(
            param_frame,
            textvariable=self.tape_count_var,
            values=[1, 2, 3],
            state="readonly"
        )
        tape_count_combobox.grid(row=2, column=1, padx=5, pady=5)

        # Кнопка расчета
        ttk.Button(
            param_frame,
            text="Рассчитать",
            command=self.calculate
        ).grid(row=3, column=0, columnspan=2, pady=10)

        # Привязка событий
        width_combobox.bind("<<ComboboxSelected>>", lambda e: self.calculate())
        length_combobox.bind("<<ComboboxSelected>>", lambda e: self.calculate())
        tape_count_combobox.bind("<<ComboboxSelected>>", lambda e: self.calculate())

        # Таблица результатов
        result_frame = ttk.LabelFrame(parent, text="Результаты")
        result_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        columns = ("layers", "thickness", "deflection", "reduction", "area", "efficiency")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # График прогиба
        graph_frame = ttk.LabelFrame(parent, text="График прогиба")
        graph_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        self.figure_deflection = Figure(figsize=(10, 4), dpi=100)
        self.deflection_plot = self.figure_deflection.add_subplot(111)
        self.canvas_deflection = FigureCanvasTkAgg(self.figure_deflection, master=graph_frame)
        self.canvas_deflection.get_tk_widget().pack(fill="both", expand=True)
        
    def create_tab2_content(self, parent):
        """Создание вкладки с графиком эффективности"""
        # Основной контейнер
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # График эффективности
        graph_frame = ttk.LabelFrame(main_frame, text="График эффективности усиления")
        graph_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.figure_efficiency = Figure(figsize=(10, 5), dpi=100)
        self.efficiency_plot = self.figure_efficiency.add_subplot(111)
        
        self.canvas_efficiency = FigureCanvasTkAgg(
            self.figure_efficiency, 
            master=graph_frame
        )
        self.canvas_efficiency.get_tk_widget().pack(fill="both", expand=True)

        # Панель управления
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", padx=5, pady=5)

        # Слайдеры только для просмотра (без расчета)
        ttk.Label(control_frame, text="Ширина ленты (мм):").pack(side="left", padx=5)
        self.width_slider_eff = ttk.Scale(
            control_frame,
            from_=50,
            to=300,
            length=200
        )
        self.width_slider_eff.pack(side="left", padx=5)
        self.width_slider_eff.set(100)

        ttk.Label(control_frame, text="Длина усиления (%):").pack(side="left", padx=5)
        self.length_slider_eff = ttk.Scale(
            control_frame,
            from_=0,
            to=100,
            length=200
        )
        self.length_slider_eff.pack(side="left", padx=5)
        self.length_slider_eff.set(30)

        # Кнопка для применения параметров из слайдеров
        ttk.Button(
            control_frame,
            text="Применить параметры",
            command=self.apply_slider_values
        ).pack(side="left", padx=10)

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
        """Создает вкладку с эпюрами с прокруткой и правильными размерами"""
        # Основной контейнер
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True)

        self.epure_selection_var = tk.StringVar()
        self.epure_selection = ttk.Combobox(...)

            # Создаем Combobox для выбора варианта
        self.epure_selection = ttk.Combobox(
            control_frame,
            textvariable=self.epure_selection_var,
            state="readonly",
            width=40
        )
        self.epure_selection.pack(side="left", padx=5, expand=True, fill="x")
        self.epure_selection.bind("<<ComboboxSelected>>", self.update_epures)

        # 1. Панель управления параметрами
        control_frame = ttk.LabelFrame(main_frame, text="Параметры эпюр")
        control_frame.pack(fill="x", padx=5, pady=5)

        # Выбор варианта из таблицы (широкий выпадающий список)
        ttk.Label(control_frame, text="Выберите вариант:").pack(side="left", padx=5)
        self.epure_selection_var = tk.StringVar()
        self.epure_selection = ttk.Combobox(
            control_frame,
            textvariable=self.epure_selection_var,
            state="readonly",
            width=40  # Увеличиваем ширину combobox
        )
        self.epure_selection.pack(side="left", padx=5, expand=True, fill="x")
        self.epure_selection.bind("<<ComboboxSelected>>", self.update_epures)

        # Кнопка обновления
        ttk.Button(
            control_frame,
            text="Построить эпюры",
            command=self.update_epures
        ).pack(side="left", padx=5)

        # 2. Область с прокруткой для графиков
        canvas_container = ttk.Frame(main_frame)
        canvas_container.pack(fill="both", expand=True)

        # Настройка системы прокрутки
        self.epure_canvas = tk.Canvas(canvas_container)
        scrollbar = ttk.Scrollbar(
            canvas_container,
            orient="vertical",
            command=self.epure_canvas.yview
        )
        self.epure_scrollable_frame = ttk.Frame(self.epure_canvas)

        # Конфигурация прокрутки
        self.epure_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.epure_canvas.configure(
                scrollregion=self.epure_canvas.bbox("all")
            )
        )

        # Связывание элементов
        self.epure_canvas.create_window(
            (0, 0),
            window=self.epure_scrollable_frame,
            anchor="nw"
        )
        self.epure_canvas.configure(yscrollcommand=scrollbar.set)

        # Прокрутка колесом мыши
        self.epure_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.epure_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        )

        # Размещение элементов
        self.epure_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 3. Создание графиков внутри прокручиваемой области
        self.figure_epure = Figure(figsize=(10, 12), dpi=100)
        
        # Распределение графиков (3x2)
        self.epure_m_plot = self.figure_epure.add_subplot(321)
        self.epure_q_plot = self.figure_epure.add_subplot(322)
        self.epure_deflection_plot = self.figure_epure.add_subplot(323)
        self.epure_section_plot = self.figure_epure.add_subplot(324)
        self.epure_stress_plot = self.figure_epure.add_subplot(325)

        # Встраивание графиков
        self.canvas_epure = FigureCanvasTkAgg(
            self.figure_epure,
            master=self.epure_scrollable_frame
        )
        self.canvas_epure.get_tk_widget().pack(fill="both", expand=True)
        self.figure_epure.tight_layout(pad=3.0)
        
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
        """Расчет кривой прогиба"""
        try:
            width = width_mm / 1000
            thickness = thickness_mm / 1000
            L_lenta = (length_percent / 100) * self.slab_params['span_length']

            carbon_area = width * thickness if thickness_mm > 0 else 0
            I = self.calculate_inertia(carbon_area, thickness)

            L = self.slab_params['span_length']
            q = self.slab_params['q_load']
            E = self.slab_params['E_concrete']

            # Точки для расчета прогиба
            x_points = np.linspace(0, L, n_points)
            deflections = []

            for x in x_points:
                def integrand(xi):
                    M = self.calculate_moment(xi, L, q)
                    M_bar = xi * (L - x) / L if xi <= x else x * (L - xi) / L
                    return M * M_bar / (E * I)

                if length_percent >= 100:
                    deflection, _ = quad(integrand, 0, L)
                else:
                    a = (L - L_lenta) / 2
                    b = L - a
                    part1, _ = quad(integrand, 0, a)
                    part2, _ = quad(integrand, a, b)
                    part3, _ = quad(integrand, b, L)
                    deflection = part1 + part2 + part3

                deflections.append(deflection * 1000)  # в мм

            return x_points, np.array(deflections)

        except Exception as e:
            raise RuntimeError(f"Ошибка расчета кривой прогиба: {str(e)}")

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

    def update_efficiency_graph(self):
        if not self.graph_data:
            return

        try:
            width = int(float(self.width_slider_eff.get()))
            length = int(float(self.length_slider_eff.get()))

            if width != self.current_width or length != self.current_length:
                self.current_width = width
                self.current_length = length
                self.width_var.set(str(width))
                self.length_var.set(str(length))
                self.calculate()
                return

            thicknesses = [d['thickness'] for d in self.graph_data]
            efficiencies = [d['efficiency']
                for d in self.graph_data if d['efficiency'] > 0]
            eff_thicknesses = [d['thickness']
                for d in self.graph_data if d['efficiency'] > 0]

            self.efficiency_plot.clear()

            if eff_thicknesses:
                self.efficiency_plot.plot(eff_thicknesses, efficiencies, 'g-o')
                self.efficiency_plot.set_title(
                    f"Эффективность усиления (ширина: {width}мм, длина: {length}%)")
                self.efficiency_plot.set_xlabel("Толщина ленты (мм)")
                self.efficiency_plot.set_ylabel("Эффективность (%/м²)")
                self.efficiency_plot.grid(True)

            self.figure_efficiency.tight_layout()
            self.canvas_efficiency.draw()

        except Exception as e:
            messagebox.showerror(
        "Ошибка", f"Ошибка обновления графика эффективности: {str(e)}")

    def update_epures(self, event=None):
        """Обновляет все эпюры на основе выбранного варианта"""
        try:
            if not hasattr(self, 'graph_data') or not self.graph_data:
                messagebox.showwarning("Предупреждение", "Сначала выполните расчет на вкладке 1")
                return

            # Получаем выбранный вариант
            selection = self.epure_selection.current()
            if selection < 0:
                selection = 0
                
            data = self.graph_data[selection]
            layers = data['layers']
            thickness_mm = data['thickness']
            width = self.current_width

            # Очищаем все графики
            for plot in [self.epure_m_plot, self.epure_q_plot, 
                        self.epure_deflection_plot, self.epure_section_plot,
                        self.epure_stress_plot]:
                plot.clear()

            # Расчет и отрисовка эпюр
            L = self.slab_params['span_length']
            q = self.slab_params['q_load']
            x = np.linspace(0, L, 100)
            
            # Эпюра моментов
            M = [self.calculate_moment(xi, L, q) for xi in x]
            self.epure_m_plot.plot(x, M, 'b-')
            self.epure_m_plot.set_title("Эпюра изгибающего момента M")
            self.epure_m_plot.grid(True)
            
            # Эпюра поперечных сил
            Q = [self.calculate_shear_force(xi, L, q) for xi in x]
            self.epure_q_plot.plot(x, Q, 'r-')
            self.epure_q_plot.set_title("Эпюра поперечной силы Q")
            self.epure_q_plot.grid(True)
            
            # Эпюра прогибов
            x_def, deflection = self.calculate_deflection_curve(width, thickness_mm, self.current_length)
            self.epure_deflection_plot.plot(x_def, deflection, 'g-')
            self.epure_deflection_plot.set_title("Эпюра прогибов")
            self.epure_deflection_plot.grid(True)
            
            # Схема сечения
            self.draw_section_plot()
            
            # Эпюра напряжений
            self.draw_stress_plot(thickness_mm)
            
            self.canvas_epure.draw()
            self.epure_canvas.yview_moveto(0)  # Прокрутка в начало
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка построения эпюр: {str(e)}")
    
    def draw_section_plot(self):
        """Отрисовка поперечного сечения плиты с усилением"""
        try:
            ax = self.epure_section_plot
            ax.clear()
            
            # Параметры плиты
            width = self.slab_params['width']
            height = self.slab_params['height']
            r = self.slab_params['void_radius']
            h_rect = self.slab_params['void_rect_height']
            n_voids = self.slab_params['n_voids']
            
            # Параметры усиления
            carbon_thickness = self.current_thickness / 1000 if hasattr(self, 'current_thickness') else 0
            carbon_width = self.current_width / 1000 if hasattr(self, 'current_width') else 0
            tape_count = self.current_tape_count if hasattr(self, 'current_tape_count') else 1
            
            # 1. Рисуем ленты усиления (если есть)
            if carbon_thickness > 0 and carbon_width > 0:
                if tape_count > 1:
                    # Расчет параметров для нескольких лент
                    total_space = width - carbon_width * tape_count
                    spacing = total_space / (tape_count + 1)
                    
                    for i in range(tape_count):
                        x_pos = spacing * (i + 1) + carbon_width * i
                        carbon_patch = plt.Rectangle(
                            (x_pos, -carbon_thickness), carbon_width, carbon_thickness,
                            fill=True, color='blue', alpha=0.5, linewidth=1
                        )
                        ax.add_patch(carbon_patch)
                else:
                    # Одиночная лента по центру
                    carbon_patch = plt.Rectangle(
                        (width/2 - carbon_width/2, -carbon_thickness),
                        carbon_width, carbon_thickness,
                        fill=True, color='blue', alpha=0.5, linewidth=1
                    )
                    ax.add_patch(carbon_patch)
            
            # 2. Рисуем контур плиты
            slab_patch = plt.Rectangle(
                (0, -carbon_thickness), width, height + carbon_thickness,
                fill=False, linewidth=2, edgecolor='black'
            )
            ax.add_patch(slab_patch)
            
            # 3. Рисуем пустоты
            void_spacing = width / (n_voids + 1)
            for i in range(n_voids):
                x_center = void_spacing * (i + 1)
                y_top = height/2 + h_rect/2 - carbon_thickness
                y_bottom = height/2 - h_rect/2 - carbon_thickness
                
                # Верхний полукруг
                ax.add_patch(patches.Wedge(
                    (x_center, y_top), r, 0, 180,
                    fill=False, color='red', linewidth=1
                ))
                
                # Центральный прямоугольник
                ax.add_patch(plt.Rectangle(
                    (x_center - r, y_bottom), 2*r, h_rect,
                    fill=False, color='red', linewidth=1
                ))
                
                # Нижний полукруг
                ax.add_patch(patches.Wedge(
                    (x_center, y_bottom), r, 180, 360,
                    fill=False, color='red', linewidth=1
                ))
            
            # Настройка области просмотра
            x_center = width / 2
            y_center = (height - carbon_thickness) / 2
            view_size = max(width, height + carbon_thickness) * self.section_zoom
            padding = max(width, height) * 0.1 / self.section_zoom
            
            ax.set_xlim(x_center - view_size/2 - padding, x_center + view_size/2 + padding)
            ax.set_ylim(y_center - view_size/2 - padding, y_center + view_size/2 + padding)
            
            ax.set_title(f"Схема сечения [Масштаб: {self.section_zoom:.1f}x] (+/-)")
            ax.set_aspect('equal')
            ax.grid(True, linestyle=':', alpha=0.7)
            
        except Exception as e:
            print(f"Ошибка при отрисовке сечения: {e}")
            messagebox.showerror("Ошибка", f"Ошибка при отрисовке сечения: {str(e)}")
            
    def draw_stress_plot(self, thickness_mm):
        """Эпюра нормальных напряжений с учетом усиления"""
        try:
            ax = self.epure_stress_plot
            ax.clear()
            
            height = self.slab_params['height']
            thickness = thickness_mm / 1000
            
            # Расчет максимального момента
            L = self.slab_params['span_length']
            q = self.slab_params['q_load']
            M_max = q * L**2 / 8
            
            # Параметры усиления
            carbon_width = self.current_width / 1000
            carbon_thickness = thickness
            carbon_area = carbon_width * carbon_thickness
            
            # Момент инерции составного сечения
            I_total = self.calculate_inertia(carbon_area, carbon_thickness)
            
            # Коэффициент приведения
            n = self.slab_params['E_carbon'] / self.slab_params['E_concrete']
            
            # Напряжения по высоте сечения
            y_points = np.linspace(-carbon_thickness, height, 100)
            stresses = []
            
            for y in y_points:
                if y >= 0:  # Бетонная часть
                    sigma = M_max * (y - (height - carbon_thickness)/2) / I_total
                else:  # Углепластиковая часть
                    sigma = n * M_max * (y - (height - carbon_thickness)/2) / I_total
                stresses.append(sigma / 1e6)  # Переводим в МПа
            
            # Рисуем эпюру
            line, = ax.plot(stresses, y_points, 'm-', linewidth=2, label='Эпюра напряжений')
            ax.fill_betweenx(y_points, stresses, 0, color='m', alpha=0.2)
            
            # Линия раздела материалов
            divider = ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)
            
            # Подписи
            max_stress = max(abs(s) for s in stresses)
            ax.annotate(f'σmax = {max_stress:.2f} МПа',
                       xy=(max_stress, height/2),
                       xytext=(max_stress*1.1, height*0.7),
                       arrowprops=dict(arrowstyle="->"))
            
            # Легенда
            ax.legend(handles=[line, divider], 
                    labels=['Эпюра напряжений', 'Граница бетон/углепластик'],
                    loc='upper right')
            
            ax.set_title("Эпюра нормальных напряжений с учетом усиления")
            ax.set_xlabel("Напряжение, МПа")
            ax.set_ylabel("Высота сечения, м")
            ax.grid(True)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка построения эпюры напряжений: {str(e)}")

    def _plot_moment_epure(self, x, M):
        """Отрисовка эпюры моментов"""
        max_moment = max(M)
        max_moment_x = x[np.argmax(M)]
        self.epure_m_plot.plot(x, M, 'b-', linewidth=2)
        self.epure_m_plot.fill_between(x, M, color='b', alpha=0.2)
        self.epure_m_plot.annotate(f'Mmax = {max_moment:.2f} Н·м', 
                                 xy=(max_moment_x, max_moment),
                                 xytext=(max_moment_x+1, max_moment*0.8),
                                 arrowprops=dict(arrowstyle="->"))
        self.epure_m_plot.set_title("Эпюра изгибающего момента M")
        self.epure_m_plot.set_ylabel("M, Н·м")
        self.epure_m_plot.grid(True)

    def _plot_shear_epure(self, x, Q):
        """Отрисовка эпюры поперечных сил"""
        max_shear = max(abs(q) for q in Q)
        max_shear_x = x[np.argmax(np.abs(Q))]
        self.epure_q_plot.plot(x, Q, 'r-', linewidth=2)
        self.epure_q_plot.fill_between(x, Q, color='r', alpha=0.2)
        self.epure_q_plot.annotate(f'Qmax = {max_shear:.2f} Н',
                                 xy=(max_shear_x, Q[np.argmax(np.abs(Q))]),
                                 xytext=(max_shear_x+1, max_shear*0.8),
                                 arrowprops=dict(arrowstyle="->"))
        self.epure_q_plot.set_title("Эпюра поперечной силы Q")
        self.epure_q_plot.set_ylabel("Q, Н")
        self.epure_q_plot.grid(True)

    def _plot_deflection_epure(self, x, deflection):
        """Отрисовка эпюры прогибов"""
        max_deflection = max(deflection)
        max_deflection_x = x[np.argmax(deflection)]
        self.epure_deflection_plot.plot(x, deflection, 'g-', linewidth=2)
        self.epure_deflection_plot.annotate(f'fmax = {max_deflection:.2f} мм',
                                          xy=(max_deflection_x, max_deflection),
                                          xytext=(max_deflection_x+1, max_deflection*0.8),
                                          arrowprops=dict(arrowstyle="->"))
        self.epure_deflection_plot.set_title("Эпюра прогибов")
        self.epure_deflection_plot.set_xlabel("Длина пролета, м")
        self.epure_deflection_plot.set_ylabel("Прогиб, мм")
        self.epure_deflection_plot.grid(True)
        
    def update_info(self):
        """Обновление информационной панели с текущими параметрами системы"""
        try:
            # Очищаем текстовое поле и разрешаем редактирование
            self.info_text.config(state="normal")
            self.info_text.delete(1.0, tk.END)
            
            # Формируем информацию о плите
            slab_info = [
                "=== Параметры плиты ===",
                f"Ширина: {self.slab_params['width']:.3f} м",
                f"Высота: {self.slab_params['height']:.3f} м",
                f"Пролет: {self.slab_params['span_length']:.2f} м",
                f"Нагрузка: {self.slab_params['q_load']:.2f} Н/м",
                f"Пустоты: {self.slab_params['n_voids']} шт",
                "",
                "=== Параметры усиления ===",
                f"Ширина ленты: {getattr(self, 'current_width', 100)} мм",
                f"Количество лент: {getattr(self, 'current_tape_count', 1)}",
                f"Длина усиления: {getattr(self, 'current_length', 30)}%",
                f"Толщина слоя: {self.LAYER_THICKNESS_MM:.1f} мм",
                "",
                "=== Материалы ===",
                f"Модуль бетона: {self.slab_params['E_concrete']/1e9:.1f} ГПа",
                f"Модуль углепластика: {self.slab_params['E_carbon']/1e9:.1f} ГПа"
            ]
            
            # Добавляем результаты расчетов, если они есть
            if hasattr(self, 'base_deflection'):
                results_info = [
                    "",
                    "=== Результаты ===",
                    f"Базовый прогиб: {self.base_deflection:.2f} мм"
                ]
                
                if hasattr(self, 'graph_data') and self.graph_data:
                    last_result = self.graph_data[-1]
                    results_info.extend([
                        f"Текущий прогиб: {last_result['deflection']:.2f} мм",
                        f"Снижение: {last_result['reduction']:.1f}%",
                        f"Эффективность: {last_result['efficiency']:.2f} %/м²"
                    ])
                
                slab_info.extend(results_info)
            
            # Вставляем текст и форматируем
            self.info_text.insert(tk.END, "\n".join(slab_info))
            
            # Выделяем заголовки жирным
            for i, line in enumerate(slab_info):
                if line.startswith("==="):
                    start = f"1.{i+1}"
                    end = f"{start}+{len(line)}c"
                    self.info_text.tag_add("bold", start, end)
            
            # Настраиваем теги для форматирования
            self.info_text.tag_configure("bold", font=('TkDefaultFont', 10, 'bold'))
            
            # Запрещаем редактирование
            self.info_text.config(state="disabled")
            
        except Exception as e:
            # В случае ошибки выводим сообщение в консоль
            print(f"Ошибка обновления информации: {str(e)}")
            # Пытаемся показать хотя бы базовую информацию
            self.info_text.config(state="normal")
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, "Ошибка загрузки данных")
            self.info_text.config(state="disabled")

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