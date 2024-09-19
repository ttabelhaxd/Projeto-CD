import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from queue import Queue
from protocolo import *

def server_maker(node):
    class SudokuHTTPRequestHandler(BaseHTTPRequestHandler):
        
        def do_GET(self):
            if self.path == '/stats':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(node.getStats()).encode('utf-8'))
                return
            if self.path == '/network':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(node.getNetwork()).encode('utf-8'))
                return
            
            self.send_response(404)
            self.end_headers()
        
        def do_POST(self):
            if self.path == '/solve':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                sudoku = json.loads(post_data)['sudoku']
                queue = Queue()
                node.receiveSudoku(sudoku, queue)
                solved = queue.get()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(solved).encode('utf-8'))
                return
            
            self.send_response(404)
            self.end_headers()
            
    return SudokuHTTPRequestHandler
