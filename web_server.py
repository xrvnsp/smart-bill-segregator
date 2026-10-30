#!/usr/bin/env python3
"""Smart Bill Segregator - Native Mobile & PC Local Web Server
Requires ZERO third-party packages (uses Python's built-in http.server).
Serves the exact, responsive web dashboard across both PC and Mobile phones over local Wi-Fi.
"""

import http.server
import os
import socket
import socketserver
import webbrowser
import unlock_statements

PORT = 8080

def get_local_ip():
    """Finds the local network IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class DashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Redirect root to Statement_Dashboard.html
        if self.path in ["/", "/index.html"]:
            self.path = "/Statement_Dashboard.html"
        return super().do_GET()

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    # Ensure latest dashboard is generated
    dash_file = "Statement_Dashboard.html"
    if not os.path.exists(dash_file):
        print("[INFO] Generating latest Statement_Dashboard.html...")
        results = []
        for test_dir in ["Statements_October_2026", "."]:
            if os.path.exists(test_dir):
                for fname in sorted(os.listdir(test_dir)):
                    if fname.lower().endswith(".pdf"):
                        p = os.path.join(test_dir, fname)
                        suc, _, rd = unlock_statements.process_statement_file(p, ".")
                        if suc and not any(r.get("bank_short") == rd.get("bank_short") for r in results):
                            results.append(rd)
        if results:
            unlock_statements.generate_modern_dashboard_html(results, ".")

    local_ip = get_local_ip()
    pc_url = f"http://localhost:{PORT}/Statement_Dashboard.html"
    mobile_url = f"http://{local_ip}:{PORT}/Statement_Dashboard.html"

    print("=" * 64)
    print("  💳 Smart Bill Segregator - Mobile & PC Web Server")
    print("=" * 64)
    print(f"\n  🖥️  On this PC:      {pc_url}")
    print(f"  📱  On your Phone:   {mobile_url}")
    print("\n  (Connect your phone to the same Wi-Fi network and open the mobile URL!)")
    print("  Press Ctrl + C anytime to stop the server.\n" + "=" * 64 + "\n")

    # Automatically open on this PC
    webbrowser.open(pc_url)

    handler = DashboardRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Server stopped.")

if __name__ == "__main__":
    main()
