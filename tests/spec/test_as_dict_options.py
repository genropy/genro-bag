from genro_bag import Bag


def test_recursive_null_filter_and_defaults():
    child = Bag()
    for key, value in [('Null', None), ('Zero', 0), ('False', False), ('Empty', ''), ('Bag', Bag()), ('Code', 'x::JS')]:
        child.set_item(key, value)
    bag = Bag()
    bag.set_item('Child', child)
    assert bag.as_dict()['Child'] is child
    expected = {'child': {'zero': 0, 'false': False, 'empty': '', 'bag': {}, 'code': 'x::JS'}}
    assert bag.as_dict(lower=True, recursive=True, exclude_null_values=True) == expected
    assert bag.asDict(False, True, True, True) == expected
    assert child.get_node('Null') is not None
    assert bag.as_dict(recursive=True)['Child']['Null'] is None


def test_ordinary_containers_and_empty_bags_preserved():
    bag = Bag()
    obj = {'x': None}
    bag.set_item('obj', obj)
    empty = Bag()
    bag.set_item('empty', empty)
    assert bag.as_dict(recursive=True, exclude_null_values=True)['obj'] is obj
    assert bag.as_dict(exclude_null_values=True)['empty'] is empty
