#!/usr/bin/env python3

import argparse
import re
from datetime import datetime
from pathlib import Path

import requests
import yaml


class GithubClient:

    def __init__(self, github_url: str):
        self.gitlab_url = github_url

    def get_image_tags(self, docker_image_name: str, _tags_regex: str) -> []:
        url = f'{self.gitlab_url}/v2/repositories/{docker_image_name}/tags'
        response = requests.get(url=url)
        if response.status_code == 200:
            tag_pattern = re.compile(_tags_regex)
            tags = []
            for image_tag in response.json()['results']:
                if tag_pattern.match(image_tag['name']):
                    tags.append(
                        (image_tag['name'], datetime.strptime(image_tag["last_updated"], "%Y-%m-%dT%H:%M:%S.%f%z")))
            return tags
        return None


def generate_versioned_services(services: {}, tags_regex: str, github_client: GithubClient) -> {}:
    versioned_services = {}
    for service_name, service_config in services.items():
        image, *tag = service_config['image'].split(':')
        if tag and tag[0] == 'latest':
            latest_version = get_latest_tag(github_client.get_image_tags(image, _tags_regex=tags_regex))
            if latest_version:
                versioned_image = f'{image}:{latest_version}'
                print(f'versioned: {versioned_image}')
            else:
                print(f'version is not set using latest for {image}')
                versioned_image = f'{image}:latest'
            service_config['image'] = versioned_image

        versioned_services.update({service_name: service_config})
    return versioned_services


def get_latest_tag(image_tags: []) -> str:
    if not image_tags:
        return 'latest'
    else:
        image_tags.sort(key=lambda x: x[0], reverse=True)
        return image_tags[0][0]


def process_compose_file(compose_file: str) -> {}:
    compose_file_path = Path(compose_file)
    if compose_file_path.exists():
        with open(compose_file_path) as _file:
            docker_compose = yaml.load(_file, Loader=yaml.FullLoader)
            return docker_compose
    else:
        raise RuntimeError(f'Compose file not found: {compose_file}')


def save_compose_file(compose_dict: {}, filename: Path) -> None:
    with open(filename, 'w') as _file:
        yaml.dump(compose_dict, _file, default_flow_style=False)


def version_compose_file(compose_file_path: str, output_dir: str, gc: GithubClient, tags_regex: str):
    print(f'Processing: {compose_file_path}')
    docker_compose_dict = process_compose_file(compose_file_path)
    docker_compose_dict['services'] = generate_versioned_services(docker_compose_dict['services'],
                                                                  tags_regex=tags_regex, github_client=gc)
    compose_file_name = Path(compose_file_path).name
    output_compose_path = Path(output_dir).joinpath(compose_file_name)

    save_compose_file(docker_compose_dict, output_compose_path)


if __name__ == "__main__":
    DEFAULT_DOCKER_HUB_TAG_REGEX = '^(\d+\.)?(\d+\.)?(\*|\d+)$'
    parser = argparse.ArgumentParser(description='Compose file images version')
    parser.add_argument('--files', nargs='+', required=True, type=str)
    parser.add_argument('--output_dir', required=True, type=str)
    parser.add_argument('--tag_regex', required=False, type=str)
    parser.add_argument('--docker_registry_url', required=False, type=str, default='https://hub.docker.com')
    args = parser.parse_args()

    github_client = GithubClient(github_url=args.docker_registry_url)
    if args.tag_regex is None:
        tags_regex = DEFAULT_DOCKER_HUB_TAG_REGEX
    else:
        tags_regex = args.tag_regex

    for file in args.files:
        version_compose_file(file, gc=github_client, output_dir=args.output_dir, tags_regex=tags_regex)
