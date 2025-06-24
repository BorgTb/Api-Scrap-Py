import asyncio
from sii_scraper import scrap_sii

if __name__ == "__main__":
    data = asyncio.run(scrap_sii("8659993-7", "emasy993", "4", "2025"))
    print(data)
