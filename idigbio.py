import logging
from typing import Tuple

import aiohttp


COUNT = 5
MEDIA_URL = "https://search.idigbio.org/v2/search/media?rq=%7B{query},%22hasImage%22:true%7D&fields=%5B%22accessuri%22%5D&sort=uuid&limit={count}&offset={offset}"

logger = logging.getLogger("fossil-id")

QUERIES = {}
with open("data/queries.txt", "rt") as f:
    for raw_row in f.readlines():
        row = raw_row.strip().split("\t")
        if row:
            if row[1] in ["order", "family", "genus", "scientificname"]:
                QUERIES[row[0]] = f"%22{row[1]}%22:%22{row[0]}%22"
            elif row[1] == "":
                QUERIES[
                    row[0]
                ] = f"%22data%22:%7B%22type%22:%22fulltext%22,%22value%22:%22{row[0]}%22%7D"
            else:
                QUERIES[row[0]] = row[1]


async def get_urls(
    session: aiohttp.ClientSession,
    item: str,
    index: int,
    count: int = COUNT,
) -> Tuple[int, Tuple[str, ...]]:
    """Return URLS of images of the specimen to download.

    This method uses iDigBio's API to fetch image urls. It will
    try up to 2 times to successfully retrieve URLS.

    `index` is the offset of the last observation that was downloaded.
    This function will try to return `images_to_download` number of
    images. The new offset is returned as the first element of the tuple.
    """
    urls = []
    query = (
        QUERIES[item]
        if item in QUERIES
        else f"%22data%22:%7B%22type%22:%22fulltext%22,%22value%22:%22{item}%22%7D"
    )
    async with session.get(
        MEDIA_URL.format(query=query, count=count, offset=index)
    ) as resp:
        data = await resp.json()
        records = data["items"]

    if not records:
        index = 0
        async with session.get(
            MEDIA_URL.format(query=query, count=count, offset=0)
        ) as resp:
            data = await resp.json()
            records = data["items"]

    if not records:
        return (0, tuple())

    logger.info(f"item ids: {','.join([str(r['uuid']) for r in records])}")
    for record in records:
        if "indexTerms" in record and "accessuri" in record["indexTerms"]:
            urls.append(record["indexTerms"]["accessuri"])
    return ((index + count) % data["itemCount"], tuple(urls))
