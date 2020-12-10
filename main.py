import pickle
from atop_report import AtopReport
from matplotlib_plotter import MatplotlibPlotter


def load_report(args):
    atop_file = args.atop
    if atop_file:
        return AtopReport(atop_file)
    pickle_file = args.pickle
    if pickle_file:
        with open(pickle_file, 'rb') as f:
            return pickle.load(f)


def main(args):
    report = load_report(args)
    if args.to_pickle:
        with open(args.to_pickle, 'wb') as f:
            pickle.dump(report, f)

    if args.to_png or args.interactive:
        plotter = MatplotlibPlotter(report)
        plotter.plot(args.interactive, args.to_png)


def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-atop', help='path to the atop file')
    input_group.add_argument('-pickle', help='path to pickle file')

    parser.add_argument('-to_png', help='path to the png file')
    parser.add_argument('-to_pickle', help='path to pickle')
    parser.add_argument('-i', '--interactive', help='open interactive plot', action='store_true')

    return parser.parse_args()


if __name__ == '__main__':
    main(parse_args())
