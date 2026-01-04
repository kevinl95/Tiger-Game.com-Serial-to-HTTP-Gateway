# Tiger Game.com Web Gateway

**Browsing 2025 web on a 1997 handheld by reverse-engineering its modem protocol and building a serial-to-HTTP gateway.**

## What Is This?

The [Tiger Game.com (1997)](https://en.wikipedia.org/wiki/Game.com) was a handheld gaming console with an optional modem accessory and text-only web browser—decades before smartphones. This project brings it back to life by creating a serial gateway that translates between the Game.com's AT modem commands and modern HTTPS web traffic.

Connect your Game.com to a computer via serial, and suddenly you can browse Hacker News, Reddit, Wikipedia, and the modern web on a 29-year-old black-and-white LCD display.

## Features

- **Modem Emulation**: Responds to AT commands from the Game.com's browser
- **Modern Web Access**: Fetches web content and strips it down to text-only format
- **Pre-configured Services**:
  - Hacker News top stories
  - Reddit r/technology
  - Custom URL browsing
- **Text Optimization**: Automatically wraps and formats content for display
- **Link Extraction**: Navigable links with simple number-based selection
- **Pagination**: Browse long lists and articles page by page

## Hardware Requirements

- Tiger Game.com handheld console (1997)
- Game.com Link Cable or serial adapter
- USB-to-Serial adapter (if your computer lacks a serial port)
- Computer running Linux/macOS/Windows

## Software Requirements

- Python 3.7+
- Required packages (see `requirements.txt`):
  - `pyserial` - Serial port communication
  - `requests` - HTTP requests
  - `beautifulsoup4` - HTML parsing

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kevinl95/Tiger-Game.com-Serial-to-HTTP-Gateway.git
   cd Tiger-Game.com-Serial-to-HTTP-Gateway
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure serial port**:
   Edit `browser.py` to match your serial device:
   ```python
   gateway = GameComGateway(port='/dev/ttyUSB0', baudrate=9600)
   ```
   
   Common ports:
   - Linux: `/dev/ttyUSB0`, `/dev/ttyACM0`
   - macOS: `/dev/cu.usbserial-*`
   - Windows: `COM3`, `COM4`, etc.

4. **Set permissions** (Linux/macOS):
   ```bash
   sudo usermod -a -G dialout $USER
   # Log out and back in for changes to take effect
   ```

## Usage

1. **Start the gateway**:
   ```bash
   python browser.py
   ```

2. **On your Game.com**:
   - Insert the Internet cartridge
   - In "Modem Setup" set the buad rate to 9600
   - Return to the main menu
   - Press "Connect to Delphi" and enter any phone number you'd like (it won't be used)
   - The gateway will respond and connect automatically

3. **Navigate the menu**:
   - `1` - Browse Hacker News
   - `2` - Browse Reddit r/technology
   - `3` - Enter a custom URL
   - `4` - View help
   - `M` - Return to main menu
   - `N/P` - Next/Previous page
   - `#` - Follow a numbered link

## How It Works

1. **AT Command Handling**: The Game.com browser sends Hayes-compatible modem commands (`ATZ`, `ATDT`, etc.). The gateway responds as if it were a real modem establishing a connection.

2. **Menu System**: Once "connected," the gateway presents a text menu optimized for the Game.com's small screen.

3. **Web Scraping**: When you select a site, the gateway:
   - Fetches the page
   - Parses HTML with BeautifulSoup
   - Strips scripts, styles, and complex formatting
   - Extracts main content and links

## Troubleshooting

**Gateway doesn't connect:**
- Verify serial port name and permissions
- Check cable connections
- Try different baud rates (9600 is standard)

**Game.com shows garbage characters:**
- Ensure baud rate matches in both `browser.py` and the Internet cartridge's modem settings (9600 by default)

**No web content appears:**
- Check internet connection on host computer
- Verify firewall isn't blocking Python
- Try simpler sites (wikipedia.org) before complex ones

**Links don't work:**
- Some sites block scrapers or require JavaScript
- Try the original URL directly
- Check console output for error messages

## Contributing

This is a niche retro computing project, but contributions are welcome! Feel free to:
- Add more pre-configured services
- Improve text formatting algorithms
- Add support for other retro handhelds
- Enhance error handling
- Submit bug reports