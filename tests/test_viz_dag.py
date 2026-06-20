import asyncio
import os
import pytest

from src.backends.dag_viz import render_dag
from src.demo import live_demo


@pytest.mark.asyncio
async def test_dag_gif_written():
    board = (await live_demo())["replica"]
    nodes = list(board.dag.nodes.values())
    path = "out/test_dag.gif"
    if os.path.exists(path):
        os.remove(path)
    n = render_dag(nodes, path)
    assert n > 1
    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert f.read(6) == b"GIF89a"
