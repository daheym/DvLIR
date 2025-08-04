"""
Server handlers for the DvLIR application.
This module contains the main server logic organized by functionality.
"""
from shiny import reactive, render, ui
import pandas as pd

# Configure matplotlib backend before importing pyplot to avoid Qt issues
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for web applications
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import io
from datetime import datetime
from typing import List, Tuple, Any

from server.state import AppState
from data.processing import (
    load_and_process_files, 
    calculate_energy_data, 
    calculate_energy_statistics,
    filter_data_by_date_range,
    filter_data_by_time_periods
)
from config import config


def create_server(app_state: AppState):
    """
    Create the server function with all handlers.
    
    Args:
        app_state: Application state management instance
        
    Returns:
        Server function for the Shiny app
    """
    def server(input, output, session):
        
        # Helper function to update daterange slider
        def update_daterange(df: pd.DataFrame):
            """Update the date range slider based on data."""
            if df.empty:
                return
            
            _min = df.index.min()
            _max = df.index.max()
            _off = pd.Timedelta('1day')
            
            ui.update_date_range(
                'daterange', 
                start=_min, 
                end=_max, 
                min=_min-_off, 
                max=_max+_off
            )

        # Value box renderers
        @render.ui
        def totalkWhconsum() -> str:
            """Render total energy consumption."""
            df = app_state.get_original_data()
            if df.empty or '1.8.0[kWh]' not in df.columns:
                return "0 kWh"
            
            stats = calculate_energy_statistics(df)
            return f"{stats['total_consumption']:.4g} kWh"
        
        @render.ui
        def totalkWhprod() -> str:
            """Render total energy production."""
            df = app_state.get_original_data()
            if df.empty or '2.8.0[kWh]' not in df.columns:
                return "0 kWh"
            
            stats = calculate_energy_statistics(df)
            return f"{stats['total_production']:.3g} kWh"
        
        @render.ui
        def maxkWhconsum() -> str:
            """Render peak energy consumption."""
            df = app_state.get_original_data()
            if df.empty:
                return "0 kWh"
            
            stats = calculate_energy_statistics(df)
            return f"{stats['max_daily_consumption']:.3g} kWh"

        @render.ui
        def maxkWhprod() -> str:
            """Render peak energy production."""
            df = app_state.get_original_data()
            if df.empty:
                return "0 kWh"
            
            stats = calculate_energy_statistics(df)
            return f"{stats['max_daily_production']:.3g} kWh"

        # File selection display
        @reactive.calc
        @render.data_frame
        def showselectedfiles():
            """Show selected files in a data grid."""
            df = app_state.get_selected_files()
            if df.empty:
                return render.DataGrid(pd.DataFrame(), width='100%', height='130px', summary=False)
            return render.DataGrid(df, width='100%', height='130px', summary=False)

        # File loading and processing
        @render.data_frame
        @reactive.event(input.files, input.parsefiles)
        def read_files():
            """Load and process input files."""
            try:
                # Get files from input or use test data
                files = input.files() if input.files() else []
                
                # Load and process files
                df, file_names = load_and_process_files(files)
                
                # Update selected files display
                files_df = pd.DataFrame({'Files loaded': file_names})
                app_state.set_selected_files(files_df)
                
                # Store original data
                app_state.set_original_data(df)
                
                # Update date range slider
                if not df.empty:
                    update_daterange(df)
                
                return render.DataGrid(
                    df.reset_index(), 
                    width='100%', 
                    height='150px', 
                    summary=False
                )
                
            except Exception as e:
                print(f"Error in read_files: {e}")
                return render.DataGrid(
                    pd.DataFrame(), 
                    width='100%', 
                    height='150px', 
                    summary=False
                )

        # Data analysis
        @render.data_frame
        @reactive.event(input.start_analysis)
        def show_dataframe():
            """Process and display analyzed data."""
            try:
                df = app_state.get_original_data()
                if df.empty:
                    return render.DataGrid(pd.DataFrame(), width='100%', height='150px', summary=False)
                
                daytime_range = input.dayrange()
                date_range = input.daterange()
                
                # Calculate energy data
                df_calc = calculate_energy_data(df, daytime_range)
                
                # Store calculated data
                app_state.set_calculated_data(df_calc)
                
                # Filter by date range for display
                df_display = filter_data_by_date_range(df_calc, date_range)
                df_display = df_display.dropna()
                
                return render.DataGrid(
                    df_display.reset_index(), 
                    width='100%', 
                    height='150px', 
                    summary=False
                )
                
            except Exception as e:
                print(f"Error in show_dataframe: {e}")
                return render.DataGrid(pd.DataFrame(), width='100%', height='150px', summary=False)

        # Reset analysis
        @reactive.effect()
        @reactive.event(input.reset_analysis)
        def reset_analysis_params():
            """Reset analysis parameters to defaults."""
            ui.update_slider('dayrange', value=config.DEFAULT_DAY_RANGE or [8, 17])
            df = app_state.get_original_data()
            if not df.empty:
                update_daterange(df)

        # Reset plot
        @reactive.effect()
        @reactive.event(input.reset_plot)
        def reset_plot_params():
            """Reset plot parameters to defaults."""
            ui.update_checkbox_group(
                'selectconsumptionfeed', 
                selected=['Power consumption (kWh)', 'Power feed (kWh)']
            )
            ui.update_checkbox_group('selectdaynight', selected=['Day', 'Night'])
            ui.update_radio_buttons('selectmarkerslines', selected='Lines')
            ui.update_slider('plotyrange', value=(None,None))
            
            app_state.reset_plot_state()

        # Plotting
        @render.plot
        @reactive.event(input.plot_data, input.start_analysis)
        def plot_dataset():
            """Generate and display the plot."""
            try:
                # Get input parameters
                date_range = input.daterange()
                curves = input.selectconsumptionfeed()
                appearance = input.selectmarkerslines()
                day_night = input.selectdaynight()
                daytime_range = input.dayrange()

                # Get calculated data
                df = app_state.get_calculated_data()
                if df.empty:
                    fig, ax = plt.subplots()
                    ax.text(0.5, 0.5, 'No data to plot', ha='center', va='center', transform=ax.transAxes)
                    return fig

                # Filter data
                df_filtered = filter_data_by_date_range(df, date_range)
                df_filtered = filter_data_by_time_periods(df_filtered, day_night, daytime_range)

                # Plot formatting
                fmt = {}
                if appearance == 'Markers':
                    fmt = {'marker': 'o', 'ls': ''}

                # Create plot
                fig, ax = plt.subplots()
                
                if not df_filtered.empty and curves:
                    df_filtered[list(curves)].plot(**fmt, ax=ax)

                # Set axis parameters
                y_range = input.plotyrange()
                ylim = None
                if y_range and y_range != [0, 10]:
                    ylim = tuple(y_range)

                ax.set(
                    xlabel='Date (year-month)', 
                    ylabel='Power (kWh)', 
                    ylim=ylim
                )
                ax.xaxis.set_major_locator(mdates.MonthLocator())

                # Store plot data
                app_state.set_plotted_data((fig, ax))
                
                return fig
                
            except Exception as e:
                print(f"Error in plot_dataset: {e}")
                fig, ax = plt.subplots()
                ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', transform=ax.transAxes)
                return fig

        # Download functionality would go here
        # For now, we'll create placeholder functions
        
        @render.download(filename=lambda: f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_DvLIR-data.xlsx")
        def download_table():
            """Download data table."""
            # Placeholder - would implement full download logic
            df = app_state.get_calculated_data()
            if df.empty:
                df = pd.DataFrame({'message': ['No data available']})
            
            with io.BytesIO() as buf:
                df.to_excel(buf, sheet_name='data')
                yield buf.getvalue()

        @render.download(filename=lambda: f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_DvLIR-plot.png")
        def download_plot():
            """Download plot."""
            fig, ax = app_state.get_plotted_data()
            if fig is None:
                # Create empty plot if none exists
                fig, ax = plt.subplots()
                ax.text(0.5, 0.5, 'No plot available', ha='center', va='center', transform=ax.transAxes)
            
            with io.BytesIO() as buf:
                fig.savefig(buf, format='png', dpi=config.DEFAULT_DPI, bbox_inches='tight')
                yield buf.getvalue()

    return server
