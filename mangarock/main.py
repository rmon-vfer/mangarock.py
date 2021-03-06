import argparse
import json
import os.path
import requests
from mri_to_webp import parse_mri_data_to_webp_buffer
from random import choice
from slugify import slugify
from time import sleep
from werkzeug.utils import secure_filename
from PIL import Image

query_version = 401


def make_series_info_uri(series_oid):
    # series_oid - mrs-serie-{series_num}
    return f"https://api.mangarockhd.com/query/web{query_version}/info?oid={series_oid}&last=0"


def make_chapter_data_uri(chapter_oid):
    return f"https://api.mangarockhd.com/query/web{query_version}/pages?oid={chapter_oid}"


def get_chapters(args, series_info):
    chapters = series_info['chapters']

    if args.chapters:
        of_interest = set(args.chapters.split(','))
        chapters = filter(lambda c: c['oid'] in of_interest, chapters)
        chapters = tuple(chapters)

    return chapters


def main():
    argparser = create_argparser()
    args = argparser.parse_args()
    series_info_url = make_series_info_uri(args.series)

    series_info_json: dict = requests.get(series_info_url).json()
    series_info: dict = series_info_json['data']
    series_name = series_info['name']
    series_name_secure = secure_filename(series_name)
    series_dirpath = slugify(series_name_secure)
    series_info_filepath = os.path.join(series_dirpath, "info.json")

    if not os.path.exists(series_dirpath):
        os.mkdir(series_dirpath)

    if not os.path.exists(series_info_filepath):
        with open(series_info_filepath, "w") as fs:
            json.dump(series_info, fs)

    for chapter in get_chapters(args, series_info):
        chapter_name = chapter['name']
        chapter_name_secure = secure_filename(chapter_name)
        chapter_dirpath = os.path.join(series_dirpath, slugify(chapter_name_secure))

        if not os.path.exists(chapter_dirpath):
            os.mkdir(chapter_dirpath)

        chapter_data_url = make_chapter_data_uri(chapter['oid'])
        chapter_data = requests.get(chapter_data_url).json()

        has_failed_download = False

        for index, mri_url in enumerate(chapter_data['data']):
            filename = f"{index:03}.webp"
            filepath = os.path.join(chapter_dirpath, filename)

            if os.path.exists(filepath) and (os.path.getsize(filepath) > 0):
                print(f"skipping {filename}")
                continue

            for i in range(3):
                mri_buffer = requests.get(mri_url).content

                if len(mri_buffer) > 0:
                    break

            # nothing to write
            if len(mri_buffer) == 0:
                has_failed_download = True
                continue

            webp_buffer = parse_mri_data_to_webp_buffer(mri_buffer)

            with open(filepath, "wb") as fs:
                fs.write(bytes(webp_buffer))

            ## Convert webp to png using Pillow
            webp_abspath = os.path.join(os.getcwd(), filepath)
            webp_image = Image.open(webp_abspath).convert("RGB")
            webp_image.save(f"{chapter_dirpath}{os.sep}{filename.split('.')[0]}.png")
            
            # Delete the decoded WebP to save disk space
            os.remove(filepath)

            print(f"{filepath.split('.')[0]}.png written to file")
            sleep(choice([0.1, 0.2, 0.3, 0.4, 0.5]))

        print(f"{chapter_name_secure} downloaded" + (has_failed_download and ' [fail]' or ''))


def create_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('series', help='series oid')
    parser.add_argument('-c', '--chapters', nargs='?', help='comma separated chapter oid list')
    return parser


if __name__ == '__main__':
    main()
