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
        self.root.title("Расчет усиления углепластиком")
        self.root.geometry("1800x1200")

        # Константы
        self.LAYER_THICKNESS = 0.0004

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
        self.thickness_options = list(range(0, 11))
        self.length_options = list(range(0, 101, 5))

        # Переменные для графиков
        self.current_width = 100
        self.current_length = 30
        self.current_thickness = 0
        self.graph_data = []
        self.base_deflection = None

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

        # Привязка клавиш масштабирования
        self.section_zoom = 1.0  # Инициализация переменной масштаба
        # Привязка клавиш
        self.root.bind('<plus>', self.zoom_in)
        self.root.bind('<minus>', self.zoom_out)
        self.root.bind('<KP_Add>', self.zoom_in)
        self.root.bind('<KP_Subtract>', self.zoom_out)

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
        """Расчет прогиба без усиления"""
        try:
            self.base_deflection = self.calculate_deflection(0, 0, 0)
        except Exception as e:
            messagebox.showerror(
    "Ошибка", f"Не удалось рассчитать базовый прогиб: {str(e)}")
            self.base_deflection = 0

    def create_tab1_content(self, parent):
        # Панель параметров
        param_frame = ttk.LabelFrame(parent, text="Параметры усиления")
        param_frame.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=5,
    pady=5,
     rowspan=2)

        # Элементы управления
        ttk.Label(
    param_frame,
    text="Ширина ленты (мм):").grid(
        row=0,
        column=0,
        padx=5,
         pady=5)
        self.width_var = tk.StringVar(value="100")
        width_combobox = ttk.Combobox(param_frame, textvariable=self.width_var,
                                    values=self.width_options, state="readonly")
        width_combobox.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(
    param_frame,
    text="Длина усиления (%):").grid(
        row=1,
        column=0,
        padx=5,
         pady=5)
        self.length_var = tk.StringVar(value="30")
        length_combobox = ttk.Combobox(param_frame, textvariable=self.length_var,
                                      values=self.length_options, state="readonly")
        length_combobox.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(
    param_frame,
    text="Рассчитать",
    command=self.calculate).grid(
        row=2,
        column=0,
        columnspan=2,
         pady=10)

        # Таблица результатов
        result_frame = ttk.LabelFrame(
    parent, text="Результаты для всех толщин")
        result_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        columns = (
    "thickness",
    "deflection",
    "reduction",
    "layers",
    "area",
     "efficiency")
        self.tree = ttk.Treeview(
    result_frame,
    columns=columns,
    show="headings",
     height=15)

        # Настройка колонок
        self.tree.heading("thickness", text="Толщина (мм)")
        self.tree.heading("deflection", text="Прогиб (мм)")
        self.tree.heading("reduction", text="Снижение (%)")
        self.tree.heading("layers", text="Слоёв")
        self.tree.heading("area", text="Площадь (м²)")
        self.tree.heading("efficiency", text="Эффективность (%/м²)")

        for col in columns:
            self.tree.column(col, width=100, anchor="center")

        scrollbar = ttk.Scrollbar(
    result_frame,
    orient="vertical",
     command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Информационная панель
        info_frame = ttk.LabelFrame(parent, text="Параметры системы")
        info_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self.info_text = tk.Text(info_frame, height=10, width=40)
        self.info_text.pack(fill="both", expand=True)

        # Графики на первой вкладке
        graph_frame = ttk.LabelFrame(parent, text="График прогиба")
        graph_frame.grid(
    row=2,
    column=0,
    columnspan=2,
    sticky="nsew",
    padx=5,
     pady=5)

        # Создаем фигуру для графика прогиба
        self.figure_deflection = Figure(figsize=(10, 4), dpi=100)
        self.deflection_plot = self.figure_deflection.add_subplot(111)

        self.canvas_deflection = FigureCanvasTkAgg(
            self.figure_deflection, master=graph_frame)
        self.canvas_deflection.get_tk_widget().pack(fill="both", expand=True)

        # Настройка размеров
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        parent.rowconfigure(2, weight=3)

    def create_tab2_content(self, parent):
        # График эффективности
        efficiency_frame = ttk.LabelFrame(parent, text="График эффективности")
        efficiency_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Создаем фигуру для графика эффективности
        self.figure_efficiency = Figure(figsize=(10, 4), dpi=100)
        self.efficiency_plot = self.figure_efficiency.add_subplot(111)

        self.canvas_efficiency = FigureCanvasTkAgg(
    self.figure_efficiency, master=efficiency_frame)
        self.canvas_efficiency.get_tk_widget().pack(fill="both", expand=True)

        # Панель управления для графика эффективности
        control_frame = ttk.Frame(efficiency_frame)
        control_frame.pack(fill="x", pady=5)

        # Ползунок для ширины ленты
        ttk.Label(
    control_frame,
    text="Ширина ленты (мм):").pack(
        side="left",
         padx=5)
        self.width_slider_eff = ttk.Scale(control_frame, from_=50, to=300,
                                        command=lambda e: self.update_efficiency_graph())
        self.width_slider_eff.pack(side="left", fill="x", expand=True, padx=5)
        self.width_slider_eff.set(100)

        # Ползунок для длины усиления
        ttk.Label(
    control_frame,
    text="Длина усиления (%):").pack(
        side="left",
         padx=5)
        self.length_slider_eff = ttk.Scale(control_frame, from_=0, to=100,
                                         command=lambda e: self.update_efficiency_graph())
        self.length_slider_eff.pack(side="left", fill="x", expand=True, padx=5)
        self.length_slider_eff.set(30)

    def create_tab3_content(self, parent):
        """Создает вкладку с эпюрами (M, Q, прогибов, сечений и напряжений) с прокруткой"""
        # Основной контейнер
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True)

        # 1. Панель управления параметрами
        control_frame = ttk.LabelFrame(main_frame, text="Параметры эпюр")
        control_frame.pack(fill="x", padx=5, pady=5)

        # Выбор толщины усиления
        ttk.Label(
    control_frame,
    text="Толщина усиления (мм):").pack(
        side="left",
         padx=5)
        self.thickness_var_epure = tk.StringVar()
        self.thickness_combobox_epure = ttk.Combobox(
            control_frame,
            textvariable=self.thickness_var_epure,
            values=self.thickness_options[1:],
            state="readonly"
        )
        self.thickness_combobox_epure.pack(side="left", padx=5)
        self.thickness_combobox_epure.bind(
    "<<ComboboxSelected>>", self.update_epures)

        # Кнопка обновления
        ttk.Button(
    control_frame,
    text="Построить эпюры",
    command=self.update_epures).pack(
        side="left",
         padx=5)

        # 2. Область с прокруткой для графиков
        container = ttk.Frame(main_frame)
        container.pack(fill="both", expand=True)

        # Настройка системы прокрутки
        self.epure_canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(
    container,
    orient="vertical",
     command=self.epure_canvas.yview)
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
    (0, 0), window=self.epure_scrollable_frame, anchor="nw")
        self.epure_canvas.configure(yscrollcommand=scrollbar.set)

        # Прокрутка колесом мыши
        self.epure_canvas.bind_all("<MouseWheel>",
            lambda e: self.epure_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # Размещение элементов
        self.epure_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 3. Создание графиков внутри прокручиваемой области
        self.figure_epure = Figure(figsize=(12, 14), dpi=100)

        # Распределение графиков:
        # 3.1 Эпюра изгибающих моментов
        self.epure_m_plot = self.figure_epure.add_subplot(321)
        # 3.2 Эпюра поперечных сил
        self.epure_q_plot = self.figure_epure.add_subplot(322)
        # 3.3 Эпюра прогибов
        self.epure_deflection_plot = self.figure_epure.add_subplot(323)
        # 3.4 Схема сечения (с лентой усиления)
        self.epure_section_plot = self.figure_epure.add_subplot(325)
        # 3.5 Эпюра напряжений (со ступенькой в углепластике)
        self.epure_stress_plot = self.figure_epure.add_subplot(326)

        # Встраивание графиков в интерфейс
        self.canvas_epure = FigureCanvasTkAgg(
            self.figure_epure,
            master=self.epure_scrollable_frame
        )
        self.canvas_epure.get_tk_widget().pack(fill="both", expand=True)
        self.figure_epure.tight_layout()

    def calculate_inertia(self, carbon_area=0, carbon_thickness=0):
        """Пересчитанный метод с правильной геометрией пустот"""
        # Момент инерции сплошного прямоугольника
        I_solid = (self.slab_params['width'] *
                   self.slab_params['height']**3) / 12

        # Параметры пустоты
        r = self.slab_params['void_radius']
        h_rect = self.slab_params['void_rect_height']
        n_voids = self.slab_params['n_voids']

        # Момент инерции одной составной пустоты:
        # 1. Полукруг (верхний)
        I_semicircle_top = (math.pi * r**4) / 8

        # 2. Прямоугольник (центральная часть)
        I_rect = (2 * r * h_rect**3) / 12

        # 3. Полукруг (нижний)
        I_semicircle_bottom = (math.pi * r**4) / 8

        # Суммарный момент инерции одной пустоты
        I_one_void = I_semicircle_top + I_rect + I_semicircle_bottom

        # Общий момент инерции всех пустот
        total_I_void = n_voids * I_one_void

        # Момент инерции бетонного сечения
        I_concrete = I_solid - total_I_void

        # Учет усиления углеволокном
        if carbon_area > 0 and carbon_thickness > 0:
            d = (self.slab_params['height'] + carbon_thickness) / 2
            n = self.slab_params['E_carbon'] / self.slab_params['E_concrete']
            I_total = I_concrete + n * carbon_area * d**2
            return I_total

        return I_concrete

    def calculate_deflection(self, width_mm, thickness_mm, length_percent):
        try:
            width = width_mm / 1000
            thickness = thickness_mm / 1000
            L_lenta = (length_percent / 100) * self.slab_params['span_length']

            carbon_area = width * thickness if thickness_mm > 0 else 0
            I = self.calculate_inertia(carbon_area, thickness)

            def integrand(x):
                M = (self.slab_params['q_load'] * self.slab_params['span_length'] * x / 2) - \
                    (self.slab_params['q_load'] * x**2 / 2)
                M_bar = x / 2 if x <= self.slab_params['span_length'] / 2 else \
                       (self.slab_params['span_length'] - x) / 2
                return M * M_bar / (self.slab_params['E_concrete'] * I)

            if length_percent >= 100:
                result, _ = quad(integrand, 0, self.slab_params['span_length'])
                return result * 1000

            a = (self.slab_params['span_length'] - L_lenta) / 2
            b = self.slab_params['span_length'] - a

            I_unreinforced = self.calculate_inertia(0, 0)

            def integrand_unreinforced(x):
                M = (self.slab_params['q_load'] * self.slab_params['span_length'] * x / 2) - \
                    (self.slab_params['q_load'] * x**2 / 2)
                M_bar = x / 2 if x <= self.slab_params['span_length'] / 2 else \
                       (self.slab_params['span_length'] - x) / 2
                return M * M_bar / \
                    (self.slab_params['E_concrete'] * I_unreinforced)

            part1, _ = quad(integrand_unreinforced, 0, a)
            part2, _ = quad(integrand, a, b)
            part3, _ = quad(integrand_unreinforced, b,
                            self.slab_params['span_length'])

            return (part1 + part2 + part3) * 1000

        except Exception as e:
            raise RuntimeError(f"Ошибка расчета: {str(e)}")

    def calculate_moment(self, x, L, q):
        """Расчет изгибающего момента в сечении x"""
        return (q * L * x / 2) - (q * x**2 / 2)

    def calculate_shear_force(self, x, L, q):
        """Расчет поперечной силы в сечении x"""
        return (q * L / 2) - (q * x)

    def calculate_deflection_curve(
        self, width_mm, thickness_mm, length_percent, n_points=50):
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
        try:
            self.tree.delete(*self.tree.get_children())
            self.graph_data = []
            
            width = int(self.width_var.get())
            length = int(self.length_var.get())
            self.current_width = width
            self.current_length = length
            
            self.width_slider_eff.set(width)
            self.length_slider_eff.set(length)
            
            base_deflection = self.calculate_deflection(0, 0, 0)
            
            for thickness in self.thickness_options:
                try:
                    if thickness == 0:
                        continue
                        
                    deflection = self.calculate_deflection(width, thickness, length)
                    reduction = ((base_deflection - deflection) / base_deflection * 100) if base_deflection != 0 else 0
                    layers = ceil(thickness / 0.4)
                    L_lenta = (length / 100) * self.slab_params['span_length']
                    area_per_layer = (width/1000) * L_lenta
                    total_area = area_per_layer * layers
                    
                    efficiency = reduction / total_area if total_area > 0 else 0
                    
                    self.tree.insert("", "end", values=(
                        thickness,
                        f"{deflection:.2f}",
                        f"{reduction:.1f}" if reduction > 0 else "0.0",
                        layers,
                        f"{total_area:.4f}",
                        f"{efficiency:.4f}" if efficiency > 0 else "-"
                    ))
                    
                    self.graph_data.append({
                        'thickness': thickness,
                        'deflection': deflection,
                        'reduction': reduction,
                        'efficiency': efficiency
                    })
                    
                except Exception as e:
                    messagebox.showwarning("Ошибка", f"Для толщины {thickness} мм: {str(e)}")
            
            self.update_info()
            self.update_deflection_graph()
            self.update_efficiency_graph()
            
            # Строка 698:
            self.thickness_combobox_epure['values'] = [d['thickness'] for d in self.graph_data]
            if self.graph_data:
                self.thickness_var_epure.set(self.graph_data[0]['thickness'])
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка расчета: {str(e)}")
    
    def update_deflection_graph(self):
        if not self.graph_data:
            return

        try:
            thicknesses = [d['thickness'] for d in self.graph_data]
            deflections = [d['deflection'] for d in self.graph_data]

            self.deflection_plot.clear()

            # Добавляем горизонтальную линию для базового прогиба
            self.deflection_plot.axhline(y=self.base_deflection, color='r', linestyle='--',
                                       label=f'Без усиления: {self.base_deflection:.2f} мм')

            # График прогиба
            self.deflection_plot.plot(
    thicknesses, deflections, 'b-o', label='С усилением')
            self.deflection_plot.set_title(
                f"Зависимость прогиба от толщины (ширина: {self.current_width}мм, длина: {self.current_length}%)")
            self.deflection_plot.set_xlabel("Толщина ленты (мм)")
            self.deflection_plot.set_ylabel("Прогиб (мм)")
            self.deflection_plot.legend()
            self.deflection_plot.grid(True)

            self.figure_deflection.tight_layout()
            self.canvas_deflection.draw()

        except Exception as e:
            messagebox.showerror(
    "Ошибка", f"Ошибка обновления графика прогиба: {str(e)}")

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
        """Обновляет все эпюры с обработкой ошибок"""
        try:
            if not self.graph_data:
                messagebox.showwarning(
        "Предупреждение", "Сначала выполните расчет")
                return

            thickness = int(self.thickness_var_epure.get())
            self.current_thickness = thickness

            L = self.slab_params['span_length']
            q = self.slab_params['q_load']
            x = np.linspace(0, L, 100)

            # Расчет моментов и сил
            M = [self.calculate_moment(xi, L, q) for xi in x]
            Q = [self.calculate_shear_force(xi, L, q) for xi in x]

            # Расчет прогибов
            x_def, deflection = self.calculate_deflection_curve(
                self.current_width, thickness, self.current_length)

            # Сглаживание кривой
            if len(x_def) > 3:
                spline = make_interp_spline(x_def, deflection, k=3)
                x_smooth = np.linspace(0, L, 200)
                deflection_smooth = spline(x_smooth)
            else:
                x_smooth = x_def
                deflection_smooth = deflection

            # Очистка графиков
            for plot in [self.epure_m_plot, self.epure_q_plot,
                        self.epure_deflection_plot, self.epure_section_plot,
                        self.epure_stress_plot]:
                plot.clear()

            # Построение эпюр
            self._plot_moment_epure(x, M)
            self._plot_shear_epure(x, Q)
            self._plot_deflection_epure(x_smooth, deflection_smooth)
            self.draw_section_plot()
            self.draw_stress_plot(thickness)

            self.figure_epure.tight_layout()
            self.canvas_epure.draw()
            self.epure_canvas.yview_moveto(0)

        except ValueError as ve:
            messagebox.showerror(
            "Ошибка значения",
            f"Некорректные данные: {str(ve)}")
        except RuntimeError as re:
            messagebox.showerror(
            "Ошибка расчета",
            f"Ошибка вычислений: {str(re)}")
        except Exception as e:
            messagebox.showerror(
            "Неизвестная ошибка",
            f"Произошла непредвиденная ошибка: {str(e)}")
            import traceback
            with open("error_log.txt", "a") as f:
                traceback.print_exc(file=f)

    def draw_section_plot(self):
        """Улучшенное отображение сечения с динамическим масштабированием"""
        try:
            if not hasattr(self, 'epure_section_plot'):
                return
            
            ax = self.epure_section_plot
            ax.clear()
            
            # Параметры плиты
            width = self.slab_params['width']
            height = self.slab_params['height']
            r = self.slab_params['void_radius']
            h_rect = self.slab_params['void_rect_height']
            n_voids = self.slab_params['n_voids']
            
            # Параметры усиления
            carbon_width = self.current_width / 1000 if self.current_thickness > 0 else 0
            carbon_thickness = self.current_thickness / 1000 if self.current_thickness > 0 else 0
            
            # 1. Рисуем ленту усиления (если есть)
            if self.current_thickness > 0:
                carbon_patch = plt.Rectangle(
                    (width/2 - carbon_width/2, -carbon_thickness),
                    carbon_width, carbon_thickness,
                    fill=True, color='blue', alpha=0.5, linewidth=1
                )
                ax.add_patch(carbon_patch)
                
                # Компактная подпись с выноской
                ax.annotate(
                    f"{self.current_width}×{self.current_thickness} мм",
                    xy=(width/2, -carbon_thickness/2),
                    xytext=(width/2, -carbon_thickness*1.5),
                    ha='center', va='top', fontsize=8,
                    arrowprops=dict(arrowstyle="-", color='blue', linewidth=0.5),
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7)
                )
            
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
        self.info_text.delete(1.0, tk.END)
        info = [
            "Параметры плиты:",
            f"Ширина: {self.slab_params['width']} м",
            f"Высота: {self.slab_params['height']} м",
            f"Пролет: {self.slab_params['span_length']} м",
            f"Нагрузка: {self.slab_params['q_load']} Н/м",
            f"Количество пустот: {self.slab_params['n_voids']}",
            "",
            "Базовый прогиб без усиления:",
            f"{self.base_deflection:.2f} мм",
            "",
            "Текущие параметры усиления:",
            f"Ширина ленты: {self.current_width} мм",
            f"Длина усиления: {self.current_length}%",
            "",
            "Параметры материала:",
            f"Модуль упругости бетона: {self.slab_params['E_concrete']/1e9:.1f} ГПа",
            f"Модуль упругости углепластика: {self.slab_params['E_carbon']/1e9:.1f} ГПа",
            f"Толщина одного слоя: {self.LAYER_THICKNESS*1000:.1f} мм"
        ]
        self.info_text.insert(tk.END, "\n".join(info))

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