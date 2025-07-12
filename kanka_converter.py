import json
import os
import re
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
# Set the path to your main Kanka export folder
INPUT_DIRECTORY = 'SET/THE/PATH/TO/YOUR/kanka-export-here'
# Set the path where you want the text files to be saved
OUTPUT_DIRECTORY = 'NotebookLM_Files/'
# --- END CONFIGURATION ---


def clean_html(html_content):
    """
    Cleans an HTML string by converting it to formatted plain text.
    Removes instructional links and converts tags to readable text.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove Kanka-specific instructional links
    for a in soup.find_all('a', href=True):
        if 'app.kanka.io' in a['href'] and 'click here' in a.get_text().lower():
            p = a.find_parent('p')
            if p:
                p.decompose()

    # Convert basic HTML tags to plain text with formatting
    text_parts = []
    for element in soup.find_all(['p', 'ul', 'h3', 'h4', 'b', 'strong', 'i', 'em']):
        if element.name == 'p':
            text_parts.append(element.get_text().strip() + '\n')
        elif element.name == 'ul':
            for li in element.find_all('li'):
                text_parts.append(f"- {li.get_text().strip()}\n")
            text_parts.append('\n')
        elif element.name in ['h3', 'h4', 'b', 'strong']:
            text_parts.append(f"{element.get_text().strip()}\n")
        elif element.name in ['i', 'em']:
            # For quotes/italics, we can wrap in blockquote-style '>'
            lines = [f"> {line.strip()}" for line in element.get_text().split('\n')]
            text_parts.append('\n'.join(lines) + '\n')

    # Fallback for content that isn't in a recognized tag
    if not text_parts:
        return soup.get_text()
        
    return "".join(text_parts).strip()


def resolve_mentions(text, id_map):
    """
    Finds all Kanka-style mentions like [character:1234] and replaces
    them with the proper 'Name (Type)' format using the id_map.
    """
    if not text:
        return ""
        
    def replace_func(match):
        entity_id = int(match.group(2))
        if entity_id in id_map:
            entry = id_map[entity_id]
            return f"{entry['name']} ({entry['type']})"
        else:
            entity_type = match.group(1).capitalize()
            return f"[{entity_type} Not Found: {entity_id}]"

    # Regex to find patterns like [character:12345] or [family:54321|Optional Name]
    pattern = r'\[([a-zA-Z]+):(\d+)(?:\|[^\]]*)?\]'
    return re.sub(pattern, replace_func, text)


def create_id_map(input_dir):
    """
    PASS 1: Scans all JSON files to create a master map of
    {id: {'name': name, 'type': type_name}}.
    """
    print("--- Starting Pass 1: Indexing all entities ---")
    id_map = {}
    
    type_name_map = {
        'characters': 'Character',
        'families': 'Family',
        'locations': 'Location',
        'journals': 'Journal',
        'notes': 'Note',
        'organisations': 'Organisation',
        'races': 'Race'
    }

    for root, _, files in os.walk(input_dir):
        for filename in files:
            if filename.endswith('.json'):
                folder_name = os.path.basename(root)
                if folder_name not in type_name_map:
                    continue
                entity_type_display = type_name_map[folder_name]

                file_path = os.path.join(root, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        # FIX: Kanka export is double-encoded. Load once to get the string,
                        # then load the string to get the data dictionary.
                        data_string = json.load(f)
                        data = json.loads(data_string)
                        
                        entity_id = data.get('id')
                        name = data.get('name')
                        if entity_id and name:
                            id_map[entity_id] = {'name': name, 'type': entity_type_display}
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"Warning: Could not parse JSON from {filename}. Error: {e}")
    
    print(f"Indexing complete. Found {len(id_map)} unique entities.")
    return id_map


def generate_text_files(input_dir, output_dir, id_map):
    """
    PASS 2: Processes each JSON file, formats its content, and aggregates it
    into one text file per entity type.
    """
    print("\n--- Starting Pass 2: Generating consolidated text files ---")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # A dictionary to hold the collected text for each entity type
    # e.g., {'characters': ['content of char1', 'content of char2'], ...}
    output_buffers = {
        'characters': [], 'families': [], 'locations': [],
        'journals': [], 'notes': [], 'organisations': [], 'races': []
    }
    
    type_name_map = {
        'characters': 'Character', 'families': 'Family', 'locations': 'Location',
        'journals': 'Journal', 'notes': 'Note', 'organisations': 'Organisation',
        'races': 'Race'
    }

    # First, process all files and store their content in memory
    for root, _, files in os.walk(input_dir):
        for filename in files:
            if not filename.endswith('.json'):
                continue
            
            folder_name = os.path.basename(root)
            if folder_name not in output_buffers:
                continue

            file_path = os.path.join(root, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data_string = json.load(f)
                    data = json.loads(data_string)
                    
                    # Get the formatted content for this single entity
                    content = format_entity(data, root, id_map)
                    
                    if content:
                        # Resolve the mentions and add the result to the buffer
                        resolved_content = resolve_mentions(content, id_map)
                        output_buffers[folder_name].append(resolved_content)
                        print(f"  - Processed {filename}")

                except (json.JSONDecodeError, TypeError) as e:
                    print(f"Warning: Skipping invalid JSON file {filename}. Error: {e}")

    # Now, write the contents of each buffer to a single file
    print("\n--- Writing consolidated files ---")
    for entity_type, content_list in output_buffers.items():
        if not content_list:
            print(f"  - No content for type '{entity_type}', skipping file.")
            continue
            
        output_filename = f"{entity_type}.txt"
        output_path = os.path.join(output_dir, output_filename)
        
        # Join all individual entries with a clear separator
        separator = "\n\n\n" + ("=" * 80) + "\n\n\n"
        final_content = separator.join(content_list)
        
        with open(output_path, 'w', encoding='utf-8') as out_f:
            out_f.write(final_content)
        print(f"  -> Successfully created {output_filename}")


def format_entity(data, root, id_map):
    """
    Main router function to call the correct formatter based on the folder.
    """
    folder_name = os.path.basename(root)
    name = data.get('name', 'Unnamed')
    entity_id = data.get('id')
    
    # Base header for all files
    header = f"========================================\n {folder_name.upper()[:-1]}: {name}\n========================================\n\n"
    
    # Call the specific formatter
    if folder_name == 'characters':
        body = format_character(data, id_map)
    elif folder_name == 'families':
        body = format_family(data, id_map)
    elif folder_name == 'journals':
        body = format_journal(data)
    elif folder_name == 'locations':
        body = format_location(data)
    elif folder_name == 'notes':
        body = format_note(data)
    elif folder_name == 'organisations':
        body = format_organisation(data, id_map)
    elif folder_name == 'races':
        body = format_race(data)
    else:
        return None # Skip unknown types

    return header + body

# --- Specific Formatters for Each Entity Type ---

def format_character(data, id_map):
    parts = ["[Basic Information]"]
    parts.append(f"Name: {data.get('name', 'N/A')}")
    if data.get('title'): parts.append(f"Title: {data.get('title')}")
    if data.get('type'): parts.append(f"Type: {data.get('type')}")
    if data.get('sex'): parts.append(f"Sex: {data.get('sex')}")

    if data.get('character_races'):
        race_id = data['character_races'][0]['race_id']
        race_info = id_map.get(race_id)
        parts.append(f"Race: {race_info['name'] if race_info else 'Unknown'}")
        
    if data.get('character_families'):
        family_id = data['character_families'][0]['family_id']
        family_info = id_map.get(family_id)
        parts.append(f"Family: {family_info['name'] if family_info else 'Unknown'}")

    parts.append("\n---\n[Primary Description]\n")
    parts.append(clean_html(data.get('entry')))

    if data.get('entity', {}).get('posts'):
        for post in data['entity']['posts']:
            parts.append(f"\n---\n[Notes: {post.get('name')}]\n")
            parts.append(clean_html(post.get('entry')))
            
    return "\n".join(parts)

def format_family(data, id_map):
    parts = ["[Basic Information]"]
    parts.append(f"Name: {data.get('name', 'N/A')}")
    if data.get('entity', {}).get('type'):
        parts.append(f"Type: {data['entity']['type']}")
        
    if data.get('pivotMembers'):
        parts.append("\n[Members]")
        for member in data['pivotMembers']:
            char_id = member['character_id']
            member_info = id_map.get(char_id)
            if member_info:
                parts.append(f"- {member_info['name']} (Character)")
            else:
                parts.append(f"- [Character Not Found: {char_id}]")

    parts.append("\n---\n[Primary Description]\n")
    parts.append(clean_html(data.get('entity', {}).get('entry')))

    if data.get('entity', {}).get('posts'):
        for post in data['entity']['posts']:
            parts.append(f"\n---\n[Notes: {post.get('name')}]\n")
            parts.append(clean_html(post.get('entry')))
            
    return "\n".join(parts)
    
def format_journal(data):
    parts = ["[Basic Information]"]
    parts.append(f"Title: {data.get('name', 'N/A')}")
    if data.get('entity', {}).get('type'):
        parts.append(f"Type: {data['entity']['type']}")
    if data.get('date'):
        parts.append(f"Date: {data.get('date')}")

    parts.append("\n---\n[Primary Description]\n")
    parts.append(clean_html(data.get('entity', {}).get('entry')))
    
    if data.get('entity', {}).get('posts'):
        for post in data['entity']['posts']:
            parts.append(f"\n---\n[Entry: {post.get('name')}]\n")
            parts.append(clean_html(post.get('entry')))

    return "\n".join(parts)

def format_location(data):
    parts = ["[Basic Information]"]
    parts.append(f"Name: {data.get('name', 'N/A')}")
    if data.get('entity', {}).get('type'):
        parts.append(f"Type: {data['entity']['type']}")
    status = "Destroyed" if data.get('is_destroyed') else "Intact"
    parts.append(f"Status: {status}")

    parts.append("\n---\n[Primary Description]\n")
    parts.append(clean_html(data.get('entity', {}).get('entry')))
    
    if data.get('entity', {}).get('posts'):
        for post in data['entity']['posts']:
            parts.append(f"\n---\n[Notes: {post.get('name')}]\n")
            parts.append(clean_html(post.get('entry')))
            
    return "\n".join(parts)

def format_note(data):
    parts = ["[Primary Content]\n"]
    entry_text = data.get('entity', {}).get('entry', '')
    # For prophecies, blockquote the indented parts
    cleaned_entry = clean_html(entry_text)
    parts.append(cleaned_entry)
    return "\n".join(parts)

def format_organisation(data, id_map):
    parts = ["[Basic Information]"]
    parts.append(f"Name: {data.get('name', 'N/A')}")
    if data.get('entity', {}).get('type'):
        parts.append(f"Type: {data['entity']['type']}")
    status = "Defunct" if data.get('is_defunct') else "Active"
    parts.append(f"Status: {status}")

    if data.get('pivotLocations'):
        loc_id = data['pivotLocations'][0]['location_id']
        loc_info = id_map.get(loc_id)
        if loc_info:
            parts.append(f"\n[Location]\nBased in: {loc_info['name']} ({loc_info['type']})")
        
    parts.append("\n---\n[Primary Description]\n")
    parts.append(clean_html(data.get('entity', {}).get('entry')))

    if data.get('members'):
        parts.append("\n---\n[Members Roster]")
        for member in data['members']:
            role = member.get('role', 'Member')
            char_id = member['character_id']
            member_info = id_map.get(char_id)
            parts.append(f"\n- Role: {role}")
            if member_info:
                parts.append(f"  - Member: {member_info['name']} ({member_info['type']})")
            else:
                parts.append(f"  - Member: [Character Not Found: {char_id}]")
                
    return "\n".join(parts)

def format_race(data):
    parts = ["[Basic Information]"]
    parts.append(f"Name: {data.get('name', 'N/A')}")
    if data.get('entity', {}).get('type'):
        parts.append(f"Type: {data['entity']['type']}")
    status = "Extinct" if data.get('is_extinct') else "Extant"
    parts.append(f"Status: {status}")

    parts.append("\n---\n[Primary Description]\n")
    parts.append(clean_html(data.get('entity', {}).get('entry')))
    
    return "\n".join(parts)


def main():
    """Main function to orchestrate the conversion process."""
    id_map = create_id_map(INPUT_DIRECTORY)
    generate_text_files(INPUT_DIRECTORY, OUTPUT_DIRECTORY, id_map)
    print("\nAll done! Your files are ready in the '{}' folder.".format(OUTPUT_DIRECTORY))


if __name__ == "__main__":
    main()
