"""
Main application file for the DvLIR analyzer.
This is the refactored version with improved code organization.
"""
from shiny import App
import shinyswatch

# Import our modular components
from ui.layout import create_ui
from server.handlers import create_server
from server.state import AppState


def create_app():
    """
    Create and configure the DvLIR application.
    
    Returns:
        Configured Shiny App instance
    """
    # Create application state
    app_state = AppState()
    
    # Create UI and server components
    app_ui = create_ui()
    server_func = create_server(app_state)
    
    # Create and return the app
    return App(app_ui, server_func)


# Create the app instance
app = create_app()

if __name__ == "__main__":
    # Run the app if executed directly
    app.run()
