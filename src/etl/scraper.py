import re
import csv
import asyncio
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup


def get_default_frequency(line_number: str, line_name: str) -> float:
    num_str = str(line_number).lstrip("0")
    try:
        num = int(num_str) if num_str else 0
    except ValueError:
        num = 0

    name_upper = line_name.upper()

    if any(k in name_upper for k in ["NOCTURNA", "NOCTURNO", "711", "970", "971", "972", "974", "975"]):
        return 0.5

    if any(k in name_upper for k in ["TEIDE", "PORTILLO", "MASCA", "TENO", "CHAMORGA", "AFUR", "ALMACIGA"]):
        return 0.75

    if num in [14, 15, 100, 102, 103, 110, 111, 910, 934]:
        return 5.0

    if num in [10, 20, 30, 40, 101, 104, 105, 106, 108, 112, 120, 122, 232, 233, 343, 363, 416, 467, 473]:
        return 3.0

    if 900 <= num <= 999:
        return 3.0

    if 200 <= num <= 299:
        return 2.5

    if 300 <= num <= 399:
        return 2.0

    if 400 <= num <= 499:
        return 2.0

    if 600 <= num <= 699:
        return 2.0

    return 1.5


def parse_schedule_html(html_content: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html_content, "html.parser")

    stops = []
    stop_elements = soup.find_all(class_=re.compile(r'parada|stop|estacion', re.IGNORECASE))
    for el in stop_elements:
        text = el.get_text(strip=True)
        if text and len(text) > 3 and text not in stops:
            stops.append(text)

    departure_times = []
    time_matches = re.findall(r'\b([01]?\d|2[0-3]):[0-5]\d\b', html_content)
    if time_matches:
        departure_times = sorted(list(set(time_matches)))

    daily_departures = len(departure_times)
    frequency = max(0.5, round(daily_departures / 16.0, 2)) if daily_departures > 0 else None

    return {
        "scraped_stops": stops,
        "daily_departures": daily_departures,
        "frequency": frequency
    }


async def fetch_line_data(client: httpx.AsyncClient, line_number: str, line_name: str, line_url: str) -> Dict[str, Any]:
    result = {
        "line_number": line_number,
        "line_name": line_name,
        "line_url": line_url,
        "frequency": get_default_frequency(line_number, line_name),
        "source": "heuristic"
    }

    if not line_url or not line_url.startswith("http"):
        return result

    try:
        response = await client.get(line_url, timeout=5.0, follow_redirects=True)
        if response.status_code == 200:
            parsed = parse_schedule_html(response.text)
            if parsed.get("frequency"):
                result["frequency"] = parsed["frequency"]
                result["source"] = "scraped"
            if parsed.get("scraped_stops"):
                result["scraped_stops"] = parsed["scraped_stops"]
    except Exception:
        pass

    return result


async def scrape_all_lines(csv_path: str, max_concurrency: int = 5) -> Dict[str, Dict[str, Any]]:
    lines_to_fetch = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lines_to_fetch.append((
                row.get("linea_numero", "").strip().zfill(3),
                row.get("linea_nombre", "").strip(),
                row.get("linea_url", "").strip()
            ))

    semaphore = asyncio.Semaphore(max_concurrency)
    results = {}

    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0 (compatible; TenerifeTransitGraph/1.0)"}) as client:
        async def sem_fetch(num: str, name: str, url: str):
            async with semaphore:
                data = await fetch_line_data(client, num, name, url)
                results[num] = data

        tasks = [sem_fetch(num, name, url) for num, name, url in lines_to_fetch]
        await asyncio.gather(*tasks)

    return results
