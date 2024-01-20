import sys
import boto3
import requests
import configparser
import argparse
from pathlib import Path
import os
import urllib.parse


def create_arg_parser():
    parser = argparse.ArgumentParser(description='CloudPhoto')
    parser.add_argument('command', type=str, help='Input command for CloudPhoto script')
    parser.add_argument('-a', '--album', type=str, help='name of the album where photos will be uploaded')
    parser.add_argument('-p', '--path', type=str, help='the name of the directory from which the photos will be uploaded', default=".")
    parser.add_argument('--photo', type=str, help='the name of the photo which needs to be deleted', default=".")
    args = parser.parse_args()
    return args


def create_ini_file(input_bucket, aws_access_key_id, aws_secret_access_key):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'region': 'ru-central1',
        'endpoint_url': 'https://storage.yandexcloud.net',
        'bucket': input_bucket,
        'aws_access_key_id': aws_access_key_id,
        'aws_secret_access_key': aws_secret_access_key
    }

    config_dir = Path.home() / ".config" / "cloudphoto"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "cloudphotorc.ini"
    with open(config_file, "w") as ini_file:
        config.write(ini_file)


def get_list_of_albums(bucket):
    objects = sorted(obj.key for obj in bucket.objects.all())
    dir_list = []
    if objects:
        for obj in objects:
            if "/" in obj and obj.split('/')[0] not in dir_list:
                dir_list.append(obj.split('/')[0])
        return dir_list
    else:
        raise RuntimeError('Photo albums not found')


def generate_index(dir_list):
    html_content = "<!DOCTYPE><html><head><title>Photo archive</title></head><body><h1>Photo archive</h1><ul>"
    for index, dir_ in enumerate(dir_list):
        html_content += f'<li><a href="album{index}.html">{dir_}</a></li>'
    html_content += "</ul></body>"
    return html_content


def generate_error():
    return '<!DOCTYPE><html><head><title>Photo archive</title></head><body><h1>Error</h1><p>Error accessing photo archive. Return to <a href="index.html">home page</a> of photo archive.</p></body></html>'


def generate_album_page(dir_, bucket):
    html_content = '<!DOCTYPE><html><head><link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/classic/galleria.classic.min.css" /><style>.galleria{ width: 960px; height: 540px; background: #000 }</style><script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script><script src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/galleria.min.js"></script><script src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/classic/galleria.classic.min.js"></script></head><body><div class="galleria">'
    for photo in bucket.objects.all():
        if dir_ in photo.key:
            html_content += f'<img src={photo.key} data-title="{photo.key.split("/")[1]}">'
    html_content += '</div><p>Go back to <a href="index.html">main page</a> of photo archive</p><script>(function() {Galleria.run(".galleria");}());</script></body></html>'
    return html_content


def init():
    aws_access_key_id = input("Введите айди ключа: ")
    aws_secret_access_key = input("Введите секретный ключ: ")
    input_bucket = input("Введите название бакета: ")

    admin_session = boto3.session.Session(aws_access_key_id=aws_access_key_id,
                                          aws_secret_access_key=aws_secret_access_key, region_name="ru-central1")
    admin_resource = admin_session.resource(service_name='s3', endpoint_url='https://storage.yandexcloud.net')

    if input_bucket not in (bucket.name for bucket in admin_resource.buckets.all()):
        admin_resource.Bucket(input_bucket).create()

    create_ini_file(input_bucket, aws_access_key_id, aws_secret_access_key)


def main():
    args = create_arg_parser()
    command = args.command
    if command == "init":
        init()
    else:
        cloudphoto = CloudPhoto(args)
        cloudphoto.choose_function(command)


class CloudPhoto:
    def __init__(self, args):
        self.functions = {"list": self.list,
                          "upload": self.upload,
                          "download": self.download,
                          "delete": self.delete,
                          "mksite": self.mksite}
        self.types = ["jpeg", "jpg"]
        self.args = args

        open(f"{Path.home()}/.config/cloudphoto/cloudphotorc.ini", "r")
        config = configparser.ConfigParser()
        config.read(f"{Path.home()}/.config/cloudphoto/cloudphotorc.ini")

        if (
                config['DEFAULT']['bucket'] and
                config['DEFAULT']['aws_access_key_id'] and
                config['DEFAULT']['aws_secret_access_key'] and
                config['DEFAULT']['region'] and
                config['DEFAULT']['endpoint_url']
        ):
            self.bucket = config['DEFAULT']['bucket']
            self.aws_access_key_id = config['DEFAULT']['aws_access_key_id']
            self.aws_secret_access_key = config['DEFAULT']['aws_secret_access_key']
            self.region = config['DEFAULT']['region']
            self.endpoint_url = config['DEFAULT']['endpoint_url']
        else:
            raise AttributeError('configuration file does not have necessary fields')

    def choose_function(self, command):
        function = self.functions.get(command)
        if function:
            function()
        else:
            raise AttributeError(f'cloudphoto does not have a definition for command <{command}>')

    def create_connection(self):
        admin_session = boto3.session.Session(aws_access_key_id=self.aws_access_key_id,
                                              aws_secret_access_key=self.aws_secret_access_key, region_name=self.region)
        admin_resource = admin_session.resource(service_name='s3', endpoint_url=self.endpoint_url)
        bucket = admin_resource.Bucket(self.bucket)
        return bucket


    def list(self):
        bucket = self.create_connection()
        try:
            if self.args.album:
                # Вывод фотографий в конкретном альбоме
                self.list_photos_in_album(bucket, self.args.album)
            else:
                # Вывод всех альбомов
                albums = get_list_of_albums(bucket)
                for album in sorted(albums):
                    print(album)
        except RuntimeError as e:
            sys.stderr.write(str(e) + '\n')
            sys.exit(1)


    def list_photos_in_album(self, bucket, album_name):
        photos = []
        for obj in bucket.objects.filter(Prefix=album_name + '/'):
            photo_name = obj.key.split('/')[-1]
            if photo_name:  # Игнорировать пустые имена
                photos.append(photo_name)
        if photos:
            for photo in sorted(photos):
                print(photo)
        else:
            sys.stderr.write(f"No photos found in album '{album_name}'\n")
            sys.exit(1)


    def upload(self):
        if not self.args.album:
            raise RuntimeError("Album name is required")

        upload_bucket = self.create_connection()
        photos_dir = self.args.path if self.args.path else '.'

        if not os.path.isdir(photos_dir):
            raise RuntimeError(f"Directory '{photos_dir}' does not exist")

        photos_uploaded = False
        for filename in os.listdir(photos_dir):
            if self.is_photo(filename):
                photo_path = os.path.join(photos_dir, filename)
                if os.path.isfile(photo_path):
                    try:
                        self.upload_photo(upload_bucket, self.args.album, filename, photo_path)
                        photos_uploaded = True
                    except Exception as e:
                        sys.stderr.write(f"Warning: Photo '{filename}' not sent: {e}\n")

        if not photos_uploaded:
            raise RuntimeError(f"No photos found in directory '{photos_dir}'")


    def is_photo(self, filename):
        return filename.lower().endswith(('.jpg', '.jpeg'))


    def upload_photo(self, bucket, album_name, filename, photo_path):
        object_key = f"{album_name}/{filename}"
        bucket.Object(object_key).upload_file(Filename=photo_path)


    def download(self):
        if not self.args.album:
            raise RuntimeError("Album name is required")

        download_bucket = self.create_connection()
        download_dir = self.args.path if self.args.path else '.'

        if not os.path.isdir(download_dir):
            os.makedirs(download_dir)

        photos_found = False
        for obj in download_bucket.objects.filter(Prefix=self.args.album + '/'):
            photo_name = obj.key.split('/')[-1]
            if photo_name:  # Игнорировать пустые имена
                self.download_photo(download_bucket, obj.key, os.path.join(download_dir, photo_name))
                photos_found = True

        if not photos_found:
            raise RuntimeError(f"No photos found in album '{self.args.album}'")


    def download_photo(self, bucket, photo_key, local_path):
        try:
            bucket.Object(photo_key).download_file(local_path)
            print(f"Downloaded '{photo_key}' to '{local_path}'")
        except Exception as e:
            raise RuntimeError(f"Error downloading photo '{photo_key}': {e}")


    def delete(self):
        if not self.args.album:
            raise RuntimeError("Album name is required")

        bucket = self.create_connection()
        deleted = False

        if self.args.photo:
            # Удаление конкретной фотографии
            photo_key = f"{self.args.album}/{self.args.photo}"
            if self.photo_exists(bucket, photo_key):
                bucket.Object(photo_key).delete()
                print(f"Photo '{self.args.photo}' deleted from album '{self.args.album}'")
                deleted = True
            else:
                raise RuntimeError(f"Photo '{self.args.photo}' not found in album '{self.args.album}'")
        else:
            # Удаление всех фотографий в альбоме и самого альбома
            for obj in bucket.objects.filter(Prefix=self.args.album + '/'):
                obj.delete()
                deleted = True
            if not deleted:
                raise RuntimeError(f"Album '{self.args.album}' not found")

    def photo_exists(self, bucket, photo_key):
        return any(obj.key == photo_key for obj in bucket.objects.filter(Prefix=photo_key))


    def mksite(self):
        bucket = self.create_connection()
        dir_list = get_list_of_albums(bucket)
        bucket.Acl().put(ACL='public-read')
        bucket_website = bucket.Website()
        index_document = {'Suffix': 'index.html'}
        error_document = {'Key': 'error.html'}
        bucket_website.put(WebsiteConfiguration={'ErrorDocument': error_document, 'IndexDocument': index_document})

        html_object = bucket.Object('index.html')
        html_object.put(Body=generate_index(dir_list), ContentType='text/html')

        html_object = bucket.Object('error.html')
        html_object.put(Body=generate_error(), ContentType='text/html')

        for index, dir_ in enumerate(dir_list):
            html_object = bucket.Object(f'album{index}.html')
            html_object.put(Body=generate_album_page(dir_, bucket), ContentType='text/html')

        print(f"https://{bucket.name}.website.yandexcloud.net")


if __name__ == '__main__':
    main()