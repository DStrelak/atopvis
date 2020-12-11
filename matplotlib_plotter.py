import matplotlib.pyplot as plt
from atop_constants import *
from matplotlib.ticker import AutoMinorLocator
import matplotlib.dates as mdates
from atop_report import AtopReport


class MatplotlibPlotter:
    def __init__(self, report: AtopReport):
        self.report = report
        self.annotation_texts = {p.time: p for p in report.processes}
        self.last_event_xy = ()
        self.last_annotation = None
        self.fig = None
        self.ctrl_pushed = False

    def __add_annotation(self, ax):
        self.last_annotation = ax.annotate("", xy=(0, 0), xytext=(-20, 20),
                                           xycoords='figure pixels',
                                           textcoords="offset points",
                                           bbox=dict(boxstyle="round", fc="w", alpha=0.8),
                                           arrowprops=dict(arrowstyle="->"))
        # Put the annotation in the figure instead of the axes so that it will be on
        # top of other subplots.
        ax.figure.texts.append(ax.texts.pop())
        self.last_annotation.set_visible(False)

    def __set(self, ax, ylabel, data):
        data.set_index(ATOP_TIMESTAMP).plot(ax=ax)
        ax.grid(True, which='major')
        ax.grid(True, which='minor', alpha=0.2)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", which="both", rotation=75)  # rotate labels
        ax.xaxis.set_minor_locator(AutoMinorLocator(10))  # create subgrid, divided in 5 pieces
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # fix formatting
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%H:%M:%S'))  # show tick labels for minors too
        ax.set_picker(True)
        self.__add_annotation(ax)

    def __set2(self, ax, ylabel, data):
        ax2 = ax.twinx()
        ax2.set_picker(True)
        ax2._get_lines.prop_cycler = ax._get_lines.prop_cycler
        data.set_index(ATOP_TIMESTAMP).plot(ax=ax2)
        ax2.set_ylabel(ylabel)
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.get_legend().remove()
        ax2.legend(lines + lines2, labels + labels2)
        self.__add_annotation(ax2)

    def __on_key_press(self, event):
        if 'control' == event.key:
            print(f'pushing {event.key}')
            self.ctrl_pushed = True

    def __on_key_release(self, event):
        if 'control' == event.key:
            self.ctrl_pushed = False

    def __show_process_annotation(self, time):
        text = str(self.annotation_texts[time])
        text = text + '\nPress Ctrl+Click to open atop'
        self.last_annotation.set_text(text)
        self.last_annotation.set_visible(True)
        self.fig.canvas.draw_idle()

    def __open_atop(self, time):
        import distutils.spawn
        import os.path
        import subprocess
        atop = distutils.spawn.find_executable('atop')
        terminal = distutils.spawn.find_executable('gnome-terminal')
        text = ''
        if not atop or not terminal:
            text = 'atop or gnome-terminal not found'
        file = self.report.file
        if not os.path.exists(file):
            text = f'file {file} does not exist'
        if text:
            self.last_annotation.set_text(text)
            self.last_annotation.set_visible(True)
            self.fig.canvas.draw_idle()
        else:
            self.ctrl_pushed = False  # otherwise if user releases Ctrl in terminal, we won't get the event
            subprocess.call(f'gnome-terminal --maximize -- atop -b {time} -r {file}', shell=True)

    def __on_pick(self, event):
        xy = (event.mouseevent.x, event.mouseevent.y)
        if xy == self.last_event_xy:
            return  # ignore multiple events at the same location
        self.last_event_xy = xy
        xydata = (event.mouseevent.xdata, event.mouseevent.ydata)
        time = mdates.num2date(xydata[0]).strftime('%H:%M:%S')
        self.last_annotation.xy = xy
        if self.ctrl_pushed:
            self.__open_atop(time)
        else:
            self.__show_process_annotation(time)

    def __on_figure_leave(self, event):
        if self.last_annotation is not None and self.last_annotation.get_visible():
            self.last_annotation.set_visible(False)
            self.fig.canvas.draw_idle()

    def __register_events(self):
        self.fig.canvas.mpl_connect('pick_event', self.__on_pick)
        self.fig.canvas.mpl_connect('figure_leave_event', self.__on_figure_leave)
        self.fig.canvas.mpl_connect('key_press_event', self.__on_key_press)
        self.fig.canvas.mpl_connect('key_release_event', self.__on_key_release)

    def plot(self, interactive, destination):
        resources = self.report.resources
        plt.rcParams.update({'font.family': 'monospace'})
        self.fig, axes = plt.subplots(nrows=len(resources), ncols=1, sharex='col')
        self.fig.suptitle(self.report.file)
        for i, r in enumerate(sorted(resources)):
            ax = axes[i]
            ax.set_title(r.name, loc='left')
            self.__set(ax, r.unit, r.data)
            if r.data_opt is not None:
                self.__set2(ax, r.data_opt_unit, r.data_opt)

        self.fig.set_size_inches(20, len(resources) * 2.5)
        self.__register_events()
        if destination:
            plt.savefig(destination, dpi=300, bbox_inches='tight')
        if interactive:
            plt.show()
