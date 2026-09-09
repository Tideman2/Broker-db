# app/templates.py
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Create template environment
template_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html"])
)
