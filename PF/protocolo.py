def new_join_request(address: tuple[str, int]) -> dict:
    """Create a new join request."""
    return {
        "Message": "Join_req",
        "Address": address
    }

def new_network_info_request() -> dict:
    """Create a new network info request."""
    return {
        "Message": "Network_Info_req",
    }

def network_info_response(network: list[tuple[str, int]], address: tuple[str, int]) -> dict:
    """Create a new network info response."""
    return {
        "Message": "Network_Info_res",
        "Address":  address,
        "Network": network
    }

def new_stats_request() -> dict:
    """Create a new stats request."""
    return {
        "Message": "Stats_req"
    }

def stats_response(solves: int, validations: int, address: tuple[str, int]) -> dict:
    """Create a new stats response."""
    return {
        "Message": "Stats_res",
        "Address" : address,
        "Validations": validations,
        "Solves": solves
    }

def send_sudoku_request(sudoku: list[list[int]]) -> dict:
    """Create a new sudoku request."""
    return {
        "Message": "Sudoku_req",
        "Sudoku": sudoku
    }

def sudoku_response(sudoku: list[list[int]]) -> dict:
    """Create a new sudoku response."""
    return {
        "Message": "Sudoku_res",
        "Sudoku": sudoku
    }

