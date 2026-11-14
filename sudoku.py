"""A small, dependency-free Sudoku game built with Tkinter."""

from __future__ import annotations

import random
import time
import tkinter as tk
from tkinter import messagebox, ttk


SIZE = 9
BOX = 3


def candidates(board: list[list[int]], row: int, col: int) -> list[int]:
    used = set(board[row])
    used.update(board[r][col] for r in range(SIZE))
    box_row, box_col = row // BOX * BOX, col // BOX * BOX
    used.update(
        board[r][c]
        for r in range(box_row, box_row + BOX)
        for c in range(box_col, box_col + BOX)
    )
    return [n for n in range(1, 10) if n not in used]


def solve(board: list[list[int]], limit: int = 1) -> int:
    """Solve in place and return the number of solutions found (up to limit)."""
    best_cell = None
    best_options = None
    for row in range(SIZE):
        for col in range(SIZE):
            if board[row][col] == 0:
                options = candidates(board, row, col)
                if not options:
                    return 0
                if best_options is None or len(options) < len(best_options):
                    best_cell, best_options = (row, col), options
                    if len(options) == 1:
                        break
        if best_options is not None and len(best_options) == 1:
            break

    if best_cell is None:
        return 1

    row, col = best_cell
    count = 0
    for value in best_options or []:
        board[row][col] = value
        count += solve(board, limit - count)
        if count >= limit:
            board[row][col] = 0
            return count
    board[row][col] = 0
    return count


def make_puzzle(difficulty: str) -> tuple[list[list[int]], list[list[int]]]:
    solution = [[0] * SIZE for _ in range(SIZE)]

    def fill() -> bool:
        empty = None
        options = None
        for r in range(SIZE):
            for c in range(SIZE):
                if solution[r][c] == 0:
                    possible = candidates(solution, r, c)
                    if not possible:
                        return False
                    if options is None or len(possible) < len(options):
                        empty, options = (r, c), possible
        if empty is None:
            return True
        r, c = empty
        random.shuffle(options)
        for value in options:
            solution[r][c] = value
            if fill():
                return True
        solution[r][c] = 0
        return False

    fill()
    puzzle = [row[:] for row in solution]
    # Target clue counts keep games quick while retaining a unique solution.
    clues = {"Easy": 40, "Medium": 34, "Hard": 29}[difficulty]
    cells = [(r, c) for r in range(SIZE) for c in range(SIZE)]
    random.shuffle(cells)
    remaining = SIZE * SIZE
    for row, col in cells:
        if remaining <= clues:
            break
        value = puzzle[row][col]
        puzzle[row][col] = 0
        probe = [line[:] for line in puzzle]
        if solve(probe, limit=2) != 1:
            puzzle[row][col] = value
        else:
            remaining -= 1
    return puzzle, solution


class SudokuGame:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Sudoku")
        self.root.resizable(True, True)
        self.root.minsize(640, 850)
        self.root.configure(bg="#f4f6fa")
        self.entries: list[list[tk.Entry]] = []
        self.puzzle: list[list[int]] = []
        self.solution: list[list[int]] = []
        self.started_at = 0.0
        self.elapsed_before_pause = 0
        self.finished = False
        self.difficulty = tk.StringVar(value="Easy")
        self.status = tk.StringVar(value="Fill the grid. Each row, column, and box needs 1–9.")
        self.timer_text = tk.StringVar(value="00:00")
        self._build_ui()
        self.new_game()
        self._tick()

    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg="#f4f6fa", padx=22, pady=18)
        outer.pack()
        heading = tk.Frame(outer, bg="#f4f6fa")
        heading.pack(fill="x", pady=(0, 12))
        tk.Label(heading, text="SUDOKU", font=("Segoe UI", 23, "bold"),
                 fg="#17233b", bg="#f4f6fa").pack(side="left")
        tk.Label(heading, textvariable=self.timer_text, font=("Segoe UI", 15, "bold"),
                 fg="#52627d", bg="#f4f6fa").pack(side="right", padx=(0, 4))

        controls = tk.Frame(outer, bg="#f4f6fa")
        controls.pack(fill="x", pady=(0, 12))
        ttk.Label(controls, text="Difficulty").pack(side="left", padx=(0, 7))
        self.level_box = ttk.Combobox(controls, textvariable=self.difficulty,
                                      values=("Easy", "Medium", "Hard"),
                                      state="readonly", width=9)
        self.level_box.pack(side="left")
        self._button(controls, "New game", self.new_game, primary=True).pack(side="right")

        grid_frame = tk.Frame(outer, bg="#24334d", padx=3, pady=3)
        grid_frame.pack()
        for r in range(SIZE):
            row_entries = []
            for c in range(SIZE):
                cell = tk.Frame(grid_frame, bg="#d9e0eb", padx=1, pady=1)
                cell.grid(row=r, column=c, padx=(1 if c % 3 else 2, 1),
                          pady=(1 if r % 3 else 2, 1))
                entry = tk.Entry(
                    cell, width=3, justify="center", relief="flat", bd=0,
                    font=("Segoe UI", 20, "bold"),
                    disabledbackground="#e8edf5", disabledforeground="#293955",
                    readonlybackground="white", bg="white", fg="#2366c2",
                    insertbackground="#2366c2", highlightthickness=0,
                )
                entry.pack(ipady=2)
                entry.bind("<KeyPress>", lambda event, rr=r, cc=c: self._on_key(event, rr, cc))
                entry.bind("<FocusIn>", lambda _event, rr=r, cc=c: self._focus_related(rr, cc))
                row_entries.append(entry)
            self.entries.append(row_entries)

        actions = tk.Frame(outer, bg="#f4f6fa")
        actions.pack(fill="x", pady=(13, 8))
        self._button(actions, "Check", self.check_board).pack(side="left")
        self._button(actions, "Clear entries", self.clear_entries).pack(side="left", padx=8)
        self._button(actions, "Show solution", self.show_solution).pack(side="right")
        tk.Label(outer, textvariable=self.status, anchor="w", justify="left",
                 wraplength=430, font=("Segoe UI", 9), fg="#52627d",
                 bg="#f4f6fa").pack(fill="x", pady=(2, 0))

    @staticmethod
    def _button(parent: tk.Widget, text: str, command, primary: bool = False) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command, cursor="hand2",
            font=("Segoe UI", 9, "bold" if primary else "normal"),
            bg="#2868c7" if primary else "#e5eaf2",
            fg="white" if primary else "#263752",
            activebackground="#1e55a5" if primary else "#d5deea",
            activeforeground="white" if primary else "#263752",
            relief="flat", padx=12, pady=7,
        )

    def new_game(self) -> None:
        self.puzzle, self.solution = make_puzzle(self.difficulty.get())
        self.finished = False
        self.started_at = time.time()
        self.elapsed_before_pause = 0
        for r in range(SIZE):
            for c in range(SIZE):
                entry = self.entries[r][c]
                entry.config(state="normal")
                entry.delete(0, "end")
                entry.config(disabledbackground="#e8edf5", bg="white")
                if self.puzzle[r][c]:
                    entry.insert(0, str(self.puzzle[r][c]))
                    entry.config(state="disabled")
        self.status.set(f"{self.difficulty.get()} puzzle ready. Each row, column, and box needs 1–9.")
        self.entries[0][0].focus_set()

    def _on_key(self, event: tk.Event, row: int, col: int):
        if event.keysym in ("BackSpace", "Delete", "0"):
            self.entries[row][col].delete(0, "end")
            self._clear_marks()
            return "break"
        if event.char and event.char in "123456789":
            self.entries[row][col].delete(0, "end")
            self.entries[row][col].insert(0, event.char)
            self._clear_marks()
            return "break"
        if event.keysym in ("Left", "Right", "Up", "Down"):
            dr, dc = {"Left": (0, -1), "Right": (0, 1),
                      "Up": (-1, 0), "Down": (1, 0)}[event.keysym]
            self.entries[(row + dr) % SIZE][(col + dc) % SIZE].focus_set()
            return "break"
        if event.keysym in ("Tab", "ISO_Left_Tab", "Shift_L"):
            return None
        return "break"

    def _focus_related(self, row: int, col: int) -> None:
        for r in range(SIZE):
            for c in range(SIZE):
                if self.puzzle and not self.puzzle[r][c]:
                    related = r == row or c == col or (r // 3 == row // 3 and c // 3 == col // 3)
                    self.entries[r][c].config(bg="#f0f5fc" if related else "white")

    def _board(self) -> list[list[int]]:
        board = []
        for row in self.entries:
            values = []
            for entry in row:
                value = entry.get().strip()
                values.append(int(value) if value and value in "123456789" else 0)
            board.append(values)
        return board

    def _clear_marks(self) -> None:
        for r in range(SIZE):
            for c in range(SIZE):
                if self.puzzle and not self.puzzle[r][c]:
                    self.entries[r][c].config(fg="#2366c2")

    def check_board(self) -> None:
        board = self._board()
        conflicts: set[tuple[int, int]] = set()
        for r in range(SIZE):
            for c in range(SIZE):
                value = board[r][c]
                if not value:
                    continue
                peers = [(r, x) for x in range(SIZE) if x != c]
                peers += [(x, c) for x in range(SIZE) if x != r]
                peers += [(x, y) for x in range(r // 3 * 3, r // 3 * 3 + 3)
                          for y in range(c // 3 * 3, c // 3 * 3 + 3)
                          if (x, y) != (r, c)]
                if any(board[x][y] == value for x, y in peers):
                    conflicts.add((r, c))
        self._clear_marks()
        for r, c in conflicts:
            self.entries[r][c].config(fg="#d33b42")
        if conflicts:
            self.status.set(f"There are {len(conflicts)} conflicting entries. Red cells break a row, column, or box rule.")
        elif all(all(row) for row in board):
            if board == self.solution:
                self.finished = True
                self.status.set("Solved! Great work.")
                messagebox.showinfo("Sudoku", "Puzzle solved. Great work!")
            else:
                self.status.set("No rule conflicts, but some numbers are not in the solution yet.")
        else:
            filled = sum(value != 0 for row in board for value in row)
            self.status.set(f"So far, so good: {filled} of 81 cells filled, with no conflicts.")

    def clear_entries(self) -> None:
        for r in range(SIZE):
            for c in range(SIZE):
                if not self.puzzle[r][c]:
                    self.entries[r][c].delete(0, "end")
                    self.entries[r][c].config(fg="#2366c2")
        self.status.set("Your entries have been cleared.")

    def show_solution(self) -> None:
        if not messagebox.askyesno("Show solution", "Fill the board with the solution?"):
            return
        for r in range(SIZE):
            for c in range(SIZE):
                entry = self.entries[r][c]
                if not self.puzzle[r][c]:
                    entry.config(state="normal")
                    entry.delete(0, "end")
                    entry.insert(0, str(self.solution[r][c]))
                    entry.config(state="disabled", disabledforeground="#2366c2")
        self.finished = True
        self.status.set("Solution shown. Start a new game whenever you’re ready.")

    def _tick(self) -> None:
        if not self.finished:
            seconds = int(time.time() - self.started_at)
            self.timer_text.set(f"{seconds // 60:02}:{seconds % 60:02}")
        self.root.after(1000, self._tick)


def main() -> None:
    root = tk.Tk()
    SudokuGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
