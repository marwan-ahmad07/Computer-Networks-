<div align="center">
  <h1>🌐 Computer Networks Engineering Labs</h1>
  <p><em>A comprehensive suite of networking projects spanning the OSI model, from low-level Transport protocols to Application-layer services.</em></p>
</div>

---

## 📌 Overview

This repository contains my laboratory assignments and projects for the **Computer Networks** course (Term 8). The projects are implemented primarily in **Python** and demonstrate a deep understanding of network protocols, socket programming, traffic analysis, and client-server architectures.

## 📂 Laboratory Breakdown

### 🔹 [Lab 1: Transport Layer - TCP & UDP Socket Programming](./Lab1)
Designed and implemented low-level client-server architectures using Python sockets.
- **TCP Server/Client**: Reliable stream-oriented communication.
- **UDP Server/Client**: Datagram-oriented, low-latency communication.
- Explored the fundamental differences between connection-oriented (TCP) and connectionless (UDP) protocols through hands-on scripting.

### 🔹 [Lab 2: Application Layer - Email Client GUI (SMTP/IMAP)](./Lab2)
Developed a fully functional, graphical Email Client using Python.
- **SMTP Protocol**: Automated email composition and transmission.
- **IMAP/POP3 Protocol**: Email retrieval and inbox reading.
- **GUI Integration**: Built an interactive user interface that handles real-time notifications (`sent popup`, `received notifications`).

### 🔹 [Lab 3: Network Traffic Analysis & Wireshark](./Lab3)
Deep packet inspection and analysis of network traffic.
- Utilized **Wireshark** to intercept, dissect, and analyze network packets.
- Traced the transmission of specific payloads (e.g., `alice.txt`).
- Investigated the headers and encapsulation processes across the OSI model layers.

### 🔹 [Lab 4: HTTP Protocol & Reliable UDP](./lab4)
Built custom implementations of core web protocols from scratch.
- **HTTP Server & Client**: Implemented `http_server.py` and `http_client.py` to handle GET requests and serve web pages (e.g., `index.html`).
- **Reliable UDP**: Engineered a custom protocol (`reliable_udp.py`) on top of standard UDP to ensure packet delivery, simulating TCP-like reliability mechanisms such as acknowledgments and retransmissions.

---

## ⚙️ Technologies & Tools
- **Language**: Python 3.x
- **Libraries**: `socket`, `smtplib`, `imaplib`
- **Tools**: Wireshark, Cisco Packet Tracer, Git

## 🚀 How to Run
Each laboratory folder contains its own specific source code. In general:
1. Clone the repository.
2. Navigate to the specific lab directory (e.g., `cd Lab1`).
3. Run the server script first, followed by the client script in a separate terminal window.
