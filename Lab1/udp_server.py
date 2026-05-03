import socket
def process_message(msg):
    if not msg:
        return ""
    
    cmd = msg[0]
    text = msg[1:]
    
    if cmd == 'A':
        return "".join(sorted(text, reverse=True))
    elif cmd == 'C':
        return "".join(sorted(text))
    elif cmd == 'D':
        return text.upper()
    else:
        return msg

# UDP server
def run_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', 12346))
    print("UDP Server started on port 12346")
    
    while True:
        data, client_addr = sock.recvfrom(1024)
        message = data.decode('utf-8').strip()
        print(f"Received from {client_addr}: {message}")
        
        result = process_message(message)
        sock.sendto(result.encode('utf-8'), client_addr)

if __name__ == "__main__":
    run_server()