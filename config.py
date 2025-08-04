"""
Configuration settings for the DvLIR application.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

@dataclass
class AppConfig:
    """Application configuration settings."""
    
    VERSION: str = '1.3.3'
    DEFAULT_THEME: str = 'cosmo'
    SIDEBAR_WIDTH: str = '300px'
    
    # Test datasets
    TEST_DATASETS: Optional[List[Dict[str, Any]]] = None
    
    # File settings
    ACCEPTED_FILE_TYPES: Optional[List[str]] = None
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # Plot settings
    DEFAULT_DAY_RANGE: Optional[List[int]] = None
    DEFAULT_DPI: int = 600
    
    # Data processing settings
    MIN_THRESHOLD_COLUMNS: int = 2
    UNIX_TIME_CUTOFF: str = '1970-01-30'
    
    def __post_init__(self):
        """Initialize default values that require complex objects."""
        if self.TEST_DATASETS is None:
            self.TEST_DATASETS = [
                {
                    'name': 'dataset1', 
                    'size': 42, 
                    'type': '.csv', 
                    'datapath': 'www/example_data/dataset1.csv'
                },
                {
                    'name': 'dataset2', 
                    'size': 42, 
                    'type': '.csv', 
                    'datapath': 'www/example_data/dataset2.csv'
                }
            ]
        
        if self.ACCEPTED_FILE_TYPES is None:
            self.ACCEPTED_FILE_TYPES = ['.csv']
            
        if self.DEFAULT_DAY_RANGE is None:
            self.DEFAULT_DAY_RANGE = [8, 17]

# Global config instance
config = AppConfig()
