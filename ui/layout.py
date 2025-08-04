"""
UI layout components for the DvLIR application.
"""
from shiny import ui
import shinyswatch
from faicons import icon_svg as icon
from config import config


def create_ui():
    """
    Create the main UI layout for the DvLIR application.
    
    Returns:
        UI layout object
    """
    return ui.page_fluid(
        ui.hr(),
        ui.panel_title('Analyze DvLIR datasets', 'DvLIR analyzer'),
        ui.hr(),
        ui.page_sidebar(
            _create_sidebar(),
            _create_main_content()
        ),
        theme=shinyswatch.theme.cosmo
    )


def _create_sidebar():
    """Create the sidebar with input controls."""
    return ui.sidebar(
        # Input parameters section
        ui.h4('Input parameters'),
        ui.input_file(
            'files', 
            'Select file(s) to upload', 
            multiple=True, 
            accept='.csv', 
            placeholder='no file selected', 
            button_label='Browse...'
        ),
        ui.output_data_frame('showselectedfiles'),
        ui.layout_column_wrap(
            ui.input_action_button(
                'parsefiles', 
                'Import', 
                icon=icon('file-import', 'solid')
            ),
            width=1
        ),
        
        ui.hr(),
        
        # Analysis parameters section
        ui.h4('Analysis parameters'),
        ui.input_date_range('daterange', 'Select date range'), 
        ui.input_slider(
            'dayrange', 
            'Select daytime', 
            min=0, 
            max=24, 
            value=config.DEFAULT_DAY_RANGE or [8, 17]
        ),
        ui.layout_column_wrap(
            ui.input_action_button(
                'start_analysis', 
                'Analyze', 
                icon=icon('magnifying-glass-chart', 'solid')
            ),
            ui.input_action_button(
                'reset_analysis', 
                'Reset', 
                icon=icon('arrow-rotate-left', 'solid')
            ),
            width=.5
        ),

        ui.hr(),
        
        # Plot settings section
        ui.h4('Plot settings'),
        ui.input_checkbox_group(
            'selectconsumptionfeed', 
            'Select traces to plot',
            ['Power consumption (kWh)', 'Power feed (kWh)'], 
            selected=['Power consumption (kWh)', 'Power feed (kWh)']
        ),
        ui.input_checkbox_group(
            'selectdaynight', 
            'Select timeperiods to plot',
            ['Day', 'Night'], 
            selected=['Day', 'Night']
        ),
        ui.input_radio_buttons(
            'selectmarkerslines', 
            'Show plot as markers/lines',
            ['Markers', 'Lines'], 
            selected='Lines'
        ),
        ui.input_slider(
            'plotyrange', 
            'Optional: Adjust kWh-axis range', 
            min=0, 
            max=10, 
            value=(None,None), 
            step=.25
        ),
        ui.layout_column_wrap(
            ui.input_action_button(
                'plot_data', 
                'Plot', 
                icon=icon('chart-line', 'solid')
            ),
            ui.input_action_button(
                'reset_plot', 
                'Reset', 
                icon=icon('arrow-rotate-left', 'solid')
            ),
            width=.5
        ),

        ui.hr(),

        # Download settings section
        ui.h4('Download settings'),
        ui.input_switch(
            'separate_data', 
            'Separate tables for Day/Night values', 
            False
        ),
        ui.help_text(
            'Note: CSV-files always contain the whole dataset and cannot be '
            'splitted into Day/Night tabs. Only applicable for analyzed dataset.'
        ),
        ui.input_radio_buttons(
            'outputformat', 
            'Select output format', 
            {'xlsx': 'Excel', 'csv':'CSV'}, 
            selected='xlsx'
        ),
        ui.input_radio_buttons(
            'outputtable', 
            'Select data to export', 
            {'calc': 'Analyzed', 'raw': 'Raw (concatenated)'}, 
            selected='calc'
        ),
        
        ui.hr(),
        ui.markdown(f'{icon("github")} [GitHub](https://github.com/daheym/DvLIR)'),
        ui.help_text(f'version: {config.VERSION}'),
        
        # Sidebar parameters
        open='always',
        width=config.SIDEBAR_WIDTH
    )


def _create_main_content():
    """Create the main content area."""
    return [
        # Overview section
        ui.h4('Overview'),
        ui.layout_column_wrap(
            ui.value_box(
                'Total energy consumption', 
                value=ui.output_ui('totalkWhconsum'), 
                showcase=icon('plug', 'solid')
            ),
            ui.value_box(
                'Total energy feed', 
                value=ui.output_ui('totalkWhprod'), 
                showcase=icon('solar-panel', 'solid')
            ),
            ui.value_box(
                'Peak energy consumption', 
                value=ui.output_ui('maxkWhconsum'), 
                showcase=icon('power-off', 'solid')
            ),
            ui.value_box(
                'Peak energy feed', 
                value=ui.output_ui('maxkWhprod'), 
                showcase=icon('bolt', 'solid')
            )
        ),
        
        # Data display sections
        ui.h4('Raw data (concatenated)'),
        ui.card(
            ui.output_data_frame('read_files')
        ),
        ui.h4('Processed data'),
        ui.card(
            ui.output_data_frame('show_dataframe'),
        ),
        ui.card(
            ui.output_plot('plot_dataset')
        ),
        ui.card(
            ui.layout_column_wrap(
                ui.download_button(
                    'download_table', 
                    ' Download table', 
                    icon=icon('table', 'solid')
                ),
                ui.download_button(
                    'download_plot', 
                    ' Download plot', 
                    icon=icon('chart-line', 'solid')
                )
            )
        )
    ]
