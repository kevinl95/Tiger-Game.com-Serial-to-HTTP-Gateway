import serial
import time
import threading
import requests
from bs4 import BeautifulSoup
import textwrap
import re
from urllib.parse import urlparse, urljoin

class GameComGateway:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        self.ser = serial.Serial(port, baudrate, timeout=0.1)
        self.ser.dtr = True
        self.ser.rts = True
        self.connected = False
        self.buffer = ""
        self.current_menu = "main"
        self.hn_stories = []
        self.reddit_posts = []
        self.awaiting_url = False
        self.current_links = []
        self.current_url = ""
        self.page = 0
        self.items_per_page = 5
        
    def send(self, text):
        """Send text to Game.com"""
        self.ser.write(text.encode('ascii', errors='ignore'))
        time.sleep(0.05)
        
    def send_line(self, text):
        """Send line with CR LF"""
        self.send(text + '\r\n')
    
    def wrap_text(self, text, width=30, first_line_indent=''):
        """Wrap text without subsequent indentation"""
        wrapped = textwrap.fill(text, 
                            width=width,
                            initial_indent=first_line_indent,
                            subsequent_indent='',
                            break_long_words=True)
        # Replace \n with \r\n for proper carriage return on serial terminals
        return wrapped.replace('\n', '\r\n')
    
    def validate_url(self, url):
        """Basic URL validation"""
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        try:
            result = urlparse(url)
            if result.scheme in ['http', 'https'] and result.netloc:
                return True, url
            else:
                return False, "Invalid URL format"
        except Exception as e:
            return False, str(e)
    
    def extract_links(self, soup, base_url):
        """Extract links from page"""
        links = []
        seen_urls = set()
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            text = link.get_text().strip()
            
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            
            try:
                absolute_url = urljoin(base_url, href)
            except:
                continue
            
            if absolute_url in seen_urls:
                continue
            
            seen_urls.add(absolute_url)
            
            if not text:
                text = href
            text = text[:40]
            
            links.append({
                'url': absolute_url,
                'text': text
            })
            
            if len(links) >= 20:
                break
        
        return links
    
    def show_paginated_items(self, items, item_type="items"):
        """Show a page of items with pagination controls"""
        start_idx = self.page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = items[start_idx:end_idx]
        
        total_pages = (len(items) + self.items_per_page - 1) // self.items_per_page
        current_page_num = self.page + 1
        
        self.send_line(f'\r\nPage {current_page_num}/{total_pages}\r\n')
        
        for i, item in enumerate(page_items, start=start_idx + 1):
            if isinstance(item, dict):
                text = f"{i}. {item['text']}"
            else:
                text = f"{i}. {item}"
            
            wrapped = self.wrap_text(text, width=30)
            self.send_line(wrapped)
            self.send_line('')
        
        nav_options = []
        if self.page > 0:
            nav_options.append('P. Previous')
        if end_idx < len(items):
            nav_options.append('N. Next')
        
        if nav_options:
            self.send_line(' | '.join(nav_options))
    
    def fetch_url(self, url):
        """Fetch and display arbitrary URL"""
        valid, result = self.validate_url(url)
        
        if not valid:
            self.send_line(f'\r\nError: {result}')
            self.send_line('Try again or M for menu')
            self.send('URL> ')
            return
        
        url = result
        self.current_url = url
        
        try:
            self.send_line(f'\r\nFetching...')
            
            resp = requests.get(
                url, 
                headers={'User-Agent': 'GameCom/1.0 (Retro Browser)'},
                timeout=15,
                allow_redirects=True
            )
            
            if resp.status_code != 200:
                self.send_line(f'\r\nHTTP Error {resp.status_code}')
                self.send_line('M. Main Menu')
                self.send('> ')
                return
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            for script in soup(["script", "style", "nav", "footer", "header", "iframe"]):
                script.decompose()
            
            title = soup.find('title')
            if title:
                title_text = title.get_text().strip()[:40]
                self.send_line(f'\r\n=== {title_text} ===\r\n')
            
            main_content = (
                soup.find('article') or 
                soup.find('main') or 
                soup.find('div', class_=re.compile('content|article|post|entry', re.I)) or
                soup.find('body')
            )
            
            if main_content:
                paragraphs = main_content.find_all('p', limit=3)
                
                if paragraphs:
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if len(text) > 20:
                            wrapped = self.wrap_text(text, width=30)
                            self.send_line(wrapped)
                            self.send_line('')
                else:
                    text = main_content.get_text()
                    text = re.sub(r'\s+', ' ', text).strip()[:300]
                    wrapped = self.wrap_text(text, width=30)
                    self.send_line(wrapped)
                    self.send_line('')
            
            self.current_links = self.extract_links(soup, url)
            self.page = 0
            
            if self.current_links:
                self.send_line('\r\n--- LINKS ---')
                self.show_paginated_items(self.current_links, "links")
                self.send_line('\r\nEnter # to follow')
            
            self.send_line('U. New URL  M. Menu')
            self.send('> ')
            self.current_menu = "page"
            self.awaiting_url = False
            
        except requests.exceptions.Timeout:
            self.send_line('\r\nTimeout - site too slow')
            self.send_line('Try again or M for menu')
            self.send('URL> ')
        except requests.exceptions.ConnectionError:
            self.send_line('\r\nConnection failed')
            self.send_line('Check URL or M for menu')
            self.send('URL> ')
        except Exception as e:
            self.send_line(f'\r\nError: {str(e)[:40]}')
            self.send_line('M. Main Menu')
            self.send('> ')
            self.current_menu = "main"
            self.awaiting_url = False
    
    def handle_at_command(self, cmd):
        """Handle AT commands from Game.com"""
        cmd = cmd.lower().strip()
        if cmd == 'atz':
            self.send_line('OK')
        elif cmd.startswith('atdt'):
            self.send_line('CONNECT 9600')
            self.connected = True
            time.sleep(0.5)
            self.show_main_menu()
        else:
            self.send_line('OK')
    
    def show_main_menu(self):
        """Show main menu"""
        self.send_line('\r\n=== GAME.COM GATEWAY ===')
        self.send_line('1997 -> 2025 Portal')
        self.send_line('')
        self.send_line('1. Hacker News')
        self.send_line('2. Reddit r/technology')
        self.send_line('3. Enter URL')
        self.send_line('4. Help')
        self.send_line('')
        self.send('> ')
        self.current_menu = "main"
        self.awaiting_url = False
        self.page = 0
    
    def fetch_hackernews(self):
        """Fetch Hacker News headlines"""
        try:
            self.send_line('\r\nFetching HN...')
            resp = requests.get('https://news.ycombinator.com', timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            stories = []
            story_links = []
            
            for item in soup.select('.titleline')[:15]:
                link = item.find('a')
                if link:
                    title = link.get_text()
                    href = link.get('href', '')
                    stories.append(title)
                    story_links.append(href)
            
            self.hn_stories = stories
            self.hn_links = story_links
            self.page = 0
            
            self.send_line('\r\n=== HACKER NEWS ===')
            self.show_paginated_items(stories, "stories")
            
            self.send_line('Enter # to read')
            self.send_line('M. Main Menu')
            self.send('> ')
            self.current_menu = "hn"
            
        except Exception as e:
            self.send_line(f'\r\nError: {str(e)[:40]}')
            self.send_line('M. Main Menu')
            self.send('> ')
    
    def fetch_reddit(self):
        """Fetch Reddit r/technology"""
        try:
            self.send_line('\r\nFetching Reddit...')
            resp = requests.get(
                'https://old.reddit.com/r/technology', 
                headers={'User-Agent': 'GameCom/1.0'}, 
                timeout=10
            )
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            posts = []
            self.reddit_posts = []
            
            for post in soup.select('.thing')[:15]:
                title_elem = post.select_one('.title')
                if title_elem:
                    title = title_elem.get_text().strip()
                    link = title_elem.find('a')
                    url = link.get('href', '') if link else ''
                    posts.append(title)
                    self.reddit_posts.append(url)
            
            self.page = 0
            
            self.send_line('\r\n=== r/technology ===')
            self.show_paginated_items(posts, "posts")
            
            self.send_line('Enter # to read')
            self.send_line('M. Main Menu')
            self.send('> ')
            self.current_menu = "reddit"
            
        except Exception as e:
            self.send_line(f'\r\nError: {str(e)[:40]}')
            self.send_line('M. Main Menu')
            self.send('> ')
    
    def prompt_for_url(self):
        """Prompt user to enter URL"""
        self.send_line('\r\n=== ENTER URL ===')
        self.send_line('Examples:')
        self.send_line('  wikipedia.org')
        self.send_line('  bbc.com/news')
        self.send_line('  nytimes.com')
        self.send_line('')
        self.send_line('Or M for main menu')
        self.send('URL> ')
        self.awaiting_url = True
    
    def handle_pagination(self, direction):
        """Handle N/P pagination commands"""
        if direction == 'N':
            self.page += 1
        elif direction == 'P':
            self.page = max(0, self.page - 1)
        
        if self.current_menu == "hn":
            self.send_line('\r\n=== HACKER NEWS ===')
            self.show_paginated_items(self.hn_stories, "stories")
            self.send_line('Enter # to read')
            self.send_line('M. Main Menu')
            self.send('> ')
        elif self.current_menu == "reddit":
            self.send_line('\r\n=== r/technology ===')
            # Store reddit titles separately for re-display
            self.send_line('Use M to return to menu')
            self.send('> ')
        elif self.current_menu == "page":
            self.send_line('\r\n--- LINKS ---')
            self.show_paginated_items(self.current_links, "links")
            self.send_line('\r\nEnter # to follow')
            self.send_line('U. New URL  M. Menu')
            self.send('> ')
    
    def handle_user_input(self, line):
        """Handle user input based on current menu"""
        line = line.strip()
        
        if self.awaiting_url:
            if line.upper() == 'M':
                self.show_main_menu()
            else:
                self.fetch_url(line)
            return
        
        line_upper = line.upper()
        
        if line_upper == 'M':
            self.show_main_menu()
            return
        
        if line_upper == 'U':
            self.prompt_for_url()
            return
        
        if line_upper in ['N', 'P']:
            self.handle_pagination(line_upper)
            return
        
        if self.current_menu == "main":
            if line == '1':
                self.fetch_hackernews()
            elif line == '2':
                self.fetch_reddit()
            elif line == '3':
                self.prompt_for_url()
            elif line == '4':
                self.send_line('\r\n=== HELP ===')
                self.send_line('Type menu numbers')
                self.send_line('M = main menu')
                self.send_line('U = enter new URL')
                self.send_line('# = follow link')
                self.send_line('N/P = next/prev page')
                self.send_line('')
                self.send('> ')
            else:
                self.send_line('\r\nInvalid option')
                self.send('> ')
        
        elif self.current_menu == "hn":
            try:
                num = int(line)
                if 1 <= num <= len(self.hn_links):
                    url = self.hn_links[num - 1]
                    if not url.startswith('http'):
                        url = 'https://news.ycombinator.com/' + url
                    self.fetch_url(url)
                else:
                    self.send_line('\r\nInvalid number')
                    self.send('> ')
            except ValueError:
                self.send_line('\r\nEnter number, N/P, or M')
                self.send('> ')
        
        elif self.current_menu == "reddit":
            try:
                num = int(line)
                if 1 <= num <= len(self.reddit_posts):
                    url = self.reddit_posts[num - 1]
                    self.fetch_url(url)
                else:
                    self.send_line('\r\nInvalid number')
                    self.send('> ')
            except ValueError:
                self.send_line('\r\nEnter number, N/P, or M')
                self.send('> ')
        
        elif self.current_menu == "page":
            try:
                num = int(line)
                if 1 <= num <= len(self.current_links):
                    new_url = self.current_links[num - 1]['url']
                    self.fetch_url(new_url)
                else:
                    self.send_line('\r\nInvalid link number')
                    self.send('> ')
            except ValueError:
                self.send_line('\r\nEnter #, N/P, U, or M')
                self.send('> ')
    
    def run(self):
        """Main loop"""
        print("Game.com Web Gateway running...")
        print("Waiting for connection...\n")
        
        user_buffer = ""
        
        try:
            while True:
                data = self.ser.read(100)
                if data:
                    if not self.connected:
                        self.buffer += data.decode('ascii', errors='ignore')
                        if '\r' in self.buffer:
                            lines = self.buffer.split('\r')
                            for line in lines[:-1]:
                                print(f"<< AT: {line}")
                                self.handle_at_command(line)
                            self.buffer = lines[-1]
                    else:
                        text = data.decode('ascii', errors='ignore')
                        for char in text:
                            if char == '\r':
                                print(f"User: {user_buffer}")
                                self.send('\r\n')
                                self.handle_user_input(user_buffer)
                                user_buffer = ""
                            elif char == '\x08' or char == '\x7f':
                                if user_buffer:
                                    user_buffer = user_buffer[:-1]
                                    self.send('\x08 \x08')
                            elif char >= ' ' or char == '\t':
                                user_buffer += char
                                self.send(char)
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.ser.close()

if __name__ == "__main__":
    gateway = GameComGateway()
    gateway.run()