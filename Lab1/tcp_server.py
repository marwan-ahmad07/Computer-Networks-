import socket
import threading
def handle_connection(conn, addr):
    print(f"Client connected: {addr}")
    try:
        # Read until client closes
        buffer = []
        while True:
            chunk = conn.recv(1024)
            if not chunk:
                break
            buffer.append(chunk)
        
        message = b''.join(buffer).decode('utf-8').strip()
        result = process_message(message)
        conn.sendall(result.encode('utf-8'))
    except:
        pass
    finally:
        conn.close()
        print(f"Client disconnected: {addr}")

# Process message
def process_message(msg):
    if not msg:
        return ""
    
    cmd = msg[0]
    text = msg[1:]
    
    # A: sort descending
    if cmd == 'A':
        return "".join(sorted(text, reverse=True))
    # C: sort ascending
    elif cmd == 'C':
        return "".join(sorted(text))
    # D: uppercase
    elif cmd == 'D':
        return text.upper()
    # Unknown command, return as is
    else:
        return msg

# Main server function
def run_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', 12345))
    sock.listen(5)
    print("TCP Server started on port 12345")
    
    while True:
        client_conn, client_addr = sock.accept()
        # Use threading for multiple clients
        t = threading.Thread(target=handle_connection, args=(client_conn, client_addr))
        t.start()

if __name__ == "__main__":
    run_server()