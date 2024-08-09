#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging
import tempfile
import subprocess
import json
from dateutil import parser
import jsonschema.exceptions
import re
from packaging.version import Version, InvalidVersion


# Define module-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


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
        logger.error(f'Error launching editor: {e}')
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
        logger.error(f'File is not found: {path}')
    except IOError as e:
        logger.error(f'Failed to read file {path}: {e}')


def resolve_file_path(release_version, release_notes_dir):
    """
    Searches for the given release_version for a filename within the release_notes_dir directory and returns the full path if found.

    Args:
        release_version (str): The release version of the file to search for.
        release_notes_dir (str): The directory to search for the file.

    Returns:
        str or None: The full path to the file if found, otherwise None.
    """
    filename = f'release-notes-{release_version}.json'
    full_path = os.path.join(release_notes_dir, filename)
    if os.path.exists(full_path):
        return full_path
    return None


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
        logger.error(f'File is not found: "{filepath}"')
    except json.JSONDecodeError:
        logger.error(f'Error decoding JSON from file "{filepath}".')
    except Exception as e:
        logger.error(f'Error loading JSON from file "{filepath}": {e}.')
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
        logger.error(f'Error saving JSON to file "{filepath}": {e}')


def convert_date(input_date: str) -> str:
    """
    Convert a date string from the format '1st January 2024' to 'YYYYMMDD'.

    Args:
        input_date (str): The date string in the format '1st January 2024'.

    Returns:
        str: The date string in the format 'YYYYMMDD'.

    Example:
        >>> convert_date('1st January 2024')
        '20240101'
    """
    parsed_date = parser.parse(input_date)
    formatted_date = parsed_date.strftime('%Y%m%d')
    return formatted_date


def validate_json(data, schema):
    """
    Validate JSON data against a JSON Schema.

    Args:
        data (dict): The JSON data to validate.
        schema (dict): The JSON Schema to validate against.

    Returns:
        bool: True if the JSON data is valid, False otherwise.
    """
    try:
        jsonschema.validate(instance=data, schema=schema)
        return True
    except jsonschema.exceptions.ValidationError as e:
        logger.error(f"JSON schema validation error: {e.message}")
        return False


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
                "tickets": []
            }
            if len(section_names) > 1 or include_subsections:
                section['subsections'] = []
            current_level.append(section)
        current_level = section.get('subsections', [])
    return section


def ticket_exists(sections, ticket_id):
    """
    Recursively check if a ticket with the given ID exists in the sections.

    Args:
        sections (list): List of sections to check.
        ticket_id (str): The ID of the ticket to check for.

    Returns:
        bool: True if the ticket exists, False otherwise.
    """
    for section in sections:
        if any(ticket['id'] == ticket_id for ticket in section.get('tickets', [])):
            return True
        if ticket_exists(section.get('subsections', []), ticket_id):
            return True
    return False


def find_latest_release_notes_file(release_notes_dir):
    """
    Find the release notes file with the latest version.

    Args:
        release_notes_dir (str): Path to the release notes JSON directory.

    Returns:
        str: The file path to the release notes JSON file with the latest version.
    """
    version_pattern = re.compile(r'release-notes-(\d+\.\d+\.\d+)\.json')
    latest_version = None
    latest_file = None

    for filename in os.listdir(release_notes_dir):
        match = version_pattern.match(filename)
        if match:
            try:
                version = Version(match.group(1))
                if latest_version is None or version > latest_version:
                    latest_version = version
                    latest_file = filename
            except InvalidVersion:
                continue

    if latest_file:
        return os.path.join(release_notes_dir, latest_file)
    return None


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
        logger.error(f'Error saving AsciiDoc content to file "{filename}": {e}')
