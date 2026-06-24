"""Maker base interface. Every alpha strategy subclasses Strategy.

A strategy maps prices -> target position in [-1, 1] per bar.
It knows NOTHING about Sharpe, drawdown, or the Checker.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd


class Strategy(ABC):
    name: str = "base"

    @abstractmethod
    def signal(self, prices: pd.DataFrame) -> pd.Series:
        """Return a position series indexed like `prices`, values in [-1, 1]."""
        raise NotImplementedError
