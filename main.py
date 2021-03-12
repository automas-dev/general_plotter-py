#!/usr/bin/env python3

import os
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from tkinter import messagebox
import csv
from pathlib import Path

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

from sbframe import VerticalScrolledFrame


class GraphControl(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self._fig = Figure(figsize=(5, 4), dpi=100)

        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._toolbar = NavigationToolbar2Tk(self._canvas, self)
        self._toolbar.update()
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._canvas.mpl_connect('key_press_event', self._on_key_press)

    def _on_key_press(self, event):
        key_press_handler(event, self._canvas, self._toolbar)

    def add_subplot(self, *args, **kwargs):
        return self._fig.add_subplot(*args, **kwargs)


class OptionDialog:
    def __init__(self, master, text, options):
        top = tk.Toplevel(master)
        top.title(text)

        self._vars = []
        self._top = top
        self._res = False

        pad = {'padx': 4, 'pady': 4}

        ttk.Label(top, text=text).grid(row=0, column=0, columnspan=2, **pad)

        f = VerticalScrolledFrame(top)
        f.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW)

        for i, name in enumerate(options):
            var = tk.BooleanVar()
            self._vars.append((name, var))
            ttk.Checkbutton(f.interior, text=name, variable=var).pack(anchor=tk.W, **pad)

        row = len(options) + 1
        ttk.Button(top, text='Ok', command=self._ok).grid(row=row, column=0, **pad)
        ttk.Button(top, text='Cancel', command=self._cancel).grid(row=row, column=1, **pad)

    def show(self):
        self._top.wait_window()
        res = []
        if self._res:
            for name, var in self._vars:
                if var.get():
                    res.append(name)
        return res

    def _ok(self):
        self._res = True
        self._top.destroy()

    def _cancel(self):
        self._res = False
        self._top.destroy()


def askoptions(master, text, options):
    dialog = OptionDialog(master, text, options)
    return dialog.show()


class App(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        pad = {'padx': 4, 'pady': 4}

        ttk.Label(self, text='Use the button bellow to open a csv or tsv file').pack(**pad)
        ttk.Button(self, text='Open File', command=self._open).pack(**pad)

    def _open(self):
        filename = filedialog.askopenfilename(parent=self, filetypes=[('CSV', '*.csv'), ('TSV', '*.txt'), ('TSV', '*.xlm'), ('All Files', '*.*')])
        if filename:
            self.plot_file(filename)

    def plot_file(self, filename):
        path = Path(filename)

        is_csv = filename.endswith('.csv')
        with open(filename, 'r', newline='\n') as f:
            delim = ',' if is_csv else '\t'
            reader = csv.reader(f, delimiter=delim)

            headers = next(reader)
            while len(headers) == 0:
                headers = next(reader)
            
            colnames = askoptions(self, 'Select columns to plot', headers)
            cols = [(headers.index(col), col) for col in colnames]

            if len(cols) == 0:
                messagebox.showwarning('No columns selected', 'You did not select any columns')
                return
            
            plots = [[] for _ in cols]

            rows = filter(lambda row: len(row) > 0, reader)
            for row in rows:
                for i, (col, name) in enumerate(cols):
                    val = float(row[col])
                    plots[i].append(val)
            self._show_graph(plots, path.name, path.parent, 'Index', 'Value', colnames)
 
    def _show_graph(self, plots, title, subtitle, xlabel, ylabel, legend):
        top = tk.Toplevel(self.master)
        top.title('GPS Tracks')
        g = GraphControl(top)
        g.pack(fill=tk.BOTH, expand=True)

        ax = g.add_subplot(111)
        for plot, label in zip(plots, legend):
            ax.plot(plot, label=label)
        ax.legend()
        ax.set_title(str(title) + '\n' + str(subtitle))
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)


if __name__ == '__main__':
    root = tk.Tk()
    root.wm_title('General Plotter')
    root.resizable(0, 0)
    App(root).pack(fill=tk.BOTH, padx=4, pady=4)
    root.mainloop()
