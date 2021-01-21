# AtopVis

AtopVis is a simple tool for visualization of the [Atop](https://www.atoptool.nl/) monitor tool report. It allows you to:

  - open an interactive plot with resources utilization
  - generate png image 
  - serialize parsed report to a pickle object

# Requirements

  - Python 3.8 with Matplotlib and Pandas
  - atop 2.5


# Usage
```
main.py [-h] (-atop ATOP | -pickle PICKLE) [-to_png TO_PNG] [-to_pickle TO_PICKLE] [-i] [-timeline TIMELINE]
```
Generate pickle object for later use:
```
python main.py -atop monitor.atop -to_pickle report.pck
INFO:root:Detected 4.0 cores (assuming multithreading support)
INFO:root:Detected 31986 MB of memory
INFO:root:Detected 31986 MB of swap
```
Load generated pickle object in interactive graph:
```
python main.py -pickle report.pck -i
```
Create a png file with the timeline:
```
python main.py -pickle report.pck -to_png timeline.png
```

# Experimental support
## Routines timeline ##
Timeline for running routines can also be visualized. Currently, only external input in form of the pre-processed [Scipion](http://scipion.i2pc.es/) project logs can be used to show running protocols.
Use
```
-timeline path_to_csv
```
to load the project data.

## Aggregated process data ##
Aggregated data regarding running processes can be generated in form of the Sheet (xls) files.
```
process_info.py [-h] -atop ATOP -dest DEST
```
Generater file contains aggregated data for each process reported in the atop file, as well as an aggregation on the processes with the same name.
See atop documentation for detailed description of the reported values.

# Interactive plot
In addition to standard Matplotlib interactive features (zoom, pan), the three most demanding processes (in terms of CPU, Disk, and Memory) are shown on the left click. Ctrl+left click opens atop in interactive mode at a specific time.

# Images
![image](https://user-images.githubusercontent.com/28389367/105348132-28347980-5be8-11eb-8cdf-50d3f19a81d8.png)
![image](https://user-images.githubusercontent.com/28389367/105349720-692d8d80-5bea-11eb-90fe-f8e52721971a.png)
![image](https://user-images.githubusercontent.com/28389367/105349849-94b07800-5bea-11eb-8fac-f3f88be7edfd.png)

