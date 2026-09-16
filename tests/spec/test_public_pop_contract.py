"""Public removal preserves identity and detaches after notifications."""
import pytest

from genro_bag import Bag


@pytest.mark.parametrize('operation', ['pop_node', 'pop'])
@pytest.mark.parametrize('action', ['normal', 'raise', 'reinsert', 'transfer'])
def test_public_removal(operation, action):
    root = Bag()
    root.set_item('outer.child.leaf', 1)
    root.set_backref()
    parent = root['outer']
    node = root.get_node('outer.child')
    child = node.value
    node.attr['caption'] = 'Child'
    destination = Bag()
    destination.set_backref()
    seen = []

    def deleted(**event):
        seen.append(node.parent_bag)
        assert node.parent_bag is parent
        if action == 'raise':
            raise RuntimeError('subscriber failed')
        if action in ('reinsert', 'transfer'):
            target = parent if action == 'reinsert' else destination
            # No public API inserts an existing node; establish callback ownership.
            target._nodes._list.append(node)
            target._nodes._dict[node.label] = node
            node.parent_bag = target

    root.subscribe('watch', delete=deleted)
    if action == 'raise':
        with pytest.raises(RuntimeError, match='subscriber failed'):
            getattr(root, operation)('outer.child')
    else:
        result = getattr(root, operation)('outer.child')
        assert result is (node if operation == 'pop_node' else child)
    assert seen == [parent]
    assert node.attr['caption'] == 'Child'
    if action in ('normal', 'raise'):
        assert node.parent_bag is None
        assert child.parent is None
        assert child.parent_node is None
        assert child.get_node('leaf').parent_bag is child
        local = []
        child.subscribe('local', update=lambda **event: local.append(event))
        child['leaf'] = 2
        assert len(local) == 1
        assert len(seen) == 1
    else:
        target = parent if action == 'reinsert' else destination
        assert node.parent_bag is target
        assert target.get_node('child') is node
        assert child.parent is target


def test_pop_node_preserves_unresolved_resolver():
    from genro_bag.resolver import BagCbResolver
    calls = []
    resolver = BagCbResolver(lambda: calls.append(1) or 42)
    bag = Bag()
    bag.set_item('lazy', resolver)
    node = bag.get_node('lazy')
    assert bag.pop_node('lazy') is node
    assert node.resolver is resolver
    assert calls == []
    assert node.parent_bag is None
