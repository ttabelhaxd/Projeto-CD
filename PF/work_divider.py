from itertools import product
import threading

class WorkDivider(threading.Thread):
    def __init__(self, sudoku: list[list[int]], node) -> None:
        super().__init__()
        self.divisions = self.generate_sudoku_permutations(sudoku)
        self.node = node
        self.workers = list(node.peers.values())
        
    def generate_sudoku_permutations(self, sudoku: list[list[int]]):
        # Find the positions of all the zeros
        zero_positions = [(i, j) for i in range(9) for j in range(9) if sudoku[i][j] == 0]
        
        # Generate all possible combinations of numbers (1 to 9) for the zero positions
        all_combinations = product(range(1, 10), repeat=len(zero_positions))
        
        # Generate all possible sudokus
        all_sudokus = []
        for combination in all_combinations:
            new_sudoku = [row[:] for row in sudoku]  # Create a copy of the original sudoku
            for pos, value in zip(zero_positions, combination):
                new_sudoku[pos[0]][pos[1]] = value
            all_sudokus.append(new_sudoku)
        
        return all_sudokus

    def run(self):
        while len(self.divisions) > 0:
            if len(self.workers) == 0:
                continue
            worker = self.workers.pop()
            sudoku = self.divisions.pop()
            self.node.sendSudoku(sudoku, worker)

    def worker_finished(self, worker):
        self.workers.append(worker)