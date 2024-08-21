import os
from datetime import datetime

# Define the base URL of your website
base_url = "https://whatsgood.sg"  # Replace with your base URL

# Function to generate the <url> XML block for each .html file
def generate_url_block(file_name, lastmod):
    return f"""
    <url>
        <loc>{base_url}/{file_name}</loc>
        <lastmod>{lastmod}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1</priority>
    </url>
    """

# Get the current date for the lastmod tag
current_date = datetime.now().strftime("%Y-%m-%d")

# Start of the XML sitemap
sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""

# Loop through all files in the current directory and add .html files to the sitemap
for file_name in os.listdir():
    if file_name.endswith(".html"):
        # Generate the URL block and append it to the sitemap content
        sitemap_content += generate_url_block(file_name, current_date)

# End of the XML sitemap
sitemap_content += """
</urlset>
"""

# Write the sitemap content to a sitemap.xml file in the current directory
with open("sitemap.xml", "w") as sitemap_file:
    sitemap_file.write(sitemap_content)

print("sitemap.xml generated successfully!")
