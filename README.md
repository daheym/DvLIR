## DvLIR analyzer

### Overview
Python based Shiny application for the analysis of Smart Meter data (DvLIR). For a usable application visit https://daheym.shinyapps.io/dvlir-analyzer/. 

### How to use
- Upload one or multiple .csv files that are exported from the DvLIR device
- The data is automatically concatenated, sorted ny date and duplicates are removed
- Select the *date range* of interest and use the *daytime* slider to determine which hours is considered as Day in the analysis
- A click on the **Run analysis** button analyzes the data according to your settings and plots the timecurves
- Customize the plot and export the plot and/or the data

### UI
![](figures/ui.jpg)