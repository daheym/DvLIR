"""
Application state management for the DvLIR application.
This module replaces global variables with a proper state management class.
"""
from shiny import reactive
from typing import Optional, Tuple, Any, Union
import pandas as pd
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class AppState:
    """
    Centralized state management for the DvLIR application.
    
    This class encapsulates all application state using Shiny's reactive values,
    replacing the global variables from the original implementation.
    """
    
    def __init__(self):
        """Initialize all reactive state variables."""
        
        # File and data management
        self.selected_files = reactive.Value(pd.DataFrame())
        self.original_data = reactive.Value(pd.DataFrame())
        self.calculated_data = reactive.Value(pd.DataFrame())
        self.plotted_data = reactive.Value()  # Will store (fig, ax) tuple
        self.outfile_data_name = reactive.Value("")
        
        # Plot state management (replaces global variables)
        self.plot_execution_state = reactive.Value(False)
        self.y_max_range = reactive.Value()  # Will store tuple of floats or None
        
    def reset_plot_state(self):
        """Reset plot-related state variables."""
        self.plot_execution_state.set(False)
        self.y_max_range.set(None)
        
    def update_y_range(self, y_range: Optional[Tuple[Optional[float], Optional[float]]]):
        """
        Update y-axis range with validation.
        
        Args:
            y_range: Tuple of (min, max) values for y-axis
        """
        if y_range and len(y_range) == 2:
            # Validate and convert to proper tuple
            min_val = y_range[0] if y_range[0] is not None and y_range[0] > 0 else 0.0
            max_val = y_range[1] if y_range[1] is not None else 10.0
            validated_range = (min_val, max_val)
            self.y_max_range.set(validated_range)
        else:
            self.y_max_range.set(None)
    
    def set_plot_executed(self, executed: bool = True):
        """Mark that the plot function has been executed."""
        self.plot_execution_state.set(executed)
    
    def is_plot_executed(self) -> bool:
        """Check if the plot function has been executed."""
        return self.plot_execution_state.get()
    
    def get_y_max_range(self) -> Tuple[Optional[float], Optional[float]]:
        """Get the current y-axis maximum range."""
        return self.y_max_range.get()
    
    def set_selected_files(self, files_df: pd.DataFrame):
        """Set the selected files dataframe."""
        self.selected_files.set(files_df)
    
    def get_selected_files(self) -> pd.DataFrame:
        """Get the selected files dataframe."""
        return self.selected_files.get()
    
    def set_original_data(self, data: pd.DataFrame):
        """Set the original (raw) data."""
        self.original_data.set(data)
        # Reset plot state when new data is loaded
        self.reset_plot_state()
    
    def get_original_data(self) -> pd.DataFrame:
        """Get the original (raw) data."""
        return self.original_data.get()
    
    def set_calculated_data(self, data: pd.DataFrame):
        """Set the calculated/processed data."""
        self.calculated_data.set(data)
    
    def get_calculated_data(self) -> pd.DataFrame:
        """Get the calculated/processed data."""
        return self.calculated_data.get()
    
    def set_plotted_data(self, fig_ax_tuple: Tuple[Optional[Figure], Optional[Any]]):
        """Set the plotted data (figure and axes)."""
        self.plotted_data.set(fig_ax_tuple)
    
    def get_plotted_data(self) -> Tuple[Optional[Figure], Optional[Any]]:
        """Get the plotted data (figure and axes)."""
        return self.plotted_data.get()
    
    def set_output_filename(self, filename: str):
        """Set the output filename for downloads."""
        self.outfile_data_name.set(filename)
    
    def get_output_filename(self) -> str:
        """Get the output filename for downloads."""
        return self.outfile_data_name.get()
    
    def has_data(self) -> bool:
        """Check if any data has been loaded."""
        original = self.get_original_data()
        return not original.empty if original is not None else False
    
    def has_calculated_data(self) -> bool:
        """Check if calculated data is available."""
        calculated = self.get_calculated_data()
        return not calculated.empty if calculated is not None else False
