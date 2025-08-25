import os
import logging
import datetime as dt
from io import StringIO
from abc import ABC, abstractmethod
import pandas as pd
import boto3
from botocore.exceptions import ClientError
from fixed_income.data.handler import DatasetHandler, AWSDatasetHandler


class Dataset(ABC):
    """Abstract base class for all datasets."""
    def __init__(self, handler: DatasetHandler):
        self.handler = handler
        self.type = ""
        self.url = ""

    @abstractmethod
    def fetch_data(self, *args, **kwargs):
        pass


class USTreasuryDailyYieldsDataset(Dataset):
    """Concrete implementation of Dataset for U.S. Treasury Daily Yields."""
    def __init__(self, handler: DatasetHandler, date = "{}".format(dt.datetime.now().year)):
        self.handler = handler
        self.date = date
        self.from_url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{}/all?type=daily_treasury_yield_curve&field_tdr_date_value={}&page&_format=csv".format(self.date, self.date)
        self.type = "USTreasuryDailyYields"
        self.url = ""

    def fetch_data(self):
        df = pd.read_csv(self.from_url)