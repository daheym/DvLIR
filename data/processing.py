"""
Data processing functions for the DvLIR application.
"""
import pandas as pd
from typing import List, Dict, Any, Tuple
from config import config


def load_and_process_files(files: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, List[str]]:
    """
    Load and process CSV files into a consolidated DataFrame.
    
    Args:
        files: List of file dictionaries with 'name' and 'datapath' keys
        
    Returns:
        Tuple of (processed_dataframe, list_of_filenames)
    """
    df = pd.DataFrame()
    file_names = []
    
    # Use test datasets if no files provided
    if not files:
        files = config.TEST_DATASETS or []
    
    # Process each file
    for file in files:
        try:
            path = file['datapath']
            df_temp = pd.read_csv(path, sep=';', index_col=0)
            df = pd.concat([df, df_temp], ignore_index=True)
            file_names.append(file['name'])
        except Exception as e:
            print(f"Error loading file {file.get('name', 'unknown')}: {e}")
            continue
    
    if df.empty:
        return df, file_names
    
    # Clean and process the data
    df = clean_dataframe(df)
    
    return df, file_names


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and preprocess the raw dataframe.
    
    Args:
        df: Raw dataframe from CSV files
        
    Returns:
        Cleaned and processed dataframe
    """
    if df.empty:
        return df
    
    # Remove duplicate entries
    df = df.drop_duplicates()
    
    # Create DateTime index
    df['DateTime'] = df['Date[UTC]'] + '_' + df['Time[UTC]']
    df['DateTime'] = pd.to_datetime(df['DateTime'], format='%d.%m.%Y_%H:%M:%S')
    
    # Set DateTime as index and drop unnecessary columns
    df.set_index('DateTime', drop=True, inplace=True)
    columns_to_drop = ['Date[UTC]', 'Time[UTC]', 'DvLIR-SN', 'MeterNumber', 'Status']
    df.drop([col for col in columns_to_drop if col in df.columns], axis=1, inplace=True)
    
    # Sort by index
    df.sort_index(inplace=True)
    
    # Remove rows with too many NaN values
    df.dropna(thresh=config.MIN_THRESHOLD_COLUMNS, inplace=True)
    
    # Remove data from 1st Jan 1970 (Unix time errors)
    cutoff_date = pd.to_datetime(config.UNIX_TIME_CUTOFF)
    drop_1970 = df[df.index < cutoff_date].index
    df = df.drop(drop_1970)
    
    # Convert data to floats
    for col in ['1.8.0[kWh]', '2.8.0[kWh]']:
        if col in df.columns:
            df[col] = df[col].str.replace(',', '.').astype(float)
    
    return df


def calculate_energy_data(df: pd.DataFrame, daytime_range: List[int]) -> pd.DataFrame:
    """
    Calculate energy consumption and production data based on daytime range.
    
    Args:
        df: Original dataframe with energy data
        daytime_range: List of [start_hour, end_hour] for daytime period
        
    Returns:
        Processed dataframe with calculated values
    """
    if df.empty:
        return pd.DataFrame()
    
    # Select relevant columns
    df_calc = df[['1.8.0[kWh]', '2.8.0[kWh]']].copy()
    
    # Resample to hourly data
    df_calc = df_calc.resample('1h').min()
    
    # Group by daytime/nighttime periods
    df_calc["group"] = df_calc.index.hour.isin(list(daytime_range)).cumsum()
    
    # Aggregate by groups
    df_calc = df_calc.reset_index().groupby("group").agg({
        "DateTime": "min", 
        "1.8.0[kWh]": "min", 
        "2.8.0[kWh]": "min"
    })
    
    # Calculate differences (actual consumption/production)
    df_calc[["1.8.0[kWh]", "2.8.0[kWh]"]] = df_calc[["1.8.0[kWh]", "2.8.0[kWh]"]].diff()
    
    # Set DateTime as index
    df_calc = df_calc.set_index('DateTime')
    
    # Rename columns to more descriptive names
    df_calc.columns = ['Power consumption (kWh)', 'Power feed (kWh)']
    
    # Calculate difference
    df_calc['Difference (kWh)'] = df_calc['Power consumption (kWh)'] - df_calc['Power feed (kWh)']
    
    return df_calc


def calculate_energy_statistics(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate energy statistics from the original dataframe.
    
    Args:
        df: Original dataframe with cumulative energy data
        
    Returns:
        Dictionary with energy statistics
    """
    if df.empty:
        return {
            'total_consumption': 0.0,
            'total_production': 0.0,
            'max_daily_consumption': 0.0,
            'max_daily_production': 0.0
        }
    
    stats = {}
    
    # Total energy (difference between max and min cumulative values)
    if '1.8.0[kWh]' in df.columns:
        stats['total_consumption'] = df['1.8.0[kWh]'].max() - df['1.8.0[kWh]'].min()
    else:
        stats['total_consumption'] = 0.0
        
    if '2.8.0[kWh]' in df.columns:
        stats['total_production'] = df['2.8.0[kWh]'].max() - df['2.8.0[kWh]'].min()
    else:
        stats['total_production'] = 0.0
    
    # Peak daily values
    try:
        if '1.8.0[kWh]' in df.columns:
            daily_consumption = df['1.8.0[kWh]'].resample('D').last()
            daily_consumption_increment = daily_consumption.diff()
            stats['max_daily_consumption'] = daily_consumption_increment.max()
        else:
            stats['max_daily_consumption'] = 0.0
            
        if '2.8.0[kWh]' in df.columns:
            daily_production = df['2.8.0[kWh]'].resample('D').last()
            daily_production_increment = daily_production.diff()
            stats['max_daily_production'] = daily_production_increment.max()
        else:
            stats['max_daily_production'] = 0.0
    except Exception:
        stats['max_daily_consumption'] = 0.0
        stats['max_daily_production'] = 0.0
    
    return stats


def filter_data_by_date_range(df: pd.DataFrame, date_range: Tuple[str, str]) -> pd.DataFrame:
    """
    Filter dataframe by date range.
    
    Args:
        df: Dataframe to filter
        date_range: Tuple of (start_date, end_date) as strings
        
    Returns:
        Filtered dataframe
    """
    if df.empty or not date_range or len(date_range) != 2:
        return df
    
    try:
        return df.loc[date_range[0]:date_range[1], :]
    except Exception:
        return df


def filter_data_by_time_periods(df: pd.DataFrame, day_night_selection: List[str], 
                               daytime_range: List[int]) -> pd.DataFrame:
    """
    Filter dataframe by day/night time periods.
    
    Args:
        df: Dataframe to filter
        day_night_selection: List containing 'Day' and/or 'Night'
        daytime_range: List of [start_hour, end_hour] for daytime period
        
    Returns:
        Filtered dataframe
    """
    if df.empty or not day_night_selection:
        return pd.DataFrame(columns=['Power consumption (kWh)', 'Power feed (kWh)'])
    
    if len(day_night_selection) == 2:
        # Both day and night selected, return all data
        return df
    
    night_hour, day_hour = daytime_range
    
    if 'Day' in day_night_selection:
        # Filter for daytime hours - use at_time to match original logic
        return df.at_time(f'{day_hour:02d}:00:00')
    elif 'Night' in day_night_selection:
        # Filter for nighttime hours - use at_time to match original logic
        return df.at_time(f'{night_hour:02d}:00:00')
    else:
        return pd.DataFrame(columns=['Power consumption (kWh)', 'Power feed (kWh)'])
