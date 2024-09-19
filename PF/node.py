import argparse
import socket
import selectors
import threading
import json
from protocolo import *
from server import server_maker
from http.server import ThreadingHTTPServer
from logger_function import save
from sudoku import Sudoku
from work_divider import WorkDivider
from queue import Queue


class P2PNode(threading.Thread):
    def __init__(self, p2p_port, initial_peer=None):
        super().__init__()
        self.node_address = (getHostIP(), p2p_port)
        self.peers: dict[tuple[str, int], socket.socket] = dict()
        self.validations: dict[tuple[str, int], tuple[int, int]] = dict()
        self.topology: dict[tuple[str, int], list[tuple[str, int]]] = dict()
        self.solves: int = 0
        self.verifications: int = 0
        self.work_divider: WorkDivider = None

        self.p2p_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.p2p_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.p2p_socket.bind(self.node_address)
        self.p2p_socket.listen(5)

        self.selector = selectors.DefaultSelector()
        self.selector.register(self.p2p_socket, selectors.EVENT_READ, data=self.accept)
        self.logger = save(f"[node:{p2p_port}]")

        if initial_peer:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect(initial_peer)
            self.selector.register(conn, selectors.EVENT_READ, self.parse_message)
            self.peers[initial_peer] = conn
            self.send_message(conn, new_join_request(self.node_address))

        self.updateNetwork()
        self.updateStats()

    def run(self) -> None:
        """Loop indefinetely."""
        while True:
            for key, mask in self.selector.select():
                callback = key.data
                selsocket = key.fileobj
                callback(selsocket, mask)

    def accept(self, sock, mask) -> None:
        """Accept new connection."""
        connection, addr = sock.accept()

        self.logger.info(f"Accepted connection from {addr}")
        self.selector.register(connection, selectors.EVENT_READ, self.parse_message)

    def read_socket(self, sock) -> str:
        """Read from socket."""
        message_length = int.from_bytes(sock.recv(4), byteorder="big")
        if message_length == 0:
            for peer, connection in self.peers.items():
                if connection == sock:
                    del self.peers[peer]
                    del self.topology[peer]
                    break
            return None

        data = sock.recv(message_length)
        self.logger.info(f"Received message: {data}")
        return json.loads(data.decode("utf-8"))

    def parse_message(self, conn, mask) -> None:
        """Get message from socket."""
        data = self.read_socket(conn)
        if not data:
            self.selector.unregister(conn)
            conn.close()
            return
        if data["Message"] == "Join_req":
            address = tuple(data["Address"])
            self.peers[address] = conn
            self.send_message(
                conn, network_info_response(list(self.peers.keys()), self.node_address)
            )
            if self.work_divider:
                self.work_divider.workers.append(conn)
            return

        if data["Message"] == "Network_Info_req":
            self.send_message(
                conn, network_info_response(list(self.peers.keys()), self.node_address)
            )
            return

        if data["Message"] == "Network_Info_res":
            network = data["Network"]
            address = tuple(data["Address"])
            self.topology[address] = network

            self.logger.info(f"Received network info: {network}")

            for peer in network:
                peer = tuple(peer)
                if peer not in self.peers:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect(peer)
                    self.selector.register(s, selectors.EVENT_READ, self.parse_message)
                    self.peers[peer] = s
                    self.send_message(s, new_join_request(self.node_address))
            return

        if data["Message"] == "Stats_req":
            self.send_message(
                conn, stats_response(self.solves, self.verifications, self.node_address)
            )
            return

        if data["Message"] == "Stats_res":
            validations = data["Validations"]
            solves = data["Solves"]
            address = tuple(data["Address"])
            self.validations[address] = (solves, validations)
            return

        if data["Message"] == "Sudoku_req":
            sudoku = data["Sudoku"]
            self.logger.info(f"Received request to see if sudoku is correct: \n{sudoku}")
            threading.Thread(target=self.solveSudoku, args=(sudoku, conn)).start()
            return

        if data["Message"] == "Sudoku_res":
            sudoku = data["Sudoku"]
            self.work_divider.worker_finished(conn)
            if sudoku:
                self.logger.info(f"Sudoku solved: \n{sudoku}")
                if self.queue is not None:
                    self.queue.put(sudoku)
            return

        self.logger.error(f"Unknown message type: {data['Message']}")

    def send_message(self, connection: socket.socket, message: dict) -> None:
        """Send message to socket."""
        self.logger.info(f"Sending message: {message}")
        data = json.dumps(message).encode("utf-8")
        connection.sendall(len(data).to_bytes(4, byteorder="big") + data)

    def getStats(self) -> dict:
        return {
            "all": {
                "solved": sum(map(lambda k: k[0], self.validations.values())),
                "validations": sum(map(lambda v: v[1], self.validations.values())),
            },
            "nodes": [
                {"address": node, "validations": self.validations.get(node, (0, 0))[1]}
                for node in self.peers.keys()
            ],
        }

    def getNetwork(self) -> dict:
        self.topology[self.node_address] = list(self.peers.keys())
        return {
            f"{key[0]}:{key[1]}": [f"{item[0]}:{item[1]}" for item in values]
            for (key, values) in self.topology.items()
        }

    def updateNetwork(self):
        for peer in self.peers.values():
            self.send_message(peer, new_network_info_request())
        threading.Timer(10, self.updateNetwork).start()

    def updateStats(self):
        for peer in self.peers.values():
            self.send_message(peer, new_stats_request())
        threading.Timer(10, self.updateStats).start()

    def sendSudoku(self, sudoku: list[list[int]], peer: socket.socket) -> None:
        self.send_message(peer, send_sudoku_request(sudoku))

    def solveSudoku(self, sudoku: list[list[int]], socket: socket.socket) -> None:
        sudoku = Sudoku(sudoku)
        self.logger.info(f"Checking sudoku")
        is_valid = sudoku.check()
        self.logger.info(f"Finished checking sudoku")
        self.verifications += sudoku.verifications

        if is_valid:
            self.solves += 1
            self.send_message(socket, sudoku_response(sudoku.grid))
            return

        self.send_message(socket, sudoku_response(None))

    def receiveSudoku(self, sudoku: list[list[int]], queue: Queue) -> None:
        self.queue = queue
        self.work_divider = WorkDivider(sudoku, self)
        self.work_divider.start()

def getHostIP() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 1))
        IP = s.getsockname()[0]
    except:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distributed Sudoku Solver Node")
    parser.add_argument(
        "-p", "--http_port", type=int, required=True, help="HTTP port of the node"
    )
    parser.add_argument(
        "-s", "--p2p_port", type=int, required=True, help="P2P port of the node"
    )
    parser.add_argument(
        "-a", "--anchor", type=str, help="Address of an existing node to join"
    )
    parser.add_argument(
        "-H",
        "--handicap",
        type=int,
        default=0,
        help="Handicap/delay for validation function in milliseconds",
    )
    args = parser.parse_args()

    anchor = args.anchor.split(":") if args.anchor else None
    if anchor:
        anchor = (anchor[0], int(anchor[1]))
    p2p_node = P2PNode(args.p2p_port, anchor)
    p2p_node.start()

    with ThreadingHTTPServer(("", args.http_port), server_maker(p2p_node)) as server:
        server.serve_forever()
