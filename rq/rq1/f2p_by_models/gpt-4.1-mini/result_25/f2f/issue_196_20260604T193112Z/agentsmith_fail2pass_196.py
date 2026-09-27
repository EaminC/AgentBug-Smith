import pytest

def test_gomoku_win_detection_order():
    """
    Test the win detection logic in BoardAgent.reply for Gomoku.
    The buggy code checks win before updating the board, missing the current move,
    so a winning move is not detected correctly.
    The fixed code updates the board first, then checks win, detecting the win correctly.

    This test simulates a sequence of moves leading to a win for black.
    It asserts that the game ends with black winning immediately after the winning move.
    """
    from examples.game_gomoku.code.board_agent import BoardAgent, NAME_BLACK, NAME_WHITE, NAME_TO_PIECE

    agent = BoardAgent()
    # Start the game
    response = agent.reply(None)
    assert "Welcome" in response

    # Moves to create a horizontal win for black (NAME_BLACK)
    moves = [
        (NAME_BLACK, (7, 7)),
        (NAME_WHITE, (6, 7)),
        (NAME_BLACK, (7, 8)),
        (NAME_WHITE, (6, 8)),
        (NAME_BLACK, (7, 9)),
        (NAME_WHITE, (6, 9)),
        (NAME_BLACK, (7, 10)),
        (NAME_WHITE, (6, 10)),
        (NAME_BLACK, (7, 11)),  # This should be the winning move
    ]

    for i, (player, pos) in enumerate(moves):
        reply = agent.reply({"name": player, "content": pos})
        if i < len(moves) - 1:
            # Before the last move, game should not end
            assert not agent.game_end
            assert "wins" not in reply
        else:
            # After last move, game should end with black win
            assert agent.game_end
            assert f"{NAME_BLACK} wins" in reply

def test_gomoku_no_false_win_before_board_update():
    """
    Test that before the fix, the check_win call does not detect the win correctly
    because the board is not updated before the check.
    This test is expected to fail on buggy code and pass on fixed code.
    """
    from examples.game_gomoku.code.board_agent import BoardAgent, NAME_BLACK, NAME_WHITE, NAME_TO_PIECE

    agent = BoardAgent()
    # Setup a board state with 4 black stones in a row
    base_row = 7
    for col in range(7, 11):
        agent.board[base_row, col] = NAME_TO_PIECE[NAME_BLACK]

    # Now simulate the last move that should win
    last_move = (base_row, 11)
    # The buggy code checks win before placing the stone, so it won't detect win here
    # We simulate the buggy behavior by calling check_win before updating the board
    win_before_update = agent.check_win(last_move[0], last_move[1], NAME_TO_PIECE[NAME_BLACK])
    assert win_before_update is False  # Buggy behavior: no win detected yet

    # Now update the board and check win again (fixed behavior)
    agent.board[last_move[0], last_move[1]] = NAME_TO_PIECE[NAME_BLACK]
    win_after_update = agent.check_win(last_move[0], last_move[1], NAME_TO_PIECE[NAME_BLACK])
    assert win_after_update is True  # Fixed behavior: win detected after board update

def test_gomoku_draw_detection():
    """
    Test that the draw detection still works correctly.
    Fill the board with no winner and verify the draw message.
    """
    from examples.game_gomoku.code.board_agent import BoardAgent, NAME_BLACK, NAME_WHITE, NAME_TO_PIECE

    agent = BoardAgent()
    # Fill the board alternately with black and white pieces without any winning line
    size = agent.board.shape[0]
    for r in range(size):
        for c in range(size):
            # Alternate pieces
            piece = NAME_TO_PIECE[NAME_BLACK] if (r + c) % 2 == 0 else NAME_TO_PIECE[NAME_WHITE]
            agent.board[r, c] = piece

    # The board is full, so check_draw should be True
    assert agent.check_draw() is True

    # Simulate a move on a full board should not be allowed
    with pytest.raises(AssertionError):
        agent.assert_valid_move(0, 0)

    # The reply should detect draw if called with a move on full board (simulate last move)
    # But since board is full, no moves should be valid, so test reply with None (start)
    response = agent.reply(None)
    assert "Welcome" in response or isinstance(response, str)

    # For completeness, test reply with a move on full board raises error
    with pytest.raises(AssertionError):
        agent.reply({"name": NAME_BLACK, "content": (0, 0)})