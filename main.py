import os
import logging
import html2text
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import PhotoImage
import subprocess
from tkinterdnd2 import DND_FILES, TkinterDnD

logging.basicConfig(level=logging.DEBUG)


def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def read_wordpress_xml(file_path):
    logging.debug(f"Reading XML file from {file_path}")
    tree = ET.parse(file_path)
    root = tree.getroot()

    channel = root.find('channel')
    website_name = channel.find('title').text

    rows = []
    for item in root.findall(".//item"):
        post_type = item.find("./{http://wordpress.org/export/1.2/}post_type").text
        categories = [category.text for category in item.findall("category[@domain='category']")]

        title_element = item.find("title")
        title = title_element.text if title_element is not None else "Untitled"

        content_encoded_element = item.find("./{http://purl.org/rss/1.0/modules/content/}encoded")
        if content_encoded_element is None or content_encoded_element.text is None:
            logging.warning(f"Skipping an item '{title}' due to missing content_encoded")
            continue

        content = content_encoded_element.text
        pub_date = item.find("pubDate").text
        link = item.find("link").text
        slug = link.split("/")[-2]

        logging.debug(f"Read {post_type}: {title}, Slug: {slug}, Date: {pub_date}, Content Length: {len(content)}")

        rows.append({
            'title': title,
            'text': content,
            'date': pub_date,
            'slug': slug,
            'categories': categories,
            'taxonomy': post_type
        })

    return rows, website_name


def write_markdown(rows, website_name):
    ensure_directory_exists(website_name)
    converter = html2text.HTML2Text()
    for row in rows:
        taxonomy = row.get('taxonomy', 'misc')
        root_folder = os.path.join(website_name, taxonomy)
        ensure_directory_exists(root_folder)

        categories = row.get('categories', [])
        if not categories:
            folder_path = os.path.join(root_folder)
        else:
            folder_path = [os.path.join(root_folder, category) for category in categories]
            for path in folder_path:
                ensure_directory_exists(path)

        original_filename = f"{row['slug']}.md"
        counter = 1

        for path in folder_path if isinstance(folder_path, list) else [folder_path]:
            filename = os.path.join(path, original_filename)
            while os.path.exists(filename):
                logging.debug(f"File {filename} already exists, appending a number.")
                filename = os.path.join(
                    path, f"{os.path.splitext(original_filename)[0]}_{counter}{os.path.splitext(original_filename)[1]}")
                counter += 1

            logging.debug(f"Writing to file: {filename}")

            with open(filename, 'w', encoding='utf-8') as md_file:
                md_file.write(f"# {row['title']}\n\n")
                md_file.write(f"**Categories**: {', '.join(row['categories'])}\n\n")
                md_file.write(f"**Date**: {row['date']}\n\n")
                md_file.write(converter.handle(row['text']))

    # Open the top-level directory
    if os.name == 'nt':  # Windows
        subprocess.run([f'explorer', website_name])
    elif os.name == 'posix':  # macOS and Linux
        subprocess.run(['open', website_name])

# Initialize the TkinterDnD window
root = TkinterDnD.Tk()
root.title("WordPress XML to Markdown Converter")

# Load the initial image
initial_image = PhotoImage(file=".assets/drag.png")
initial_label = tk.Label(root, image=initial_image)
initial_label.pack(fill=tk.BOTH, expand=True)

# Load the drag-over image
drag_over_image = PhotoImage(file=".assets/drop.png")

def on_drag_enter(event):
    initial_label.config(image=drag_over_image)

def on_drag_leave(event):
    initial_label.config(image=initial_image)

def drop(event):
    file_path = event.data.strip()
    print(f"File dropped: {file_path}")
    rows, website_name = read_wordpress_xml(file_path)
    write_markdown(rows, website_name)

root.title("WordPress XML to Markdown Converter")
root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', drop)
root.dnd_bind('<<DragEnter>>', on_drag_enter)
root.dnd_bind('<<DragLeave>>', on_drag_leave)

# Start the Tkinter event loop
root.mainloop()
