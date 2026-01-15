# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for retry_policy functionality in BagResolver."""

import asyncio

import pytest

from genro_bag.resolver import RETRY_POLICIES, BagResolver


class FailingResolver(BagResolver):
    """Resolver that fails N times before succeeding."""

    class_args = ["fail_count", "result"]
    class_kwargs = {"cache_time": 0, "read_only": True, "retry_policy": None}

    def init(self):
        self._attempts = 0

    def load(self):
        self._attempts += 1
        if self._attempts <= self._kw["fail_count"]:
            raise ConnectionError(f"Attempt {self._attempts} failed")
        return self._kw["result"]


class AsyncFailingResolver(BagResolver):
    """Async resolver that fails N times before succeeding."""

    class_args = ["fail_count", "result"]
    class_kwargs = {"cache_time": 0, "read_only": True, "retry_policy": None}

    def init(self):
        self._attempts = 0

    async def async_load(self):
        self._attempts += 1
        if self._attempts <= self._kw["fail_count"]:
            raise ConnectionError(f"Attempt {self._attempts} failed")
        return self._kw["result"]


class TestRetryPoliciesDict:
    """Test RETRY_POLICIES predefined configurations."""

    def test_network_policy_exists(self):
        """Network policy is defined."""
        assert "network" in RETRY_POLICIES
        policy = RETRY_POLICIES["network"]
        assert policy["max_attempts"] == 3
        assert policy["delay"] == 1.0
        assert policy["backoff"] == 2.0
        assert policy["jitter"] is True
        assert ConnectionError in policy["on"]

    def test_aggressive_policy_exists(self):
        """Aggressive policy is defined."""
        assert "aggressive" in RETRY_POLICIES
        policy = RETRY_POLICIES["aggressive"]
        assert policy["max_attempts"] == 5

    def test_gentle_policy_exists(self):
        """Gentle policy is defined."""
        assert "gentle" in RETRY_POLICIES
        policy = RETRY_POLICIES["gentle"]
        assert policy["max_attempts"] == 2
        assert policy["jitter"] is False


class TestRetryPolicySync:
    """Test retry_policy with sync resolvers."""

    def test_no_retry_policy_no_retry(self):
        """Without retry_policy, failures are not retried."""
        resolver = FailingResolver(1, "success")
        with pytest.raises(ConnectionError):
            resolver()
        assert resolver._attempts == 1

    def test_retry_policy_string_network(self):
        """retry_policy='network' uses predefined policy."""
        resolver = FailingResolver(2, "success", retry_policy="network")
        result = resolver()
        assert result == "success"
        assert resolver._attempts == 3  # 2 failures + 1 success

    def test_retry_policy_custom_dict(self):
        """retry_policy as dict for custom configuration."""
        policy = {
            "max_attempts": 4,
            "delay": 0.01,
            "backoff": 1.0,
            "jitter": False,
            "on": (ConnectionError,),
        }
        resolver = FailingResolver(3, "success", retry_policy=policy)
        result = resolver()
        assert result == "success"
        assert resolver._attempts == 4

    def test_retry_exhausted_raises(self):
        """When all retries exhausted, raises last error."""
        policy = {
            "max_attempts": 2,
            "delay": 0.01,
            "backoff": 1.0,
            "jitter": False,
            "on": (ConnectionError,),
        }
        resolver = FailingResolver(5, "success", retry_policy=policy)
        with pytest.raises(ConnectionError) as exc_info:
            resolver()
        assert "Attempt 2 failed" in str(exc_info.value)
        assert resolver._attempts == 2

    def test_retry_only_on_specified_exceptions(self):
        """Retry only happens for exceptions in 'on' tuple."""

        class WrongErrorResolver(BagResolver):
            class_kwargs = {"cache_time": 0, "read_only": True, "retry_policy": None}

            def init(self):
                self._attempts = 0

            def load(self):
                self._attempts += 1
                raise ValueError("Wrong error type")

        policy = {
            "max_attempts": 3,
            "delay": 0.01,
            "on": (ConnectionError,),  # ValueError not included
        }
        resolver = WrongErrorResolver(retry_policy=policy)
        with pytest.raises(ValueError):
            resolver()
        assert resolver._attempts == 1  # No retry for ValueError


class TestRetryPolicyAsync:
    """Test retry_policy with async resolvers."""

    @pytest.mark.asyncio
    async def test_async_no_retry_policy(self):
        """Async resolver without retry_policy fails immediately."""
        resolver = AsyncFailingResolver(1, "success")
        with pytest.raises(ConnectionError):
            await resolver()
        assert resolver._attempts == 1

    @pytest.mark.asyncio
    async def test_async_retry_policy_network(self):
        """Async resolver with retry_policy='network' retries."""
        resolver = AsyncFailingResolver(2, "success", retry_policy="network")
        result = await resolver()
        assert result == "success"
        assert resolver._attempts == 3

    @pytest.mark.asyncio
    async def test_async_retry_policy_custom(self):
        """Async resolver with custom retry_policy."""
        policy = {
            "max_attempts": 3,
            "delay": 0.01,
            "backoff": 1.0,
            "jitter": False,
            "on": (ConnectionError,),
        }
        resolver = AsyncFailingResolver(2, "success", retry_policy=policy)
        result = await resolver()
        assert result == "success"
        assert resolver._attempts == 3

    @pytest.mark.asyncio
    async def test_async_retry_exhausted(self):
        """Async resolver exhausts retries and raises."""
        policy = {
            "max_attempts": 2,
            "delay": 0.01,
            "on": (ConnectionError,),
        }
        resolver = AsyncFailingResolver(5, "success", retry_policy=policy)
        with pytest.raises(ConnectionError):
            await resolver()
        assert resolver._attempts == 2


class TestRetryPolicyInheritance:
    """Test retry_policy with resolver inheritance."""

    def test_subclass_default_retry_policy(self):
        """Subclass can set default retry_policy in class_kwargs."""

        class NetworkResolver(BagResolver):
            class_kwargs = {
                "cache_time": 0,
                "read_only": True,
                "retry_policy": "network",
            }

            def init(self):
                self._attempts = 0

            def load(self):
                self._attempts += 1
                if self._attempts <= 2:
                    raise ConnectionError("Network error")
                return "success"

        resolver = NetworkResolver()
        result = resolver()
        assert result == "success"
        assert resolver._attempts == 3

    def test_instance_override_class_default(self):
        """Instance can override class default retry_policy."""

        class NetworkResolver(BagResolver):
            class_kwargs = {
                "cache_time": 0,
                "read_only": True,
                "retry_policy": "network",
            }

            def init(self):
                self._attempts = 0

            def load(self):
                self._attempts += 1
                if self._attempts <= 2:
                    raise ConnectionError("Network error")
                return "success"

        # Instance disables retry
        resolver = NetworkResolver(retry_policy=None)
        with pytest.raises(ConnectionError):
            resolver()
        assert resolver._attempts == 1


class TestRetryPolicyUnknownString:
    """Test behavior with unknown policy string."""

    def test_unknown_policy_string_no_retry(self):
        """Unknown policy string results in no retry (returns None)."""
        resolver = FailingResolver(1, "success", retry_policy="unknown_policy")
        # Should behave as if no retry policy (None returned by _get_retry_policy)
        with pytest.raises(ConnectionError):
            resolver()
        assert resolver._attempts == 1
