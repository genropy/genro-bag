"""Value lookup follows paths inside Bag rows, without searching extra rows."""
import pytest

from genro_bag import Bag


@pytest.mark.parametrize('value', [1, 0, False, ''])
def test_bag_row_path_lookup(value):
    bag = Bag()
    bag.set_item('first.nested.field', value)
    bag.set_item('second.nested.field', value)
    assert bag.get_node_by_value('nested.field', value) is bag.get_node('first')
    assert bag.getNodeByValue('nested.field', value) is bag.get_node('first')
    assert bag.get_node_by_value('field', value) is None


def test_dictionary_keys_remain_literal():
    bag = Bag()
    bag.set_item('row', {'nested.field': 7})
    assert bag.get_node_by_value('nested.field', 7) is bag.get_node('row')
