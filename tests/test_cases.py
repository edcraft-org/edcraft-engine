cases = [
    {
        "code": """def dft(graph, start):
    visited = set()
    stack = [start]

    while stack:
        node = stack.pop()
        
        if node not in visited:
            visited.add(node)
            stack.extend(reversed(graph[node]))
    """,
        "question_spec": {
            "target": [
                {
                    "type": "loop",
                    "id": [0],
                    "name": None,
                    "line_number": 5,
                    "modifier": "loop_iterations",
                },
                {
                    "type": "function",
                    "id": [3],
                    "name": "visited.add",
                    "line_number": 9,
                    "modifier": "arguments",
                },
            ],
            "output_type": "first",
            "question_type": "mcq",
        },
        "execution_spec": {
            "entry_function": "dft",
            "input_data": {
                "graph": {"A": ["B", "C"], "B": ["D"], "C": [], "D": []},
                "start": "A",
            },
        },
        "generation_options": {"num_distractors": 3},
        "answer": "['A', 'B', 'D', 'C']",
    },
    {
        "code": "def insertionSort(arr):\n    for i in range(1, len(arr)):\n        key = arr[i]\n        j = i - 1\n        while j >= 0 and key < arr[j]:\n            arr[j + 1] = arr[j]\n            j -= 1\n\n        arr[j + 1] = key",
        "execution_spec": {
            "entry_function": "insertionSort",
            "input_data": {"arr": [3, 1, 5, 2]},
        },
        "question_spec": {
            "target": [
                {
                    "type": "loop",
                    "id": [0],
                    "line_number": 2,
                    "modifier": "loop_iterations",
                },
                {"type": "variable", "id": [0], "name": "arr"},
            ],
            "output_type": "last",
            "question_type": "mcq",
        },
        "generation_options": {"num_distractors": 3},
        "answer": "[[1, 3, 5, 2], [1, 3, 5, 2], [1, 2, 3, 5]]",
    },
    {
        "code": """def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                swap(arr, j, j + 1)
                swapped = True
        if not swapped:
            break

def swap(arr, a, b):
    arr[a], arr[b] = arr[b], arr[a]
    """,
        "question_spec": {
            "target": [
                {
                    "type": "function",
                    "id": [4],
                    "name": "swap",
                    "line_number": 7,
                }
            ],
            "output_type": "count",
            "question_type": "mcq",
        },
        "execution_spec": {
            "entry_function": "bubble_sort",
            "input_data": {
                "arr": [64, 34, 25, 12, 22, 11, 90],
            },
        },
        "generation_options": {"num_distractors": 3},
        "answer": "14",
    },
    {
        "code": "def bft(graph, start_node):\n    visited = set([start_node])\n    frontier = [start_node]\n\n    while frontier:\n        next_frontier = []\n        while frontier:\n            current_node = frontier.pop(0)\n            for neighbor in graph.get(current_node, []):\n                if neighbor not in visited:\n                    visited.add(neighbor)\n                    next_frontier.append(neighbor)\n        frontier = next_frontier",
        "execution_spec": {
            "entry_function": "bft",
            "input_data": {
                "graph": {
                    "A": ["B", "C"],
                    "B": ["D", "E"],
                    "C": ["F"],
                    "D": [],
                    "E": ["F"],
                    "F": [],
                },
                "start_node": "A",
            },
        },
        "question_spec": {
            "target": [
                {
                    "type": "loop",
                    "id": [0],
                    "line_number": 5,
                    "modifier": "loop_iterations",
                },
                {"type": "variable", "id": [0], "name": "frontier"},
            ],
            "output_type": "first",
            "question_type": "mcq",
        },
        "generation_options": {"num_distractors": 3},
        "answer": "[['A'], ['B', 'C'], ['D', 'E', 'F']]",
    },
    {
        "code": "def sum_n(n, sum):\n    if n <= 0:\n        return n\n    return sum_n(n - 1, sum + n)\n",
        "execution_spec": {"entry_function": "sum_n", "input_data": {"n": 3, "sum": 0}},
        "question_spec": {
            "target": [
                {
                    "type": "function",
                    "id": [0],
                    "name": "sum_n",
                    "line_number": 1,
                    "modifier": "arguments",
                    "argument_keys": ["sum"],
                }
            ],
            "output_type": "list",
            "question_type": "mcq",
        },
        "generation_options": {"num_distractors": 3},
        "answer": "[0, 3, 5, 6]",
    },
    {
        "code": "def binary_search(arr, target):\n    left = 0\n    right = len(arr) - 1\n    \n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1",
        "execution_spec": {
            "entry_function": "binary_search",
            "input_data": {"arr": [1, 3, 5, 10, 11, 15, 18, 20], "target": 18},
        },
        "question_spec": {
            "target": [
                {
                    "type": "loop",
                    "id": [0],
                    "line_number": 5,
                    "modifier": "loop_iterations",
                },
                {"type": "variable", "id": [0], "name": "left,right"},
            ],
            "output_type": "first",
            "question_type": "mcq",
        },
        "generation_options": {"num_distractors": 3},
        "answer": "[(0, 7), (4, 7), (6, 7)]",
    },
    {
        "code": "def binary_search(arr, target):\n    left = 0\n    right = len(arr) - 1\n    \n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1",
        "execution_spec": {
            "entry_function": "binary_search",
            "input_data": {"arr": [1, 3, 5, 10, 11, 15, 18, 20], "target": 18},
        },
        "question_spec": {
            "target": [
                {"type": "variable", "id": [0], "name": "left,right"},
            ],
            "output_type": "list",
            "question_type": "mcq",
        },
        "generation_options": {"num_distractors": 3},
        "answer": "[{'left': [0, 4, 6], 'right': [7]}]",
    },
    {
        "code": "def example(n):\n    return n+1\n",
        "execution_spec": {"entry_function": "example", "input_data": {"n": 3}},
        "question_spec": {
            "target": [
                {"type": "function", "id": [0], "name": "example", "line_number": 1},
                {"type": "variable", "id": [0], "name": "n"},
            ],
            "output_type": "first",
            "question_type": "mcq",
        },
        "generation_options": {"num_distractors": 4},
        "answer": "[3]",
    },
    {
        "code": "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        swapped = False\n        for j in range(0, n - i - 1):\n            if arr[j] > arr[j + 1]:\n                swap(arr, j, j + 1)\n                swapped = True\n        if not swapped:\n            break\n\ndef swap(arr, a, b):\n    arr[a], arr[b] = arr[b], arr[a]",
        "execution_spec": {
            "entry_function": "bubble_sort",
            "input_data": {"arr": [9, 8, 7, 6]},
        },
        "question_spec": {
            "target": [
                {
                    "type": "loop",
                    "id": [0],
                    "line_number": 3,
                    "modifier": "loop_iterations",
                },
                {"type": "variable", "id": [0], "name": "arr"},
            ],
            "output_type": "last",
            "question_type": "mcq",
        },
        "generation_options": {"num_distractors": 3},
        "answer": "[[8, 7, 6, 9], [7, 6, 8, 9], [6, 7, 8, 9], [6, 7, 8, 9]]",
    },
    # [loop(loop_iterations), branch(branch_true)]: per-iteration count of branch_true
    {
        "code": "def count_positives(arr):\n    count = 0\n    for x in arr:\n        if x > 0:\n            count += 1\n    return count\n",
        "execution_spec": {
            "entry_function": "count_positives",
            "input_data": {"arr": [-1, 2, -3, 4, 5]},
        },
        "question_spec": {
            "target": [
                {
                    "type": "loop",
                    "id": [0],
                    "name": None,
                    "line_number": 3,
                    "modifier": "loop_iterations",
                },
                {
                    "type": "branch",
                    "id": [0],
                    "name": None,
                    "line_number": 4,
                    "modifier": "branch_true",
                },
            ],
            "output_type": "count",
            "question_type": "mcq",
        },
        "generation_options": {"num_distractors": 3},
        "answer": "[0, 1, 0, 1, 1]",
    },
]
