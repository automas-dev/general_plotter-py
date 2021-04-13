#!/usr/bin/env python3

import os
import wx
import wx.lib.agw.aui as aui
import csv

import matplotlib.axes
import matplotlib.figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar


class Plot(wx.Panel):
    def __init__(self, parent, id=-1, dpi=None, **kwargs):
        super().__init__(parent, id=id, **kwargs)
        self.figure = matplotlib.figure.Figure(dpi=dpi, figsize=(2, 2))
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.toolbar = NavigationToolbar(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND)
        sizer.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND)
        self.SetSizer(sizer)

        self.canvas.mpl_connect('pick_event', self._onpick)

        self.lines = []
        self.lined = {}

    def gca(self) -> matplotlib.axes.Axes:
        return self.figure.gca() # type: ignore

    def clear(self):
        self.lines.clear()
        for artist in self.gca().lines + self.gca().collections:
            artist.remove()

    def draw(self):
        self.canvas.draw()

    def plot(self, *args, scalex=True, scaley=True, data=None, **kwargs):
        l, = self.gca().plot(*args, scalex=scalex, scaley=scaley, data=data, **kwargs)
        self.lines.append(l)

    def config(self, title, xlabel, ylabel, inverty=False):
        ax = self.gca()
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if inverty:
            ax.invert_yaxis()

    def enable_picker(self):
        leg = self.gca().legend(loc='upper right')
        self.lined.clear()
        for legline, origline in zip(leg.get_lines(), self.lines):
            legline.set_picker(True)
            self.lined[legline] = origline

    def _onpick(self, event):
        legline = event.artist
        origline = self.lined[legline]
        vis = not origline.get_visible()
        origline.set_visible(vis)
        if vis:
            legline.set_alpha(1.0)
        else:
            legline.set_alpha(0.2)
        self.draw()


class PlotNotebook(wx.Panel):
    def __init__(self, parent, id=-1):
        super().__init__(parent, id=id)
        style = aui.AUI_NB_TOP | aui.AUI_NB_TAB_SPLIT | aui.AUI_NB_TAB_MOVE | aui.AUI_NB_CLOSE_ON_ALL_TABS | aui.AUI_NB_SCROLL_BUTTONS
        self.nb = aui.AuiNotebook(self, agwStyle=style)
        sizer = wx.BoxSizer()
        sizer.Add(self.nb, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def add(self, tabname):
        page = Plot(self.nb)
        self.nb.AddPage(page, tabname)
        self.nb.SetSelection(self.nb.GetPageCount()-1)
        return page


def try_float(text):
    try:
        return float(text)
    except ValueError:
        return float('nan')


class SelectColumnDialog(wx.Dialog):
    def __init__(self, parent, title, choices):
        super().__init__(parent, title=title)

        sizer = wx.BoxSizer(wx.VERTICAL)

        self._check = ck = wx.CheckListBox(self, id=wx.ID_ANY, choices=choices)
        sizer.Add(self._check, 1, wx.ALL | wx.EXPAND, 5)

        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            sizer.Add(buttons, 0, wx.ALL | wx.HORIZONTAL, 5)

        self.SetSizer(sizer)
        self.Fit()

    def GetCheckedItems(self):
        return self._check.GetCheckedItems()

    def GetCheckedStrings(self):
        return self._check.GetCheckedStrings()

    def OnClose(self, event):
        print('on_close')
        self.EndModal(wx.CANCEL)


class GeneralPlotterFrame(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, id=wx.ID_ANY, title='General Plotter', size=(800, 600))

        sizer1 = wx.BoxSizer(wx.HORIZONTAL)

        self.plotter = PlotNotebook(self)
        sizer1.Add(self.plotter, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer1)

        self.Layout()
        self.m_menubar = wx.MenuBar(0)
        self.m_filemenu = wx.Menu()
        self.m_openmenuitem = wx.MenuItem(
            self.m_filemenu, wx.ID_ANY, "Open\tCtrl+O")
        self.m_filemenu.Append(self.m_openmenuitem)
        self.m_menubar.Append(self.m_filemenu, "File")
        self.SetMenuBar(self.m_menubar)

        self.Center(wx.BOTH)

        self.Bind(wx.EVT_MENU, self.openfiledialog,
                  id=self.m_openmenuitem.GetId())

    def openfiledialog(self, event):
        with wx.FileDialog(self, "Open Data File", wildcard="All Files (*.*)|*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            pathname = fileDialog.GetPath()

            try:
                self.load(pathname)
            except IOError:
                wx.LogError('Cannot open file %s' % pathname)

    def _find_delim(self, pathname, sample=10):
        with open(pathname, 'r') as f:
            n_tab = []
            n_comma = []
            for line in f:
                if len(line.strip()) > 0:
                    n_tab.append(line.count('\t'))
                    n_comma.append(line.count(','))
                if len(n_tab) > sample:
                    break

            if len(n_tab) == 0:
                return None

            count_tab = n_tab.count(n_tab[0])
            count_comma = n_comma.count(n_comma[0])

            can_tab = count_tab == len(n_tab) and n_tab[0] > 0
            can_comma = count_comma == len(n_tab) and n_comma[0] > 0

            if not can_tab and not can_comma:
                wx.MessageDialog(
                    self, "Unable to deduce file type based on content, using extension", style=wx.OK | wx.ICON_WARNING).ShowModal()
                is_tab = any(pathname.endswith(ext)
                             for ext in ['.txt', '.xlm'])
                if is_tab:
                    return '\t'
                else:
                    return ','
            elif not can_tab and can_comma:
                if n_comma[0] == 0:
                    return None
                else:
                    return ','
            elif can_tab and not can_comma:
                if n_tab[0] == 0:
                    return None
                else:
                    return '\t'
            else:
                if n_tab[0] > n_comma[0]:
                    return '\t'
                else:
                    return ','

        return None

    def load(self, pathname, delim=None):
        base = os.path.basename(pathname)
        if delim is None:
            delim = self._find_delim(pathname)

        if delim is None:
            wx.MessageDialog(
                self, "Unable to deduce file type", "Unknown File Type", style=wx.OK | wx.ICON_ERROR)
            return

        with open(pathname, 'r', newline='') as f:
            reader = csv.reader(f, delimiter=delim)
            headers = next(reader)
            while len(headers) == 0:
                headers = next(reader)

            diag = SelectColumnDialog(self, 'Select Columns', headers)
            if diag.ShowModal() == wx.ID_CANCEL:
                return

            selected = diag.GetCheckedItems()

            cols = [[] for _ in selected]
            for row in reader:
                if len(row) == 0:
                    continue
                for i, col in enumerate(selected):
                    cols[i].append(try_float(row[col]))

            page = self.plotter.add(base)
            page.config('{}\n{}'.format(base, pathname), 'Sample', 'Value')
            for i, col in enumerate(cols):
                col_i = selected[i]
                head = headers[col_i]
                if not head:
                    head = 'Column {}'.format(col_i + 1)
                page.plot(col, label=head)

            page.enable_picker()
            page.draw()


if __name__ == '__main__':
    app = wx.App()
    frame = GeneralPlotterFrame(None)
    frame.Show()
    app.MainLoop()
