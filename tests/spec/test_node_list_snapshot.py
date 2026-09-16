from genro_bag import Bag


def test_node_list_snapshot_shares_nodes_but_not_structure():
    bag = Bag({'a': 1, 'b': 2})
    nodes = bag.get_nodes()
    nodes.pop()
    assert bag.keys() == ['a', 'b']
    nodes[0].value = 3
    assert bag['a'] == 3
    bag.set_item('c', 4)
    assert len(nodes) == 1
    filtered = bag.getNodes(lambda node: node.label == 'a')
    assert filtered[0] is nodes[0]
    filtered.clear()
    assert len(bag) == 3
