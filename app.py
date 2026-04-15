import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ticket-scanner"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ticket-scanner", "web"))

from web.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
