# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Subscription and reactive examples.

Demonstrates Bag's reactive capabilities:
- Subscribing to node changes
- Callbacks on value updates
- Building reactive data flows
"""

from __future__ import annotations

from genro_bag import Bag


def demo_basic_subscription():
    """Basic subscription to value changes."""
    print("=" * 60)
    print("Basic Subscription")
    print("=" * 60)

    bag = Bag()
    bag.set_item("counter", 0)

    # Track changes
    changes = []

    def on_change(node, info, evt, **kwargs):
        """Callback receives: node, info (old_value), evt (event type)."""
        old_value = info
        new_value = node.value
        changes.append((old_value, new_value))
        print(f"  Counter changed: {old_value} -> {new_value} (evt={evt})")

    # Subscribe to changes
    node = bag.get_node("counter")
    node.subscribe("demo", on_change)

    print("Subscribing to 'counter' changes...")
    print()

    # Make changes
    bag.set_item("counter", 1)
    bag.set_item("counter", 2)
    bag.set_item("counter", 5)

    print(f"\nTotal changes recorded: {len(changes)}")


def demo_nested_subscription():
    """Subscription to nested structure changes."""
    print("\n" + "=" * 60)
    print("Nested Structure Subscription")
    print("=" * 60)

    bag = Bag()
    bag.set_item("user", Bag())
    bag["user"].set_item("profile", Bag())
    bag["user.profile"].set_item("name", "John")
    bag["user.profile"].set_item("email", "john@example.com")

    def on_profile_change(node, info, evt, **kwargs):
        old_value = info
        new_value = node.value
        print(f"  Profile '{node.label}' changed: {old_value} -> {new_value}")

    # Subscribe to profile fields
    for node in bag["user.profile"]:
        node.subscribe("profile_watcher", on_profile_change)

    print("Subscribing to all profile fields...")
    print()

    # Make changes
    bag["user.profile"].set_item("name", "John Doe")
    bag["user.profile"].set_item("email", "johndoe@example.com")


def demo_computed_values():
    """Using subscriptions for computed values."""
    print("\n" + "=" * 60)
    print("Computed Values")
    print("=" * 60)

    bag = Bag()
    bag.set_item("price", 100)
    bag.set_item("quantity", 2)
    bag.set_item("total", 200)  # computed

    def update_total(node, info, evt, **kwargs):
        price = bag["price"]
        quantity = bag["quantity"]
        new_total = price * quantity
        print(f"  Recalculating total: {price} x {quantity} = {new_total}")
        bag.set_item("total", new_total)

    # Subscribe price and quantity to update total
    bag.get_node("price").subscribe("calc", update_total)
    bag.get_node("quantity").subscribe("calc", update_total)

    print("Price and quantity subscribed to update total...")
    print()

    print("Changing price to 150:")
    bag.set_item("price", 150)

    print("\nChanging quantity to 3:")
    bag.set_item("quantity", 3)

    print(f"\nFinal total: {bag['total']}")


def demo_unsubscribe():
    """Unsubscribing from changes."""
    print("\n" + "=" * 60)
    print("Unsubscribe")
    print("=" * 60)

    bag = Bag()
    bag.set_item("value", 0)

    call_count = 0

    def on_change(node, info, evt, **kwargs):
        nonlocal call_count
        call_count += 1
        old_value = info
        new_value = node.value
        print(f"  Change #{call_count}: {old_value} -> {new_value}")

    node = bag.get_node("value")
    node.subscribe("counter", on_change)

    print("Making changes while subscribed:")
    bag.set_item("value", 1)
    bag.set_item("value", 2)

    print("\nUnsubscribing...")
    node.unsubscribe("counter")

    print("\nMaking changes after unsubscribe:")
    bag.set_item("value", 3)
    bag.set_item("value", 4)

    print(f"\nTotal callbacks received: {call_count} (expected: 2)")


def demo():
    """Run all demos."""
    demo_basic_subscription()
    demo_nested_subscription()
    demo_computed_values()
    demo_unsubscribe()


if __name__ == "__main__":
    demo()
