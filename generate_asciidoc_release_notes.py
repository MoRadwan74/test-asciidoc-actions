#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import argparse
from utils import logger, load_json, save_asciidoc, get_filename_from_path, convert_date, resolve_file_path

RELEASE_NOTES_JSON_DIR = f'docs/modules/user-guide/pages/releases/json'
RELEASE_NOTES_DIR = f'docs/modules/user-guide/pages/releases'
CHILD_PAGES_MARKER = '=== Child pages (hotfixes, MCP Patches, Regression Considerations & JIRAs closed, other relevant info):'
CLOUD_JIRA_URL = 'https://ciena-cloudjira-rd-it.atlassian.net/browse'


def generate_asciidoc(release_notes_data):
    """
    Generates AsciiDoc content from structured JSON data containing release information,
    including highlights and a more structured approach to sections and subsections.
    """
    logger.info(f'Generating AsciiDoc version for release: {release_notes_data["cde_version"]}')
    version_dash = release_notes_data['cde_version'].replace('.', '-')
    asciidoc_content = [
        "# CDE User Guide",
        "include::ROOT:partial$attributes.adoc[]\n",
        f"[[cde-release-{version_dash}]]",
        f"== CDE-Release-{release_notes_data['cde_version']}\n",
        "=== GA Milestone:\n",
        f"{release_notes_data['release_date']}\n",
        "=== Release Overview:\n",
        f"{release_notes_data['overview']}\n"
    ]

    logger.debug('Creating release sections & tickets...')
    # Process sections, subsections, highlights and construct links if associated with tickets
    for section in release_notes_data['sections']:
        asciidoc_content.append(f"=== {section['name']}:\n")
        if 'tickets' in section:
            for ticket in section['tickets']:
                ticket_link = f"* {ticket['title']}: {CLOUD_JIRA_URL}/RD-{ticket['id']}[(RD-{ticket['id']}) {ticket['title']}].\n"
                asciidoc_content.append(ticket_link)
        if 'highlights' in section:
            logger.debug('Populating release highlights...')
            for highlight in section['highlights']:
                highlight_tickets = [
                    ticket for section in release_notes_data['sections'] if 'subsections' in section for subsection in section['subsections']
                    for ticket in subsection['tickets'] if ticket.get('highlight_id') == highlight['id']
                ]
                ticket_links = ', '.join(
                    f"{ticket['title']}: {CLOUD_JIRA_URL}/RD-{ticket['id']}[(RD-{ticket['id']}) {ticket['title']}]"
                    for ticket in highlight_tickets
                )
                if ticket_links:
                    asciidoc_content.append(f"* {highlight['title']} [{ticket_links}].\n")
        if 'subsections' in section:
            for subsection in section['subsections']:
                if subsection['tickets']:
                    asciidoc_content.append(f"==== {subsection['name']}:\n")
                    for ticket in subsection['tickets']:
                        ticket_link = f"* {ticket['title']}: {CLOUD_JIRA_URL}/RD-{ticket['id']}[(RD-{ticket['id']}) {ticket['title']}].\n"
                        asciidoc_content.append(ticket_link)
                else:
                    # If subsection has no tickets, still list the subsection for structure completeness
                    asciidoc_content.append(f"==== {subsection['name']}:\n")

    asciidoc_content.append(CHILD_PAGES_MARKER + "\n\n***")

    # Process patches
    if 'patches' in release_notes_data:
        for patch in release_notes_data['patches']:
            logger.info(f'Populating release patch: {patch["number"]}...')
            patch_content = [
                f"\n=== CDE-Release-{release_notes_data['cde_version']}-patch-{convert_date(patch['release_date'])} ({patch['number']})",
                "\n==== General Description",
                f"\nThis patch was declared Generally Available on {patch['release_date']}. This patch is now supported on CDE to provide the following:\n"
            ]
            patch_content.extend([f"* {ticket['title']}\n" for ticket in patch['tickets']])
            patch_content.append("Relevant Jira tickets are listed below:\n")
            patch_content.extend([f"* {CLOUD_JIRA_URL}/RD-{ticket['id']}[(RD-{ticket['id']}) {ticket['title']}].\n" for ticket in patch['tickets']])
            asciidoc_content.append('\n'.join(patch_content))

    return '\n'.join(asciidoc_content)


def update_antora_structure(cde_version, asciidoc_file_name):
    """
    Updates Antora's structure by adding references to the new release notes in the
    release-notes.adoc and meta.yml files.

    Args:
        cde_version (str): The version of the CDE release.
        asciidoc_file_name (str): The file name of the generated AsciiDoc file.
    """
    logger.info("Updating Antora's structure (i.e., release-notes.adoc and meta.yml)...")
    # Update release-notes.adoc
    release_notes_doc = os.path.join(RELEASE_NOTES_DIR, '../release-notes.adoc')
    release_notes_line = f'\n* xref:releases/{asciidoc_file_name}[CDE-Release-{cde_version}]'
    with open(release_notes_doc, 'r+') as file:
        content = file.read()
        if release_notes_line not in content:
            file.write(release_notes_line)
        else:
            logger.debug(f'Reference for release: "{cde_version}" was already added in release-notes.adoc. No action to do.')

    # Update meta.yml
    meta_yml = os.path.join(RELEASE_NOTES_DIR, '../meta.yml')
    meta_yml_line = f'    - releases/{asciidoc_file_name}\n'
    with open(meta_yml, 'r+') as file:
        lines = file.readlines()
        if meta_yml_line not in lines:
            insert_index = next(i for i, line in enumerate(lines) if '- how-to-guides.adoc' in line)
            lines.insert(insert_index, f'    - releases/{asciidoc_file_name}\n')
            file.seek(0)
            file.writelines(lines)
        else:
            logger.debug(f'Reference for release: "{cde_version}" was already added in meta.yml. No action to do.')

    logger.info('"release-notes.adoc" and "meta.yml" are updated successfully.')


def main():
    parser = argparse.ArgumentParser(description='Generate AsciiDoc from JSON release notes')
    parser.add_argument('-r', '--release', required=True, type=str, help='Release number (e.g., 2.6.0)')
    args = parser.parse_args()

    # Resolve the full path of the release-notes file
    if hasattr(args, 'release'):
        release_notes_file = resolve_file_path(args.release, RELEASE_NOTES_JSON_DIR)
        if not release_notes_file:
            logger.error(f'The given release notes: "{args.release}" JSON file could not be found. Please check the filename and try again.')
            logger.info('If you need to create a new release notes file, use the command: ./release_notes_manager.py create-release-notes -v <version>')
            return

        release_notes_data = load_json(release_notes_file)
        if release_notes_data:
            asciidoc_content = generate_asciidoc(release_notes_data)
            asciidoc_file_path = os.path.join(RELEASE_NOTES_DIR, f"release-{release_notes_data['cde_version']}.adoc")
            save_asciidoc(asciidoc_content, asciidoc_file_path)
            logger.info(f"AsciiDoc file is generated: '{get_filename_from_path(asciidoc_file_path)}' at releases directory.")
            update_antora_structure(release_notes_data['cde_version'], f"release-{release_notes_data['cde_version']}.adoc")
        else:
            logger.error('Failed to load release notes data.')
    else:
        logger.error('No release version provided. Please provide a release version to generate AsciiDoc release notes.')


if __name__ == "__main__":
    main()
