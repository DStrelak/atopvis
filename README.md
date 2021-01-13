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
main.py [-h] (-atop ATOP | -pickle PICKLE) [-to_png TO_PNG] [-to_pickle TO_PICKLE] [-i]
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

# Interactive plot
In addition to standard Matplotlib interactive features (zoom, pan), the three most demanding processes (in terms of CPU, Disk, and Memory) are shown on the left click. Ctrl+left click opens atop in interactive mode at a specific time.

# Images
![Screenshot from 2020-12-21 15-08-29](https://user-images.githubusercontent.com/28389367/102786364-add1c900-439f-11eb-8b0f-89754ddcf511.png)
