import socket
import time

def send_tcp_message(msg):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', 12345))
    sock.sendall(msg.encode('utf-8'))
    sock.shutdown(socket.SHUT_WR)
    response = sock.recv(1024)
    print(f"TCP: Sent '{msg}' -> Got '{response.decode('utf-8')}'")
    sock.close()

def send_udp_message(msg):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(msg.encode('utf-8'), ('127.0.0.1', 12346))
    response, _ = sock.recvfrom(1024)
    print(f"UDP: Sent '{msg}' -> Got '{response.decode('utf-8')}'")
    sock.close()

print("Sending test messages for Wireshark capture...")
print("-" * 50)

# TCP Examples
send_tcp_message("Aabcde")
time.sleep(0.5)
send_tcp_message("Cabcde")
time.sleep(0.5)
send_tcp_message("Dhello")
time.sleep(0.5)

print("-" * 50)

# UDP Examples
send_udp_message("Azyxwv")
time.sleep(0.5)
send_udp_message("Cworld")
time.sleep(0.5)
send_udp_message("Dtest")

print("-" * 50)
print("Done! Check Wireshark now.")
