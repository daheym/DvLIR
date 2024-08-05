import io
from tkinter import N, NO
from turtle import st
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

#version string
_version = '1.3.0'

#datasets for testing, stored in www/example_data
#is loaded when Import button is pressed without specifying input files
test_datasets = [{'name':'dataset1', 'size':42, 'type': '.csv', 'datapath': 'www/example_data/dataset1.csv'},
                 {'name':'dataset2', 'size':42, 'type': '.csv', 'datapath': 'www/example_data/dataset2.csv'}]

#no better solution than storing in global variables
_execution = False
_ymaxrange = (None, None)

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
        'files', 'Select file(s) to upload', multiple=True, accept='.csv', placeholder='no file selected', button_label='Browse'),
      ui.output_data_frame('showselectedfiles'),
      ui.layout_column_wrap(
        ui.input_action_button(
          'parsefiles', 'Import', icon=icon('file-import', 'solid')),
        ui.input_action_button(
          'addfiles', 'Add Files', icon=icon('square-plus', 'solid')),
        width=.5),
      
      ui.hr(),
      
      ui.h4('Analysis parameters'),
      ui.input_date_range(
        'daterange', 'Select date range'), 
      ui.input_slider(
        'dayrange', 'Select daytime', min=0, max=24, value=[8, 17]),
      # ui.markdown('**Note:** The selected range will be treated as daytime and summarized for the concluding time.'),
      ui.layout_column_wrap(
        ui.input_action_button(
          'start_analysis', 'Analyze', icon=icon('magnifying-glass-chart', 'solid')),
        ui.input_action_button(
          'reset_analysis', 'Reset', icon=icon('arrow-rotate-left', 'solid')),
        width=.5),

      ui.hr(),
      
      ui.h4('Plot settings'),
      ui.input_checkbox_group(
        'selectconsumptionfeed', 'Select traces to plot',
        ['Power consumption (kWh)', 'Power feed (kWh)'], selected=['Power consumption (kWh)', 'Power feed (kWh)']),
      ui.input_checkbox_group(
        'selectdaynight', 'Select timeperiods to plot',
        ['Day', 'Night'], selected=['Day', 'Night']),
      # ui.HTML('<hr style="border-style: dotted;" />'),
      ui.input_radio_buttons(
        'selectmarkerslines', 'Show plot as markers/lines',
        ['Markers', 'Lines'], selected='Lines'),
      ui.input_slider('plotyrange', 'Optional: Adjust kWh-axis range', min=0, max=10, value=(None,None), step=.25),
      ui.layout_column_wrap(
        ui.input_action_button(
        'plot_data', 'Plot', icon=icon('chart-line', 'solid')),
        ui.input_action_button(
        'reset_plot', 'Reset', icon=icon('arrow-rotate-left', 'solid')),
        width=.5),

      ui.hr(),

      ui.h4('Download settings'),
      ui.input_switch(
        'separate_data', 'Separate tables for Day/Night values', False),
      ui.help_text('Note: CSV-files always contain the whole dataset and cannot be splitted into Day/Night tabs. Only applicable for analyzed dataset.'),
      ui.input_radio_buttons(
        'outputformat', 'Select output format', {'xlsx': 'Excel', 'csv':'CSV'}, selected='xlsx'),
      ui.input_radio_buttons(
        'outputtable', 'Select data to export', {'calc': 'Analyzed', 'raw': 'Raw (concatenated)'}, selected='calc'),
      
      ui.hr(),
      ui.markdown(f'{icon('github')} [GitHub](https://github.com/daheym/DvLIR)'),
      ui.help_text(f'version: {_version}'),
      
      #parameters for sidebar
      open='always',
      width='300px'
      ),
      
      #Main window
      ui.h4('Overview'),
      ui.layout_column_wrap(
        ui.value_box('Total energy consumption', value=ui.output_ui('totalkWhconsum'), showcase=icon('plug', 'solid')),
        ui.value_box('Total energy feed', value=ui.output_ui('totalkWhprod'), showcase=icon('solar-panel', 'solid')), #plug-circle-bolt
        ui.value_box('Peak energy consumption', value=ui.output_ui('maxkWhconsum'), showcase=icon('power-off', 'solid')),
        ui.value_box('Peak energy feed', value=ui.output_ui('maxkWhprod'), showcase=icon('bolt', 'solid'))
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
  # plot_yrange = reactive.Value()

  outfile_data_name = reactive.Value()
  # outfile_icon = reactive.Value(icon('file-excel', 'solid'))

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

    #remove duplicate entries
    df = df.drop_duplicates()
    
    #create DateTime index
    df['DateTime'] = df['Date[UTC]'] + '_' + df['Time[UTC]']
    df['DateTime'] = pd.to_datetime(df['DateTime'], format='%d.%m.%Y_%H:%M:%S')
    
    df.set_index('DateTime', drop=True, inplace=True)
    df.drop(['Date[UTC]', 'Time[UTC]', 'DvLIR-SN', 'MeterNumber', 'Status'], axis=1, inplace=True)
    df.sort_index(inplace=True)
    
    df.dropna(thresh=2, inplace=True)
    
    #remove data from 1st Jan 1970 (appear when device is switched on; likely Unix time error)
    _drop1970 = df[df.index < pd.to_datetime('1970-01-30')].index
    df = df.drop(_drop1970)

    #convert data to floats
    for col in ['1.8.0[kWh]', '2.8.0[kWh]']:
      df[col] = df[col].str.replace(',', '.').astype(float)

    #update slider and store df
    update_daterange(df)
    original_data.set(df)

    #update global variable
    global _execution
    _execution = False

    #return data
    return render.DataGrid(df.reset_index(), width='100%', height='150px', summary=False)

  
  #summarize data based on daytime range
  @render.data_frame
  @reactive.event(input.start_analysis)
  def show_dataframe():

    df = original_data.get()
    _daytime = input.dayrange()
    _daterange = input.daterange()

    df_calc = df[['1.8.0[kWh]','2.8.0[kWh]']]
    df_calc = df_calc.resample('1h').min()
    df_calc["group"] = df_calc.index.hour.isin(list(_daytime)).cumsum()

    df_calc = df_calc.reset_index().groupby("group").agg({"DateTime":"min", "1.8.0[kWh]":"min", "2.8.0[kWh]":"min"})
    df_calc[["1.8.0[kWh]","2.8.0[kWh]"]] = df_calc[["1.8.0[kWh]","2.8.0[kWh]"]].diff()
    df_calc = df_calc.set_index('DateTime')

    df_calc.columns = ['Power consumption (kWh)', 'Power feed (kWh)']
    df_calc['Difference (kWh)'] = df_calc['Power consumption (kWh)'] - df_calc['Power feed (kWh)']

    df_calc = df_calc.loc[_daterange[0]:_daterange[1], :]
    
    #no good solution: leads to lines connecting empty time intervals!
    # df_calc = df_calc.dropna()
    
    calculated_data.set(df_calc)
    return render.DataGrid(df_calc.dropna().reset_index(), width='100%', height='150px', summary=False)

  
  #function to reset the plot settings
  @reactive.effect()
  @reactive.event(input.reset_plot)
  def reset_plot_params():
    ui.update_checkbox_group('selectconsumptionfeed', selected=['Power consumption (kWh)', 'Power feed (kWh)'])
    ui.update_checkbox_group('selectdaynight', selected=['Day', 'Night'])
    ui.update_radio_buttons('selectmarkerslines', selected='Lines')
    
    #this correct?!
    ui.update_slider('plotyrange', value=(None,None))

    global _execution
    _execution = False

  
  #helper function to update the plotyrange.slider
  def update_plotyrange(max, value):
    ui.update_slider('plotyrange', max=max, value=value)
 
  
  #function to plot the dataframe
  @render.plot
  @reactive.event(input.plot_data, input.start_analysis)
  def plot_dataset() -> plt.Figure:

    #data import
    df = calculated_data.get()
    _curves = input.selectconsumptionfeed()
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
      else:
        df = pd.DataFrame(columns=['Power consumption (kWh)', 'Power feed (kWh)'])
    
    #plot formatting
    fmt = dict()
    if _appearance == 'Markers':
      fmt = {'marker': 'o', 'ls': ''}
    
    #plotting
    fig,ax = plt.subplots()
    df[list(_curves)].plot(**fmt, ax=ax)

    #store initial y-axis range settings
    #and set variable to remember that function has been executed initially
    global _execution
    global _ymaxrange
    if not _execution: 
      _execution = True
      _yrange = tuple([round(i, 2) for i in ax.get_ylim()])
      _ymaxrange = tuple([i if i>0 else 0 for i in _yrange])
         
      #why is this not executed right away?!
      update_plotyrange(max=_yrange[1], value=_ymaxrange)
      _ylim = (None,None)
    
    ##ToDo: update slider upon checkbox changes!
    
    #set ylim parameter;
    #check if slider set onto stored values, then set ylim to (None,None)
    else:
      _ylim = input.plotyrange()
      if _ylim == _ymaxrange:
        _ylim = (None,None)
      elif _ylim[0] == 0:
        _ylim = (None, _ylim[1])
    
    #set ax parameters
    ax.set(xlabel='Date (year-month)', ylabel='Power (kWh)', ylim=_ylim)
    ax.xaxis.set_major_locator(mdates.MonthLocator())

    #store and return figure
    plotted_data.set((fig,ax))
    return fig
  
  
  #helper function to update the 'plotyrange' slider after the checkboxes are changed
  #would require to split the plotting function into plot generation & plot returnal
  # @reactive.effect
  # @reactive.event(input.plot_data)
  # def updateyrange():
    # pass
    # _,ax = plotted_data.get()
    # _yrange = tuple([round(i, 2) for i in ax.get_ylim()])
    # _ymaxrange = tuple([i if i>0 else 0 for i in _yrange])
    # update_plotyrange(max=_yrange[1], value=_ymaxrange)
  

  #helper function to toggle separate switch to off when csv or raw is chosen
  @reactive.effect
  def toggleswitchoff():
    if input.outputformat() == 'csv' or input.outputtable() == 'raw':
      ui.update_switch('separate_data', value=False)

  
  #helper function to change output format to Excel when toggle is activatedn & set dataset to calc
  @reactive.effect()
  def setoutputtoexcel():
    if input.separate_data():
      ui.update_radio_buttons('outputformat', selected='xlsx')
      ui.update_radio_buttons('outputtable', selected='calc')

  
  #helper function to change download button icon
  #Note: not supported yet... maybe in future?!
  # @reactive.effect()
  # def setoutputicon():
  #   if input.outputformat() == 'xlsx':
  #     ui.update_download_button('download_table', icon=icon('file-excel', 'solid'))
  #   elif input.outputformat() == 'csv':
  #     ui.update_download_button('download_table', icon=icon('file-csv', 'solid'))

  
  #helper function to yield multi-sheet Excel file
  def create_multi_sheet_excel_file(df):
    
    # _split = input.separate_data()
    _daytime = input.dayrange()
  
    with io.BytesIO() as buf:  
      with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        for _time,_period in zip(_daytime, ['Night', 'Day']):

          _sheet = f'{_period}_{_time:02}'

          dfx = df.reset_index()
          dfx = dfx[dfx['DateTime'].dt.time.apply(lambda x: x.strftime("%H:%M:%S")).eq(f'{_time:02}:00:00')]
          dfx['DateTime'] = dfx['DateTime'].astype(str)

          dfx.to_excel(writer, index=False, sheet_name=_sheet)

      buf.seek(0)
      return buf.getvalue()

  
  #helper function to provide Excel as tempfile
  #Note: not working, not used
  def create_excel_file(df):

    _split = input.separate_data()
    _daytime = input.dayrange()

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
      workbook = Workbook()
      sheet = workbook.active
      sheet.title = 'data'

      if not _split:
        for row in dataframe_to_rows(df, index=True, header=True):
          sheet.append(row)

      else:
        for _time,_period in zip(_daytime, ['Night', 'Day']):
          _sheet = f'{_period}_{_time:02}'
          workbook.create_sheet(_sheet)
          sheet = workbook[_sheet]

          dfx = df.reset_index()
          dfx = dfx[dfx['DateTime'].dt.time.apply(lambda x: x.strftime("%H:%M:%S")).eq(f'{_time:02}:00:00')]
          # dfx = dfx.set_index('DateTime') #wrong DateTime, likely due to Unix time format
          dfx['DateTime'] = dfx['DateTime'].astype(str)

          for row in dataframe_to_rows(
            dfx, 
            index=True, header=True
          ):
            sheet.append(row)
        
        del workbook['data']
          
      workbook.save(temp_file.name)
      return temp_file.name
   
  
  #helper function to create the name of the downloaded data table
  @reactive.effect()
  def construct_download_filename():
    _format = input.outputformat()
    _table = input.outputtable()
    
    outfile_data_name.set(f'{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_DvLIR-data_{_table}.{_format}')
    
   
  #function to download the results table
  @render.download(filename=lambda: outfile_data_name.get())
  def download_table():

    _format = input.outputformat()
    _table = input.outputtable()
    
    #get data table
    if _table == 'calc':
      df = calculated_data.get()
    elif _table == 'raw':
      df = original_data.get()
    
    _split = input.separate_data()
    
    #respond to output format
    if _format == 'xlsx':
      if not _split:
        with io.BytesIO() as buf:
          df.to_excel(buf, sheet_name='data')
          yield buf.getvalue()
      
      else:
        yield create_multi_sheet_excel_file(df)
   
    elif _format == 'csv':
      yield df.to_csv()
      

  #function to download the plot
  @render.download(filename=f'{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_DvLIR-plot.png')
  def download_plot():
    fig,ax = plotted_data.get()
    
    with io.BytesIO() as buf:
      fig.savefig(buf, format='png', dpi=600, bbox_inches='tight')
      yield buf.getvalue()


### App
app = App(app_ui, server)