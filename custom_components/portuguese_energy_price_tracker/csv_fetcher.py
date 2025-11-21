"""CSV Data Fetcher for Energy Price Tracker.

This module fetches Portuguese energy price data from Tiago Felícia's repository.

Data Source Credits:
    The data is maintained by Tiago Felícia at:
    https://github.com/tiagofelicia/tiagofelicia.github.io

    Special thanks to Tiago Felícia for collecting and maintaining accurate
    hourly energy price data for multiple Portuguese providers and making it
    freely available to the community.
"""
from __future__ import annotations

import asyncio
import csv
import logging
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

import aiohttp
from homeassistant.util import dt as dt_util
from homeassistant.util.file import write_utf8_file

_LOGGER = logging.getLogger(__name__)

# Data source: Tiago Felícia's Portuguese Energy Price Data
# Repository: https://github.com/tiagofelicia/tiagofelicia.github.io
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/tiagofelicia/tiagofelicia.github.io"
GITHUB_API_BASE = "https://api.github.com/repos/tiagofelicia/tiagofelicia.github.io"
CSV_FILE_PATH = "data/precos-horarios.csv"

# Cache settings
CACHE_DURATION = timedelta(hours=1)

# Tariff mapping from CSV to config
TARIFF_MAPPING = {
    "Simples": "SIMPLE",
    "Bi-horário - Ciclo Diário": "BIHORARIO_DIARIO",
    "Bi-horário - Ciclo Semanal": "BIHORARIO_SEMANAL",
    "Tri-horário - Ciclo Diário": "TRIHORARIO_DIARIO",
    "Tri-horário - Ciclo Semanal": "TRIHORARIO_SEMANAL",
    "Tri-horário > 20.7 kVA - Ciclo Diário": "TRIHORARIO_DIARIO_HV",
    "Tri-horário > 20.7 kVA - Ciclo Semanal": "TRIHORARIO_SEMANAL_HV",
}

# Reverse mapping
TARIFF_MAPPING_REVERSE = {v: k for k, v in TARIFF_MAPPING.items()}


class CSVDataCache:
    """Cache for CSV data."""

    def __init__(self):
        """Initialize cache."""
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_times: dict[str, datetime] = {}

    def get(self, date_key: str, bypass_cache: bool = False) -> dict[str, Any] | None:
        """Get cached data for a date."""
        if bypass_cache:
            return None

        if date_key not in self._cache:
            return None

        cache_time = self._cache_times.get(date_key)
        if cache_time and datetime.now() - cache_time < CACHE_DURATION:
            _LOGGER.debug(f"Using cached data for {date_key}")
            return self._cache[date_key]

        # Cache expired
        del self._cache[date_key]
        del self._cache_times[date_key]
        return None

    def set(self, date_key: str, data: dict[str, Any]):
        """Cache data for a date."""
        self._cache[date_key] = data
        self._cache_times[date_key] = datetime.now()
        _LOGGER.debug(f"Cached data for {date_key}")


class CSVDataFetcher:
    """Fetcher for CSV data from GitHub."""

    def __init__(self, session: aiohttp.ClientSession, data_dir: Path):
        """Initialize fetcher."""
        self.session = session
        self.data_dir = data_dir
        self.cache = CSVDataCache()

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_current_csv(self, bypass_cache: bool = False, max_retries: int = 3) -> str:
        """Fetch the current CSV file from GitHub main branch with retry logic."""
        url = f"{GITHUB_RAW_BASE}/main/{CSV_FILE_PATH}"

        for attempt in range(max_retries):
            try:
                _LOGGER.debug(f"Fetching current CSV from: {url} (attempt {attempt + 1}/{max_retries})")

                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 404:
                        raise Exception(f"CSV file not found (HTTP 404)")

                    if response.status != 200:
                        raise Exception(f"Failed to fetch CSV: HTTP {response.status}")

                    content = await response.text()
                    _LOGGER.info(f"Successfully fetched current CSV ({len(content)} bytes)")
                    return content

            except asyncio.TimeoutError:
                if attempt == max_retries - 1:
                    raise Exception("Timeout fetching CSV from GitHub after all retries")

                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                _LOGGER.warning(f"Timeout on attempt {attempt + 1}, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

            except Exception as err:
                if attempt == max_retries - 1:
                    raise Exception(f"Error fetching CSV after all retries: {err}")

                wait_time = 2 ** attempt
                _LOGGER.warning(f"Error on attempt {attempt + 1}: {err}, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

    async def fetch_historical_csv(self, target_date: datetime) -> str:
        """Fetch historical CSV from GitHub commit history for a specific date."""
        date_str = target_date.strftime("%Y-%m-%d")

        _LOGGER.info(f"Fetching historical CSV for date: {date_str}")

        # Search for commit on or after the target date
        url = f"{GITHUB_API_BASE}/commits"
        params = {
            "path": CSV_FILE_PATH,
            "since": target_date.isoformat(),
            "per_page": 1,
        }

        try:
            # Get the commit SHA for the date
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch commit history: HTTP {response.status}")

                commits = await response.json()
                if not commits:
                    raise Exception(f"No commits found for {date_str}")

                commit_sha = commits[0]["sha"]
                _LOGGER.debug(f"Found commit for {date_str}: {commit_sha}")

            # Fetch the file content at that commit
            file_url = f"{GITHUB_RAW_BASE}/{commit_sha}/{CSV_FILE_PATH}"
            async with self.session.get(file_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch historical CSV: HTTP {response.status}")

                content = await response.text()
                _LOGGER.info(f"Successfully fetched historical CSV for {date_str} ({len(content)} bytes)")
                return content

        except asyncio.TimeoutError:
            raise Exception("Timeout fetching historical CSV from GitHub")
        except Exception as err:
            raise Exception(f"Error fetching historical CSV: {err}")

    async def save_to_local(self, date: datetime, content: str):
        """Save CSV content to local file."""
        date_str = date.strftime("%Y-%m-%d")
        file_path = self.data_dir / f"prices_{date_str}.csv"

        await write_utf8_file(str(file_path), content)
        _LOGGER.debug(f"Saved CSV to local file: {file_path}")

    async def load_from_local(self, date: datetime) -> str | None:
        """Load CSV content from local file."""
        date_str = date.strftime("%Y-%m-%d")
        file_path = self.data_dir / f"prices_{date_str}.csv"

        if not file_path.exists():
            return None

        def _read_file():
            return file_path.read_text(encoding="utf-8")

        content = await asyncio.to_thread(_read_file)

        # Remove BOM if present (in case cached files have it)
        if content.startswith('\ufeff'):
            content = content[1:]

        _LOGGER.debug(f"Loaded CSV from local file: {file_path}")
        return content

    def parse_csv(self, content: str, provider: str, tariff: str, vat_rate: int) -> list[dict]:
        """Parse CSV content and filter for provider/tariff."""
        # Convert tariff code to CSV format
        tariff_csv = TARIFF_MAPPING_REVERSE.get(tariff, tariff)

        _LOGGER.debug(f"Parsing CSV for provider={provider}, tariff={tariff_csv}, VAT={vat_rate}%")

        # Remove BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]

        reader = csv.DictReader(StringIO(content))
        prices = []
        skipped_invalid = 0
        skipped_nan = 0

        for row in reader:
            # Filter by provider and tariff
            if row.get("tarifario") != provider or row.get("opcao") != tariff_csv:
                continue

            try:
                # Parse date and interval
                date_str = row["dia"]  # Format: 18/11/2025
                interval_str = row["intervalo"]  # Format: [00:00-00:15[

                # Parse date (DD/MM/YYYY format)
                day, month, year = date_str.split("/")

                # Parse interval start time using regex
                import re
                match = re.search(r'\[(\d{2}):(\d{2})-', interval_str)
                if not match:
                    skipped_invalid += 1
                    continue

                hour = int(match.group(1))
                minute = int(match.group(2))

                # Create datetime with timezone (Europe/Lisbon)
                dt = dt_util.as_local(datetime(
                    int(year), int(month), int(day),
                    hour, minute, 0
                ))

                # Parse prices from CSV columns
                # col = final price without VAT (omie + tar + provider_cost + fixed_cost)
                # omie = market price
                # tar = regulated tariff cost
                col_price = row.get("col", "").strip()
                omie_price = row.get("omie", "").strip()
                tar_price = row.get("tar", "").strip()

                # Check for NaN or empty values
                if not col_price or not omie_price or not tar_price:
                    skipped_nan += 1
                    continue

                try:
                    col_float = float(col_price)
                    omie_float = float(omie_price)
                    tar_float = float(tar_price)
                except (ValueError, TypeError):
                    skipped_nan += 1
                    continue

                # Use col as the base price (already includes everything)
                price_no_vat = col_float

                # Calculate price with VAT
                price_with_vat = price_no_vat * (1 + vat_rate / 100)

                prices.append({
                    "datetime": dt.isoformat(),
                    "interval": interval_str,
                    "price": round(price_no_vat, 5),
                    "price_w_vat": round(price_with_vat, 5),
                    "market_price": round(omie_float, 5),
                    "tar_cost": round(tar_float, 5),
                })

            except (ValueError, KeyError) as err:
                _LOGGER.warning(f"Error parsing CSV row: {err}, row={row}")
                skipped_invalid += 1
                continue

        if skipped_nan > 0:
            _LOGGER.info(f"Skipped {skipped_nan} rows with NaN/empty values")
        if skipped_invalid > 0:
            _LOGGER.warning(f"Skipped {skipped_invalid} rows with invalid data")

        _LOGGER.info(f"Parsed {len(prices)} price entries for {provider} - {tariff_csv}")
        return prices


    async def get_prices(
        self,
        provider: str,
        tariff: str,
        vat_rate: int,
        target_date: datetime | None = None,
        bypass_cache: bool = False,
    ) -> list[dict]:
        """
        Get prices for provider/tariff, optionally for a specific date.

        The GitHub CSV always contains 2 days:
        - Today: Complete data (96 intervals)
        - Tomorrow: Incomplete data (only intervals published so far)

        Caching strategy:
        - Today's data: Cache to disk when complete (96 data points)
        - Tomorrow's data: Keep in memory cache only, don't persist
        - Past dates: Fetch from Git history only when explicitly requested

        Args:
            provider: Provider name
            tariff: Tariff code (e.g., BIHORARIO_SEMANAL)
            vat_rate: VAT percentage (e.g., 23)
            target_date: Date to fetch data for (defaults to today)
            bypass_cache: Force fetch from GitHub, ignore cache

        Returns:
            List of price dictionaries with datetime, interval, price, price_w_vat
        """
        if target_date is None:
            target_date = datetime.now()

        date_key = target_date.strftime("%Y-%m-%d")
        is_today = target_date.date() == datetime.now().date()
        is_tomorrow = target_date.date() == (datetime.now() + timedelta(days=1)).date()
        is_past = target_date.date() < datetime.now().date()

        # Check memory cache first (unless bypassing)
        cached_data = self.cache.get(date_key, bypass_cache=bypass_cache)
        if cached_data:
            prices = cached_data.get(f"{provider}_{tariff}")
            if prices is not None:
                _LOGGER.debug(f"Using cached data for {date_key} ({len(prices)} entries)")
                return prices

        csv_content = None

        # For past dates, always fetch from Git history (unless we have a complete local cache)
        if is_past:
            if not bypass_cache:
                csv_content = await self.load_from_local(target_date)

            if csv_content is None:
                _LOGGER.info(f"Fetching historical data for {date_key} from Git history")
                csv_content = await self.fetch_historical_csv(target_date)
                # Save past dates to local cache
                await self.save_to_local(target_date, csv_content)

        # For today/tomorrow, always fetch from current CSV (contains both days)
        else:
            # Try loading today from local file first (if it's complete)
            if is_today and not bypass_cache:
                csv_content = await self.load_from_local(target_date)
                if csv_content:
                    # Check if cached data is complete (96 data points expected)
                    temp_prices_all = self.parse_csv(csv_content, provider, tariff, vat_rate)

                    # Filter to only today's date (CSV may contain multiple days)
                    temp_prices = []
                    for p in temp_prices_all:
                        dt_obj = datetime.fromisoformat(p["datetime"])
                        if dt_obj.date() == target_date.date():
                            temp_prices.append(p)

                    if len(temp_prices) >= 96:
                        _LOGGER.debug(f"Using complete cached data for today ({len(temp_prices)} entries)")
                        prices = temp_prices
                        # Cache in memory too
                        if date_key not in self.cache._cache:
                            self.cache._cache[date_key] = {}
                        self.cache._cache[date_key][f"{provider}_{tariff}"] = prices
                        self.cache._cache_times[date_key] = datetime.now()
                        return prices
                    else:
                        _LOGGER.debug(f"Cached today data incomplete ({len(temp_prices)} entries), fetching fresh")

            # Fetch current CSV (has both today and tomorrow)
            _LOGGER.info(f"Fetching current CSV for {date_key}")
            csv_content = await self.fetch_current_csv(bypass_cache=bypass_cache)

        # Parse CSV for the requested date
        all_prices = self.parse_csv(csv_content, provider, tariff, vat_rate)

        # Filter prices to only include the requested date
        prices = []
        for p in all_prices:
            dt_obj = datetime.fromisoformat(p["datetime"])
            if dt_obj.date() == target_date.date():
                prices.append(p)

        _LOGGER.info(f"Parsed {len(prices)} price entries for {date_key}")

        # Smart disk persistence: only save if new data has more points than existing cache
        # This ensures we don't overwrite complete data with incomplete data
        should_save = False

        if is_past:
            # Past dates are already saved above
            pass
        elif is_today or is_tomorrow:
            # Check if we should save this data
            existing_file = await self.load_from_local(target_date)
            if existing_file:
                # Parse existing to count data points
                existing_prices = self.parse_csv(existing_file, provider, tariff, vat_rate)
                existing_for_date = [p for p in existing_prices if datetime.fromisoformat(p["datetime"]).date() == target_date.date()]

                if len(prices) > len(existing_for_date):
                    _LOGGER.debug(
                        f"New data has more points ({len(prices)}) than existing ({len(existing_for_date)}), "
                        f"saving to disk"
                    )
                    should_save = True
                else:
                    _LOGGER.debug(
                        f"Existing data already has {len(existing_for_date)} points, "
                        f"not overwriting with {len(prices)} points"
                    )
            else:
                # No existing file, save new data
                _LOGGER.debug(f"No existing cache, saving {len(prices)} entries to disk")
                should_save = True

            if should_save:
                await self.save_to_local(target_date, csv_content)

        # Cache the result in memory
        if date_key not in self.cache._cache:
            self.cache._cache[date_key] = {}
        self.cache._cache[date_key][f"{provider}_{tariff}"] = prices
        self.cache._cache_times[date_key] = datetime.now()

        return prices
