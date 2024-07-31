import io
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from shiny import App, reactive, render, ui
import shinyswatch
from faicons import icon_svg as icon
from datetime import datetime
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import tempfile

#for testing
#remove together with parsefiles button!
test_datasets = [{'name':'dataset1', 'size':42, 'type': '.csv', 'datapath': 'www/example_data/dataset1.csv'},
                 {'name':'dataset2', 'size':42, 'type': '.csv', 'datapath': 'www/example_data/dataset2.csv'}]

#no better solution than storing in global variable
file_format = 'xlsx'

### layout
app_ui = ui.page_fluid(
  ui.hr(),
  ui.panel_title('Analyze DvDIR datasets'),
  ui.hr(),
  ui.page_sidebar(
    ui.sidebar(
      #Sidebar
      ui.h4('Input parameters'),
      ui.input_file(
        'files', 'Select file(s) to upload', multiple=True, accept='.csv', placeholder='no file selected', button_label='Choose'),
      ui.output_data_frame('showselectedfiles'),
      ui.input_action_button(
        'parsefiles', 'Repeat import', disabled=False),
      
      ui.hr(),
      
      ui.h4('Analysis parameters'),
      ui.input_date_range(
        'daterange', 'Select date range'), 
      ui.input_slider(
        'dayrange', 'Select daytime', min=0, max=24, value=[8, 17]),
      # ui.markdown('**Note:** The selected range will be treated as daytime and summarized for the concluding time.'),
      ui.input_action_button(
        'start_analysis', 'Run analysis', disabled=False),

      ui.hr(),
      
      ui.h4('Plot settings'),
      ui.input_checkbox_group(
        'selectverbraucheinspeisung', 'Select traces to plot',
        ['Power consumption (kWh)', 'Power feed (kWh)'], selected=['Power consumption (kWh)', 'Power feed (kWh)']),
      ui.input_checkbox_group(
        'selectdaynight', 'Select timeperiods to plot',
        ['Day', 'Night'], selected=['Day', 'Night']),
      ui.input_radio_buttons(
        'selectmarkerslines', 'Show plot as markers/lines',
        ['Markers', 'Lines'], selected=['Lines']),
      ui.input_action_button(
        'plot_data', 'Update plot', disabled=False),

      ui.hr(),

      ui.h4('Download settings'),
      # ui.input_switch(
      #   'separate_data', 'Separate tables for Day/Night values (applies only to analyzed data)', False),
      ui.input_radio_buttons(
        'outputformat', 'Select output format', {'csv':'CSV'}, selected='csv'),
      # ui.help_text('Note: CSV-files always contain the whole dataset and cannot be splitted into Day/Night tabs.'),
      ui.input_radio_buttons(
        'outputtable', 'Select data to export', {'calc': 'Analyzed', 'raw': 'Raw (combined)'}, selected='calc'),
      
      #parameters for sidebar
      open='always',
      width='300px'
      ),
      
      #Main window
      ui.h4('Overview'),
      ui.layout_column_wrap(
        ui.value_box('Total energy consumption', value=ui.output_ui('totalkWhconsum'), showcase=icon('plug', 'solid')),
        ui.value_box('Total energy production', value=ui.output_ui('totalkWhprod'), showcase=icon('plug-circle-bolt', 'solid')),
        ui.value_box('Peak energy consumption', value=ui.output_ui('maxkWhconsum'), showcase=icon('power-off', 'solid')),
        ui.value_box('Peak energy production', value=ui.output_ui('maxkWhprod'), showcase=icon('bolt', 'solid'))
      ),
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
          ui.download_button('download_table', ' Download table', icon=icon('table', 'solid')),
          ui.download_button('download_plot', ' Download plot', icon=icon('chart-line', 'solid'))
        )
      )

    #more parameters for page_sidebar
  ),
  theme=shinyswatch.theme.cosmo     #cosmo, journal, lumen, [lux]
)
    

### server
def server(input, output, session):

  ## define the reactive variables

  selectedfiles = reactive.Value()
  
  original_data = reactive.Value()
  calculated_data = reactive.Value()
  
  plotted_data = reactive.Value()

  ## function definitions

  #helper function to update daterange slider:
  def update_daterange(df):
    _min = df.index.min()
    _max = df.index.max()
    _off = pd.Timedelta('1day')

    ui.update_date_range('daterange', start=_min, end=_max, min=_min-_off, max=_max+_off)

  #helper functions to update the value boxes
  @render.ui
  def totalkWhconsum() -> str:
    df = original_data.get()
    _total = df['1.8.0[kWh]'].max() - df['1.8.0[kWh]'].min()
    return f'{_total:.4g} kWh'
  
  @render.ui
  def totalkWhprod() -> str:
    df = original_data.get()
    _total = df['2.8.0[kWh]'].max() - df['2.8.0[kWh]'].min()
    return f'{_total:.3g} kWh'
  
  @render.ui
  def maxkWhconsum() -> str:
    df = original_data.get()
    daily_totals = df['1.8.0[kWh]'].resample('D').last()
    daily_increment = daily_totals.diff().reset_index()
    _total = daily_increment['1.8.0[kWh]'].max()
    # df = calculated_data.get()
    # _total = df['Power consumption (kWh)'].max()
    return f'{_total:.3g} kWh'

  @render.ui
  def maxkWhprod() -> str:
    df = original_data.get()
    daily_totals = df['2.8.0[kWh]'].resample('D').last()
    daily_increment = daily_totals.diff().reset_index()
    _total = daily_increment['2.8.0[kWh]'].max()
    # df = calculated_data.get()
    # _total = df['Power feed (kWh)'].max()
    return f'{_total:.3g} kWh'
  

  #helper function to populate the files table
  @reactive.calc
  @render.data_frame
  def showselectedfiles():
    df = selectedfiles.get()
    return render.DataGrid(df, width='100%', height='130px', summary=False)
  
  
  #read the input file(s) into a dataframe
  #and re-format datetime column
  @render.data_frame
  @reactive.event(input.files, input.parsefiles)
  # @reactive.event(input.files)
  def read_files():
    
    df = pd.DataFrame()
    
    if not input.files():
      files = test_datasets
    else:
      files = input.files()

    _names = []

    for file in files:
      path = file['datapath']
      df_temp = pd.read_csv(path, sep=';', index_col=0)
      df = pd.concat([df, df_temp], ignore_index=True)

      name = file['name']
      _names.append(name)

    #update file list; function would have to be splitted here?
    _files = pd.DataFrame({'Files loaded': _names})
    selectedfiles.set(_files)

    #perform calculations
    df = df.drop_duplicates()
    
    df['DateTime'] = df['Date[UTC]'] + '_' + df['Time[UTC]']
    df['DateTime'] = pd.to_datetime(df['DateTime'], format='%d.%m.%Y_%H:%M:%S')
    
    df.set_index('DateTime', drop=True, inplace=True)
    df.drop(['Date[UTC]', 'Time[UTC]', 'DvLIR-SN', 'MeterNumber', 'Status'], axis=1, inplace=True)
    df.sort_index(inplace=True)
    
    df.dropna(thresh=2, inplace=True)

    for col in ['1.8.0[kWh]', '2.8.0[kWh]']:
      df[col] = df[col].str.replace(',', '.').astype(float)

    #update slider and store df
    update_daterange(df)
    original_data.set(df)

    #return data
    return render.DataGrid(df.reset_index(), width='100%', height='150px', summary=False)

  
  #summarize data based on daytime range
  @render.data_frame
  @reactive.event(input.start_analysis)
  def show_dataframe():

    df = original_data.get()
    _daytime = input.dayrange()
    _daterange = input.daterange()

    verbrauch = df[['1.8.0[kWh]','2.8.0[kWh]']]
    verbrauch = verbrauch.resample('1h').min()
    verbrauch["group"] = verbrauch.index.hour.isin(list(_daytime)).cumsum()

    verbrauch = verbrauch.reset_index().groupby("group").agg({"DateTime":"min","1.8.0[kWh]":"min", "2.8.0[kWh]":"min"})
    verbrauch[["1.8.0[kWh]","2.8.0[kWh]"]] = verbrauch[["1.8.0[kWh]","2.8.0[kWh]"]].diff()
    verbrauch = verbrauch.set_index('DateTime')

    verbrauch.columns = ['Power consumption (kWh)', 'Power feed (kWh)']
    verbrauch['Difference (kWh)'] = verbrauch['Power consumption (kWh)'] - verbrauch['Power feed (kWh)']

    verbrauch = verbrauch.loc[_daterange[0]:_daterange[1], :]
    
    calculated_data.set(verbrauch)
    return render.DataGrid(verbrauch.reset_index(), width='100%', height='150px', summary=False)

  
  #function to plot the dataframe
  @render.plot
  @reactive.event(input.plot_data, input.start_analysis)
  # @reactive.event(input.start_analysis)
  def plot_dataset() -> plt.Figure:

    #data import
    df = calculated_data.get()
    _curves = input.selectverbraucheinspeisung()
    _appearance = input.selectmarkerslines()
    _daynight = input.selectdaynight()
    _dayrange = input.dayrange()

    #select day/night datapoints
    _night,_day = _dayrange
    if not len (_daynight) == 2:
      if 'Day' in _daynight:
        df = df.at_time(f'{_day}:00:00')
      elif 'Night' in _daynight:
        df = df.at_time(f'{_night}:00:00')
    
    #plot formatting
    fmt = dict()
    if _appearance == 'Markers':
      fmt = {'marker': 'o', 'ls': ''}
    
    #plotting
    fig,ax = plt.subplots()
    df[list(_curves)].plot(**fmt, ax=ax)
    
    ax.set(xlabel='Date (year-month)', ylabel='Power (kWh)')
    ax.xaxis.set_major_locator(mdates.MonthLocator())

    plotted_data.set(fig)
    return fig
  

  #helper function to provide output file format ending in decorator
  @reactive.effect
  @reactive.event(input.outputformat)
  def fileending():
    global file_format
    file_format = input.outputformat()

  
  #helper function to provide Excel as tempfile
  def create_excel_file(df):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
      workbook = Workbook()
      sheet = workbook.active

      for row in dataframe_to_rows(df, index=True, header=True):
        sheet.append(row)

      workbook.save(temp_file.name)
      return temp_file.name
   
  
  #function to download the results table
  @render.download(filename=f'{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_DvLIR-data.csv')
  def download_table():

    # _format = input.outputformat()
    _table = input.outputtable()
    
    if _table == 'calc':
      df = calculated_data.get()
      
      # if not input.separate_data():
        # if _format == 'xlsx':
        #   file = create_excel_file(df)
        #   yield file
        # elif _format == 'csv':
      yield df.to_csv()
      
      # else:
      #   _daytime = input.dayrange()
      #   with io.BytesIO() as buf:
      #     with pd.ExcelWriter(buf) as writer:
      #       for _time,_period in zip(_daytime, ['Night', 'Day']):
      #         df.reset_index()[df.reset_index()['DateTime'].dt.time.apply(lambda x: x.strftime("%H:%M:%S")).eq(f'{_time}:00:00')].to_excel(writer, sheet_name=f'{_period}')
      #       yield buf.getvalue()

    elif _table == 'raw':
      df = original_data.get()
      
      # if _format == 'xlsx':
      #   pass
      # elif _format == 'csv':
      yield df.to_csv()


  #function to download the plot
  @render.download(filename=f'{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_DvLIR-plot.png')
  def download_plot():
    fig = plotted_data.get()
    with io.BytesIO() as buf:
      fig.savefig(buf, format='png', dpi=600, bbox_inches='tight')
      yield buf.getvalue()


### App
app = App(app_ui, server)