"""
3. Update the routes/__init__.py file to fix circular imports
"""

# api/routes/__init__.py
"""
Routes package initialization
"""
# Don't import blueprints here - this will prevent circular imports
# The application will import blueprints directly from their modules

# Empty __init__.py file - much safer to avoid importing blueprints here