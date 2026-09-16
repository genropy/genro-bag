"""Connected nodes have paths; detached nodes do not."""
from genro_bag import Bag


def test_fullpath_connected_detached_and_reattached():
    root = Bag()
    root.set_item('cliente.nome', 'Mario')
    root.set_backref()
    node = root.get_node('cliente')
    child = node.value
    assert node.fullpath == 'cliente'
    assert child.get_node('nome').fullpath == 'cliente.nome'
    assert root.fullpath is None
    root.pop_node('cliente')
    assert node.fullpath is None
    assert child.get_node('nome').fullpath == 'nome'
    root.set_item('altro', child)
    assert root.get_node('altro').fullpath == 'altro'
    assert child.get_node('nome').fullpath == 'altro.nome'
