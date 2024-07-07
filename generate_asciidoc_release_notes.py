#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from utils import load_json, save_asciidoc

RELEASE_NOTES_FILE_PATH = f'docs/modules/user-guide/pages/releases/current_release_notes.json'
CHILD_PAGES_MARKER = '=== Child pages (hotfixes, MCP Patches, Regression Considerations & JIRAs closed, other relevant info):'
CLOUD_JIRA_URL = 'https://ciena-cloudjira-rd-it.atlassian.net/browse'
RELEASE_NOTES_DIR = f'docs/modules/user-guide/pages/releases'


def generate_asciidoc(release_notes_data):
    """
    Generates AsciiDoc content from structured JSON data containing release information,
    including highlights and a more structured approach to sections and subsections.
    """
    version_dash = release_notes_data['cde_version'].replace('.', '-')
    asciidoc_content = [
        "# CDE User Guide",
        "include::ROOT:partial$attributes.adoc[]\n",
        f"[[cde-release-{version_dash}]]",
        f"== CDE-Release-{release_notes_data['cde_version']}\n",
        "=== GA Milestone:\n",
        "TBD\n",
        "=== Release Overview:\n",
        f"{release_notes_data['overview']}\n",
        "=== New Content Highlights:"
    ]

    # Process highlights and construct links if associated with tickets
    for highlight in release_notes_data['highlights']:
        highlight_tickets = [
            ticket for section in release_notes_data['sections'] for subsection in section['subsections']
            for ticket in subsection['tickets'] if ticket.get('highlight_id') == highlight['id']
        ]
        ticket_links = ', '.join(
            f"{ticket['title']}: {CLOUD_JIRA_URL}/RD-{ticket['id']}[(RD-{ticket['id']}) {ticket['title']}]"
            for ticket in highlight_tickets
        )
        if ticket_links:
            asciidoc_content.append(f"\n* {highlight['description']} [{ticket_links}].")

    # Process sections and subsections
    for section in release_notes_data['sections']:
        asciidoc_content.append(f"\n=== {section['name']}:\n")
        for subsection in section['subsections']:
            if subsection['tickets']:
                asciidoc_content.append(f"==== {subsection['name']}:\n")
                for ticket in subsection['tickets']:
                    ticket_link = f"* {ticket['title']}: {CLOUD_JIRA_URL}/RD-{ticket['id']}[(RD-{ticket['id']}) {ticket['title']}].\n"
                    asciidoc_content.append(ticket_link)
            else:
                # If subsection has no tickets, still list the subsection for structure completeness
                asciidoc_content.append(f"==== {subsection['name']}:\n")

    asciidoc_content.append(CHILD_PAGES_MARKER)

    # Process patches
    if 'patches' in release_notes_data:
        for patch in release_notes_data['patches']:
            patch_content = [
                f"\n=== CDE-Release-{release_notes_data['cde_version']}-patch-#TO UPDATE# ({patch['number']})",
                "\n==== General Description",
                "\nThis patch was declared Generally Available on #TO UPDATE# 2024. This patch is now supported on CDE to provide the following:\n"
            ]
            patch_content.extend([f"* {ticket['title']}\n" for ticket in patch['tickets']])
            patch_content.append("Relevant Jira tickets are listed below:\n")
            patch_content.extend([f"* {CLOUD_JIRA_URL}/RD-{ticket['id']}[(RD-{ticket['id']}) {ticket['title']}].\n" for ticket in patch['tickets']])
            asciidoc_content.append('\n'.join(patch_content))

    return '\n'.join(asciidoc_content)


def main():
    release_notes_data = load_json(RELEASE_NOTES_FILE_PATH)
    if release_notes_data:
        asciidoc_content = generate_asciidoc(release_notes_data)
        asciidoc_file_path = os.path.join(RELEASE_NOTES_DIR, f"release-{release_notes_data['cde_version']}.adoc")
        save_asciidoc(asciidoc_content, asciidoc_file_path)
        print(f"AsciiDoc file generated: {asciidoc_file_path}")


if __name__ == "__main__":
    main()
