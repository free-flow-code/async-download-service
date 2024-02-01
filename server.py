import os
from aiohttp import web
import aiofiles
import asyncio
import argparse
import logging

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Microservice for downloading files.'
    )
    parser.add_argument(
        '-l', '--logging',
        help='If True, turns on logging. Default is True.',
        action='store_true'
    )
    parser.add_argument(
        '-d', '--delay',
        help='Response delay time. In seconds. Default 0.',
        type=int,
        default=0
    )
    parser.add_argument(
        '-p', '--path',
        help='Path to the directory with photos.',
        type=str,
        default='test_photos'
    )
    return parser.parse_args()


async def create_archive(source_directory, time_delay):
    command = ['zip', '-r', '-', '.']
    zip_process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        cwd=f'{source_directory}'
    )
    read_kilobytes = 500
    bytes_per_kb = 1024
    archive = b''

    try:
        while not zip_process.stdout.at_eof():
            chunk = await zip_process.stdout.read(n=read_kilobytes * bytes_per_kb)
            archive += chunk
            logger.debug(f"Sending archive chunk ...")
            await asyncio.sleep(time_delay)
    except asyncio.CancelledError:
        logger.debug(f"\nDownload was interrupted")
        raise
    finally:
        if zip_process.returncode is None:
            zip_process.kill()
            await zip_process.communicate()

    return archive


async def check_dir_exist(archive_hash):
    dirs = next(os.walk('test_photos'))[1]
    if archive_hash in dirs:
        return True
    raise web.HTTPNotFound()


async def archive(request):
    archive_hash = request.match_info.get('archive_hash')
    if not archive_hash:
        raise web.HTTPNotFound(text='No archive hash')

    photos_directory = request.app['path']
    source_directory = f'{photos_directory}/{archive_hash}/'
    output_zip_file = 'archive.zip'

    response = web.StreamResponse()
    response.enable_chunked_encoding()
    response.headers['Content-Type'] = 'text/html'
    response.headers['Transfer-Encoding'] = 'chunked'
    response.headers['Content-Disposition'] = f'attachment; filename="{output_zip_file}"'
    await response.prepare(request)

    try:
        if await check_dir_exist(archive_hash):
            zip_archive = await create_archive(source_directory, request.app['delay'])
            await response.write(zip_archive)

            return response

    except web.HTTPNotFound:
        return web.HTTPNotFound(text='Архив не существует или был удален', content_type='text/html')


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


def main():
    args = parse_arguments()

    app = web.Application()
    app['delay'] = args.delay
    app['path'] = args.path

    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    if args.logging:
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    web.run_app(app)


if __name__ == '__main__':
    main()
