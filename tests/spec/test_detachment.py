import pytest
from genro_bag import Bag

@pytest.mark.parametrize('operation', ['replace', 'none', 'pop', 'clear', 'silent_clear'])
def test_removed_subtree_is_independent(operation):
    root = Bag()
    root.set_backref()
    child = Bag()
    child.set_item('nested', Bag({'x': 1}))
    root.set_item('child', child)
    node = root.get_node('child')
    events = []
    root.subscribe('test', any=lambda **kw: events.append(kw))
    if operation == 'replace': root.set_item('child', Bag({'y': 2}))
    if operation == 'none': node.set_value(None, trigger=False)
    if operation == 'pop': root.pop_node('child')
    if operation == 'clear': root.clear()
    if operation == 'silent_clear': root.clear(trigger=False)
    assert child.parent is None
    assert child.parent_node is None
    assert child.get_item('nested').parent is child
    if operation in ('pop', 'clear', 'silent_clear'): assert node.parent_bag is None
    events.clear()
    child.set_item('nested.x', 2)
    assert not events
    root.set_item('reattached', child)
    events.clear()
    child.set_item('nested.x', 3)
    assert len(events) == 1

def test_delete_subscribers_see_popped_node_still_attached():
    root = Bag()
    root.set_backref()
    root.set_item('outer.child', Bag({'x': 1}))
    inner = root.get_item('outer')
    node = inner.get_node('child')
    seen = []
    root.subscribe('test', delete=lambda node, **kw: seen.append((node.parent_bag, node.parent_node.label)))
    root.pop_node('outer.child')
    assert seen == [(inner, 'outer')]
    assert node.parent_bag is None
    assert node.parent_node is None

def test_identical_child_stays_attached():
    root = Bag()
    root.set_backref()
    child = Bag()
    root.set_item('child', child)
    root.set_item('child', child)
    assert child.parent is root

def test_nested_clear_transfers_children_to_independent_event_snapshot():
    root = Bag()
    root.set_backref()
    child = Bag({'nested': Bag({'x': 1})})
    root.set_item('child', child)
    nested = child.get_item('nested')
    events = []
    root.subscribe('test', any=lambda **kw: events.append(kw))
    child.clear()
    assert nested.parent is not child
    assert nested.parent.parent is None
    events.clear()
    nested.set_item('x', 2)
    assert not events

def test_replacement_callback_observes_detached_old_subtree():
    root = Bag()
    root.set_backref()
    child = Bag({'x': 1})
    root.set_item('child', child)
    seen = []
    def changed(**event):
        assert event['oldvalue'] is child
        assert child.parent_node is None
        seen.append(event)
    root.subscribe('watch', update=changed)
    root.set_item('child', 1)
    assert len(seen) == 1

def test_explicit_parent_removal_clears_both_links():
    root = Bag()
    root.set_backref()
    child = Bag()
    root.set_item('child', child)
    child.del_parent_ref()
    assert child.parent is None
    assert child.parent_node is None
