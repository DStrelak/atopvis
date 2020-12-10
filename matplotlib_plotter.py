import matplotlib.pyplot as plt
from atop_constants import *
from matplotlib.ticker import AutoMinorLocator
import matplotlib.dates as mdates
from atop_report import AtopReport


class MatplotlibPlotter:
    @staticmethod
    def __set(ax, ylabel, data):
        data.set_index(ATOP_TIMESTAMP).plot(ax=ax)
        ax.grid(True, which='major')
        ax.grid(True, which='minor', alpha=0.2)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", which="both", rotation=75)  # rotate labels
        ax.xaxis.set_minor_locator(AutoMinorLocator(10))  # create subgrid, divided in 5 pieces
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # fix formatting
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%H:%M:%S'))  # show tick labels for minors too
        ax.set_picker(True)

    def __set2(ax, ylabel, data):
        ax2 = ax.twinx()
        ax2._get_lines.prop_cycler = ax._get_lines.prop_cycler
        data.set_index(ATOP_TIMESTAMP).plot(ax=ax2)
        ax2.set_ylabel(ylabel)
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.get_legend().remove()
        ax2.legend(lines + lines2, labels + labels2)

    @staticmethod
    def plot(report: AtopReport, interactive, destination):
        resources = report.resources
        fig, axes = plt.subplots(nrows=len(resources), ncols=1, sharex='col')
        fig.suptitle(report.file)
        for i, r in enumerate(sorted(resources)):
            ax = axes[i]
            ax.set_title(r.name, loc='left')
            MatplotlibPlotter.__set(ax, r.unit, r.data)
            if r.data_opt is not None:
                MatplotlibPlotter.__set2(ax, r.data_opt_unit, r.data_opt)

        fig.set_size_inches(20, len(resources) * 2.5)
        if destination:
            plt.savefig(destination, dpi=300, bbox_inches='tight')
        if interactive:
            plt.show()
