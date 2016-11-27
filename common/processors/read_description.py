"""A processor to convert the description file into a datapackage."""

import json
import logging
import arrow
import yaml

from parser import ParserError
from slugify import slugify
from datapackage_pipelines.wrapper import spew, ingest
from common.config import SOURCE_FILE, SOURCE_DATAPACKAGE_FILE, JSON_FORMAT


def load_description():
    """Return the description file as dictionary.
    """
    with open(SOURCE_FILE) as stream:
        return yaml.load(stream.read())


def save_to_file(datapackage):
    """Save the datapackage dictionary to JSON.
    """
    with open(SOURCE_DATAPACKAGE_FILE, 'w+') as stream:
        stream.write(json.dumps(datapackage, indent=4, ensure_ascii=False))


def drop_empty_properties(field):
    """Remove empty properties, as they cause the validation to fail.
    """
    return {
        key: value
        for key, value
        in field.items()
        if value
        }


def fix_date(raw_date):
    """Return an ISO-8601 date or None if parsing is impossible.
    """
    try:
        return arrow.get(raw_date).format('YYYY-MM-DD')
    except ParserError:
        logging.warning('Could not parse date = %s', raw_date)


def fix_resource(first_resource, resource):
    """Use the first resource to fill in other resources.
    """
    for property_ in first_resource.keys():
        if property_ not in resource:
            resource[property_] = first_resource[property_]
    return resource


def convert_to_name(title):
    """Return the name property given the title.
    """
    return slugify(title, separator='-').lower()


def fix_fields(fields):
    """Return a valid and clean version of the field property.
    """
    for i, field in enumerate(fields):
        new_field = drop_empty_properties(field)
        new_field['name'] = ' '.join(new_field['name'].split())
        new_field['type'] = 'string'
        fields[i] = new_field
    return fields


def create_datapackage(save_datapackage=False):
    """Convert a source description to a standard datapackage."""

    description = load_description()
    datapackage = drop_empty_properties(description)
    datapackage['name'] = convert_to_name(datapackage['title'])
    first_resource = datapackage['resources'][0]

    for resource in datapackage['resources']:
        resource = fix_resource(first_resource, resource)
        resource['name'] = convert_to_name(resource['title'])
        resource['schema']['fields'] = fix_fields(resource['schema']['fields'])

        if 'publication_date' in resource:
            raw_date = resource['publication_date']
            resource['publication_date'] = fix_date(raw_date)

    if save_datapackage:
        save_to_file(datapackage)

    datapackage_dump = json.dumps(datapackage, **JSON_FORMAT)
    logging.debug('Datapackage: \n%s', datapackage_dump)

    return datapackage


if __name__ == '__main__':
    parameters, _, _ = ingest()
    datapackage_ = create_datapackage(**parameters)
    spew(datapackage_, [[]])
