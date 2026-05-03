from __future__ import annotations

# This file implements the custom reliable transport required by the lab.
#
# Limitation mapping summary:
# - Stop-and-wait reliability: send one packet and wait for ACK before next send.
# - Handshake and flags: SYN, SYN-ACK, ACK, FIN are implemented.
# - Retransmission + timeout: sender retries when ACK/response is missing.
# - Sequence-number handling: in-order, duplicate, and out-of-order cases are handled.
# - Checksum: computed before send and validated on receive.
# - Loss/corruption simulation: outbound and inbound paths can intentionally drop/corrupt.

import base64
import json
import math
import random
import socket
import struct
import zlib
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


FLAG_SYN = "SYN"
FLAG_ACK = "ACK"
FLAG_FIN = "FIN"

FRAGMENT_HEADER = struct.Struct("!I I H H H")
MAX_UDP_PAYLOAD = 1024
DEFAULT_TIMEOUT = 1.0


@dataclass(frozen=True)
class Packet:
    # Sequence number for this packet.
    seq: int
    # ACK number carried by this packet (if any).
    ack: int
    # Transport flags (SYN/ACK/FIN) required by lab handshake/teardown.
    flags: Tuple[str, ...]
    # CRC32 checksum included in serialized packet.
    checksum: int
    # Raw application payload bytes.
    data: bytes

    def to_bytes(self) -> bytes:
        # Build a stable representation (excluding checksum) before CRC calculation.
        # Limitation: "calculate checksum before sending and include it in packet".
        payload = {
            "ack": self.ack,
            "data": base64.b64encode(self.data).decode("ascii"),
            "flags": list(self.flags),
            "seq": self.seq,
        }
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        checksum = zlib.crc32(raw) & 0xFFFFFFFF
        payload["checksum"] = checksum
        return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    @classmethod
    def from_bytes(cls, raw: bytes) -> "Packet":
        # Validate checksum before accepting packet.
        # Limitation: "if checksum is not correct, packet is dropped".
        payload = json.loads(raw.decode("utf-8"))
        checksum = int(payload.pop("checksum"))
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        expected = zlib.crc32(encoded) & 0xFFFFFFFF
        if checksum != expected:
            raise ValueError("checksum mismatch")
        return cls(
            seq=int(payload["seq"]),
            ack=int(payload["ack"]),
            flags=tuple(payload.get("flags", [])),
            checksum=checksum,
            data=base64.b64decode(payload["data"].encode("ascii")),
        )


class ReliableUDP:
    """A small reliable transport built on top of UDP sockets.

    The protocol uses a TCP-like handshake and stop-and-wait retransmission.
    Application payloads are fragmented into independently acknowledged packets.
    """

    def __init__(
        self,
        local_addr: Optional[Tuple[str, int]] = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        loss_rate: float = 0.0,
        corruption_rate: float = 0.0,
        seed: Optional[int] = None,
    ) -> None:
        # Underlying UDP socket (lab requires UDP socket usage).
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Timeout is used to trigger retransmissions when no ACK/response arrives.
        self.socket.settimeout(timeout)
        if local_addr is not None:
            # Server binds to a known local endpoint.
            self.socket.bind(local_addr)
        self.timeout = timeout
        # Simulation knobs for packet loss and corruption.
        self.loss_rate = max(0.0, min(1.0, loss_rate))
        self.corruption_rate = max(0.0, min(1.0, corruption_rate))
        self.random = random.Random(seed)
        # Peer endpoint selected after connect/accept handshake.
        self.peer_addr: Optional[Tuple[str, int]] = None
        self._connected = False
        # Sequence-number state used by stop-and-wait protocol.
        self.send_seq = self.random.randint(1_000, 50_000)
        self.expected_seq = self.random.randint(1_000, 50_000)
        self._closed = False
        # Buffers used to reassemble fragmented application messages.
        self._pending_fragments: Dict[int, Dict[int, bytes]] = {}
        self._fragment_meta: Dict[int, Tuple[int, int]] = {}

    def log(self, message: str) -> None:
        print(f"[RUDP] {message}")

    def close(self) -> None:
        # Graceful close sends FIN if we already have a peer.
        if self._closed:
            return
        try:
            if self._connected and self.peer_addr is not None:
                self._terminate_connection()
        finally:
            self.socket.close()
            self._closed = True

    def connect(self, remote_addr: Tuple[str, int]) -> None:
        # Client-side 3-way handshake:
        # 1) send SYN, 2) wait SYN-ACK, 3) send final ACK.
        # Limitation: special consideration for handshake and SYN/SYNACK/ACK flags.
        self.peer_addr = remote_addr
        client_isn = self.send_seq
        syn = Packet(seq=client_isn, ack=0, flags=(FLAG_SYN,), checksum=0, data=b"")
        self.log(f"Sending SYN seq={client_isn} to {remote_addr}")
        # Retries happen on timeout if SYN-ACK is missing.
        syn_ack = self._exchange_until_ack(syn, expected_ack=client_isn + 1, max_attempts=8)
        if FLAG_SYN not in syn_ack.flags or FLAG_ACK not in syn_ack.flags:
            raise ConnectionError("invalid SYN-ACK during handshake")
        server_isn = syn_ack.seq
        self.expected_seq = server_isn + 1
        ack = Packet(seq=client_isn + 1, ack=server_isn + 1, flags=(FLAG_ACK,), checksum=0, data=b"")
        self.log(f"Sending final ACK seq={client_isn + 1} ack={server_isn + 1}")
        for _ in range(3):
            self._send_packet(ack)
        self.send_seq = client_isn + 2
        self._connected = True
        self.log("Client handshake complete")

    def accept(self) -> Tuple[Tuple[str, int], "ReliableUDP"]:
        # Server-side handshake counterpart.
        self.log("Waiting for incoming SYN")
        while True:
            try:
                packet, addr = self._receive_any_packet()
            except socket.timeout:
                continue
            if packet is None or FLAG_SYN not in packet.flags:
                continue
            self.peer_addr = addr
            client_isn = packet.seq
            self.expected_seq = client_isn + 1
            server_isn = self.send_seq
            syn_ack = Packet(seq=server_isn, ack=client_isn + 1, flags=(FLAG_SYN, FLAG_ACK), checksum=0, data=b"")
            self.log(f"Received SYN from {addr}, replying with SYN-ACK seq={server_isn} ack={client_isn + 1}")
            while True:
                self._send_packet(syn_ack)
                try:
                    response, response_addr = self._receive_any_packet()
                except socket.timeout:
                    # If final ACK is not received, retransmit SYN-ACK.
                    self.log("Handshake timeout waiting for final ACK, retransmitting SYN-ACK")
                    continue
                if response_addr != addr:
                    continue
                if response is None or FLAG_ACK not in response.flags:
                    continue
                if response.ack != server_isn + 1 or response.seq != client_isn + 1:
                    continue
                self.send_seq = server_isn + 1
                self.expected_seq = client_isn + 2
                self.log(f"Handshake complete with {addr}")
                return addr, self

    def send_message(self, data: bytes) -> None:
        # Application messages are fragmented to fit UDP payload limits,
        # then each fragment is sent with stop-and-wait reliability.
        if self.peer_addr is None:
            raise ConnectionError("peer is not connected")
        message_id = self.random.getrandbits(32)
        chunk_size = max(1, MAX_UDP_PAYLOAD - FRAGMENT_HEADER.size - 200)
        total_chunks = max(1, math.ceil(len(data) / chunk_size))
        if len(data) == 0:
            chunks = [b""]
        else:
            chunks = [data[index : index + chunk_size] for index in range(0, len(data), chunk_size)]
        self.log(f"Sending message {message_id} in {len(chunks)} fragment(s)")
        for index, chunk in enumerate(chunks):
            fragment = FRAGMENT_HEADER.pack(message_id, len(data), index, total_chunks, len(chunk)) + chunk
            packet = Packet(seq=self.send_seq, ack=0, flags=(), checksum=0, data=fragment)
            # Core stop-and-wait behavior: do not move to next packet until ACK.
            self._send_packet_with_retry(packet, expect_ack=self.send_seq + 1)
            self.send_seq += 1

    def recv_message(self) -> bytes:
        # Receiver enforces sequence ordering and ACK behavior.
        # Limitation: duplicate packet and sequence-number handling.
        if self.peer_addr is None:
            raise ConnectionError("peer is not connected")
        while True:
            try:
                packet, addr = self._receive_any_packet()
            except socket.timeout:
                continue
            if packet is None:
                continue
            if addr != self.peer_addr:
                continue
            if packet.seq < self.expected_seq:
                # Duplicate packet: ACK expected sequence again.
                self.log(f"Duplicate packet seq={packet.seq}, resending ACK {self.expected_seq}")
                self._send_ack(self.expected_seq)
                continue
            if packet.seq > self.expected_seq:
                # Out-of-order packet: ask sender to retransmit missing sequence.
                self.log(f"Out-of-order packet seq={packet.seq}, expected={self.expected_seq}")
                self._send_ack(self.expected_seq)
                continue
            if packet.seq == self.expected_seq:
                self.log(f"Received in-order packet seq={packet.seq}")
                self._send_ack(packet.seq + 1)
                self.expected_seq += 1
                if FLAG_FIN in packet.flags:
                    # FIN closes the logical connection.
                    self.log("Received FIN, closing connection")
                    self._closed = True
                    raise ConnectionError("peer closed connection")
                if not packet.data:
                    continue
                message = self._process_fragment(packet.data)
                if message is not None:
                    return message

    def _process_fragment(self, fragment: bytes) -> Optional[bytes]:
        # Reassemble message only when all fragments arrive.
        if len(fragment) < FRAGMENT_HEADER.size:
            return fragment
        message_id, total_length, index, total_chunks, chunk_length = FRAGMENT_HEADER.unpack(
            fragment[: FRAGMENT_HEADER.size]
        )
        chunk = fragment[FRAGMENT_HEADER.size : FRAGMENT_HEADER.size + chunk_length]
        if len(chunk) != chunk_length:
            return None
        fragments = self._pending_fragments.setdefault(message_id, {})
        self._fragment_meta[message_id] = (total_chunks, total_length)
        if index not in fragments:
            fragments[index] = chunk
            self.log(f"Stored fragment {index + 1}/{total_chunks} for message {message_id}")
        if len(fragments) != total_chunks:
            return None
        assembled = b"".join(fragments[i] for i in range(total_chunks))
        if len(assembled) != total_length:
            self.log(f"Discarding message {message_id} due to length mismatch")
            self._pending_fragments.pop(message_id, None)
            self._fragment_meta.pop(message_id, None)
            return None
        self._pending_fragments.pop(message_id, None)
        self._fragment_meta.pop(message_id, None)
        self.log(f"Reassembled message {message_id}")
        return assembled

    def _terminate_connection(self) -> None:
        # Graceful close sends FIN and expects ACK.
        # Limitation: special consideration for FIN flag and timeout/retry.
        if self.peer_addr is None:
            return
        fin = Packet(seq=self.send_seq, ack=0, flags=(FLAG_FIN,), checksum=0, data=b"")
        self.log(f"Sending FIN seq={self.send_seq}")
        try:
            self._send_packet_with_retry(fin, expect_ack=self.send_seq + 1, max_attempts=3)
        except TimeoutError:
            self.log("FIN not acknowledged before close")

    def _send_ack(self, ack_number: int) -> None:
        # Utility used by receiver side to acknowledge sequence progress.
        ack_packet = Packet(seq=self.send_seq, ack=ack_number, flags=(FLAG_ACK,), checksum=0, data=b"")
        self._send_packet(ack_packet)

    def _exchange_until_ack(
        self,
        packet: Packet,
        expected_ack: Optional[int],
        max_attempts: Optional[int] = None,
    ) -> Packet:
        # Generic retry loop used during handshake request/response exchange.
        attempts = 0
        while True:
            attempts += 1
            self._send_packet(packet)
            try:
                response, addr = self._receive_any_packet()
            except (socket.timeout, ConnectionResetError, ConnectionError) as exc:
                # Timeout => retransmission, as required by reliable transport behavior.
                self.log("Timeout waiting for response, retransmitting")
                if max_attempts is not None and attempts >= max_attempts:
                    raise TimeoutError(f"no response from peer {self.peer_addr}") from exc
                continue
            if addr != self.peer_addr:
                continue
            if response is None:
                continue
            if expected_ack is not None and response.ack != expected_ack:
                continue
            return response

    def _send_packet_with_retry(
        self,
        packet: Packet,
        *,
        expect_ack: Optional[int],
        max_attempts: Optional[int] = None,
    ) -> None:
        # Stop-and-wait send loop: keep resending until expected ACK arrives.
        attempts = 0
        while True:
            attempts += 1
            self._send_packet(packet)
            if expect_ack is None:
                return
            try:
                response, addr = self._receive_any_packet()
            except socket.timeout:
                # No ACK in time => retransmit packet.
                self.log(f"Timeout waiting for ACK seq={packet.seq}, retransmitting")
                if max_attempts is not None and attempts >= max_attempts:
                    raise TimeoutError(f"packet seq={packet.seq} not acknowledged")
                continue
            if addr != self.peer_addr or response is None:
                continue
            if FLAG_ACK in response.flags and response.ack == expect_ack:
                self.log(f"Received ACK ack={response.ack} for seq={packet.seq}")
                return
            if max_attempts is not None and attempts >= max_attempts:
                raise TimeoutError(f"packet seq={packet.seq} not acknowledged")

    def _send_packet(self, packet: Packet) -> None:
        # Serialize packet with checksum and optionally simulate network faults.
        if self.peer_addr is None:
            raise ConnectionError("peer is not connected")
        raw = packet.to_bytes()
        if self.random.random() < self.loss_rate:
            # Limitation: packet loss simulation method.
            self.log(f"Simulated drop of outbound packet seq={packet.seq} flags={packet.flags}")
            return
        if self.random.random() < self.corruption_rate:
            # Limitation: packet corruption simulation method.
            raw = self._corrupt_bytes(raw)
            self.log(f"Simulated corruption of outbound packet seq={packet.seq} flags={packet.flags}")
        self.socket.sendto(raw, self.peer_addr)
        self.log(f"Sent packet seq={packet.seq} ack={packet.ack} flags={packet.flags} bytes={len(raw)}")

    def _receive_any_packet(self) -> Tuple[Optional[Packet], Tuple[str, int]]:
        # Receive, optionally simulate faults, then checksum-validate packet.
        try:
            raw, addr = self.socket.recvfrom(65535)
        except ConnectionResetError as exc:
            raise ConnectionError(
                f"peer {self.peer_addr} is unreachable or not listening"
            ) from exc
        if self.random.random() < self.loss_rate:
            # Simulated inbound loss: behave like timeout.
            self.log(f"Simulated drop of inbound packet from {addr}")
            raise socket.timeout("simulated drop")
        if self.random.random() < self.corruption_rate:
            # Simulated inbound corruption to test checksum drop behavior.
            raw = self._corrupt_bytes(raw)
            self.log(f"Simulated corruption of inbound packet from {addr}")
        try:
            packet = Packet.from_bytes(raw)
        except Exception as exc:
            # Corrupted/invalid packet is dropped and ignored.
            self.log(f"Dropped corrupted packet from {addr}: {exc}")
            return None, addr
        self.log(f"Received packet seq={packet.seq} ack={packet.ack} flags={packet.flags} from {addr}")
        return packet, addr

    def _corrupt_bytes(self, raw: bytes) -> bytes:
        # Helper used by corruption simulation: flip one random byte.
        if not raw:
            return raw
        data = bytearray(raw)
        index = self.random.randrange(len(data))
        data[index] ^= 0xFF
        return bytes(data)
