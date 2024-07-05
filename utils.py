import os
import logging
import tempfile
import subprocess
import json


def setup_logging():
    """
    Setup and configure logger with a basic configuration.

    Returns:
        Logger: Configured logger object.
    """
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def confirm_action(prompt):
    """
    Ask user to confirm an action via input.

    Args:
        prompt (str): The confirmation prompt to display to the user.

    Returns:
        bool: True if user confirms, False otherwise.
    """
    response = input(prompt + " (y/n): ").lower().strip()
    while response not in ['y', 'n', 'yes', 'no']:
        response = input("Please enter 'y' for yes or 'n' for no: ").lower().strip()
    return response in ['y', 'yes']


def launch_overview_editor(default_text, editor='vim'):
    """
    Launches the default system editor with pre-filled text.

    Args:
        default_text (str): Pre-filled text to be placed in the editor.

    Returns:
        str: The text entered or modified by the user in the editor.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix='.tmp', mode='w+', delete=False) as tf:
            tf.write(default_text)
            tf.flush()
            try:
                subprocess.call([editor, tf.name])
            except FileNotFoundError:
                return default_text
            tf.seek(0)
            return tf.read().strip()
    except Exception as e:
        print(f'Error launching editor: {e}')
        return default_text


def get_filename_from_path(path):
    """
    Extract the file name from a given file path.

    Args:
        path (str): The full path to the file.

    Returns:
        str: The file name extracted from the path.
    """
    try:
        return os.path.basename(path)
    except FileNotFoundError:
        print(f'File is not found: {path}')
    except IOError as e:
        print(f'Failed to read file {path}: {e}')


def load_json(filepath):
    """
    Load JSON data from a file.

    Args:
        filepath (str): Path to the JSON file.

    Returns:
        dict: The JSON data loaded from the file.
    """
    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f'File is not found: "{filepath}"')
    except json.JSONDecodeError:
        print(f'Error decoding JSON from file "{filepath}".')
    except Exception as e:
        print(f'Error loading JSON from file "{filepath}": {e}.')
    return None


def save_json(data, filepath):
    """
    Save data to a JSON file.

    Args:
        data (dict): Data to be saved.
        filepath (str): Path to the JSON file where data will be saved.
    """
    try:
        with open(filepath, 'w') as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        print(f'Error saving JSON to file "{filepath}": {e}')


def find_section(existing_sections, section_names):
    """
    Find the section and its parent sections.

    Args:
        existing_sections (list): List of existing sections.
        section_names (list): List of section names from highest to lowest level.

    Returns:
        dict: The final section dictionary where the ticket will be added.

    Raises:
        ValueError: If a section does not exist.
    """
    current_level = existing_sections
    for section_name in section_names:
        section = next((sec for sec in current_level if sec['name'] == section_name), None)
        if section is None:
            raise ValueError(f'Section "{section_name}" does not exist. Please create it using the add-section command.')
        current_level = section.get('subsections', [])
    return section


def create_section_hierarchy(existing_sections, section_names, include_subsections=True):
    """
    Create the section hierarchy based on the provided section names.

    Args:
        existing_sections (list): List of existing sections.
        section_names (list): List of section names from highest to lowest level.
        include_subsections (bool): Whether to include the subsections key in the section.

    Returns:
        dict: The final section dictionary where the ticket will be added.
    """
    current_level = existing_sections
    for section_name in section_names:
        section = next((sec for sec in current_level if sec['name'] == section_name), None)
        if section is None:
            section = {
                "name": section_name,
                "subsections": [] if len(section_names) > 1 or include_subsections else [],
                "tickets": []
            }
            current_level.append(section)
        current_level = section.get('subsections', [])
    return section


def save_asciidoc(content, filename):
    """
    Save content to an AsciiDoc file.

    Args:
        content (str): AsciiDoc content to be saved.
        filepath (str): Path to the AsciiDoc file where content will be saved.
    """
    try:
        with open(filename, 'w') as file:
            file.write(content)
    except Exception as e:
        print(f'Error saving AsciiDoc content to file "{filename}": {e}')
