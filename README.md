## Key Features

**🔧 Clean Architecture**
- Case-based request handling for easy extensibility
- Separation of concerns with dedicated handler classes
- Easy to add new functionality without modifying core code

**📁 File Serving**
- Serves static files (HTML, CSS, JS, images, etc.)
- Automatic content-type detection
- Directory listings with file sizes
- Security protection against directory traversal attacks

**🐍 CGI Support**
- Executes Python scripts dynamically
- Proper environment variable setup
- Timeout protection against runaway scripts
- Error handling for script failures

**🛡️ Security & Safety**
- Path sanitization to prevent access outside server directory
- Timeout limits for CGI scripts
- Proper error handling and reporting
- Hidden file protection (files starting with '.')

## How to Use

1. **Save the code** to a file (e.g., `ws.py`)

2. **Create sample files** (optional):
   ```bash
   python ws.py --create-samples
   ```

3. **Start the server**:
   ```bash
   python ws.py
   # Or specify custom host/port:
   python ws.py --host 0.0.0.0 --port 9000
   ```

4. **Visit in browser**: `http://localhost:8080`

## What You'll See

- **Static files**: Any HTML, CSS, JS files in the directory
- **Directory listings**: When browsing folders without index.html
- **Dynamic content**: Python scripts executed as CGI programs
- **Sample pages**: If you used `--create-samples`, you'll get a nice demo

## Extension Points

The case-based architecture makes it easy to add new features:

```python
class CaseSpecialFile(BaseCase):
    def test(self, handler):
        return handler.path.endswith('.special')
    
    def act(self, handler):
        # Your custom handling logic here
        pass
```

