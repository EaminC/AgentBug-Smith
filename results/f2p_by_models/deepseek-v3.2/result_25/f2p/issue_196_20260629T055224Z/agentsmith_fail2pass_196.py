import sys
import pytest


def test_gomoku_win_check_bug():
    """Test that win detection works correctly after board update (bug fix)."""
    # Mock matplotlib to avoid import errors in the board_agent
    sys.modules['matplotlib'] = type(sys)('matplotlib')
    sys.modules['matplotlib.pyplot'] = type(sys)('pyplot')
    sys.modules['matplotlib.patches'] = type(sys)('patches')

    from examples.game_gomoku.code.board_agent import (
        BoardAgent,
        NAME_BLACK,
        NAME_WHITE,
        NAME_TO_PIECE,
    )

    # Clean up the mock after import
    del sys.modules['matplotlib']
    del sys.modules['matplotlib.pyplot']
    del sys.modules['matplotlib.patches']

    # Mock the logger.chat method to avoid AttributeError
    import agentscope.agents.agent as agent_module
    original_logger = agent_module.logger
    mock_logger = type('MockLogger', (), {'chat': lambda self, x: None})()
    agent_module.logger = mock_logger

    try:
        agent = BoardAgent(name="host")

        # Place 4 black pieces horizontally at (0,0)-(0,3)
        for col in range(4):
            agent.board[0, col] = NAME_TO_PIECE[NAME_BLACK]

        # 5th horizontal piece at (0,4) should cause win
        move_msg = {"name": NAME_BLACK, "content": (0, 4)}
        response = agent.reply(move_msg)

        # In buggy version, check_win is called BEFORE board update,
        # so it will not detect win (since board[0,4] is still empty).
        # In fixed version, board is updated first, then check_win detects win.
        # We need to verify that game_end is True and content indicates win.
        assert agent.game_end is True
        assert "wins" in response["content"]
        assert NAME_BLACK in response["content"]
    finally:
        agent_module.logger = original_logger


def test_gomoku_no_false_win_before_update():
    """Test that win is not falsely detected before board update (bug)."""
    sys.modules['matplotlib'] = type(sys)('matplotlib')
    sys.modules['matplotlib.pyplot'] = type(sys)('pyplot')
    sys.modules['matplotlib.patches'] = type(sys)('patches')

    from examples.game_gomoku.code.board_agent import (
        BoardAgent,
        NAME_BLACK,
        NAME_WHITE,
        NAME_TO_PIECE,
    )

    del sys.modules['matplotlib']
    del sys.modules['matplotlib.pyplot']
    del sys.modules['matplotlib.patches']

    import agentscope.agents.agent as agent_module
    original_logger = agent_module.logger
    mock_logger = type('MockLogger', (), {'chat': lambda self, x: None})()
    agent_module.logger = mock_logger

    try:
        agent = BoardAgent(name="host")

        # Place 3 black pieces horizontally at (0,0)-(0,2)
        for col in range(3):
            agent.board[0, col] = NAME_TO_PIECE[NAME_BLACK]

        # Place a white piece interrupting at (0,3)
        agent.board[0, 3] = NAME_TO_PIECE[NAME_WHITE]

        # Black's 4th piece at (0,4) - not a win because (0,3) is white
        move_msg = {"name": NAME_BLACK, "content": (0, 4)}
        response = agent.reply(move_msg)

        # In buggy version, check_win is called BEFORE board update,
        # and it will incorrectly think there is no win (since board[0,4] empty).
        # Actually after board update, there is still no win because of white at (0,3).
        # So game_end should be False.
        # In fixed version, board updated first, check_win correctly returns False.
        assert agent.game_end is False
        assert "wins" not in response["content"]
    finally:
        agent_module.logger = original_logger


def test_gomoku_diagonal_win():
    """Test diagonal win detection after board update."""
    sys.modules['matplotlib'] = type(sys)('matplotlib')
    sys.modules['matplotlib.pyplot'] = type(sys)('pyplot')
    sys.modules['matplotlib.patches'] = type(sys)('patches')

    from examples.game_gomoku.code.board_agent import (
        BoardAgent,
        NAME_WHITE,
        NAME_TO_PIECE,
    )

    del sys.modules['matplotlib']
    del sys.modules['matplotlib.pyplot']
    del sys.modules['matplotlib.patches']

    import agentscope.agents.agent as agent_module
    original_logger = agent_module.logger
    mock_logger = type('MockLogger', (), {'chat': lambda self, x: None})()
    agent_module.logger = mock_logger

    try:
        agent = BoardAgent(name="host")

        # Place 4 white pieces diagonally
        for i in range(4):
            agent.board[i, i] = NAME_TO_PIECE[NAME_WHITE]

        # 5th diagonal piece at (4,4) should cause win
        move_msg = {"name": NAME_WHITE, "content": (4, 4)}
        response = agent.reply(move_msg)

        assert agent.game_end is True
        assert "wins" in response["content"]
        assert NAME_WHITE in response["content"]
    finally:
        agent_module.logger = original_logger


def test_gomoku_vertical_win():
    """Test vertical win detection after board update."""
    sys.modules['matplotlib'] = type(sys)('matplotlib')
    sys.modules['matplotlib.pyplot'] = type(sys)('pyplot')
    sys.modules['matplotlib.patches'] = type(sys)('patches')

    from examples.game_gomoku.code.board_agent import (
        BoardAgent,
        NAME_BLACK,
        NAME_TO_PIECE,
    )

    del sys.modules['matplotlib']
    del sys.modules['matplotlib.pyplot']
    del sys.modules['matplotlib.patches']

    import agentscope.agents.agent as agent_module
    original_logger = agent_module.logger
    mock_logger = type('MockLogger', (), {'chat': lambda self, x: None})()
    agent_module.logger = mock_logger

    try:
        agent = BoardAgent(name="host")

        # Place 4 black pieces vertically at column 0
        for row in range(4):
            agent.board[row, 0] = NAME_TO_PIECE[NAME_BLACK]

        # 5th vertical piece at (4, 0) should cause win
        move_msg = {"name": NAME_BLACK, "content": (4, 0)}
        response = agent.reply(move_msg)

        assert agent.game_end is True
        assert "wins" in response["content"]
        assert NAME_BLACK in response["content"]
    finally:
        agent_module.logger = original_logger


def test_gomoku_draw_detection():
    """Test that draw detection still works correctly after fix."""
    sys.modules['matplotlib'] = type(sys)('matplotlib')
    sys.modules['matplotlib.pyplot'] = type(sys)('pyplot')
    sys.modules['matplotlib.patches'] = type(sys)('patches')

    from examples.game_gomoku.code.board_agent import (
        BoardAgent,
        NAME_BLACK,
        NAME_WHITE,
        NAME_TO_PIECE,
    )

    del sys.modules['matplotlib']
    del sys.modules['matplotlib.pyplot']
    del sys.modules['matplotlib.patches']

    import agentscope.agents.agent as agent_module
    original_logger = agent_module.logger
    mock_logger = type('MockLogger', (), {'chat': lambda self, x: None})()
    agent_module.logger = mock_logger

    try:
        agent = BoardAgent(name="host")

        # Fill board completely without any win (alternating pattern)
        for row in range(agent.board.shape[0]):
            for col in range(agent.board.shape[1]):
                if (row + col) % 2 == 0:
                    agent.board[row, col] = NAME_TO_PIECE[NAME_BLACK]
                else:
                    agent.board[row, col] = NAME_TO_PIECE[NAME_WHITE]

        # Last move (already placed, but we need to trigger reply)
        # Set one empty spot for the move
        agent.board[-1, -1] = 0
        move_msg = {"name": NAME_BLACK, "content": (agent.board.shape[0]-1, agent.board.shape[1]-1)}
        response = agent.reply(move_msg)

        # After placing the last piece, board is full, check_draw should return True
        assert agent.game_end is True
        assert "draw" in response["content"].lower()
    finally:
        agent_module.logger = original_logger
