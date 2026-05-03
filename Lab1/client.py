import socket

# Connect and send message to server
def send_message(protocol, port):
    server_addr = ('127.0.0.1', port)
    message = input(f"Enter message for {protocol}: ")
    
    if protocol == 'TCP':
        # TCP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(server_addr)
        sock.sendall(message.encode('utf-8'))
        sock.shutdown(socket.SHUT_WR)
        response = sock.recv(1024)
        print(f"Server reply: {response.decode('utf-8')}")
        sock.close()
    else:
        # UDP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode('utf-8'), server_addr)
        response, _ = sock.recvfrom(1024)
        print(f"Server reply: {response.decode('utf-8')}")
        sock.close()

if __name__ == "__main__":
    choice = input("Choose protocol (TCP/UDP): ").upper()
    port_num = 12345 if choice == 'TCP' else 12346
    send_message(choice, port_num)