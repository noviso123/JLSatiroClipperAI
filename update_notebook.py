import json
import re

nb_path = "Open_Studio.ipynb"

with open(nb_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Iterate over cells
for cell in data['cells']:
    # Update Markdown Header
    if cell['cell_type'] == 'markdown':
        new_source = []
        for line in cell['source']:
            # Update Version to V23.0 Titanium Final
            line = re.sub(r"V\d+\.\d+.*", "V23.0 (TITANIUM FINAL)", line)
            new_source.append(line)
        cell['source'] = new_source

    # Update Code Cells (Pip Install)
    if cell['cell_type'] == 'code':
        new_source = []
        for line in cell['source']:
            # Remove yt-dlp from pip install command
            if "!pip install" in line and "yt-dlp" in line:
                line = line.replace("yt-dlp", "").replace("  ", " ")
            new_source.append(line)
        cell['source'] = new_source

with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=1)

print("✅ Notebook Updated Successfully")
