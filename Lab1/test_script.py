import socket
import threading
import time
import unittest
import subprocess
import sys
import os

# Paths to the server files
TCP_SERVER_PATH = "/Users/marwanahmed/Desktop/UNI/Term 8/Computer Networks/Labs/tcp_server.py"
UDP_SERVER_PATH = "/Users/marwanahmed/Desktop/UNI/Term 8/Computer Networks/Labs/udp_server.py"

class TestNetworkServers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start TCP server
        cls.tcp_proc = subprocess.Popen([sys.executable, TCP_SERVER_PATH])
        # Start UDP server
        cls.udp_proc = subprocess.Popen([sys.executable, UDP_SERVER_PATH])
        time.sleep(1) # Wait for servers to bind

    @classmethod
    def tearDownClass(cls):
        cls.tcp_proc.terminate()
        cls.udp_proc.terminate()

    def send_tcp(self, message):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('127.0.0.1', 12345))
            s.sendall(message.encode('utf-8'))
            s.shutdown(socket.SHUT_WR)  # Signal end of sending
            return s.recv(1024).decode('utf-8')

    def send_udp(self, message):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(message.encode('utf-8'), ('127.0.0.1', 12346))
            data, _ = s.recvfrom(1024)
            return data.decode('utf-8')

    def test_tcp_sort_descending(self):
        result = self.send_tcp("Aabcde")
        self.assertEqual(result, "edcba")

    def test_tcp_sort_ascending(self):
        result = self.send_tcp("Cabcde")
        self.assertEqual(result, "abcde")

    def test_tcp_uppercase(self):
        result = self.send_tcp("Dhello")
        self.assertEqual(result, "HELLO")

    def test_tcp_unknown_command(self):
        result = self.send_tcp("Xtest")
        self.assertEqual(result, "Xtest")

    def test_tcp_empty_string(self):
        result = self.send_tcp("")
        self.assertEqual(result, "")

    def test_udp_sort_descending(self):
        result = self.send_udp("Aabcde")
        self.assertEqual(result, "edcba")

    def test_udp_sort_ascending(self):
        result = self.send_udp("Cabcde")
        self.assertEqual(result, "abcde")

    def test_udp_uppercase(self):
        result = self.send_udp("Dhello")
        self.assertEqual(result, "HELLO")

    def test_udp_empty_string(self):
        # This used to crash the server before the fix
        result = self.send_udp("")
        self.assertEqual(result, "")

    def test_tcp_multi_threading(self):
        # Verify that multiple clients can connect simultaneously
        results = []
        threads = []

        def client_task():
            results.append(self.send_tcp("Dparallel"))

        for _ in range(5):
            t = threading.Thread(target=client_task)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        for res in results:
            self.assertEqual(res, "PARALLEL")

if __name__ == "__main__":
    unittest.main()
