#!/usr/bin/env python3
"""
A Simple Web Server in Python
Based on Greg Wilson's "500 Lines or Less" chapter

This server demonstrates:
- Serving static files
- Directory listings
- CGI script execution
- Clean extensible architecture using case handlers
"""

import os
import sys
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote

class ServerException(Exception):
    """Custom exception for server errors"""
    pass

class BaseCase:
    """Parent class for all request handlers"""
    
    def handle_file(self, handler, full_path):
        """Read and serve a file"""
        try:
            with open(full_path, 'rb') as reader:
                content = reader.read()
            handler.send_content(content)
        except IOError as msg:
            error_msg = f"'{full_path}' cannot be read: {msg}"
            handler.handle_error(error_msg)

    def index_path(self, handler):
        """Get path to index.html in a directory"""
        return os.path.join(handler.full_path, 'index.html')

    def test(self, handler):
        """Test if this handler can process the request"""
        raise NotImplementedError('Subclasses must implement test()')

    def act(self, handler):
        """Handle the request"""
        raise NotImplementedError('Subclasses must implement act()')

class CaseNoFile(BaseCase):
    """Handle requests for non-existent files"""
    
    def test(self, handler):
        return not os.path.exists(handler.full_path)

    def act(self, handler):
        raise ServerException(f"'{handler.path}' not found")

class CaseExistingFile(BaseCase):
    """Handle requests for existing files"""
    
    def test(self, handler):
        return os.path.isfile(handler.full_path)

    def act(self, handler):
        self.handle_file(handler, handler.full_path)

class CaseDirectoryIndexFile(BaseCase):
    """Handle directories with index.html"""
    
    def test(self, handler):
        return (os.path.isdir(handler.full_path) and 
                os.path.isfile(self.index_path(handler)))

    def act(self, handler):
        self.handle_file(handler, self.index_path(handler))

class CaseDirectoryNoIndex(BaseCase):
    """Handle directories without index.html - show listing"""
    
    def test(self, handler):
        return (os.path.isdir(handler.full_path) and 
                not os.path.isfile(self.index_path(handler)))

    def act(self, handler):
        handler.list_dir(handler.full_path)

class CaseCgiFile(BaseCase):
    """Handle CGI scripts (Python files)"""
    
    def test(self, handler):
        return (os.path.isfile(handler.full_path) and 
                handler.full_path.endswith('.py'))

    def act(self, handler):
        handler.run_cgi(handler.full_path)

class CaseAlwaysFail(BaseCase):
    """Fallback case - should never be reached"""
    
    def test(self, handler):
        return True

    def act(self, handler):
        raise ServerException(f"Unknown object '{handler.path}'")

class RequestHandler(BaseHTTPRequestHandler):
    """Main request handler using case-based dispatch"""
    
    # List of case handlers - order matters!
    cases = [
        CaseNoFile(),
        CaseCgiFile(),
        CaseExistingFile(), 
        CaseDirectoryIndexFile(),
        CaseDirectoryNoIndex(),
        CaseAlwaysFail()
    ]

    # HTML template for error pages
    error_page = """
    <html>
    <head><title>Error</title></head>
    <body>
        <h1>Error accessing {path}</h1>
        <p>{msg}</p>
        <hr>
        <p><em>Simple Python Web Server</em></p>
    </body>
    </html>
    """

    # HTML template for directory listings
    listing_page = """
    <html>
    <head><title>Directory: {path}</title></head>
    <body>
        <h1>Directory: {path}</h1>
        <ul>
        {entries}
        </ul>
        <hr>
        <p><em>Simple Python Web Server</em></p>
    </body>
    </html>
    """

    def do_GET(self):
        """Handle GET requests using case-based dispatch"""
        try:
            # Decode URL and get full file path
            self.path = unquote(self.path)
            self.full_path = os.path.join(os.getcwd(), self.path.lstrip('/'))
            
            # Prevent directory traversal attacks
            if not self.full_path.startswith(os.getcwd()):
                raise ServerException("Access denied")

            # Find appropriate handler
            for case in self.cases:
                if case.test(self):
                    case.act(self)
                    break

        except Exception as msg:
            self.handle_error(str(msg))

    def handle_error(self, msg):
        """Send error page to client"""
        content = self.error_page.format(path=self.path, msg=msg)
        self.send_content(content.encode('utf-8'), 404)

    def send_content(self, content, status=200):
        """Send content back to client"""
        self.send_response(status)
        
        # Determine content type
        if self.path.endswith('.html') or self.path.endswith('.htm'):
            content_type = 'text/html'
        elif self.path.endswith('.css'):
            content_type = 'text/css'
        elif self.path.endswith('.js'):
            content_type = 'application/javascript'
        elif self.path.endswith('.json'):
            content_type = 'application/json'
        elif self.path.endswith(('.jpg', '.jpeg')):
            content_type = 'image/jpeg'
        elif self.path.endswith('.png'):
            content_type = 'image/png'
        elif self.path.endswith('.gif'):
            content_type = 'image/gif'
        else:
            content_type = 'text/html'
            
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        
        if isinstance(content, str):
            content = content.encode('utf-8')
        self.wfile.write(content)

    def list_dir(self, full_path):
        """Generate directory listing"""
        try:
            entries = os.listdir(full_path)
            entries.sort()
            
            # Create HTML list items
            listing_items = []
            
            # Add parent directory link if not at root
            if self.path != '/':
                parent_path = os.path.dirname(self.path.rstrip('/'))
                if not parent_path:
                    parent_path = '/'
                listing_items.append(f'<li><a href="{parent_path}">../</a></li>')
            
            # Add entries
            for entry in entries:
                if entry.startswith('.'):  # Skip hidden files
                    continue
                    
                entry_path = os.path.join(full_path, entry)
                url_path = self.path.rstrip('/') + '/' + entry
                
                if os.path.isdir(entry_path):
                    listing_items.append(f'<li><a href="{url_path}/">{entry}/</a></li>')
                else:
                    size = os.path.getsize(entry_path)
                    size_str = self.format_size(size)
                    listing_items.append(f'<li><a href="{url_path}">{entry}</a> ({size_str})</li>')
            
            # Generate page
            entries_html = '\n        '.join(listing_items)
            page = self.listing_page.format(path=self.path, entries=entries_html)
            self.send_content(page.encode('utf-8'))
            
        except OSError as msg:
            error_msg = f"'{self.path}' cannot be listed: {msg}"
            self.handle_error(error_msg)

    def run_cgi(self, full_path):
        """Execute a Python CGI script"""
        try:
            # Set up environment variables for CGI
            env = os.environ.copy()
            env['REQUEST_METHOD'] = 'GET'
            env['PATH_INFO'] = self.path
            env['SERVER_NAME'] = self.server.server_name
            env['SERVER_PORT'] = str(self.server.server_port)
            
            # Run the Python script
            result = subprocess.run(
                [sys.executable, full_path], 
                capture_output=True, 
                text=True,
                env=env,
                timeout=30  # Prevent runaway scripts
            )
            
            if result.returncode == 0:
                self.send_content(result.stdout.encode('utf-8'))
            else:
                error_msg = f"CGI script error: {result.stderr}"
                self.handle_error(error_msg)
                
        except subprocess.TimeoutExpired:
            self.handle_error("CGI script timed out")
        except Exception as msg:
            self.handle_error(f"Cannot execute CGI script: {msg}")

    def format_size(self, size):
        """Format file size in human-readable form"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def log_message(self, format, *args):
        """Override to customize logging"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} - {self.address_string()} - {format % args}")

def create_sample_files():
    """Create some sample files for testing"""
    
    # Create a sample HTML file
    if not os.path.exists('index.html'):
        with open('index.html', 'w') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Simple Python Web Server</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        .info { background: #f0f0f0; padding: 20px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Welcome to Simple Python Web Server!</h1>
    <div class="info">
        <p>This server demonstrates:</p>
        <ul>
            <li>Serving static HTML files</li>
            <li>Directory listings</li>
            <li>CGI script execution</li>
            <li>Clean, extensible architecture</li>
        </ul>
        <p>Try visiting:</p>
        <ul>
            <li><a href="/time.py">/time.py</a> - Dynamic time display</li>
            <li><a href="/info.py">/info.py</a> - Server information</li>
        </ul>
    </div>
</body>
</html>""")

    # Create a sample CGI script
    if not os.path.exists('time.py'):
        with open('time.py', 'w') as f:
            f.write("""#!/usr/bin/env python3
from datetime import datetime

print('''<!DOCTYPE html>
<html>
<head>
    <title>Current Time</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .time { font-size: 24px; color: #2c5aa0; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Current Server Time</h1>
    <p class="time">{}</p>
    <p><a href="/">← Back to home</a></p>
</body>
</html>'''.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
""")

    # Create another sample CGI script
    if not os.path.exists('info.py'):
        with open('info.py', 'w') as f:
            f.write("""#!/usr/bin/env python3
import os
import sys

print('''<!DOCTYPE html>
<html>
<head>
    <title>Server Info</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Server Information</h1>
    <table>
        <tr><th>Property</th><th>Value</th></tr>
        <tr><td>Python Version</td><td>{}</td></tr>
        <tr><td>Working Directory</td><td>{}</td></tr>
        <tr><td>Path Info</td><td>{}</td></tr>
        <tr><td>Server Name</td><td>{}</td></tr>
        <tr><td>Server Port</td><td>{}</td></tr>
    </table>
    <p><a href="/">← Back to home</a></p>
</body>
</html>'''.format(
    sys.version,
    os.getcwd(),
    os.environ.get('PATH_INFO', 'Not set'),
    os.environ.get('SERVER_NAME', 'Not set'),
    os.environ.get('SERVER_PORT', 'Not set')
))
""")

def main():
    """Start the web server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Python Web Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to (default: 8080)')
    parser.add_argument('--create-samples', action='store_true', help='Create sample files')
    
    args = parser.parse_args()
    
    if args.create_samples:
        create_sample_files()
        print("Sample files created!")
    
    server_address = (args.host, args.port)
    
    try:
        httpd = HTTPServer(server_address, RequestHandler)
        print(f"Starting server on http://{args.host}:{args.port}/")
        print("Press Ctrl+C to stop the server")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == '__main__':
    main()