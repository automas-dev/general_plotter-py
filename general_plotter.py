#!/usr/bin/env python3

import os
import wx
from wx.lib import sized_controls
import wx.lib.agw.aui as aui
import csv

import matplotlib as mpl
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar


class Plot(wx.Panel):
    def __init__(self, parent, id=-1, dpi=None, **kwargs):
        super().__init__(parent, id=id, **kwargs)
        self.figure = mpl.figure.Figure(dpi=dpi, figsize=(2, 2))
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

    def gca(self):
        return self.figure.gca()

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


class CustomDialog(sized_controls.SizedDialog):

    def __init__(self, parent, title, choices):
        super().__init__(parent, title=title)
        pane = self.GetContentsPane()

        static_line = wx.StaticLine(pane, style=wx.LI_HORIZONTAL)
        static_line.SetSizerProps(border=(('all', 0)), expand=True)

        pane_btns = sized_controls.SizedPanel(pane)
        pane_btns.SetSizerType('vertical')
        pane_btns.SetSizerProps(align='center')

        self._check = ck = wx.CheckListBox(
            pane_btns, id=wx.ID_ANY, choices=choices)

        self.ID_OK = wx.NewId()
        self.ID_CANCEL = wx.NewId()

        button_ok = wx.Button(pane_btns, self.ID_OK, label='Ok')
        button_ok.Bind(wx.EVT_BUTTON, self.on_button)

        button_ok = wx.Button(pane_btns, self.ID_CANCEL, label='Cancel')
        button_ok.Bind(wx.EVT_BUTTON, self.on_button)

        self.Fit()

    def GetCheckedItems(self):
        return self._check.GetCheckedItems()

    def GetCheckedStrings(self):
        return self._check.GetCheckedStrings()

    def on_button(self, event):
        if self.IsModal():
            if event.EventObject.Id == self.ID_OK:
                self.EndModal(True)
            else:
                self.EndModal(False)
        else:
            self.Close()


class GeneralPlotterFrame(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, id=wx.ID_ANY, title='General Plotter', size=(800, 600))

        sizer1 = wx.BoxSizer(wx.HORIZONTAL)

        self.plotter = PlotNotebook(self)
        #self.page1 = plotter.add('Illuminance')
        #self.page2 = plotter.add('GPS Track')

        sizer1.Add(self.plotter, 1, wx.ALL | wx.EXPAND, 5)

        #self.page1.config('Illuminance', 'Index', 'Illuminance, lx')
        #self.page2.config('GPS Track', 'Longitude', 'Latitude', inverty=True)

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
        with wx.FileDialog(self, "Open RLMMS Data File", wildcard="CSV File (*.csv)|*.csv|XLM Data (*.xlm)|*.xlm|RLMMS Data (*.txt)|*.txt|All Files (*.*)|*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            pathname = fileDialog.GetPath()

            try:
                self.load(pathname)
            except IOError:
                wx.LogError('Cannot open file %s' % pathname)

    def load(self, pathname):
        with open(pathname, 'r', newline='') as f:
            base = os.path.basename(pathname)

            n_tab = []
            n_comma = []
            for line in f:
                if len(line) == 0:
                    continue
                n_tab.append(line.count('\t'))
                n_comma.append(line.count(','))

                if len(n_tab) > 10:
                    break

            if len(n_tab) == 0:
                wx.MessageDialog(
                    self, "Unable to deduce file type of an empty file", style=wx.OK | wx.ICON_ERROR)
                return

            count_tab = n_tab.count(n_tab[0])
            count_comma = n_comma.count(n_comma[0])

            if count_tab == 0 and count_comma == 0:
                wx.MessageDialog(
                    self, "Unable to deduce file type based on content, using extension", style=wx.OK | wx.ICON_WARNING)
                is_tab = any(pathname.endswith(ext)
                             for ext in ['.txt', '.xlm'])
            else:
                is_tab = count_tab > count_comma

            f.seek(0)

            delim = '\t' if is_tab else ','

            reader = csv.reader(f, delimiter=delim)
            headers = next(reader)
            while len(headers) == 0:
                headers = next(reader)

            diag = CustomDialog(self, 'title', headers)
            if not diag.ShowModal():
                return

            selected = diag.GetCheckedItems()
            print(selected)
            print(diag.GetCheckedStrings())

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
                page.plot(col, label=head)

            page.enable_picker()
            page.draw()


if __name__ == '__main__':
    app = wx.App()
    frame = GeneralPlotterFrame(None)
    frame.Show()
    app.MainLoop()
