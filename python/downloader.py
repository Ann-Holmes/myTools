import requests
import logging
import hashlib
from typing import List
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class Downloader:
    """Download files from a list of URLs to a directory.

    This class downloads files from a list of URLs to a directory. It supports resuming downloads
    and retrying failed downloads. The number of workers to download files concurrently can be
    specified.
    If the download fails, the failed URLs are stored in the `failed` attribute.
    If `continue_on_error` is True, the downloader will continue downloading the failed files one
    more time. You can set `continue_on_error` to an integer to continue downloading the failed
    files until the number of retries reaches the value.

    Args:
        urls: List of URLs to download.
        outdir: Output directory to save downloaded files.
        names: List of names to save the downloaded files. If None, the last part of the URL is
            used as the name.
        continue_on_error: If True, continue downloading the failed files. If int, continue
            downloading the failed files until the number of retries reaches the value. Default is
            False.
        resume: If True, resume downloading if the file already exists.
        max_retries: Maximum number of retries when downloading a file fails. Default is 3.
        max_workers: Maximum number of workers to download files concurrently. Default is 4.
        chunk_size: Chunk size to download files. Default is 64KB.
        timeout: Timeout for downloading single file. Default is None.

    Example:
        >>> urls = ['https://example.com/file1.zip', 'https://example.com/file2.zip']
        >>> outdir = Path('downloads')
        >>> names = ['file1.zip', 'file2.zip']
        >>> downloader = Downloader(urls, outdir, names)
        >>> downloader.download()
    """

    def __init__(
            self,
            urls: List[str],
            outdir: Path,
            names: List[str] = None,
            continue_on_error: bool | int = False,
            resume: bool = False,
            max_retries: int = 3,
            max_workers: int = 4,
            chunk_size: int = 64 * 1024,
            timeout: int = None
    ) -> None:
        self.urls = urls
        self.outdir = Path(outdir)
        self.names = self._get_names(names)
        self.continue_on_error = continue_on_error
        self.resume = resume
        self.max_retries = max_retries
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.failed = []

        self.outdir.mkdir(parents=True, exist_ok=True)

    def _get_names(self, names: List[str]) -> List[str]:
        if names is None:
            names = [url.split('/')[-1] for url in self.urls]
        return names

    def _download_single_url(self, url: str, name: str) -> None:
        outpath = self.outdir / name
        for i in range(self.max_retries):
            if self.resume and outpath.exists():
                range_header = {'Range': f'bytes={outpath.stat().st_size}-'}
            else:
                range_header = None

            try:
                with requests.get(url, headers=range_header,
                                  stream=True, timeout=self.timeout) as r:
                    if r.status_code == 416:
                        break
                    r.raise_for_status()
                    with open(outpath, 'ab') as f:
                        for chunk in r.iter_content(self.chunk_size):
                            f.write(chunk)
                break
            except Exception as e:
                logging.info(
                    f'{i+1:3d}/{self.max_retries} | Failed to download {name}. Retrying...'
                )
                logging.error(e)
                if i == self.max_retries - 1:
                    return url, name, False

        return url, name, True

    def download(self) -> None:
        logging.info(f'Start downloading {len(self.urls)} files...')
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for i, res in enumerate(executor.map(self._download_single_url, self.urls, self.names)):
                url, name, status = res
                if status:
                    logging.info(f"{i+1:6d}/{len(self.urls)} | Success: {name}")
                else:
                    self.failed.append((url, name))
                    logging.info(f"{i+1:6d}/{len(self.urls)} | Failed: {name}")

        if self.failed and self.continue_on_error:
            logging.warn(f"{len(self.failed)} downloads failed because of max retries reached.")
            logging.warn(
                f'{self.continue_on_error} continue_on_error left. Start failed downloads...'
            )
            self.continue_on_error -= 1
            urls, names = zip(*self.failed)
            self.urls = list(urls)
            self.names = list(names)
            self.failed = []
            self.download()

    def md5check(self, md5sums: List[str], chunksize: int = 1024**3 * 4) -> None:
        """Check the MD5 checksum of the downloaded files.

        Args:
            md5sums: List of MD5 checksums of the downloaded files, in the same order as the
                downloaded urls.
            chunksize: Chunk size to read files. Default is 4GB.

        Example:
            >>> md5sums = ['md5sum1', 'md5sum2']
            >>> downloader.md5check(md5sums)
        """
        if len(md5sums) != len(self.urls):
            raise ValueError('The number of MD5 checksums does not match the number of URLs.')

        logging.info('Start checking MD5 checksums...')
        md5checks = []
        for i, (md5sum, name) in enumerate(zip(md5sums, self.names)):
            outpath = self.outdir / name
            if outpath.exists():
                with open(outpath, 'rb') as f:
                    md5 = hashlib.md5()
                    for chunk in iter(lambda: f.read(chunksize), b''):
                        md5.update(chunk)
                    md5 = md5.hexdigest().lower()
                    md5checks.append(md5 == md5sum.lower())

                if md5 == md5sum.lower():
                    logging.info(f"{i+1:6d}/{len(self.urls)} | MD5 checksum matched: {name}")
                else:
                    logging.error(f"{i+1:6d}/{len(self.urls)} | MD5 checksum mismatch: {name}")
            else:
                logging.error(f"{i+1:6d}/{len(self.urls)} | File not found: {name}")

        return md5checks
