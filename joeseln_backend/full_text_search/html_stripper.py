from bs4 import BeautifulSoup
import re
def strip_html_and_binary(content):
    # remove HTML tags
    content = strip_binary(content)
    soup = BeautifulSoup(content, "lxml")
    text_only = soup.get_text()
    return text_only

# Remove binary data
def strip_binary(content):
    binary_pattern = r"data:([a-zA-Z0-9]+/[a-zA-Z0-9.+-]+);base64,[A-Za-z0-9+/=]+"
    stripped_content = re.sub(binary_pattern, "", content)
    return stripped_content.strip()
