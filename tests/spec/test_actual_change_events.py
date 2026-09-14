import pytest
from genro_bag import Bag

@pytest.mark.parametrize('value,attrs,merge,expected', [
    (2, {'a': 1}, True, 'upd_value'),
    (2, {'a': 2}, True, 'upd_value_attr'),
    (1, {'a': 2}, True, 'upd_attrs'),
    (1, {'a': 1}, True, None),
    (1, {}, False, 'upd_attrs'),
    (1, {'missing': None}, True, None),
])
def test_events_describe_actual_changes(value, attrs, merge, expected):
    bag = Bag()
    bag.set_item('item', 1, {'a': 1})
    node = bag.get_node('item')
    local, parent = [], []
    node.subscribe('watch', lambda **kw: local.append(kw))
    bag.subscribe('watch', update=lambda **kw: parent.append(kw))
    node.set_value(value, _attributes=attrs, _updattr=merge)
    assert [e['evt'] for e in local] == ([expected] if expected else [])
    assert [e['evt'] for e in parent] == ([expected] if expected else [])
    if expected == 'upd_value':
        assert parent[0]['attrs_diff'] is None

def test_update_with_unchanged_attributes_reports_only_value_change():
    target = Bag()
    target.set_item('item', 1, {'a': 1})
    source = Bag()
    source.set_item('item', 2, {'a': 1})
    events = []
    target.subscribe('watch', update=lambda **kw: events.append(kw))
    target.update(source)
    assert [e['evt'] for e in events] == ['upd_value']
